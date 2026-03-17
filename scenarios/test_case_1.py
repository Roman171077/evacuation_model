from typing import Dict, List, Tuple

from src.model.door import Door
from src.model.person import Person
from src.model.segment import Segment
from src.simulation.simulation import SimulationParams


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
