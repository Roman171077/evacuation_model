from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.catalog import (
    get_profile,
    get_profile_area,
    get_profile_geom_width,
    get_profile_label,
    get_profile_mobility_group,
)


@dataclass
class Segment:
    sid: str
    section_type: str
    length: float
    width: float
    exit_width: float
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
class SectionVisual:
    start: Tuple[float, float]
    end: Tuple[float, float]


@dataclass
class Row:
    row_index: int
    row_left: float
    row_right: float
    used_width: float = 0.0
    people: List[Person] = field(default_factory=list)


@dataclass
class PersonVisualPlacement:
    pid: int
    section_id: str
    center: Tuple[float, float]
    length_m: float
    width_m: float
    color: str
    label: str
    row_index: int
    place_in_row: int
