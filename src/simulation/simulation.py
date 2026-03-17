from __future__ import annotations

from typing import Dict, List, Tuple

from src.model.person import Person
from src.model.segment import Segment
from src.model.simulation_params import SimulationParams
from src.simulation.formulas import (
    compute_capacity_people_per_step,
    compute_local_density,
    compute_person_speed,
)
from src.simulation.grouping import build_local_groups
from src.utils.constants import ROW_STEP_X


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
