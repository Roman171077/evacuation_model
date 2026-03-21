from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Площадь горизонтальной проекции человека, м2/чел
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


@dataclass
class Segment:
    sid: str
    section_type: str
    length: float
    width: float
    exit_width: float
    next_section_id: Optional[str] = None
    merge_coord: float = 0.0
    row_capacity: Optional[int] = None

    transfer_credit: float = 0.0

    def __post_init__(self) -> None:
        if self.row_capacity is None:
            self.row_capacity = max(1, int(self.width // 0.5))


@dataclass
class Door(Segment):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.section_type != "door":
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

    @property
    def f(self) -> float:
        return MOBILITY_GROUPS[self.group]["f"]


@dataclass
class SimulationParams:
    dt: float = 0.1
    max_time: float = 3600.0
    winter_clothing: bool = False
    queue_priority_most_negative_first: bool = True


def effective_person_area(person: Person, winter: bool) -> float:
    area = person.f
    if winter and person.group == "M0":
        area *= 1.25
    return area


def compute_local_density(group_people: List[Person], section: Segment, winter: bool) -> float:
    n_people = len(group_people)
    if n_people < 2:
        return 0.0

    x_values = [person.x for person in group_people]
    delta_x = max(x_values) - min(x_values)
    if delta_x <= 0:
        return 10.0

    f_avg = sum(effective_person_area(person, winter) for person in group_people) / n_people
    return ((n_people - 1) * f_avg) / (section.width * delta_x)


def compute_section_density(section_people: List[Person], section: Segment, winter: bool) -> float:
    if not section_people:
        return 0.0
    if section.length <= 0 or section.width <= 0:
        return 0.0

    f_avg = sum(effective_person_area(person, winter) for person in section_people) / len(section_people)
    return (len(section_people) * f_avg) / (section.length * section.width)


def base_speed_mps(person: Person, section: Segment) -> float:
    base_speed = MOBILITY_GROUPS[person.group]["base_speed"]
    speed_factor = SECTION_TYPE_SPEED_FACTOR.get(section.section_type, 1.0)
    return base_speed * speed_factor


def density_reduction_factor(density: float) -> float:
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
    section_people: List[Person], section: Segment, params: SimulationParams
) -> int:
    if not section_people:
        return 0

    density = compute_section_density(section_people, section, params.winter_clothing)
    intensity = compute_intensity_q_m_per_min(section_people, section, density)
    f_avg = sum(
        effective_person_area(person, params.winter_clothing) for person in section_people
    ) / len(section_people)
    if f_avg <= 0:
        return 0

    q_step = (intensity * section.exit_width * params.dt) / (f_avg * 60.0)
    section.transfer_credit += q_step
    allowed = int(section.transfer_credit)
    section.transfer_credit -= allowed
    return max(0, allowed)


def build_local_groups(sorted_people: List[Person]) -> List[List[Person]]:
    """Build chain-based local groups with neighbor distance < 0.25 m."""
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
        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            section_people.sort(key=lambda person: person.x)

            groups = build_local_groups(section_people)
            for group in groups:
                local_density = compute_local_density(group, section, self.params.winter_clothing)
                for person in group:
                    person.v = compute_person_speed(person, section, local_density)
                    person.x_raw = person.x - person.v * self.params.dt

        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            if not section_people:
                continue

            candidates = [person for person in section_people if person.x_raw < 0]
            stay_normal = [person for person in section_people if person.x_raw >= 0]

            for person in stay_normal:
                person.x = person.x_raw

            if not candidates:
                continue

            if section.next_section_id is None:
                for person in candidates:
                    person.finished = True
                    person.exit_time = self.time + self.params.dt
                    person.section_id = "EXIT"
                    person.x = 0.0
                continue

            allowed = compute_capacity_people_per_step(section_people, section, self.params)
            if self.params.queue_priority_most_negative_first:
                candidates.sort(key=lambda person: person.x_raw)
            else:
                candidates.sort(key=lambda person: person.pid)

            to_pass = candidates[:allowed]
            to_wait = candidates[allowed:]
            next_section = self.sections[section.next_section_id]

            for person in to_pass:
                person.section_id = next_section.sid
                person.x = person.x_raw + next_section.length - next_section.merge_coord

            for idx, person in enumerate(to_wait):
                row_number = idx // max(1, section.row_capacity)
                person.x = row_number * ROW_STEP_X + ROW_STEP_X

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
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams], verbose: bool = True
) -> Dict[str, float | Dict[int, float | None]]:
    sections, people, params = scenario
    model = EvacuationModel(sections, people, params)
    return model.run(verbose=verbose)


def build_test_case_1() -> Tuple[Dict[str, Segment], List[Person], SimulationParams]:
    sections: Dict[str, Segment] = {
        "corridor": Segment(
            sid="corridor",
            section_type="horizontal",
            length=12.0,
            width=2.0,
            exit_width=0.9,
            next_section_id="door",
            merge_coord=0.0,
            row_capacity=4,
        ),
        "door": Door(
            sid="door",
            section_type="door",
            length=0.0,
            width=0.9,
            exit_width=0.9,
            next_section_id=None,
            merge_coord=0.0,
            row_capacity=1,
        ),
    }

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

    params = SimulationParams(dt=0.1, winter_clothing=False, max_time=600.0)
    return sections, people, params


if __name__ == "__main__":
    sections, people, params = build_test_case_1()
    model = EvacuationModel(sections, people, params)
    result = model.run(verbose=True)

    print("\nРЕЗУЛЬТАТ:")
    print(f"Общее время эвакуации: {result['total_evacuation_time_sec']:.2f} с")
    print(f"Эвакуировано: {result['finished_count']} из {result['total_people']}")

    print("\nВремя выхода по людям:")
    for person in sorted(people, key=lambda item: item.pid):
        print(
            f"Чел {person.pid:>2} | группа={person.group:<13} | вышел={person.finished} | t_exit={person.exit_time}"
        )
