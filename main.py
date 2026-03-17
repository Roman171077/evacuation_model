from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math


# ============================================================
# 1. СПРАВОЧНИКИ
# ============================================================

# Площадь горизонтальной проекции человека, м2/чел
# Значения можно скорректировать под вашу таблицу П2.5 / П2.6
MOBILITY_GROUPS: Dict[str, Dict[str, float]] = {
    "M0": {"f": 0.10, "base_speed": 1.30},   # обычные
    "BLIND": {"f": 0.40, "base_speed": 0.80},
    "ODA_NO_SUPPORT": {"f": 0.25, "base_speed": 0.95},
    "ODA_ONE_SUPPORT": {"f": 0.20, "base_speed": 0.80},
    "ODA_TWO_SUPPORT": {"f": 0.30, "base_speed": 0.65},
    "WHEELCHAIR": {"f": 0.96, "base_speed": 0.60},
    "STRETCHER": {"f": 1.05, "base_speed": 0.50},
    "GURNEY": {"f": 1.58, "base_speed": 0.45},
}

# Коэффициенты по типу участка
SECTION_TYPE_SPEED_FACTOR: Dict[str, float] = {
    "horizontal": 1.00,
    "door": 0.95,
    "stairs_down": 0.80,
    "stairs_up": 0.60,
    "ramp": 0.75,
    "exit": 1.00,   # технический тип для "люди уже вышли"
}

# Минимальный продольный шаг между рядами в очереди
ROW_STEP_X = 0.25


# ============================================================
# 2. МОДЕЛЬ ДАННЫХ
# ============================================================

@dataclass
class Person:
    pid: int
    group: str
    section_id: str
    x: float

    # вычисляемые поля
    v: float = 0.0                     # м/с
    x_raw: float = 0.0                 # предварительная координата после шага
    finished: bool = False
    exit_time: Optional[float] = None

    @property
    def f(self) -> float:
        return MOBILITY_GROUPS[self.group]["f"]


