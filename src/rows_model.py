from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.model_input_data_component import FLOW_PROFILES, ROW_STEP_X

MOBILITY_GROUP_COLORS: Dict[str, str] = {
    "M0": "#1f77b4",
    "M1": "#9467bd",
    "M2": "#8c564b",
    "M3": "#ff7f0e",
    "M4": "#d62728",
    "special": "#2ca02c",
    "NM": "#17becf",
}

SECTION_FALLBACK_MAP: Dict[str, str] = {
    "horizontal": "horizontal",
    "door": "door",
    "stairs_down": "stairs_down",
    "stairs_up": "stairs_up",
    "ramp": "horizontal",
    "exit": "horizontal",
}


def get_profile(profile_name: str) -> Dict[str, object]:
    if profile_name not in FLOW_PROFILES:
        raise KeyError(f"Неизвестный профиль потока: {profile_name}")
    return FLOW_PROFILES[profile_name]


def get_profile_label(profile_name: str) -> str:
    return str(get_profile(profile_name).get("label", profile_name))


def get_profile_mobility_group(profile_name: str) -> str:
    return str(get_profile(profile_name).get("mobility_group", "M0"))


def get_profile_area(profile_name: str) -> float:
    value = get_profile(profile_name).get("f")
    if value is None:
        raise ValueError(f"Для профиля {profile_name} не задано f")
    return float(value)


def get_profile_geom_width(profile_name: str) -> float:
    value = get_profile(profile_name).get("a_geom")
    if value is None:
        return 0.50
    return float(value)


def get_profile_movement_params(profile_name: str, section_type: str) -> Dict[str, float]:
    profile = get_profile(profile_name)
    movement = profile.get("movement")

    if not isinstance(movement, dict):
        raise ValueError(f"Профиль {profile_name} не является самоходным")

    if section_type in movement:
        return movement[section_type]  # type: ignore[return-value]

    fallback_key = SECTION_FALLBACK_MAP.get(section_type, "horizontal")
    if fallback_key in movement:
        return movement[fallback_key]  # type: ignore[return-value]

    if "horizontal" in movement:
        return movement["horizontal"]  # type: ignore[return-value]

    raise KeyError(f"Для профиля {profile_name} нет параметров движения для участка {section_type}")


def get_profile_color(profile_name: str) -> str:
    mobility_group = get_profile_mobility_group(profile_name)
    return MOBILITY_GROUP_COLORS.get(mobility_group, "#1f77b4")


# =========================================================
# СТРУКТУРЫ ДАННЫХ
# =========================================================

@dataclass
class Segment:
    sid: str
    section_type: str
    length: float
    width: float
    next_section_id: Optional[str] = None
    merge_lj: float = 0.0
    row_capacity: Optional[int] = None


@dataclass
class Person:
    pid: int
    group: str
    section_id: str
    x: float  # расстояние до конца участка, м

    v: float = 0.0
    x_raw: float = 0.0
    finished: bool = False
    exit_time: Optional[float] = None
    row_index: int = -1
    place_in_row: int = -1
    is_row_candidate: bool = False
    can_fit_in_row: bool = False

    initial_section_id: str = field(init=False)
    initial_x: float = field(init=False)

    def __post_init__(self) -> None:
        self.initial_section_id = self.section_id
        self.initial_x = self.x

    @property
    def f(self) -> float:
        return get_profile_area(self.group)

    @property
    def mobility_group(self) -> str:
        return get_profile_mobility_group(self.group)

    @property
    def a_geom(self) -> float:
        return get_profile_geom_width(self.group)

    @property
    def c_geom(self) -> float:
        value = get_profile(self.group).get("c_geom")
        if value is None:
            return 0.50
        return float(value)

    @property
    def label(self) -> str:
        return get_profile_label(self.group)


