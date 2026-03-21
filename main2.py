from __future__ import annotations

import matplotlib
matplotlib.use("TkAgg")   # важно: до pyplot

from collections import defaultdict
from dataclasses import dataclass, field
from math import hypot
from typing import DefaultDict, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.lines import Line2D


# =========================================================
# НОРМАТИВНЫЕ / ИСХОДНЫЕ ДАННЫЕ МОДЕЛИ
# =========================================================

# Площадь горизонтальной проекции человека, м2/чел
# и базовая скорость (пока упрощенно)
MOBILITY_GROUPS: Dict[str, Dict[str, float]] = {
    "M0": {"f": 0.10, "base_speed": 1.30},
    "BLIND": {"f": 0.40, "base_speed": 0.80},
    "ODA_NO_SUPPORT": {"f": 0.25, "base_speed": 0.95},
    "ODA_ONE_SUPPORT": {"f": 0.20, "base_speed": 0.80},
    "ODA_TWO_SUPPORT": {"f": 0.30, "base_speed": 0.65},
    "WHEELCHAIR": {"f": 0.96, "base_speed": 0.60},
    "STRETCHER": {"f": 1.05, "base_speed": 0.50},
    "GURNEY": {"f": 1.58, "base_speed": 0.45},
}

SECTION_TYPE_SPEED_FACTOR: Dict[str, float] = {
    "horizontal": 1.00,
    "door": 0.95,
    "stairs_down": 0.80,
    "stairs_up": 0.60,
    "ramp": 0.75,
    "exit": 1.00,
}

ROW_STEP_X = 0.25

GROUP_COLORS: Dict[str, str] = {
    "M0": "#1f77b4",
    "BLIND": "#9467bd",
    "ODA_NO_SUPPORT": "#2ca02c",
    "ODA_ONE_SUPPORT": "#ff7f0e",
    "ODA_TWO_SUPPORT": "#8c564b",
    "WHEELCHAIR": "#d62728",
    "STRETCHER": "#17becf",
    "GURNEY": "#e377c2",
}


# =========================================================
# СТРУКТУРЫ ДАННЫХ
# =========================================================

