from __future__ import annotations

from src.model import Person, Segment, SimulationParams


def build_test_case_simple() -> tuple[dict[str, Segment], list[Person], SimulationParams]:
    sections: dict[str, Segment] = {
        "horizontal_1": Segment(
            sid="horizontal_1",
            section_type="horizontal",
            length=12.0,
            width=2.0,
            exit_width=1.2,
            next_section_id=None,
        ),
    }

    people: list[Person] = [
        Person(
            pid=1,
            group="M0_7",
            section_id="horizontal_1",
            x=12.0,
        ),
    ]

    params = SimulationParams(
        dt=0.1,
        max_time=600.0,
    )

    return sections, people, params
