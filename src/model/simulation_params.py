from dataclasses import dataclass


@dataclass
class SimulationParams:
    dt: float = 0.1
    max_time: float = 3600.0
    winter_clothing: bool = False
    queue_priority_most_negative_first: bool = True