@dataclass
class SimulationParams:
    dt: float = 0.1
    max_time: float = 3600.0


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
class Row:
    row_index: int
    row_left: float
    row_right: float
    used_width: float = 0.0
    people: List[Person] = field(default_factory=list)
    source_left: float = 0.0
    source_right: float = 0.0

    @property
    def depth(self) -> float:
        if not self.people:
            return 0.0
        return max(person.c_geom for person in self.people)

    @property
    def center_x(self) -> float:
        return (self.row_left + self.row_right) / 2.0




# =========================================================
# РАСЧЕТНАЯ ЧАСТЬ
# ЭТАП 1: свободное движение без плотности, с переходами между участками
# =========================================================

def reset_model_state(people: List[Person]) -> None:
    for person in people:
        person.section_id = person.initial_section_id
        person.x = person.initial_x
        person.v = 0.0
        person.x_raw = person.x
        person.finished = False
        person.exit_time = None
        person.row_index = -1
        person.place_in_row = -1
        person.is_row_candidate = False
        person.can_fit_in_row = False


def get_person_interval_x(person: Person) -> Tuple[float, float]:
    person_left = person.x - person.c_geom / 2.0
    person_right = person.x + person.c_geom / 2.0
    return person_left, person_right


def is_candidate_for_row(row: Row, person: Person) -> bool:
    person_left, person_right = get_person_interval_x(person)
    return (person_left < row.row_right) and (person_right > row.row_left)


def can_fit_into_row(row: Row, person: Person, section: Segment) -> bool:
    return row.used_width + person.a_geom <= section.width + 1e-9


def add_person_to_row(row: Row, person: Person) -> None:
    person_left, person_right = get_person_interval_x(person)
    person.row_index = row.row_index
    person.place_in_row = len(row.people)

    row.people.append(person)
    row.used_width += person.a_geom
    row.source_left = min(row.source_left, person_left)
    row.source_right = max(row.source_right, person_right)
    row.row_left = row.source_left
    row.row_right = row.source_right


def create_new_row(row_index: int, person: Person) -> Row:
    person_left, person_right = get_person_interval_x(person)
    row = Row(
        row_index=row_index,
        row_left=person_left,
        row_right=person_right,
        used_width=0.0,
        people=[],
        source_left=person_left,
        source_right=person_right,
    )
    add_person_to_row(row, person)
    return row


def assign_people_to_rows(people: List[Person], section: Segment) -> List[Row]:
    rows: List[Row] = []

    for person in sorted(people, key=lambda p: (p.x, p.pid)):
        person.is_row_candidate = False
        person.can_fit_in_row = False
        person.row_index = -1
        person.place_in_row = -1

        chosen_row: Optional[Row] = None
        candidate_seen = False

        for row in rows:
            candidate = is_candidate_for_row(row, person)
            if not candidate:
                continue

            candidate_seen = True
            width_ok = can_fit_into_row(row, person, section)
            if width_ok:
                chosen_row = row
                break

        person.is_row_candidate = candidate_seen
        person.can_fit_in_row = chosen_row is not None

        if chosen_row is None:
            rows.append(create_new_row(len(rows), person))
        else:
            add_person_to_row(chosen_row, person)

    return rows


def pack_rows_tightly(rows: List[Row]) -> None:
    if not rows:
        return

    rows.sort(key=lambda row: (row.source_left + row.source_right) / 2.0)

    previous_row: Optional[Row] = None
    for row_index, row in enumerate(rows):
        row.row_index = row_index
        row_half_depth = row.depth / 2.0

        if previous_row is None:
            row_center = (row.source_left + row.source_right) / 2.0
        else:
            row_center = previous_row.row_right + row_half_depth

        row.row_left = row_center - row_half_depth
        row.row_right = row_center + row_half_depth

        for place_in_row, person in enumerate(row.people):
            person.x = row_center
            person.row_index = row_index
            person.place_in_row = place_in_row

        previous_row = row


def build_rows_on_section(
    people: List[Person],
    section: Segment,
    reposition_rows: bool = False,
) -> List[Row]:
    if not people:
        return []

    rows = assign_people_to_rows(people, section)

    if reposition_rows:
        pack_rows_tightly(rows)

    return rows