@dataclass
class Segment:
    sid: str
    section_type: str
    length: float
    width: float
    exit_width: float
    next_section_id: Optional[str] = None
    row_capacity: Optional[int] = None

    # накопление дробной пропускной способности между шагами
    transfer_credit: float = 0.0

    def __post_init__(self) -> None:
        if self.row_capacity is None:
            self.row_capacity = max(1, int(self.width // 0.5))


@dataclass
class Door(Segment):
    def __post_init__(self) -> None:
        super().__post_init__()
        self.section_type = "door"


@dataclass
class Person:
    pid: int
    group: str
    section_id: str
    x: float

    v: float = 0.0
    x_raw: float = 0.0
    finished: bool = False
    exit_time: Optional[float] = None

    initial_section_id: str = field(init=False)
    initial_x: float = field(init=False)

    def __post_init__(self) -> None:
        self.initial_section_id = self.section_id
        self.initial_x = self.x

    @property
    def f(self) -> float:
        return MOBILITY_GROUPS[self.group]["f"]


@dataclass
class SimulationParams:
    dt: float = 0.1
    max_time: float = 3600.0
    winter_clothing: bool = False
    queue_priority_most_negative_first: bool = True


@dataclass
class PersonState:
    pid: int
    group: str
    section_id: str
    x: float
    finished: bool
    exit_time: Optional[float]


@dataclass
class Snapshot:
    time: float
    people: List[PersonState]
    section_counts: Dict[str, int]
    finished_count: int
    total_people: int


@dataclass
class SectionVisual:
    start: Tuple[float, float]
    end: Tuple[float, float]


# =========================================================
# РАСЧЕТНАЯ ЧАСТЬ
# =========================================================

def effective_person_area(person: Person, winter: bool) -> float:
    area = person.f
    if winter and person.group == "M0":
        area *= 1.25
    return area


def compute_local_density(group_people: List[Person], section: Segment, winter: bool) -> float:
    """
    Локальная плотность для группы людей, расположенных цепочкой с малым расстоянием.
    """
    n_people = len(group_people)
    if n_people < 2:
        return 0.0

    x_values = [person.x for person in group_people]
    delta_x = max(x_values) - min(x_values)

    if delta_x <= 0:
        return 10.0

    f_avg = sum(effective_person_area(person, winter) for person in group_people) / n_people
    return ((n_people - 1) * f_avg) / (section.width * delta_x)


def compute_effective_occupied_length(section_people: List[Person]) -> float:
    """
    Эффективная занятая длина потока на участке.
    """
    if not section_people:
        return 0.0

    xs = sorted(person.x for person in section_people)
    span = xs[-1] - xs[0]
    return max(ROW_STEP_X, span + ROW_STEP_X)


def compute_section_density(section_people: List[Person], section: Segment, winter: bool) -> float:
    """
    Средняя плотность по реально занятой части участка.
    """
    if not section_people or section.width <= 0:
        return 0.0

    occupied_length = compute_effective_occupied_length(section_people)
    if occupied_length <= 0:
        return 0.0

    total_area = sum(effective_person_area(person, winter) for person in section_people)
    density = total_area / (occupied_length * section.width)
    return max(0.0, density)


def base_speed_mps(person: Person, section: Segment) -> float:
    base_speed = MOBILITY_GROUPS[person.group]["base_speed"]
    speed_factor = SECTION_TYPE_SPEED_FACTOR.get(section.section_type, 1.0)
    return base_speed * speed_factor


def density_reduction_factor(density: float) -> float:
    """
    Пока упрощенная кривая снижения скорости.
    Позже заменим на нормативные таблицы приложения.
    """
    if density <= 0:
        return 1.0
    if density < 0.3:
        return 1.0
    if density < 0.6:
        return max(0.80, 1.0 - 0.40 * (density - 0.3) / 0.3)
    if density < 1.0:
        return max(0.45, 0.80 - 0.35 * (density - 0.6) / 0.4)
    if density < 1.5:
        return max(0.15, 0.45 - 0.30 * (density - 1.0) / 0.5)
    return 0.10


def compute_person_speed(person: Person, section: Segment, local_density: float) -> float:
    return max(0.01, base_speed_mps(person, section) * density_reduction_factor(local_density))


def compute_intensity_q_m_per_min(section_people: List[Person], section: Segment, density: float) -> float:
    if not section_people:
        return 0.0

    representative_speed_mps = (
        sum(compute_person_speed(person, section, density) for person in section_people)
        / len(section_people)
    )
    representative_speed_mpm = representative_speed_mps * 60.0
    return representative_speed_mpm * density


def compute_capacity_people_per_step(
    section_people: List[Person],
    section: Segment,
    params: SimulationParams,
) -> int:
    """
    Максимальное число людей, которое может пройти через выход участка за текущий шаг.
    """
    if not section_people:
        return 0

    density = compute_section_density(section_people, section, params.winter_clothing)
    intensity = compute_intensity_q_m_per_min(section_people, section, density)

    f_avg = sum(
        effective_person_area(person, params.winter_clothing)
        for person in section_people
    ) / len(section_people)

    if f_avg <= 0:
        return 0

    q_step = (intensity * section.exit_width * params.dt) / (f_avg * 60.0)

    section.transfer_credit += q_step
    allowed = int(section.transfer_credit)
    section.transfer_credit -= allowed

    return max(0, allowed)


def build_local_groups(sorted_people: List[Person]) -> List[List[Person]]:
    """
    Формируем локальные группы: соседние люди, если расстояние между ними < 0.25 м.
    """
    if not sorted_people:
        return []

    groups: List[List[Person]] = []
    current_group: List[Person] = [sorted_people[0]]

    for i in range(1, len(sorted_people)):
        prev_person = sorted_people[i - 1]
        person = sorted_people[i]

        if abs(person.x - prev_person.x) < ROW_STEP_X:
            current_group.append(person)
        else:
            groups.append(current_group)
            current_group = [person]

    groups.append(current_group)
    return groups


def place_waiting_people(section: Segment, people: List[Person]) -> None:
    """
    Те, кто не прошел, выстраиваются в очередь на исходном участке.
    """
    people.sort(key=lambda person: person.pid)

    for idx, person in enumerate(people):
        row_number = idx // max(1, section.row_capacity)
        person.x = row_number * ROW_STEP_X + ROW_STEP_X


def reset_model_state(sections: Dict[str, Segment], people: List[Person]) -> None:
    for section in sections.values():
        section.transfer_credit = 0.0

    for person in people:
        person.section_id = person.initial_section_id
        person.x = person.initial_x
        person.v = 0.0
        person.x_raw = person.x
        person.finished = False
        person.exit_time = None


class EvacuationModel:
    def __init__(self, sections: Dict[str, Segment], people: List[Person], params: SimulationParams):
        self.sections = sections
        self.people = people
        self.params = params
        self.time = 0.0

    def active_people(self) -> List[Person]:
        return [person for person in self.people if not person.finished]

    def people_on_section(self, section_id: str) -> List[Person]:
        return [
            person
            for person in self.people
            if not person.finished and person.section_id == section_id
        ]

    def all_finished(self) -> bool:
        return all(person.finished for person in self.people)

    def step(self) -> None:
        # 1. Предварительно считаем свободное продвижение по каждому участку
        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            section_people.sort(key=lambda person: person.x)

            groups = build_local_groups(section_people)
            for group in groups:
                local_density = compute_local_density(group, section, self.params.winter_clothing)
                for person in group:
                    person.v = compute_person_speed(person, section, local_density)
                    person.x_raw = person.x - person.v * self.params.dt

        # 2. Формируем заявки на переход в целевые участки
        transition_requests: DefaultDict[str, List[Person]] = defaultdict(list)
        exit_requests: List[Person] = []

        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            if not section_people:
                continue

            candidates = [person for person in section_people if person.x_raw < 0]
            stay_normal = [person for person in section_people if person.x_raw >= 0]

            # кто остался на участке — просто продвигается
            for person in stay_normal:
                person.x = person.x_raw

            if not candidates:
                continue

            allowed = compute_capacity_people_per_step(section_people, section, self.params)

            if self.params.queue_priority_most_negative_first:
                candidates.sort(key=lambda person: (person.x_raw, person.pid))
            else:
                candidates.sort(key=lambda person: person.pid)

            to_pass = candidates[:allowed]
            to_wait = candidates[allowed:]

            # оставшиеся ждут на исходном участке
            place_waiting_people(section, to_wait)

            # прошедшие либо выходят наружу, либо формируют заявку в следующий участок
            if section.next_section_id is None:
                exit_requests.extend(to_pass)
            else:
                transition_requests[section.next_section_id].extend(to_pass)

        # 3. Обрабатываем окончательный выход наружу
        for person in exit_requests:
            person.finished = True
            person.exit_time = self.time + self.params.dt
            person.section_id = "EXIT"
            person.x = 0.0

        # 4. Обрабатываем честное слияние потоков в целевые участки
        for target_sid, incoming_people in transition_requests.items():
            target_section = self.sections[target_sid]

            if self.params.queue_priority_most_negative_first:
                incoming_people.sort(key=lambda person: (person.x_raw, person.pid))
            else:
                incoming_people.sort(key=lambda person: person.pid)

            for idx, person in enumerate(incoming_people):
                overshoot = abs(person.x_raw)  # сколько человек "перешел" границу исходного участка
                person.section_id = target_sid
                person.x = max(0.0, target_section.length - overshoot - idx * 1e-3)

    def run(self, verbose: bool = True) -> Dict[str, float | Dict[int, float | None]]:
        while not self.all_finished() and self.time < self.params.max_time:
            self.step()
            self.time += self.params.dt

            if verbose and int(self.time * 10) % 50 == 0:
                print(f"t = {self.time:.1f} c, осталось в здании: {len(self.active_people())}")

        return {
            "total_evacuation_time_sec": max((person.exit_time or 0.0) for person in self.people),
            "finished_count": sum(1 for person in self.people if person.finished),
            "total_people": len(self.people),
            "exit_times": {person.pid: person.exit_time for person in self.people},
        }


def run_simulation(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    verbose: bool = True,
) -> Dict[str, float | Dict[int, float | None]]:
    sections, people, params = scenario
    reset_model_state(sections, people)
    model = EvacuationModel(sections, people, params)
    return model.run(verbose=verbose)


# =========================================================
# ИСТОРИЯ СОСТОЯНИЙ / СНИМКИ
# =========================================================

def build_snapshot(model: EvacuationModel, snapshot_time: Optional[float] = None) -> Snapshot:
    people_state = [
        PersonState(
            pid=person.pid,
            group=person.group,
            section_id=person.section_id,
            x=person.x,
            finished=person.finished,
            exit_time=person.exit_time,
        )
        for person in model.people
    ]

    section_counts: Dict[str, int] = {
        sid: 0 for sid in model.sections.keys()
    }
    for person in model.people:
        if not person.finished and person.section_id in section_counts:
            section_counts[person.section_id] += 1

    return Snapshot(
        time=round(model.time if snapshot_time is None else snapshot_time, 3),
        people=people_state,
        section_counts=section_counts,
        finished_count=sum(1 for person in model.people if person.finished),
        total_people=len(model.people),
    )


def run_simulation_with_history(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    snapshot_interval: float = 1.0,
    verbose: bool = True,
) -> Tuple[Dict[str, float | Dict[int, float | None]], List[Snapshot]]:
    sections, people, params = scenario
    reset_model_state(sections, people)

    model = EvacuationModel(sections, people, params)
    history: List[Snapshot] = [build_snapshot(model, 0.0)]

    next_snapshot_time = snapshot_interval

    while not model.all_finished() and model.time < model.params.max_time:
        model.step()
        model.time += model.params.dt

        while model.time + 1e-9 >= next_snapshot_time:
            history.append(build_snapshot(model, next_snapshot_time))
            next_snapshot_time += snapshot_interval

        if verbose and int(model.time * 10) % 50 == 0:
            print(f"t = {model.time:.1f} c, осталось в здании: {len(model.active_people())}")

    result = {
        "total_evacuation_time_sec": max((person.exit_time or 0.0) for person in model.people),
        "finished_count": sum(1 for person in model.people if person.finished),
        "total_people": len(model.people),
        "exit_times": {person.pid: person.exit_time for person in model.people},
    }

    # финальный снимок, если он не попал ровно на целую секунду
    if not history or history[-1].time < model.time - 1e-9:
        history.append(build_snapshot(model, round(model.time, 3)))

    return result, history


# =========================================================
# ОПИСАНИЕ ПУТЕЙ
# =========================================================

def describe_path(sections: Dict[str, Segment], start_sid: str) -> str:
    chain = [start_sid]
    current = start_sid
    visited = {start_sid}

    while True:
        next_sid = sections[current].next_section_id
        if next_sid is None:
            chain.append("EXIT")
            break

        chain.append(next_sid)

        if next_sid in visited:
            chain.append("[LOOP]")
            break

        visited.add(next_sid)
        current = next_sid

    return " -> ".join(chain)


# =========================================================
# ТЕСТОВЫЙ СЦЕНАРИЙ
# =========================================================

def build_test_case_simple() -> tuple[dict[str, Segment], list[Person], SimulationParams]:
    sections: dict[str, Segment] = {
        "horizontal_1": Segment(
            sid="horizontal_1",
            section_type="horizontal",
            length=12.0,
            width=2.0,
            exit_width=1.2,
            next_section_id="horizontal_3",
            row_capacity=4,
        ),
        "horizontal_2": Segment(
            sid="horizontal_2",
            section_type="horizontal",
            length=10.0,
            width=1.8,
            exit_width=1.0,
            next_section_id="horizontal_3",
            row_capacity=3,
        ),
        "horizontal_3": Segment(
            sid="horizontal_3",
            section_type="horizontal",
            length=8.0,
            width=2.0,
            exit_width=1.2,
            next_section_id="door_1",
            row_capacity=4,
        ),
        "door_1": Door(
            sid="door_1",
            section_type="door",
            length=0.0,
            width=1.2,
            exit_width=1.2,
            next_section_id="stairs_down_1",
            row_capacity=2,
        ),
        "stairs_down_1": Segment(
            sid="stairs_down_1",
            section_type="stairs_down",
            length=9.0,
            width=1.35,
            exit_width=1.35,
            next_section_id="stairs_down_2",
            row_capacity=2,
        ),
        "horizontal_4": Segment(
            sid="horizontal_4",
            section_type="horizontal",
            length=7.0,
            width=1.8,
            exit_width=1.0,
            next_section_id="door_2",
            row_capacity=3,
        ),
        "door_2": Door(
            sid="door_2",
            section_type="door",
            length=0.0,
            width=1.0,
            exit_width=1.0,
            next_section_id="stairs_down_2",
            row_capacity=2,
        ),
        "stairs_down_2": Segment(
            sid="stairs_down_2",
            section_type="stairs_down",
            length=11.0,
            width=1.35,
            exit_width=1.2,
            next_section_id="door_3",
            row_capacity=2,
        ),
        "door_3": Door(
            sid="door_3",
            section_type="door",
            length=0.0,
            width=1.2,
            exit_width=1.2,
            next_section_id=None,
            row_capacity=2,
        ),
    }

    people: list[Person] = [
        Person(pid=1, group="M0", section_id="horizontal_1", x=11.0),
        Person(pid=2, group="M0", section_id="horizontal_1", x=10.6),
        Person(pid=3, group="M0", section_id="horizontal_1", x=10.2),

        Person(pid=4, group="M0", section_id="horizontal_2", x=9.0),
        Person(pid=5, group="M0", section_id="horizontal_2", x=8.6),
        Person(pid=6, group="ODA_ONE_SUPPORT", section_id="horizontal_2", x=8.0),

        Person(pid=7, group="M0", section_id="horizontal_4", x=6.5),
        Person(pid=8, group="WHEELCHAIR", section_id="horizontal_4", x=5.8),
    ]

    params = SimulationParams(
        dt=0.1,
        max_time=600.0,
        winter_clothing=False,
        queue_priority_most_negative_first=True,
    )

    return sections, people, params


# =========================================================
# СХЕМАТИЧНАЯ ВИЗУАЛИЗАЦИЯ
# =========================================================

def build_section_layout_simple() -> Dict[str, SectionVisual]:
    """
    Схема расположения участков на плоскости.
    Это не геометрия здания, а только корректная схематичная визуализация графа пути.
    """

    return {
        # два потока в horizontal_3
        "horizontal_1": SectionVisual(start=(0.0, 8.0), end=(6.0, 8.0)),
        "horizontal_2": SectionVisual(start=(0.0, 5.0), end=(6.0, 5.0)),
        "horizontal_3": SectionVisual(start=(7.2, 6.5), end=(13.2, 6.5)),

        # дверь и лестница
        "door_1": SectionVisual(start=(14.2, 6.5), end=(14.2, 6.5)),
        "stairs_down_1": SectionVisual(start=(15.0, 6.2), end=(18.2, 4.4)),

        # боковой поток в stairs_down_2
        "horizontal_4": SectionVisual(start=(10.0, 1.6), end=(15.0, 1.6)),
        "door_2": SectionVisual(start=(15.8, 1.6), end=(15.8, 1.6)),

        # общая лестница и выход
        "stairs_down_2": SectionVisual(start=(18.6, 4.0), end=(22.3, 1.8)),
        "door_3": SectionVisual(start=(23.0, 1.8), end=(23.0, 1.8)),
    }


def setup_axes(ax: plt.Axes, layout: Dict[str, SectionVisual]) -> None:
    xs: List[float] = []
    ys: List[float] = []
    for visual in layout.values():
        xs.extend([visual.start[0], visual.end[0]])
        ys.extend([visual.start[1], visual.end[1]])

    margin = 1.5
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_sections(ax: plt.Axes, sections: Dict[str, Segment], layout: Dict[str, SectionVisual]) -> None:
    # сначала рисуем сами участки
    for sid, section in sections.items():
        visual = layout[sid]
        x0, y0 = visual.start
        x1, y1 = visual.end

        if section.section_type == "horizontal":
            color = "#8c8c8c"
            lw = 6
        elif section.section_type == "stairs_down":
            color = "#4d4d4d"
            lw = 7
        elif section.section_type == "door":
            color = "#262626"
            lw = 1
        else:
            color = "#8c8c8c"
            lw = 6

        if section.length > 0:
            ax.plot([x0, x1], [y0, y1], color=color, linewidth=lw, solid_capstyle="round")

            # направление движения
            ax.annotate(
                "",
                xy=(x1, y1),
                xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", lw=1.5, color="#404040"),
            )

            label_x = (x0 + x1) / 2
            label_y = (y0 + y1) / 2 + 0.35
            ax.text(label_x, label_y, sid, ha="center", va="bottom", fontsize=9, color="#222222")
        else:
            ax.scatter([x0], [y0], s=90, marker="s", color=color, edgecolors="black", zorder=5)
            ax.text(x0, y0 + 0.35, sid, ha="center", va="bottom", fontsize=9, color="#222222")

    # затем связи между концом текущего участка и началом следующего
    for sid, section in sections.items():
        if section.next_section_id is None:
            # связь door_3 -> EXIT
            current_visual = layout[sid]
            ex_x = current_visual.end[0] + 1.0
            ex_y = current_visual.end[1]
            ax.plot(
                [current_visual.end[0], ex_x],
                [current_visual.end[1], ex_y],
                linestyle="--",
                linewidth=1.2,
                color="#6e6e6e",
            )
            ax.scatter([ex_x], [ex_y], s=120, marker="*", color="#2ca02c", zorder=6)
            ax.text(ex_x + 0.2, ex_y, "EXIT", va="center", ha="left", fontsize=10, color="#2ca02c")
            continue

        current_visual = layout[sid]
        next_visual = layout[section.next_section_id]

        x0, y0 = current_visual.end
        x1, y1 = next_visual.start

        # если это один и тот же узел, отдельно связь не рисуем
        if abs(x0 - x1) < 1e-9 and abs(y0 - y1) < 1e-9:
            continue

        ax.plot(
            [x0, x1],
            [y0, y1],
            linestyle="--",
            linewidth=1.2,
            color="#b0b0b0",
            zorder=1,
        )


def interpolate_position_on_section(section: Segment, visual: SectionVisual, local_x: float) -> Tuple[float, float]:
    """
    local_x — расстояние до конца участка.
    Визуально:
    local_x = length -> старт участка
    local_x = 0      -> конец участка
    """
    x0, y0 = visual.start
    x1, y1 = visual.end

    if section.length <= 0:
        return visual.end

    progress = (section.length - local_x) / section.length
    progress = max(0.0, min(1.0, progress))

    px = x0 + (x1 - x0) * progress
    py = y0 + (y1 - y0) * progress
    return px, py


def perpendicular_unit_vector(visual: SectionVisual) -> Tuple[float, float]:
    dx = visual.end[0] - visual.start[0]
    dy = visual.end[1] - visual.start[1]
    length = hypot(dx, dy)

    if length <= 1e-9:
        return 0.0, 1.0

    return -dy / length, dx / length


def draw_people(ax: plt.Axes, snapshot: Snapshot, sections: Dict[str, Segment], layout: Dict[str, SectionVisual]) -> None:
    people_by_section: DefaultDict[str, List[PersonState]] = defaultdict(list)

    for person in snapshot.people:
        if person.finished or person.section_id == "EXIT":
            continue
        people_by_section[person.section_id].append(person)

    for sid, people in people_by_section.items():
        section = sections[sid]
        visual = layout[sid]
        nx, ny = perpendicular_unit_vector(visual)

        # сортировка: кто ближе к выходу участка, тот первый
        people_sorted = sorted(people, key=lambda p: (p.x, p.pid))

        for idx, person in enumerate(people_sorted):
            px, py = interpolate_position_on_section(section, visual, person.x)

            # небольшой поперечный сдвиг для читаемости
            offset = (idx - (len(people_sorted) - 1) / 2.0) * 0.14
            px += nx * offset
            py += ny * offset

            color = GROUP_COLORS.get(person.group, "#1f77b4")
            ax.scatter([px], [py], s=80, color=color, edgecolors="black", linewidths=0.6, zorder=10)
            ax.text(px, py + 0.18, str(person.pid), ha="center", va="bottom", fontsize=8, color="#111111", zorder=11)


def draw_status_box(ax: plt.Axes, snapshot: Snapshot, sections: Dict[str, Segment]) -> None:
    active_count = snapshot.total_people - snapshot.finished_count

    lines = [
        f"t = {snapshot.time:.0f} c",
        f"В здании: {active_count}",
        f"Эвакуировано: {snapshot.finished_count}/{snapshot.total_people}",
        "",
        "По участкам:",
    ]

    for sid in sections.keys():
        lines.append(f"{sid}: {snapshot.section_counts.get(sid, 0)}")

    text = "\n".join(lines)

    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="white", edgecolor="#999999", alpha=0.92),
        zorder=20,
    )


