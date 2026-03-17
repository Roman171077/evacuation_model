from dataclasses import dataclass

from src.model.segment import Segment


@dataclass
class Door(Segment):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.section_type != "door":
            self.section_type = "door"