def apply_row_geometry_on_section(people: List[Person], section: Segment) -> List[Row]:
    """
    Перестраивает людей в компактный поток из рядов на участке.
    Ряды упаковываются вплотную друг к другу по x без продольных зазоров.
    """
    return build_rows_on_section(people, section, reposition_rows=True)


def compute_person_row_centers(row: Row, section: Segment) -> Dict[int, float]:
    del section
    centers: Dict[int, float] = {}
    current_offset = -row.used_width / 2.0

    for person in row.people:
        center_offset = current_offset + person.a_geom / 2.0
        centers[person.pid] = center_offset
        current_offset += person.a_geom

    return centers


def compute_person_speed_stage1(person: Person, section: Segment) -> float:
    """
    На этапе 1 скорость постоянная:
    V_i_t = V0 / 60
    где V0 берется из таблицы профиля для данного типа участка.
    """
    movement_params = get_profile_movement_params(person.group, section.section_type)
    v0_mpm = float(movement_params["V0"])  # м/мин
    v_mps = v0_mpm / 60.0                  # м/с
    return max(0.01, v_mps)


def apply_row_geometry_on_sections(people: List[Person], sections: Dict[str, Segment]) -> None:
    active_people_by_section: Dict[str, List[Person]] = {sid: [] for sid in sections.keys()}

    for person in people:
        if person.finished:
            continue
        if person.section_id in active_people_by_section:
            active_people_by_section[person.section_id].append(person)

    for sid, section_people in active_people_by_section.items():
        if section_people:
            apply_row_geometry_on_section(section_people, sections[sid])


class SinglePersonSingleSegmentModel:
    def __init__(self, sections: Dict[str, Segment], people: List[Person], params: SimulationParams):
        if not sections:
            raise ValueError("В сценарии должен быть хотя бы один участок.")
        if not people:
            raise ValueError("В сценарии должен быть хотя бы один человек.")

        self.sections = sections
        self.people = people
        self.params = params
        self.time = 0.0

    def section(self) -> Segment:
        return next(iter(self.sections.values()))

    def person(self) -> Person:
        return self.people[0]

    def section_by_id(self, section_id: str) -> Segment:
        return self.sections[section_id]

    def all_finished(self) -> bool:
        return all(person.finished for person in self.people)

    def _move_person(self, person: Person) -> None:
        current_section = self.section_by_id(person.section_id)
        person.v = compute_person_speed_stage1(person, current_section)
        person.x_raw = person.x - person.v * self.params.dt

        if person.v <= 0:
            person.x = max(0.0, person.x_raw)
            return

        remaining_distance = person.v * self.params.dt
        current_x = person.x
        section = current_section

        while True:
            if remaining_distance < current_x:
                person.section_id = section.sid
                person.x = current_x - remaining_distance
                return

            distance_to_boundary = current_x
            remaining_distance -= distance_to_boundary
            dt_to_boundary = distance_to_boundary / person.v

            if not section.next_section_id:
                person.section_id = "EXIT"
                person.x = 0.0
                person.finished = True
                person.exit_time = self.time + dt_to_boundary
                return

            next_section = self.section_by_id(section.next_section_id)
            current_x = max(0.0, next_section.length - next_section.merge_lj)
            person.section_id = next_section.sid
            person.x = current_x
            section = next_section

    def step(self) -> None:
        """
        Этап без плотности:
        1) свободное движение каждого человека,
        2) переходы между соседними участками,
        3) затем геометрическое восстановление рядов на каждом участке.
        """
        for person in self.people:
            if person.finished:
                continue
            self._move_person(person)

        apply_row_geometry_on_sections(self.people, self.sections)

    def build_result(self) -> Dict[str, float | int | Dict[int, float | None]]:
        total_path_length = sum(section.length for section in self.sections.values())
        return {
            "modeled_path_length_m": total_path_length,
            "speed_m_per_s": max((person.v for person in self.people), default=0.0),
            "travel_time_sec": max(
                (
                    person.exit_time
                    for person in self.people
                    if person.exit_time is not None
                ),
                default=self.time,
            ),
            "finished_count": sum(1 for person in self.people if person.finished),
            "total_people": len(self.people),
            "exit_times": {person.pid: person.exit_time for person in self.people},
        }

    def run(self, verbose: bool = True) -> Dict[str, float | int | Dict[int, float | None]]:
        while not self.all_finished() and self.time < self.params.max_time:
            self.step()

            if verbose and not self.all_finished() and int((self.time + self.params.dt) * 10) % 50 == 0:
                active_people = [person for person in self.people if not person.finished]
                lead_person = min(active_people, key=lambda person: person.x, default=None)
                print(
                    f"t = {self.time + self.params.dt:.1f} c | "
                    f"в здании = {len(active_people)} | "
                    f"ближайший к выходу x = {lead_person.x:.3f} м | "
                    f"v = {lead_person.v:.4f} м/с"
                    if lead_person is not None
                    else f"t = {self.time + self.params.dt:.1f} c | все эвакуированы"
                )

            self.time += self.params.dt

        return self.build_result()