def draw_group_legend(ax: plt.Axes) -> None:
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=color,
            markeredgecolor="black",
            markersize=8,
            label=group,
        )
        for group, color in GROUP_COLORS.items()
    ]
    ax.legend(handles=handles, loc="lower left", framealpha=0.92, fontsize=8)


def render_snapshot(
    ax: plt.Axes,
    snapshot: Snapshot,
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
) -> None:
    ax.clear()
    setup_axes(ax, layout)
    draw_sections(ax, sections, layout)
    draw_people(ax, snapshot, sections, layout)
    draw_status_box(ax, snapshot, sections)
    draw_group_legend(ax)
    ax.set_title("Схематичная визуализация эвакуации по участкам", fontsize=12)


def find_nearest_snapshot(history: List[Snapshot], time_sec: float) -> Snapshot:
    return min(history, key=lambda snap: abs(snap.time - time_sec))


def plot_snapshot_at_time(
    history: List[Snapshot],
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
    time_sec: float,
) -> None:
    snapshot = find_nearest_snapshot(history, time_sec)
    fig, ax = plt.subplots(figsize=(13, 8))
    render_snapshot(ax, snapshot, sections, layout)
    plt.show()


def animate_evacuation(
    history: List[Snapshot],
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
    interval_ms: int = 700,
) -> Tuple[plt.Figure, FuncAnimation]:
    fig, ax = plt.subplots(figsize=(13, 8))

    def update(frame_index: int):
        snapshot = history[frame_index]
        render_snapshot(ax, snapshot, sections, layout)

    anim = FuncAnimation(
        fig,
        update,
        frames=len(history),
        interval=interval_ms,
        repeat=False,
        blit=False,
    )

    return fig, anim


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    sections, people, params = build_test_case_simple()

    print("Путь из horizontal_1:")
    print(describe_path(sections, "horizontal_1"))

    print("\nПуть из horizontal_2:")
    print(describe_path(sections, "horizontal_2"))

    print("\nПуть из horizontal_4:")
    print(describe_path(sections, "horizontal_4"))

    result, history = run_simulation_with_history(
        (sections, people, params),
        snapshot_interval=1.0,
        verbose=True,
    )

    print("\nРЕЗУЛЬТАТ:")
    print(f"Общее время эвакуации: {result['total_evacuation_time_sec']:.2f} с")
    print(f"Эвакуировано: {result['finished_count']} из {result['total_people']}")

    print("\nВремя выхода по людям:")
    for person in sorted(people, key=lambda item: item.pid):
        print(
            f"Чел {person.pid:>2} | группа={person.group:<16} "
            f"| участок={person.section_id:<15} | вышел={person.finished} | t_exit={person.exit_time}"
        )

    layout = build_section_layout_simple()

    # 1) показать анимацию по секундам
    fig, anim = animate_evacuation(
        history=history,
        sections=sections,
        layout=layout,
        interval_ms=700,
    )

    plt.show()

    # 2) пример показа отдельного момента времени:
    # plot_snapshot_at_time(history, sections, layout, time_sec=5.0)