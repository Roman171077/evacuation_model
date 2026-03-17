from dataclasses import dataclass
from typing import Optional

from src.utils.constants import MOBILITY_GROUPS


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
