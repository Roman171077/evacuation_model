from typing import Dict

# Площадь горизонтальной проекции человека, м2/чел
MOBILITY_GROUPS: Dict[str, Dict[str, float]] = {
    "M0": {"f": 0.10, "base_speed": 1.30},
    "BLIND": {"f": 0.40, "base_speed": 0.80},
    "ODA_NO_SUPPORT": {"f": 0.25, "base_speed": 0.95},
    "ODA_ONE_SUPPORT": {"f": 0.20, "base_speed": 0.80},
    "ODA_TWO_SUPPORT": {"f": 0.30, "base_speed": 0.65},
    "WHEELCHAIR": {"f": 0.96, "base_speed": 0.60},
    "STRETCHER": {"f": 1.05, "base_speed": 0.50},
    "GURNEY": {"f": 1.58, "base_speed": 0.45},
}

SECTION_TYPE_SPEED_FACTOR: Dict[str, float] = {
    "horizontal": 1.00,
    "door": 0.95,
    "stairs_down": 0.80,
    "stairs_up": 0.60,
    "ramp": 0.75,
    "exit": 1.00,
}

ROW_STEP_X = 0.25