def run_simulation(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    verbose: bool = True,
) -> Dict[str, float | int | Dict[int, float | None]]:
    sections, people, params = scenario
    reset_model_state(people)
    model = SinglePersonSingleSegmentModel(sections, people, params)
    apply_row_geometry_on_sections(model.people, model.sections)
    return model.run(verbose=verbose)


# =========================================================
# ИСТОРИЯ СОСТОЯНИЙ / СНИМКИ
# =========================================================

def build_snapshot(model: SinglePersonSingleSegmentModel, snapshot_time: Optional[float] = None) -> Snapshot:
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

    section_counts: Dict[str, int] = {sid: 0 for sid in model.sections.keys()}

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
) -> Tuple[Dict[str, float | int | Dict[int, float | None]], List[Snapshot]]:
    sections, people, params = scenario
    reset_model_state(people)

    model = SinglePersonSingleSegmentModel(sections, people, params)
    apply_row_geometry_on_sections(model.people, model.sections)
    history: List[Snapshot] = [build_snapshot(model, 0.0)]

    next_snapshot_time = snapshot_interval

    while not model.all_finished() and model.time < model.params.max_time:
        model.step()
        model.time += model.params.dt

        while model.time + 1e-9 >= next_snapshot_time:
            history.append(build_snapshot(model, next_snapshot_time))
            next_snapshot_time += snapshot_interval

        if verbose and not model.all_finished() and int(model.time * 10) % 50 == 0:
            active_people = [person for person in model.people if not person.finished]
            lead_person = min(active_people, key=lambda person: person.x, default=None)
            print(
                f"t = {model.time:.1f} c | "
                f"в здании = {len(active_people)} | "
                f"ближайший к выходу x = {lead_person.x:.3f} м | "
                f"v = {lead_person.v:.4f} м/с"
                if lead_person is not None
                else f"t = {model.time:.1f} c | все эвакуированы"
            )

    result = model.build_result()

    if not history or history[-1].time < model.time - 1e-9:
        history.append(build_snapshot(model, round(model.time, 3)))

    return result, history


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
            next_section_id=None,
        ),
    }

    people: list[Person] = [
        Person(
            pid=1,
            group="M0_7",
            section_id="horizontal_1",
            x=12.0,  # старт в начале участка
        ),
    ]

    params = SimulationParams(
        dt=0.1,
        max_time=600.0,
    )

    return sections, people, params


def format_rows_debug(people: List[Person], section: Segment) -> List[str]:
    rows = build_rows_on_section(people, section)
    lines: List[str] = []

    for row in rows:
        row_people = ", ".join(
            f"pid={person.pid}:{person.group}:place={person.place_in_row}"
            for person in row.people
        )
        lines.append(
            " | ".join(
                [
                    f"row={row.row_index}",
                    f"used_width={row.used_width:.2f}",
                    f"x_interval=[{row.row_left:.2f}, {row.row_right:.2f}]",
                    row_people,
                ]
            )
        )

    return lines
