from __future__ import annotations

from src.model import Person, Segment, SimulationParams


def build_rows_demo_case() -> tuple[dict[str, Segment], list[Person], SimulationParams]:
    sections: dict[str, Segment] = {
        "horizontal_1": Segment(
            sid="horizontal_1",
            section_type="horizontal",
            length=50.0,
            width=2.0,
            exit_width=1.2,
            next_section_id=None,
        ),
    }

    people: list[Person] = [
        Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=40.00),
        Person(pid=2, group="M0_3", section_id="horizontal_1", x=45.00),
        Person(pid=3, group="M0_3", section_id="horizontal_1", x=45.50),
        Person(pid=4, group="M0_3", section_id="horizontal_1", x=46.00),
        Person(pid=5, group="M0_3", section_id="horizontal_1", x=45.00),
        Person(pid=6, group="M0_3", section_id="horizontal_1", x=46.50),
        Person(pid=7, group="M0_3", section_id="horizontal_1", x=47.00),
        Person(pid=8, group="M0_3", section_id="horizontal_1", x=47.50),
        Person(pid=9, group="M0_3", section_id="horizontal_1", x=48.00),
        Person(pid=10, group="M0_3", section_id="horizontal_1", x=48.50),
        Person(pid=11, group="M0_3", section_id="horizontal_1", x=49.00),
        Person(pid=12, group="M0_3", section_id="horizontal_1", x=49.70),
    ]

    params = SimulationParams(dt=0.1, max_time=60.0)
    return sections, people, params
