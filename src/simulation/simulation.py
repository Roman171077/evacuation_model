from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.model.person import Person
from src.model.segment import Segment
from src.utils.constants import MOBILITY_GROUPS, ROW_STEP_X, SECTION_TYPE_SPEED_FACTOR


@dataclass
class SimulationParams:
    dt: float = 0.1
    winter_clothing: bool = False
    max_time: float = 3600.0
    queue_priority_most_negative_first: bool = True


def effective_person_area(person: Person, winter: bool) -> float:
    f = person.f
    if winter and person.group == "M0":
        f *= 1.25
    return f


def base_speed_mps(person: Person, section: Segment) -> float:
    base = MOBILITY_GROUPS[person.group]["base_speed"]
    factor = SECTION_TYPE_SPEED_FACTOR.get(section.section_type, 1.0)
    return base * factor


def density_reduction_factor(d: float) -> float:
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


def compute_person_speed(person: Person, section: Segment, local_density: float) -> float:
    v0 = base_speed_mps(person, section)
    return max(0.01, v0 * density_reduction_factor(local_density))


def build_row_groups(sorted_people: List[Person]) -> List[List[Person]]:
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


def compute_local_density(group_people: List[Person], section: Segment, winter: bool) -> float:
    n = len(group_people)
    if n < 2:
        return 0.0

    xs = [p.x for p in group_people]
    delta_x = max(xs) - min(xs)

    if delta_x <= 1e-9:
        return 10.0

    f_avg = sum(effective_person_area(p, winter) for p in group_people) / n
    return ((n - 1) * f_avg) / (section.width * delta_x)


def compute_section_density(section_people: List[Person], section: Segment, winter: bool) -> float:
    if not section_people:
        return 0.0

    if section.length <= 1e-9 or section.width <= 1e-9:
        return 0.0

    n = len(section_people)
    f_avg = sum(effective_person_area(p, winter) for p in section_people) / n
    return (n * f_avg) / (section.length * section.width)


def compute_section_representative_speed(section_people: List[Person], section: Segment, density: float) -> float:
    if not section_people:
        return 0.0

    speeds = [compute_person_speed(p, section, density) for p in section_people]
    return sum(speeds) / len(speeds)


def compute_intensity_q_m_per_min(section_people: List[Person], section: Segment, density: float) -> float:
    v_mps = compute_section_representative_speed(section_people, section, density)
    v_mpm = v_mps * 60.0
    return v_mpm * density


def compute_capacity_people_per_step(section_people: List[Person], section: Segment, params: SimulationParams) -> int:
    if not section_people:
        return 0

    density = compute_section_density(section_people, section, params.winter_clothing)
    q = compute_intensity_q_m_per_min(section_people, section, density)

    f_avg = sum(effective_person_area(p, params.winter_clothing) for p in section_people) / len(section_people)
    if f_avg <= 1e-9:
        return 0

    q_step = (q * section.exit_width * params.dt) / (f_avg * 60.0)
    section.transfer_credit += q_step

    allowed = int(section.transfer_credit)
    section.transfer_credit -= allowed

    return max(0, allowed)


class EvacuationModel:
    def __init__(self, sections: Dict[str, Segment], people: List[Person], params: SimulationParams):
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
        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            section_people.sort(key=lambda p: p.x)

            groups = build_row_groups(section_people)
            for grp in groups:
                d_local = compute_local_density(grp, section, self.params.winter_clothing)
                for p in grp:
                    p.v = compute_person_speed(p, section, d_local)
                    p.x_raw = p.x - p.v * self.params.dt

        for sid, section in self.sections.items():
            section_people = self.people_on_section(sid)
            if not section_people:
                continue

            candidates = [p for p in section_people if p.x_raw < 0]
            stay_normal = [p for p in section_people if p.x_raw >= 0]

            for p in stay_normal:
                p.x = p.x_raw

            if not candidates:
                continue

            if section.next_section_id is None:
                for p in candidates:
                    p.finished = True
                    p.exit_time = self.time + self.params.dt
                    p.section_id = "EXIT"
                    p.x = 0.0
                continue

            allowed = compute_capacity_people_per_step(section_people, section, self.params)

            if self.params.queue_priority_most_negative_first:
                candidates.sort(key=lambda p: p.x_raw)
            else:
                candidates.sort(key=lambda p: p.pid)

            to_pass = candidates[:allowed]
            to_wait = candidates[allowed:]
            next_section = self.sections[section.next_section_id]

            for p in to_pass:
                p.section_id = next_section.sid
                p.x = p.x_raw + next_section.length - next_section.merge_coord

            for idx, p in enumerate(to_wait):
                k = idx // max(1, section.row_capacity)
                p.x = k * ROW_STEP_X + ROW_STEP_X

    def run(self, verbose: bool = True) -> Dict[str, float]:
        while (not self.all_finished()) and self.time < self.params.max_time:
            self.step()
            self.time += self.params.dt

            if verbose and int(self.time * 10) % 50 == 0:
                print(f"t = {self.time:.1f} c, осталось в здании: {len(self.active_people())}")

        return {
            "total_evacuation_time_sec": max((p.exit_time or 0.0) for p in self.people),
            "finished_count": sum(1 for p in self.people if p.finished),
            "total_people": len(self.people),
        }


def run_simulation(scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams], verbose: bool = True) -> Dict[str, float]:
    sections, people, params = scenario
    model = EvacuationModel(sections, people, params)
    return model.run(verbose=verbose)