@dataclass
class Section:
    sid: str
    section_type: str
    length: float                      # a_j
    width: float                       # b_j
    exit_width: float                  # c_j
    next_section_id: Optional[str] = None
    merge_coord: float = 0.0           # l_j
    row_capacity: Optional[int] = None

    # накопитель дробной пропускной способности
    transfer_credit: float = 0.0

    def __post_init__(self) -> None:
        if self.row_capacity is None:
            # по тексту методики ширина человека в плечах = 0.5 м
            self.row_capacity = max(1, int(self.width // 0.5))


@dataclass
class SimulationParams:
    dt: float = 0.1                    # шаг расчета, с
    winter_clothing: bool = False
    max_time: float = 3600.0           # защита от бесконечного цикла
    queue_priority_most_negative_first: bool = True


# ============================================================
# 3. ОСНОВНЫЕ ФУНКЦИИ
# ============================================================

def effective_person_area(person: Person, winter: bool) -> float:
    """Площадь проекции человека с учетом зимней одежды."""
    f = person.f
    if winter and person.group == "M0":
        # по сноске к П2.6 увеличение на 25% для обычного контингента
        f *= 1.25
    return f


def base_speed_mps(person: Person, section: Section) -> float:
    """
    Базовая скорость без учета плотности.
    Это инженерное допущение для MVP.
    """
    base = MOBILITY_GROUPS[person.group]["base_speed"]
    factor = SECTION_TYPE_SPEED_FACTOR.get(section.section_type, 1.0)
    return base * factor


def density_reduction_factor(d: float) -> float:
    """
    Понижение скорости в зависимости от плотности.
    Инженерное допущение для стартовой реализации.

    d = 0.0   -> factor ~ 1.0
    d >= 0.9  -> factor заметно падает
    d >= 1.5  -> поток почти стоит
    """
    if d <= 0:
        return 1.0
    if d < 0.3:
        return 1.0
    if d < 0.6:
        return max(0.80, 1.0 - 0.40 * (d - 0.3) / 0.3)
    if d < 1.0:
        return max(0.45, 0.80 - 0.35 * (d - 0.6) / 0.4)
    if d < 1.5:
        return max(0.15, 0.45 - 0.30 * (d - 1.0) / 0.5)
    return 0.10


def compute_person_speed(person: Person, section: Section, local_density: float) -> float:
    """
    Скорость человека, м/с.
    MVP: базовая скорость * функция снижения от плотности.
    """
    v0 = base_speed_mps(person, section)
    return max(0.01, v0 * density_reduction_factor(local_density))


def build_row_groups(sorted_people: List[Person]) -> List[List[Person]]:
    """
    Формирование групп по правилу:
    если разность координат соседних людей < 0.25 м,
    считаем, что они стоят рядом/относятся к одному локальному кластеру.
    """
    if not sorted_people:
        return []

    groups: List[List[Person]] = []
    current_group = [sorted_people[0]]

    for i in range(1, len(sorted_people)):
        prev_p = sorted_people[i - 1]
        cur_p = sorted_people[i]

        if abs(cur_p.x - prev_p.x) < ROW_STEP_X:
            current_group.append(cur_p)
        else:
            groups.append(current_group)
            current_group = [cur_p]

    groups.append(current_group)
    return groups


def compute_local_density(group_people: List[Person], section: Section, winter: bool) -> float:
    """
    Локальная плотность по формуле П7.2:
        D_i = ((n - 1) * f_avg) / (b * Δx)
    """
    n = len(group_people)
    if n < 2:
        return 0.0

    xs = [p.x for p in group_people]
    delta_x = max(xs) - min(xs)

    if delta_x <= 1e-9:
        # Практически полное наложение рядов -> очень высокая плотность
        return 10.0

    f_avg = sum(effective_person_area(p, winter) for p in group_people) / n
    return ((n - 1) * f_avg) / (section.width * delta_x)


def compute_section_density(section_people: List[Person], section: Section, winter: bool) -> float:
    """
    Плотность потока на участке.
    Берем без dt:
        D_vj = (N_j * f_avg) / (a_j * b_j)
    """
    if not section_people:
        return 0.0

    if section.length <= 1e-9 or section.width <= 1e-9:
        # Для двери длина = 0. Прямую плотность по площади не считаем.
        return 0.0

    n = len(section_people)
    f_avg = sum(effective_person_area(p, winter) for p in section_people) / n
    return (n * f_avg) / (section.length * section.width)


def compute_section_representative_speed(section_people: List[Person], section: Section, density: float) -> float:
    """
    Представительная скорость на участке для расчета интенсивности у выхода.
    Берем среднюю по людям.
    """
    if not section_people:
        return 0.0

    speeds = [compute_person_speed(p, section, density) for p in section_people]
    return sum(speeds) / len(speeds)


def compute_intensity_q_m_per_min(section_people: List[Person], section: Section, density: float) -> float:
    """
    Интенсивность q_j(t), м/мин.
    MVP:
        q = V * D
    где V в м/мин, D безразмерная.
    """
    v_mps = compute_section_representative_speed(section_people, section, density)
    v_mpm = v_mps * 60.0
    return v_mpm * density


def compute_capacity_people_per_step(section_people: List[Person], section: Section, params: SimulationParams) -> int:
    """
    Пропускная способность выхода с участка по П7.4:
        Q = q * c * dt / (f * 60)
    Используется накопитель дробной части.
    """
    if not section_people:
        return 0

    density = compute_section_density(section_people, section, params.winter_clothing)
    q = compute_intensity_q_m_per_min(section_people, section, density)

    f_avg = (
        sum(effective_person_area(p, params.winter_clothing) for p in section_people)
        / len(section_people)
    )

    if f_avg <= 1e-9:
        return 0

    q_step = (q * section.exit_width * params.dt) / (f_avg * 60.0)
    section.transfer_credit += q_step

    allowed = int(section.transfer_credit)
    section.transfer_credit -= allowed

    return max(0, allowed)


# ============================================================
# 4. СИМУЛЯТОР
# ============================================================

class EvacuationModel:
    def __init__(self,
                 sections: Dict[str, Section],
                 people: List[Person],
                 params: SimulationParams):
        self.sections = sections
        self.people = people
        self.params = params
        self.time = 0.0

    def active_people(self) -> List[Person]:
        return [p for p in self.people if not p.finished]

    def people_on_section(self, section_id: str) -> List[Person]:
        return [p for p in self.people if (not p.finished and p.section_id == section_id)]

    def all_finished(self) -> bool:
        return all(p.finished for p in self.people)

    def step(self) -> None:
        # --------------------------------------------------------
        # Шаг 1. Для каждого участка формируем локальные группы
        # и считаем предварительное движение x_raw
        # --------------------------------------------------------
        section_groups: Dict[str, List[List[Person]]] = {}

        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            section_people.sort(key=lambda p: p.x)

            groups = build_row_groups(section_people)
            section_groups[sid] = groups

            for grp in groups:
                d_local = compute_local_density(grp, section, self.params.winter_clothing)
                for p in grp:
                    p.v = compute_person_speed(p, section, d_local)
                    p.x_raw = p.x - p.v * self.params.dt

        # --------------------------------------------------------
        # Шаг 2. Для каждого участка обрабатываем переходы через выход
        # --------------------------------------------------------
        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            if not section_people:
                continue

            # Кандидаты на выход с участка
            candidates = [p for p in section_people if p.x_raw < 0]

            # Остальные остаются на участке со своими x_raw
            stay_normal = [p for p in section_people if p.x_raw >= 0]

            # Обновляем координаты тем, кто точно не дошел до границы
            for p in stay_normal:
                p.x = p.x_raw

            if not candidates:
                continue

            # Если следующего участка нет -> человек покидает здание
            if section.next_section_id is None:
                for p in candidates:
                    p.finished = True
                    p.exit_time = self.time + self.params.dt
                    p.section_id = "EXIT"
                    p.x = 0.0
                continue

            # Ограничение пропускной способности выхода
            allowed = compute_capacity_people_per_step(section_people, section, self.params)

            if self.params.queue_priority_most_negative_first:
                # Кто сильнее "перелетел" границу, того пропускаем первым
                candidates.sort(key=lambda p: p.x_raw)
            else:
                candidates.sort(key=lambda p: p.pid)

            to_pass = candidates[:allowed]
            to_wait = candidates[allowed:]

            # --- Прошедшие на следующий участок
            next_section = self.sections[section.next_section_id]

            for p in to_pass:
                p.section_id = next_section.sid
                p.x = p.x_raw + next_section.length - next_section.merge_coord

                # Если следующий участок тоже "выход наружу" с длиной 0 и без следующего участка,
                # человек еще не считается вышедшим, пока не будет обработан на следующем шаге.
                # Это корректнее для общей логики модели.

            # --- Те, кто не прошел, становятся в очередь у выхода
            for idx, p in enumerate(to_wait):
                k = idx // max(1, section.row_capacity)
                p.x = k * ROW_STEP_X + ROW_STEP_X

    def run(self, verbose: bool = True) -> Dict[str, float]:
        while (not self.all_finished()) and self.time < self.params.max_time:
            self.step()
            self.time += self.params.dt

            if verbose and int(self.time * 10) % 50 == 0:  # примерно раз в 5 секунд
                print(f"t = {self.time:.1f} c, осталось в здании: {len(self.active_people())}")

        result = {
            "total_evacuation_time_sec": max((p.exit_time or 0.0) for p in self.people),
            "finished_count": sum(1 for p in self.people if p.finished),
            "total_people": len(self.people),
        }
        return result


# ============================================================
# 5. ПРИМЕР СЦЕНАРИЯ
# ============================================================

def build_demo_scenario() -> Tuple[Dict[str, Section], List[Person], SimulationParams]:
    # Участки:
    # широкий коридор 2.0 м -> дверь 0.9 м -> наружу
    sections = {
        "corridor": Section(
            sid="corridor",
            section_type="horizontal",
            length=12.0,
            width=2.0,
            exit_width=0.9,
            next_section_id="door",
            merge_coord=0.0,
            row_capacity=4,  # floor(2.0 / 0.5)
        ),
        "door": Section(
            sid="door",
            section_type="door",
            length=0.0,            # длина пути в дверном проеме = 0
            width=0.9,
            exit_width=0.9,
            next_section_id=None,  # после двери наружу
            merge_coord=0.0,
            row_capacity=1,
        ),
    }

    # Люди:
    # две группы на одном коридоре + один колясочник
    people = [
        Person(pid=1, group="M0", section_id="corridor", x=10.0),
        Person(pid=2, group="M0", section_id="corridor", x=10.1),
        Person(pid=3, group="M0", section_id="corridor", x=10.2),
        Person(pid=4, group="M0", section_id="corridor", x=10.3),

        Person(pid=5, group="M0", section_id="corridor", x=8.0),
        Person(pid=6, group="M0", section_id="corridor", x=8.1),
        Person(pid=7, group="M0", section_id="corridor", x=8.2),

        Person(pid=8, group="WHEELCHAIR", section_id="corridor", x=6.5),
    ]

    params = SimulationParams(
        dt=0.1,
        winter_clothing=False,
        max_time=600.0,
    )

    return sections, people, params


# ============================================================
# 6. ЗАПУСК
# ============================================================

if __name__ == "__main__":
    sections, people, params = build_demo_scenario()
    model = EvacuationModel(sections, people, params)
    result = model.run(verbose=True)

    print("\nРЕЗУЛЬТАТ:")
    print(f"Общее время эвакуации: {result['total_evacuation_time_sec']:.2f} с")
    print(f"Эвакуировано: {result['finished_count']} из {result['total_people']}")

    print("\nВремя выхода по людям:")
    for p in sorted(people, key=lambda x: x.pid):
        print(
            f"Чел {p.pid:>2} | группа={p.group:<13} | "
            f"вышел={p.finished} | t_exit={p.exit_time}"
        )