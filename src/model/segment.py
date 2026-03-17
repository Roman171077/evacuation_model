from dataclasses import dataclass
from typing import Optional


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
