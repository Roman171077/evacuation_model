from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

# =========================================================
# НОРМАТИВНЫЕ / ИСХОДНЫЕ ДАННЫЕ МОДЕЛИ
# ОСТАВЛЕНЫ КАК У ТЕБЯ
# =========================================================

ROW_STEP_X = 0.25  # сохранено, хотя на этапе 1 не используется
FLOW_ROW_GAP_THRESHOLD = 0.5

FLOW_PROFILES: Dict[str, Dict[str, object]] = {
    # ---------------------------
    # M0
    # ---------------------------
    "M0_1": {
        "label": "Дети и подростки (7–18 лет)",
        "mobility_group": "M0",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.22,
        "c_geom": 0.35,
        "f": 0.06,
        "movement": {
            "horizontal":  {"V0": 92.6,  "ai": 0.284, "D0": 0.75},
            "door":        {"V0": 92.6,  "ai": 0.350, "D0": 1.20},
            "stairs_down": {"V0": 92.4,  "ai": 0.338, "D0": 0.94},
            "stairs_up":   {"V0": 65.9,  "ai": 0.289, "D0": 0.84},
            "ramp_down": {"V0": 92.6,  "ai": 0.284, "D0": 0.75},
            "ramp_up":   {"V0": 92.6,  "ai": 0.284, "D0": 0.75},
        },
    },
    "M0_2": {
        "label": "Молодежь (18–25 лет)",
        "mobility_group": "M0",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.26,
        "c_geom": 0.43,
        "f": 0.09,
        "movement": {
            "horizontal":  {"V0": 120.0, "ai": 0.308, "D0": 0.72},
            "door":        {"V0": 120.0, "ai": 0.308, "D0": 0.53},
            "stairs_down": {"V0": 129.0, "ai": 0.353, "D0": 0.58},
            "stairs_up":   {"V0": 76.8,  "ai": 0.305, "D0": 0.67},
            "ramp_down": {"V0": 120.0, "ai": 0.308, "D0": 0.72},
            "ramp_up":   {"V0": 120.0, "ai": 0.308, "D0": 0.72},
        },
    },
    "M0_3": {
        "label": "Люди трудоспособного возраста (18–60 лет)",
        "mobility_group": "M0",
        "geometry_source": "normative_P2.5",
        "a_geom": 0.28,
        "c_geom": 0.46,
        "f": 0.10,
        "movement": {
            "horizontal":  {"V0": 100.0, "ai": 0.295, "D0": 0.51},
            "door":        {"V0": 100.0, "ai": 0.295, "D0": 0.65},
            "stairs_down": {"V0": 100.0, "ai": 0.400, "D0": 0.89},
            "stairs_up":   {"V0": 60.0,  "ai": 0.305, "D0": 0.67},
            "ramp_down": {"V0": 100.0, "ai": 0.295, "D0": 0.51},
            "ramp_up":   {"V0": 100.0, "ai": 0.295, "D0": 0.51},
        },
    },
    "M0_4": {
        "label": "Дошкольники + школьники + люди трудоспособного возраста",
        "mobility_group": "M0",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.26,
        "c_geom": 0.43,
        "f": 0.09,
        "movement": {
            "horizontal":  {"V0": 93.8,  "ai": 0.353, "D0": 0.56},
            "door":        {"V0": 93.8,  "ai": 0.371, "D0": 0.64},
            "stairs_down": {"V0": 93.8,  "ai": 0.394, "D0": 0.75},
            "stairs_up":   {"V0": 57.5,  "ai": 0.375, "D0": 0.66},
            "ramp_down": {"V0": 93.8,  "ai": 0.353, "D0": 0.56},
            "ramp_up":   {"V0": 93.8,  "ai": 0.353, "D0": 0.56},
        },
    },
    "M0_5": {
        "label": "Дошкольники + школьники + трудоспособные + активные пожилые",
        "mobility_group": "M0",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.31,
        "c_geom": 0.50,
        "f": 0.121,
        "movement": {
            "horizontal":  {"V0": 91.4,  "ai": 0.357, "D0": 0.58},
            "door":        {"V0": 91.8,  "ai": 0.366, "D0": 0.62},
            "stairs_down": {"V0": 90.0,  "ai": 0.410, "D0": 0.83},
            "stairs_up":   {"V0": 56.1,  "ai": 0.379, "D0": 0.68},
            "ramp_down": {"V0": 91.4,  "ai": 0.357, "D0": 0.58},
            "ramp_up":   {"V0": 91.4,  "ai": 0.357, "D0": 0.58},
        },
    },
    "M0_6": {
        "label": "Люди трудоспособного возраста + активные пожилые",
        "mobility_group": "M0",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.31,
        "c_geom": 0.52,
        "f": 0.127,
        "movement": {
            "horizontal":  {"V0": 69.6,  "ai": 0.385, "D0": 0.71},
            "door":        {"V0": 72.1,  "ai": 0.318, "D0": 0.41},
            "stairs_down": {"V0": 61.7,  "ai": 0.394, "D0": 0.75},
            "stairs_up":   {"V0": 43.5,  "ai": 0.400, "D0": 0.78},
            "ramp_down": {"V0": 69.6,  "ai": 0.385, "D0": 0.71},
            "ramp_up":   {"V0": 69.6,  "ai": 0.385, "D0": 0.71},
        },
    },
    "M0_7": {
        "label": "Люди с грудными детьми + дошкольники + школьники + трудоспособные + активные пожилые",
        "mobility_group": "M0",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.31,
        "c_geom": 0.50,
        "f": 0.121,
        "movement": {
            "horizontal":  {"V0": 45.02, "ai": 0.425, "D0": 0.86},
            "door":        {"V0": 50.0,  "ai": 0.253, "D0": 0.18},
            "stairs_down": {"V0": 30.0,  "ai": 0.367, "D0": 0.62},
            "stairs_up":   {"V0": 30.0,  "ai": 0.414, "D0": 0.88},
            "ramp_down": {"V0": 45.02, "ai": 0.425, "D0": 0.86},
            "ramp_up":   {"V0": 45.02, "ai": 0.425, "D0": 0.86},
        },
    },

    # ---------------------------
    # M1
    # ---------------------------
    "M1_ELDERLY_60_PLUS": {
        "label": "Пожилые люди (старше 60 лет)",
        "mobility_group": "M1",
        "separate_by_default": False,
        "geometry_source": "assumption_same_as_base_m0",
        "a_geom": 0.28,
        "c_geom": 0.46,
        "f": 0.10,
        "movement": {
            "horizontal":  {"V0": 80.0,  "ai": 0.295, "D0": 0.51},
            "door":        {"V0": 80.0,  "ai": 0.295, "D0": 0.65},
            "stairs_down": {"V0": 70.0,  "ai": 0.400, "D0": 0.89},
            "stairs_up":   {"V0": 60.0,  "ai": 0.305, "D0": 0.67},
            "ramp_down": {"V0": 80.0,  "ai": 0.295, "D0": 0.51},
            "ramp_up":   {"V0": 80.0,  "ai": 0.295, "D0": 0.51},
        },
    },
    "M1_PRESCHOOL": {
        "label": "Дошкольники (дети 3–7 лет)",
        "mobility_group": "M1",
        "separate_by_default": False,
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.15,
        "c_geom": 0.25,
        "f": 0.03,
        "movement": {
            "horizontal":  {"V0": 60.0,  "ai": 0.275, "D0": 0.78},
            "door":        {"V0": 60.0,  "ai": 0.350, "D0": 1.20},
            "stairs_down": {"V0": 47.0,  "ai": 0.190, "D0": 0.64},
            "stairs_up":   {"V0": 47.0,  "ai": 0.275, "D0": 0.76},
            "ramp_down": {"V0": 60.0,  "ai": 0.275, "D0": 0.78},
            "ramp_up":   {"V0": 60.0,  "ai": 0.275, "D0": 0.78},
        },
    },
    "M1_DEAF": {
        "label": "Глухие и слабослышащие люди",
        "mobility_group": "M1",
        "separate_by_default": False,
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.31,
        "c_geom": 0.51,
        "f": 0.125,
        "movement": {
            "horizontal":  {"V0": 82.0,  "ai": 0.301, "D0": 0.58},
            "door":        {"V0": 82.0,  "ai": 0.328, "D0": 0.73},
            "stairs_down": {"V0": 82.0,  "ai": 0.380, "D0": 0.91},
            "stairs_up":   {"V0": 54.0,  "ai": 0.344, "D0": 0.72},
            "ramp_down": {"V0": 82.0,  "ai": 0.301, "D0": 0.58},
            "ramp_up":   {"V0": 82.0,  "ai": 0.301, "D0": 0.58},
        },
    },
    "M1_PREGNANT": {
        "label": "Беременные женщины",
        "mobility_group": "M1",
        "separate_by_default": False,
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.34,
        "c_geom": 0.56,
        "f": 0.15,
        "movement": {
            "horizontal":  {"V0": 56.42, "ai": 0.404, "D0": 0.991},
            "door":        {"V0": 49.47, "ai": 0.427, "D0": 1.033},
            "stairs_down": {"V0": 42.35, "ai": 0.336, "D0": 0.786},
            "stairs_up":   {"V0": 31.25, "ai": 0.411, "D0": 1.312},
            "ramp_down": {"V0": 56.42, "ai": 0.404, "D0": 0.991},
            "ramp_up":   {"V0": 56.42, "ai": 0.404, "D0": 0.991},
        },
    },

    # ---------------------------
    # M2
    # ---------------------------
    "M2_FRAIL_ELDERLY": {
        "label": "Пожилые немощные люди",
        "mobility_group": "M2",
        "geometry_source": "assumption_proxy_from_P2.5_one_support",
        "a_geom": 0.50,
        "c_geom": 0.65,
        "f": 0.20,
        "movement": {
            "horizontal":  {"V0": 25.0, "ai": 0.428, "D0": 0.96},
            "door":        {"V0": 20.0, "ai": 0.456, "D0": 1.02},
            "stairs_down": {"V0": 20.0, "ai": 0.505, "D0": 1.26},
            "stairs_up":   {"V0": 20.0, "ai": 0.338, "D0": 0.56},
            "ramp_down":   {"V0": 25.0, "ai": 0.353, "D0": 0.58},
            "ramp_up":     {"V0": 15.0, "ai": 0.368, "D0": 0.72},
        },
    },
    "M2_BLIND": {
        "label": "Слепые и слабовидящие люди",
        "mobility_group": "M2",
        "geometry_source": "normative_P2.5",
        "a_geom": 0.72,
        "c_geom": 0.82,
        "f": 0.40,
        "movement": {
            "horizontal":  {"V0": 26.0, "ai": 0.371, "D0": 0.73},
            "door":        {"V0": 17.0, "ai": 0.271, "D0": 0.77},
            "stairs_down": {"V0": 21.0, "ai": 0.519, "D0": 0.97},
            "stairs_up":   {"V0": 18.0, "ai": 0.387, "D0": 0.82},
            "ramp_down": {"V0": 26.0, "ai": 0.371, "D0": 0.73},
            "ramp_up":   {"V0": 26.0, "ai": 0.371, "D0": 0.73},
        },
    },

    # ---------------------------
    # M3
    # ---------------------------
    "M3_ODA": {
        "label": "Люди трудоспособного возраста с поражением ОДА",
        "mobility_group": "M3",
        "geometry_source": "agreed_simplification_two_supports",
        "a_geom": 0.50,
        "c_geom": 0.90,
        "f": 0.30,
        "movement": {
            "horizontal":  {"V0": 44.0, "ai": 0.414, "D0": 0.77},
            "door":        {"V0": 38.0, "ai": 0.345, "D0": 0.57},
            "stairs_down": {"V0": 24.0, "ai": 0.422, "D0": 0.96},
            "stairs_up":   {"V0": 14.0, "ai": 0.313, "D0": 0.74},
            "ramp_down": {"V0": 44.0, "ai": 0.414, "D0": 0.77},
            "ramp_up":   {"V0": 44.0, "ai": 0.414, "D0": 0.77},
        },
    },

    # ---------------------------
    # M4
    # ---------------------------
    "M4_WHEELCHAIR": {
        "label": "Инвалиды на креслах-колясках",
        "mobility_group": "M4",
        "geometry_source": "normative_P2.5",
        "a_geom": 0.80,
        "c_geom": 1.20,
        "f": 0.96,
        "movement": {
            "horizontal": {"V0": 60.0, "ai": 0.400, "D0": 0.141},
            "ramp_down":  {"V0": 60.0, "ai": 0.400, "D0": 0.141},
            "ramp_up":    {"V0": 40.0, "ai": 0.420, "D0": 0.156},
            "stairs_down": {"V0": 0.0, "ai": 0.400, "D0": 0.141},
            "stairs_up":   {"V0": 0.0, "ai": 0.400, "D0": 0.141},
        },
    },

    # ---------------------------
    # special
    # ---------------------------
    "DISABLED_CHILD": {
        "label": "Дети с ограниченными возможностями",
        "mobility_group": "special",
        "geometry_source": "assumption_scaled_from_base_m0",
        "a_geom": 0.34,
        "c_geom": 0.56,
        "f": 0.15,
        "movement": {
            "horizontal":  {"V0": 51.0, "ai": 0.290, "D0": 0.60},
            "door":        {"V0": 47.0, "ai": 0.300, "D0": 0.67},
            "stairs_down": {"V0": 23.0, "ai": 0.210, "D0": 0.63},
            "stairs_up":   {"V0": 20.0, "ai": 0.300, "D0": 0.69},
            "ramp_down": {"V0": 51.0, "ai": 0.290, "D0": 0.60},
            "ramp_up":   {"V0": 51.0, "ai": 0.290, "D0": 0.60},
        },
    },

    # ---------------------------
    # NM / NT / NO
    # ---------------------------
    "NM_STRETCHER": {
        "label": "Немобильные, транспортируемые на носилках",
        "mobility_group": "NM",
        "geometry_source": "normative_P2.5",
        "a_geom": 0.50,
        "c_geom": 2.10,
        "f": 1.05,
        "movement_model": "transport_by_staff",
    },
    "NM_GURNEY": {
        "label": "Немобильные, транспортируемые на каталках",
        "mobility_group": "NM",
        "geometry_source": "normative_P2.5",
        "a_geom": 0.75,
        "c_geom": 2.10,
        "f": 1.58,
        "movement_model": "transport_by_staff",
    },
}

MOBILITY_GROUP_COLORS: Dict[str, str] = {
    "M0": "#1f77b4",
    "M1": "#9467bd",
    "M2": "#8c564b",
    "M3": "#ff7f0e",
    "M4": "#d62728",
    "special": "#2ca02c",
    "NM": "#17becf",
}

SECTION_FALLBACK_MAP: Dict[str, str] = {
    "horizontal": "horizontal",
    "door": "door",
    "stairs_down": "stairs_down",
    "stairs_up": "stairs_up",
    "ramp": "horizontal",
    "exit": "horizontal",
}

DEBUG_TRACE_PID = 1


def get_profile(profile_name: str) -> Dict[str, object]:
    if profile_name not in FLOW_PROFILES:
        raise KeyError(f"Неизвестный профиль потока: {profile_name}")
    return FLOW_PROFILES[profile_name]


def get_profile_label(profile_name: str) -> str:
    return str(get_profile(profile_name).get("label", profile_name))


def get_profile_mobility_group(profile_name: str) -> str:
    return str(get_profile(profile_name).get("mobility_group", "M0"))


def get_profile_area(profile_name: str) -> float:
    value = get_profile(profile_name).get("f")
    if value is None:
        raise ValueError(f"Для профиля {profile_name} не задано f")
    return float(value)


def get_profile_geom_width(profile_name: str) -> float:
    value = get_profile(profile_name).get("a_geom")
    if value is None:
        return 0.50
    return float(value)


def get_profile_movement_params(profile_name: str, section_type: str) -> Dict[str, float]:
    profile = get_profile(profile_name)
    movement = profile.get("movement")

    if not isinstance(movement, dict):
        raise ValueError(f"Профиль {profile_name} не является самоходным")

    if section_type in movement:
        return movement[section_type]  # type: ignore[return-value]

    fallback_key = SECTION_FALLBACK_MAP.get(section_type, "horizontal")
    if fallback_key in movement:
        return movement[fallback_key]  # type: ignore[return-value]

    if "horizontal" in movement:
        return movement["horizontal"]  # type: ignore[return-value]

    raise KeyError(f"Для профиля {profile_name} нет параметров движения для участка {section_type}")


def resolve_section_type_for_profile(profile_name: str, section_type: str) -> str:
    profile = get_profile(profile_name)
    movement = profile.get("movement")
    if not isinstance(movement, dict):
        return section_type

    if section_type in movement:
        return section_type

    fallback_key = SECTION_FALLBACK_MAP.get(section_type, "horizontal")
    if fallback_key in movement:
        return fallback_key

    if "horizontal" in movement:
        return "horizontal"

    return section_type


def get_profile_color(profile_name: str) -> str:
    mobility_group = get_profile_mobility_group(profile_name)
    return MOBILITY_GROUP_COLORS.get(mobility_group, "#1f77b4")


# =========================================================
# СТРУКТУРЫ ДАННЫХ
# =========================================================

@dataclass
class Segment:
    sid: str
    section_type: str
    length: float
    width: float
    exit_width_cj: float | None = None
    next_section_id: Optional[str] = None
    next_by_group: Dict[str, str] = field(default_factory=dict)
    next_default: Optional[str] = None
    merge_lj: float = 0.0
    row_capacity: Optional[int] = None

    def __post_init__(self) -> None:
        if self.next_default is None and self.next_section_id is not None:
            self.next_default = self.next_section_id
        if self.next_section_id is None:
            self.next_section_id = self.next_default

    def resolve_next_section_id(self, group: str) -> Optional[str]:
        if group in self.next_by_group:
            return self.next_by_group[group]
        return self.next_default

    def outgoing_section_ids(self) -> List[str]:
        ordered: List[str] = []
        seen: set[str] = set()

        for sid in self.next_by_group.values():
            if sid and sid not in seen:
                seen.add(sid)
                ordered.append(sid)

        if self.next_default and self.next_default not in seen:
            ordered.append(self.next_default)

        return ordered


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
    flow_index: int = -1
    place_in_flow: int = -1
    is_alone_on_section: bool = False
    is_single_in_row: bool = False
    is_in_flow: bool = False
    flow_member_count: int = 0
    flow_start_x: float = 0.0
    flow_end_x: float = 0.0
    flow_delta_x: float = 0.0
    flow_density: float = 0.0
    local_density: float = 0.0
    other_flow_people_ids: List[int] = field(default_factory=list)
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
    dt: float = 1.0
    max_time: float = 3600.0


@dataclass
class PersonState:
    pid: int
    group: str
    section_id: str
    x: float
    v: float = 0.0
    speed_mps: float = 0.0
    v0_mpm: float = 0.0
    d0: float = 0.0
    ai: float = 0.0
    m: float = 1.0
    section_type: str = ""
    speed_section_type: str = ""
    row_index: int = -1
    place_in_row: int = -1
    flow_index: int = -1
    place_in_flow: int = -1
    flow_start_x: float = 0.0
    flow_end_x: float = 0.0
    flow_delta_x: float = 0.0
    flow_density: float = 0.0
    local_density: float = 0.0
    other_flow_people_ids: List[int] = field(default_factory=list)
    finished: bool = False
    exit_time: Optional[float] = None


@dataclass
class Snapshot:
    time: float
    people: List[PersonState]
    section_counts: Dict[str, int]
    section_flow_density: Dict[str, float] = field(default_factory=dict)
    section_intensity_qj: Dict[str, float] = field(default_factory=dict)
    section_capacity_qj: Dict[str, int] = field(default_factory=dict)
    finished_count: int = 0
    total_people: int = 0



@dataclass
class Row:
    row_index: int
    row_left: float
    row_right: float
    used_width: float = 0.0
    people: List[Person] = field(default_factory=list)
    longitudinal_shift: float = 0.0


@dataclass
class Flow:
    flow_index: int
    section_id: str
    rows: List[Row] = field(default_factory=list)
    people: List[Person] = field(default_factory=list)
    start_x: float = 0.0
    end_x: float = 0.0
    delta_x: float = 0.0




# =========================================================
# РАСЧЕТНАЯ ЧАСТЬ
# ЭТАП 1: свободное движение без плотности, с переходами между участками
# =========================================================

def reset_person_position_state(person: Person) -> None:
    person.row_index = -1
    person.place_in_row = -1
    person.flow_index = -1
    person.place_in_flow = -1
    person.is_alone_on_section = False
    person.is_single_in_row = False
    person.is_in_flow = False
    person.flow_member_count = 0
    person.flow_start_x = 0.0
    person.flow_end_x = 0.0
    person.flow_delta_x = 0.0
    person.flow_density = 0.0
    person.local_density = 0.0
    person.other_flow_people_ids = []
    person.is_row_candidate = False
    person.can_fit_in_row = False


def reset_model_state(people: List[Person]) -> None:
    for person in people:
        person.section_id = person.initial_section_id
        person.x = person.initial_x
        person.v = 0.0
        person.x_raw = person.x
        person.finished = False
        person.exit_time = None
        reset_person_position_state(person)


def validate_initial_same_coordinate_width(
    people: List[Person],
    sections: Dict[str, Segment],
) -> Optional[str]:
    """
    Проверка перед стартом расчета:
    если у людей с одинаковой координатой x на одном участке суммарная ширина a_geom
    превышает ширину участка, расчет не выполняется.
    """
    grouped: Dict[Tuple[str, float], List[Person]] = {}
    for person in people:
        key = (person.section_id, round(person.x, 6))
        grouped.setdefault(key, []).append(person)

    violations: List[str] = []
    for (section_id, x_coord), group in grouped.items():
        if len(group) <= 1:
            continue
        section = sections.get(section_id)
        if section is None:
            continue
        total_width = sum(current.a_geom for current in group)
        if total_width <= section.width + 1e-9:
            continue
        people_ids = ", ".join(str(current.pid) for current in sorted(group, key=lambda current: current.pid))
        violations.append(
            f"участок={section_id}, x={x_coord:.3f}, сумма a_geom={total_width:.3f} > "
            f"ширина участка={section.width:.3f}, pid=[{people_ids}]"
        )

    if not violations:
        return None
    return "ПРЕДУПРЕЖДЕНИЕ: расчет остановлен. Конфликт ширины на старте:\n" + "\n".join(violations)


def get_person_interval_x(person: Person) -> Tuple[float, float]:
    person_left = person.x - person.c_geom / 2.0
    person_right = person.x + person.c_geom / 2.0
    return person_left, person_right


def is_candidate_for_row(row: Row, person: Person) -> bool:
    person_left, person_right = get_person_interval_x(person)
    return (person_left < row.row_right) and (person_right > row.row_left)


def can_fit_into_row(row: Row, person: Person, section: Segment) -> bool:
    return row.used_width + person.a_geom <= section.width + 1e-9


def add_person_to_row(row: Row, person: Person) -> None:
    person_left, person_right = get_person_interval_x(person)
    person.row_index = row.row_index
    person.place_in_row = len(row.people)

    row.people.append(person)
    row.used_width += person.a_geom
    row.row_left = min(row.row_left, person_left)
    row.row_right = max(row.row_right, person_right)


def create_new_row(row_index: int, person: Person) -> Row:
    person_left, person_right = get_person_interval_x(person)
    row = Row(
        row_index=row_index,
        row_left=person_left,
        row_right=person_right,
        used_width=0.0,
        people=[],
        longitudinal_shift=0.0,
    )
    add_person_to_row(row, person)
    return row


def apply_longitudinal_row_offsets(rows: List[Row]) -> None:
    if not rows:
        return

    rows_sorted = sorted(rows, key=lambda row: (get_row_mean_x(row), row.row_index))
    previous_row_right: Optional[float] = None

    for new_row_index, row in enumerate(rows_sorted):
        row.row_index = new_row_index
        for place_in_row, person in enumerate(row.people):
            person.row_index = new_row_index
            person.place_in_row = place_in_row

        original_left = min(person.x - person.c_geom / 2.0 for person in row.people)
        original_right = max(person.x + person.c_geom / 2.0 for person in row.people)
        target_left = original_left

        if previous_row_right is not None:
            target_left = max(original_left, previous_row_right + ROW_STEP_X)

        row.longitudinal_shift = target_left - original_left

        if row.longitudinal_shift > 0.0:
            for person in row.people:
                person.x += row.longitudinal_shift

        row.row_left = min(person.x - person.c_geom / 2.0 for person in row.people)
        row.row_right = max(person.x + person.c_geom / 2.0 for person in row.people)
        previous_row_right = row.row_right

    rows[:] = rows_sorted


def build_rows_on_section(
    people: List[Person],
    section: Segment,
    reposition_rows: bool = False,
) -> List[Row]:
    rows: List[Row] = []

    ordered_people = sorted(people, key=lambda person: (person.x, person.pid))
    for person in ordered_people:
        person.is_row_candidate = False
        person.can_fit_in_row = False

        assigned = False
        for row in rows:
            if not is_candidate_for_row(row, person):
                continue

            person.is_row_candidate = True
            if can_fit_into_row(row, person, section):
                person.can_fit_in_row = True
                add_person_to_row(row, person)
                assigned = True
                break

        if assigned:
            continue

        new_row = create_new_row(len(rows), person)
        rows.append(new_row)

    if reposition_rows:
        apply_longitudinal_row_offsets(rows)

    return rows


def apply_row_geometry_on_section(people: List[Person], section: Segment) -> List[Row]:
    rows = build_rows_on_section(people, section, reposition_rows=False)
    apply_longitudinal_row_offsets(rows)
    return rows


def get_row_mean_x(row: Row) -> float:
    return sum(person.x for person in row.people) / len(row.people)


def rows_are_consecutive(front_row: Row, back_row: Row, threshold: float = FLOW_ROW_GAP_THRESHOLD) -> bool:
    longitudinal_gap = back_row.row_left - front_row.row_right
    return longitudinal_gap <= threshold + 1e-9


def build_flows_on_section(rows: List[Row], section: Segment) -> List[Flow]:
    del section
    if not rows:
        return []

    ordered_rows = sorted(rows, key=lambda row: (get_row_mean_x(row), row.row_index))
    projected_x_by_pid: Dict[int, float] = {}
    ordered_people: List[Person] = []
    for row in ordered_rows:
        for person in row.people:
            ordered_people.append(person)
            projected_x_by_pid[person.pid] = person.x - row.longitudinal_shift
    ordered_people.sort(key=lambda person: (projected_x_by_pid.get(person.pid, person.x), person.pid))

    if len(ordered_people) < 2:
        return []

    row_by_index = {row.row_index: row for row in rows}
    flows: List[Flow] = []
    current_people: List[Person] = [ordered_people[0]]

    def flush_current_flow() -> None:
        if len(current_people) < 2:
            return

        ordered_by_projected_x = sorted(
            current_people,
            key=lambda person: (projected_x_by_pid.get(person.pid, person.x), person.pid),
        )
        start_x = projected_x_by_pid.get(ordered_by_projected_x[0].pid, ordered_by_projected_x[0].x)
        end_x = projected_x_by_pid.get(ordered_by_projected_x[-1].pid, ordered_by_projected_x[-1].x)
        unique_row_indices = sorted({person.row_index for person in current_people if person.row_index in row_by_index})
        unique_rows = [row_by_index[row_index] for row_index in unique_row_indices]
        flows.append(
            Flow(
                flow_index=len(flows),
                section_id=current_people[0].section_id,
                rows=unique_rows,
                people=ordered_by_projected_x,
                start_x=start_x,
                end_x=end_x,
                delta_x=end_x - start_x,
            )
        )

    for person in ordered_people[1:]:
        gap = projected_x_by_pid.get(person.pid, person.x) - projected_x_by_pid.get(current_people[-1].pid, current_people[-1].x)
        if gap <= FLOW_ROW_GAP_THRESHOLD + 1e-9:
            current_people.append(person)
            continue

        flush_current_flow()
        current_people = [person]

    flush_current_flow()

    return flows


def update_person_position_state(
    section_people: List[Person],
    rows: List[Row],
    flows: List[Flow],
) -> None:
    is_single_person_on_section = len(section_people) == 1
    for person in section_people:
        person.row_index = -1
        person.place_in_row = -1
        person.is_alone_on_section = is_single_person_on_section
        person.is_single_in_row = True
        person.is_in_flow = False
        person.flow_index = -1
        person.place_in_flow = -1
        person.flow_member_count = 0
        person.flow_start_x = 0.0
        person.flow_end_x = 0.0
        person.flow_delta_x = 0.0
        person.flow_density = 0.0
        person.local_density = 0.0
        person.other_flow_people_ids = []

    if not is_single_person_on_section:
        for row in rows:
            is_single_in_row = len(row.people) == 1
            for place_in_row, person in enumerate(sorted(row.people, key=lambda current: current.pid)):
                person.row_index = row.row_index
                person.place_in_row = place_in_row
                person.is_single_in_row = is_single_in_row

    for flow in flows:
        ordered_people = sorted(flow.people, key=lambda person: (person.x, person.pid))
        people_ids = [person.pid for person in ordered_people]
        for place_in_flow, person in enumerate(ordered_people):
            person.is_in_flow = True
            person.flow_index = flow.flow_index
            person.place_in_flow = place_in_flow
            person.flow_member_count = len(ordered_people)
            person.flow_start_x = flow.start_x
            person.flow_end_x = flow.end_x
            person.flow_delta_x = flow.delta_x
            person.other_flow_people_ids = [pid for pid in people_ids if pid != person.pid]


def update_rows_and_flows_on_sections(
    people: List[Person],
    sections: Dict[str, Segment],
) -> Dict[str, Dict[str, List[Row] | List[Flow]]]:
    active_people_by_section: Dict[str, List[Person]] = {sid: [] for sid in sections.keys()}

    for person in people:
        if person.finished:
            reset_person_position_state(person)
            continue

        reset_person_position_state(person)
        if person.section_id in active_people_by_section:
            active_people_by_section[person.section_id].append(person)

    section_state: Dict[str, Dict[str, List[Row] | List[Flow]]] = {}

    for sid, section_people in active_people_by_section.items():
        if not section_people:
            section_state[sid] = {"rows": [], "flows": []}
            continue

        section = sections[sid]
        rows = apply_row_geometry_on_section(section_people, section)
        flows = build_flows_on_section(rows, section)
        update_person_position_state(section_people, rows, flows)
        section_state[sid] = {"rows": rows, "flows": flows}

    return section_state


def update_people_position_state_on_sections(
    people: List[Person],
    sections: Dict[str, Segment],
) -> Dict[str, Dict[str, List[Row] | List[Flow]]]:
    return update_rows_and_flows_on_sections(people, sections)


def compute_person_row_centers(row: Row, section: Segment) -> Dict[int, float]:
    del section
    centers: Dict[int, float] = {}
    current_offset = -row.used_width / 2.0

    for person in row.people:
        center_offset = current_offset + person.a_geom / 2.0
        centers[person.pid] = center_offset
        current_offset += person.a_geom

    return centers


def compute_person_speed_stage1(person: Person, section: Segment) -> float:
    """
    Скорость зависит от локальной плотности по инженерной формуле:
    V = V0, если D <= D0
    V = V0 * (1 - ai * ln(D / D0)), если D > D0
    V = V0 * (1 - ai * ln(D / D0)) * m, если D > D0
    где D = local_density.
    Для проема (door): m = 1.0 при D < 0.5, иначе m = 1.25 - 0.05 * D.
    Для остальных участков: m = 1.0.
    """
    speed_components = compute_person_speed_components_stage1(person, section)
    return speed_components["v_mps"]


def compute_person_speed_components_stage1(person: Person, section: Segment) -> Dict[str, float | str]:
    speed_section_type = resolve_section_type_for_profile(person.group, section.section_type)
    movement_params = get_profile_movement_params(person.group, speed_section_type)
    v0_mpm = float(movement_params["V0"])  # м/мин
    ai = float(movement_params["ai"])
    d0 = float(movement_params["D0"])
    density = max(0.0, person.local_density)
    m = 1.0
    if speed_section_type == "door" and density >= 0.5:
        m = 1.25 - 0.05 * density

    if density <= d0 or d0 <= 0.0:
        v_mpm = v0_mpm
    else:
        v_mpm = v0_mpm * (1.0 - ai * math.log(density / d0)) * m

    v_mpm = max(0.0, v_mpm)
    return {
        "v_mpm": v_mpm,
        "v_mps": v_mpm / 60.0,
        "V0": v0_mpm,
        "D0": d0,
        "ai": ai,
        "m": m,
        "density": density,
        "section_type": section.section_type,
        "speed_section_type": speed_section_type,
    }


def update_person_local_density_on_sections(
    people: List[Person],
    sections: Dict[str, Segment],
    section_state: Optional[Dict[str, Dict[str, List[Row] | List[Flow]]]] = None,
) -> Dict[str, Dict[str, List[Row] | List[Flow]]]:
    state = section_state if section_state is not None else update_rows_and_flows_on_sections(people, sections)

    for person in people:
        person.flow_density = 0.0
        person.local_density = 0.0

    for sid, data in state.items():
        section = sections[sid]
        if section.width <= 1e-9:
            continue

        flows = data["flows"]
        assert isinstance(flows, list)
        for flow in flows:
            if not isinstance(flow, Flow):
                continue
            if len(flow.people) < 2:
                continue
            if flow.delta_x <= 1e-9:
                continue

            area_sum_all = sum(other.f for other in flow.people)
            denominator = section.width * flow.delta_x
            for person in flow.people:
                area_sum_other = area_sum_all - person.f
                density = max(0.0, area_sum_other / denominator)
                person.flow_density = density
                person.local_density = density

    return state


def compute_section_flow_density(people: List[Person], sections: Dict[str, Segment]) -> Dict[str, float]:
    """
    Dvj(t) = (sum(f_i)) / (a_j * b_j)
    где sum(f_i) — сумма площадей горизонтальной проекции людей на j-ом участке.
    """
    area_sum_by_section: Dict[str, float] = {sid: 0.0 for sid in sections.keys()}
    for person in people:
        if person.finished or person.section_id not in area_sum_by_section:
            continue
        area_sum_by_section[person.section_id] += person.f

    density_by_section: Dict[str, float] = {}
    for sid, section in sections.items():
        denominator = section.length * section.width
        if denominator <= 1e-9:
            density_by_section[sid] = 0.0
            continue
        density_by_section[sid] = max(0.0, area_sum_by_section.get(sid, 0.0) / denominator)

    return density_by_section


def compute_section_speed_from_density(D_vj_t: float, V0_i: float, ai: float, D0_i: float) -> float:
    """
    Возвращает скорость участка `V_j(t)` в м/мин.

    Формула:
    - `V_j = V0_i`, если `D_vj_t <= D0_i`;
    - `V_j = V0_i * (1 - ai * ln(D_vj_t / D0_i))`, если `D_vj_t > D0_i`.
    """
    density = max(0.0, D_vj_t)
    if D0_i <= 1e-9 or density <= D0_i:
        return max(0.0, V0_i)
    return max(0.0, V0_i * (1.0 - ai * math.log(density / D0_i)))


def compute_section_intensity_qj(D_vj_t: float, V_j_t: float) -> float:
    """
    Возвращает интенсивность `q_j(t)` в м/мин.

    Формула: `q_j(t) = D_vj_t * V_j(t)`.
    """
    return max(0.0, D_vj_t) * max(0.0, V_j_t)


def compute_section_capacity_Qj(q_j_t: float, c_j: float, dt: float, f: float) -> int:
    """
    Возвращает пропускную способность за шаг `Q_j(t)` (чел/шаг).

    Единицы:
    - `q_j_t` — м/мин;
    - `dt` — сек;
    - деление на `60` обязательно для перевода времени в минуты.

    Формула: `Q_j = (q_j_t * c_j * dt) / (60 * f)`.
    """
    if c_j <= 1e-9 or f <= 1e-9 or dt <= 0.0:
        return 0
    raw_capacity = (max(0.0, q_j_t) * c_j * dt) / (60.0 * f)
    if raw_capacity <= 0.0:
        return 0
    return max(1, math.floor(raw_capacity))


def compute_section_transition_diagnostics(
    people: List[Person],
    sections: Dict[str, Segment],
    dt: float,
) -> Dict[str, Dict[str, float | int]]:
    density_by_section = compute_section_flow_density(people, sections)
    active_people_by_section: Dict[str, List[Person]] = {sid: [] for sid in sections.keys()}
    for person in people:
        if person.finished:
            continue
        if person.section_id in active_people_by_section:
            active_people_by_section[person.section_id].append(person)

    diagnostics: Dict[str, Dict[str, float | int]] = {}
    for sid, section in sections.items():
        section_people = active_people_by_section.get(sid, [])
        density = density_by_section.get(sid, 0.0)
        if section_people:
            v0_values: List[float] = []
            ai_values: List[float] = []
            d0_values: List[float] = []
            f_values: List[float] = []
            for person in section_people:
                speed_section_type = resolve_section_type_for_profile(person.group, section.section_type)
                movement_params = get_profile_movement_params(person.group, speed_section_type)
                v0_values.append(float(movement_params["V0"]))
                ai_values.append(float(movement_params["ai"]))
                d0_values.append(float(movement_params["D0"]))
                f_values.append(person.f)
            v0 = sum(v0_values) / len(v0_values)
            ai = sum(ai_values) / len(ai_values)
            d0 = sum(d0_values) / len(d0_values)
            f = sum(f_values) / len(f_values)
        else:
            v0 = 0.0
            ai = 0.0
            d0 = 0.0
            f = 0.0

        v_j = compute_section_speed_from_density(density, v0, ai, d0)
        q_j = compute_section_intensity_qj(density, v_j)
        c_j = section.exit_width_cj if section.exit_width_cj is not None else section.width
        Q_j = compute_section_capacity_Qj(q_j, c_j, dt, f)
        diagnostics[sid] = {
            "D_vj": density,
            "V_j_mpm": v_j,
            "q_j_mpm": q_j,
            "Q_j": Q_j,
            "c_j": c_j,
            "f_mean": f,
        }
    return diagnostics


def apply_row_geometry_on_sections(people: List[Person], sections: Dict[str, Segment]) -> None:
    update_rows_and_flows_on_sections(people, sections)


class SinglePersonSingleSegmentModel:
    def __init__(self, sections: Dict[str, Segment], people: List[Person], params: SimulationParams):
        if not sections:
            raise ValueError("В сценарии должен быть хотя бы один участок.")
        if not people:
            raise ValueError("В сценарии должен быть хотя бы один человек.")

        self.sections = sections
        self.people = people
        self.params = params
        self.time = 0.0
        self.last_section_diagnostics: Dict[str, Dict[str, float | int]] = {
            sid: {"D_vj": 0.0, "V_j_mpm": 0.0, "q_j_mpm": 0.0, "Q_j": 0, "c_j": section.width, "f_mean": 0.0}
            for sid, section in sections.items()
        }

    def section(self) -> Segment:
        return next(iter(self.sections.values()))

    def person(self) -> Person:
        return self.people[0]

    def section_by_id(self, section_id: str) -> Segment:
        return self.sections[section_id]

    def all_finished(self) -> bool:
        return all(person.finished for person in self.people)

    def _move_person(self, person: Person, section_remaining_capacity: Dict[str, int]) -> None:
        current_section = self.section_by_id(person.section_id)
        person.x_raw = person.x - person.v * self.params.dt

        if person.v <= 0:
            person.x = max(0.0, person.x_raw)
            return

        remaining_distance = person.v * self.params.dt
        current_x = person.x
        section = current_section

        while True:
            if remaining_distance < current_x:
                person.section_id = section.sid
                person.x = current_x - remaining_distance
                return

            distance_to_boundary = current_x
            remaining_distance -= distance_to_boundary
            dt_to_boundary = distance_to_boundary / person.v

            available = section_remaining_capacity.get(section.sid, 0)
            if available <= 0:
                person.section_id = section.sid
                person.x = 0.0
                return
            section_remaining_capacity[section.sid] = available - 1

            next_section_id = section.resolve_next_section_id(person.group)
            if not next_section_id:
                person.section_id = "EXIT"
                person.x = 0.0
                person.finished = True
                person.exit_time = self.time + dt_to_boundary
                return

            next_section = self.section_by_id(next_section_id)
            current_x = max(0.0, next_section.length - next_section.merge_lj)
            person.section_id = next_section.sid
            person.x = current_x
            section = next_section

    def step(self) -> None:
        """
        Порядок шага:
        1) обновление рядов/потоков,
        2) расчет локальной плотности,
        3) расчет скоростей,
        4) перемещение.
        """
        original_x_by_pid = {
            person.pid: person.x
            for person in self.people
            if not person.finished
        }

        section_state = update_rows_and_flows_on_sections(self.people, self.sections)
        update_person_local_density_on_sections(self.people, self.sections, section_state)
        self.last_section_diagnostics = compute_section_transition_diagnostics(
            self.people,
            self.sections,
            self.params.dt,
        )

        for person in self.people:
            if person.finished:
                continue
            current_section = self.section_by_id(person.section_id)
            speed_components = compute_person_speed_components_stage1(person, current_section)
            person.v = float(speed_components["v_mps"])
            if person.pid == DEBUG_TRACE_PID:
                print(
                    "[pid=1 speed_trace] "
                    f"group={person.group} "
                    f"section_type={speed_components['section_type']} "
                    f"speed_section_type={speed_components['speed_section_type']} "
                    f"local_density={person.local_density:.6f} "
                    f"flow_density={person.flow_density:.6f} "
                    f"V0={float(speed_components['V0']):.6f} "
                    f"D0={float(speed_components['D0']):.6f} "
                    f"ai={float(speed_components['ai']):.6f} "
                    f"m={float(speed_components['m']):.6f} "
                    f"v={person.v:.6f}"
                )
            person.x = original_x_by_pid.get(person.pid, person.x)

        section_remaining_capacity = {
            sid: int(metrics["Q_j"])
            for sid, metrics in self.last_section_diagnostics.items()
        }
        movable_people = [person for person in self.people if not person.finished]
        movable_people.sort(key=lambda current: current.x)
        for person in movable_people:
            if person.finished:
                continue
            self._move_person(person, section_remaining_capacity)

    def build_result(self) -> Dict[str, float | int | Dict[int, float | None]]:
        total_path_length = sum(section.length for section in self.sections.values())
        return {
            "modeled_path_length_m": total_path_length,
            "speed_m_per_s": max((person.v for person in self.people), default=0.0),
            "travel_time_sec": max(
                (
                    person.exit_time
                    for person in self.people
                    if person.exit_time is not None
                ),
                default=self.time,
            ),
            "finished_count": sum(1 for person in self.people if person.finished),
            "total_people": len(self.people),
            "exit_times": {person.pid: person.exit_time for person in self.people},
        }

    def run(self, verbose: bool = True) -> Dict[str, float | int | Dict[int, float | None]]:
        while not self.all_finished() and self.time < self.params.max_time:
            self.step()

            if verbose and not self.all_finished() and int((self.time + self.params.dt) * 10) % 50 == 0:
                active_people = [person for person in self.people if not person.finished]
                lead_person = min(active_people, key=lambda person: person.x, default=None)
                print(
                    f"t = {self.time + self.params.dt:.1f} c | "
                    f"в здании = {len(active_people)} | "
                    f"ближайший к выходу x = {lead_person.x:.3f} м | "
                    f"v = {lead_person.v:.4f} м/с"
                    if lead_person is not None
                    else f"t = {self.time + self.params.dt:.1f} c | все эвакуированы"
                )

            self.time += self.params.dt

        return self.build_result()


def run_simulation(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    verbose: bool = True,
) -> Dict[str, float | int | Dict[int, float | None]]:
    sections, people, params = scenario
    reset_model_state(people)
    startup_warning = validate_initial_same_coordinate_width(people, sections)
    if startup_warning is not None:
        print(startup_warning)
        return {
            "modeled_path_length_m": sum(section.length for section in sections.values()),
            "speed_m_per_s": 0.0,
            "travel_time_sec": 0.0,
            "finished_count": 0,
            "total_people": len(people),
            "exit_times": {person.pid: None for person in people},
        }
    model = SinglePersonSingleSegmentModel(sections, people, params)
    return model.run(verbose=verbose)


# =========================================================
# ИСТОРИЯ СОСТОЯНИЙ / СНИМКИ
# =========================================================

def build_snapshot(model: SinglePersonSingleSegmentModel, snapshot_time: Optional[float] = None) -> Snapshot:
    people_state: List[PersonState] = []
    for person in model.people:
        if not person.finished and person.section_id in model.sections:
            section = model.sections[person.section_id]
            speed_components = compute_person_speed_components_stage1(person, section)
            v0_mpm = float(speed_components["V0"])
            d0 = float(speed_components["D0"])
            ai = float(speed_components["ai"])
            m = float(speed_components["m"])
            section_type = str(speed_components["section_type"])
            speed_section_type = str(speed_components["speed_section_type"])
        else:
            v0_mpm = 0.0
            d0 = 0.0
            ai = 0.0
            m = 1.0
            section_type = ""
            speed_section_type = ""

        people_state.append(
            PersonState(
                pid=person.pid,
                group=person.group,
                section_id=person.section_id,
                x=person.x,
                v=person.v,
                speed_mps=person.v,
                v0_mpm=v0_mpm,
                d0=d0,
                ai=ai,
                m=m,
                section_type=section_type,
                speed_section_type=speed_section_type,
                row_index=person.row_index,
                place_in_row=person.place_in_row,
                flow_index=person.flow_index,
                place_in_flow=person.place_in_flow,
                flow_start_x=person.flow_start_x,
                flow_end_x=person.flow_end_x,
                flow_delta_x=person.flow_delta_x,
                flow_density=person.flow_density,
                local_density=person.local_density,
                other_flow_people_ids=list(person.other_flow_people_ids),
                finished=person.finished,
                exit_time=person.exit_time,
            )
        )

    section_counts: Dict[str, int] = {sid: 0 for sid in model.sections.keys()}

    for person in model.people:
        if not person.finished and person.section_id in section_counts:
            section_counts[person.section_id] += 1

    diagnostics = compute_section_transition_diagnostics(model.people, model.sections, model.params.dt)
    section_flow_density = {sid: float(values["D_vj"]) for sid, values in diagnostics.items()}
    section_intensity_qj = {sid: float(values["q_j_mpm"]) for sid, values in diagnostics.items()}
    section_capacity_qj = {sid: int(values["Q_j"]) for sid, values in diagnostics.items()}

    return Snapshot(
        time=round(model.time if snapshot_time is None else snapshot_time, 3),
        people=people_state,
        section_counts=section_counts,
        section_flow_density=section_flow_density,
        section_intensity_qj=section_intensity_qj,
        section_capacity_qj=section_capacity_qj,
        finished_count=sum(1 for person in model.people if person.finished),
        total_people=len(model.people),
    )


def build_step_payload(model: SinglePersonSingleSegmentModel, step: int) -> Dict[str, object]:
    section_counts: Dict[str, int] = {sid: 0 for sid in model.sections.keys()}
    for person in model.people:
        if not person.finished and person.section_id in section_counts:
            section_counts[person.section_id] += 1
    diagnostics = compute_section_transition_diagnostics(model.people, model.sections, model.params.dt)
    section_flow_density = {sid: float(values["D_vj"]) for sid, values in diagnostics.items()}
    section_intensity_qj = {sid: float(values["q_j_mpm"]) for sid, values in diagnostics.items()}
    section_capacity_qj = {sid: int(values["Q_j"]) for sid, values in diagnostics.items()}

    people_payload = []
    for person in sorted(model.people, key=lambda current: current.pid):
        if not person.finished and person.section_id in model.sections:
            speed_components = compute_person_speed_components_stage1(
                person,
                model.sections[person.section_id],
            )
            v0_mpm = float(speed_components["V0"])
            d0 = float(speed_components["D0"])
            ai = float(speed_components["ai"])
            m = float(speed_components["m"])
            section_type = str(speed_components["section_type"])
            speed_section_type = str(speed_components["speed_section_type"])
        else:
            v0_mpm = 0.0
            d0 = 0.0
            ai = 0.0
            m = 1.0
            section_type = ""
            speed_section_type = ""

        people_payload.append(
            {
                "pid": person.pid,
                "group": person.group,
                "section_id": person.section_id,
                "x": person.x,
                "v": person.v,
                "speed_mps": person.v,
                "v0_mpm": v0_mpm,
                "d0": d0,
                "ai": ai,
                "m": m,
                "section_type": section_type,
                "speed_section_type": speed_section_type,
                "x_raw": person.x_raw,
                "finished": person.finished,
                "exit_time": person.exit_time,
                "row_index": person.row_index,
                "place_in_row": person.place_in_row,
                "flow_index": person.flow_index,
                "place_in_flow": person.place_in_flow,
                "flow_member_count": person.flow_member_count,
                "flow_start_x": person.flow_start_x,
                "flow_end_x": person.flow_end_x,
                "flow_delta_x": person.flow_delta_x,
                "flow_density": person.flow_density,
                "local_density": person.local_density,
                "other_flow_people_ids": list(person.other_flow_people_ids),
                "is_alone_on_section": person.is_alone_on_section,
                "is_single_in_row": person.is_single_in_row,
                "is_in_flow": person.is_in_flow,
                "is_row_candidate": person.is_row_candidate,
                "can_fit_in_row": person.can_fit_in_row,
            }
        )

    finished_count = sum(1 for person in model.people if person.finished)
    total_people = len(model.people)
    return {
        "step": step,
        "time": round(model.time, 3),
        "people": people_payload,
        "stats": {
            "finished_count": finished_count,
            "total_people": total_people,
            "remaining_count": total_people - finished_count,
            "section_counts": section_counts,
            "section_flow_density": section_flow_density,
            "section_intensity_qj": section_intensity_qj,
            "section_capacity_qj": section_capacity_qj,
            "section_D_vj": section_flow_density,
            "section_q_j": section_intensity_qj,
            "section_Q_j": section_capacity_qj,
        },
    }


def write_step_replay_meta_json(
    sections: Dict[str, Segment],
    dt: float,
    step_count: int,
    people_count: int,
    output_path: str = "artifacts/replay_meta.json",
) -> str:
    def _routing_payload(section: Segment) -> Dict[str, object]:
        return {
            "map": dict(section.next_by_group),
            "default": section.next_default,
        }

    section_payload = [
        {
            "sid": section.sid,
            "section_type": section.section_type,
            "length": section.length,
            "width": section.width,
            "exit_width_cj": section.exit_width_cj,
            "routing": _routing_payload(section),
            "merge_lj": section.merge_lj,
            "row_capacity": section.row_capacity,
        }
        for section in sections.values()
    ]
    payload = {
        "format_version": 1,
        "dt": dt,
        "step_count": step_count,
        "people_count": people_count,
        "sections": section_payload,
    }

    with open(output_path, "w", encoding="utf-8") as meta_file:
        json.dump(payload, meta_file, ensure_ascii=False, indent=2)
    return output_path


def run_simulation_with_history(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    snapshot_interval: float = 1.0,
    verbose: bool = True,
    step_output_path: Optional[str] = None,
    step_meta_output_path: str = "artifacts/replay_meta.json",
) -> Tuple[Dict[str, float | int | Dict[int, float | None]], List[Snapshot]]:
    sections, people, params = scenario
    reset_model_state(people)
    startup_warning = validate_initial_same_coordinate_width(people, sections)
    if startup_warning is not None:
        print(startup_warning)
        result: Dict[str, float | int | Dict[int, float | None]] = {
            "modeled_path_length_m": sum(section.length for section in sections.values()),
            "speed_m_per_s": 0.0,
            "travel_time_sec": 0.0,
            "finished_count": 0,
            "total_people": len(people),
            "exit_times": {person.pid: None for person in people},
        }
        model = SinglePersonSingleSegmentModel(sections, people, params)
        history = [build_snapshot(model, 0.0)]
        if step_output_path:
            with open(step_output_path, "w", encoding="utf-8") as step_file:
                step_file.write(json.dumps(build_step_payload(model, 0), ensure_ascii=False) + "\n")
            write_step_replay_meta_json(
                sections=model.sections,
                dt=model.params.dt,
                step_count=1,
                people_count=len(model.people),
                output_path=step_meta_output_path,
            )
        return result, history

    model = SinglePersonSingleSegmentModel(sections, people, params)
    history: List[Snapshot] = [build_snapshot(model, 0.0)]
    step_count = 0
    step_file = open(step_output_path, "w", encoding="utf-8") if step_output_path else None
    if step_file is not None:
        step_file.write(json.dumps(build_step_payload(model, step_count), ensure_ascii=False) + "\n")

    next_snapshot_time = snapshot_interval

    while not model.all_finished() and model.time < model.params.max_time:
        model.step()
        model.time += model.params.dt
        step_count += 1
        if step_file is not None:
            step_file.write(json.dumps(build_step_payload(model, step_count), ensure_ascii=False) + "\n")

        while model.time + 1e-9 >= next_snapshot_time:
            history.append(build_snapshot(model, next_snapshot_time))
            next_snapshot_time += snapshot_interval

        if verbose and not model.all_finished() and int(model.time * 10) % 50 == 0:
            active_people = [person for person in model.people if not person.finished]
            lead_person = min(active_people, key=lambda person: person.x, default=None)
            print(
                f"t = {model.time:.1f} c | "
                f"в здании = {len(active_people)} | "
                f"ближайший к выходу x = {lead_person.x:.3f} м | "
                f"v = {lead_person.v:.4f} м/с"
                if lead_person is not None
                else f"t = {model.time:.1f} c | все эвакуированы"
            )

    result = model.build_result()

    if not history or history[-1].time < model.time - 1e-9:
        history.append(build_snapshot(model, round(model.time, 3)))
    if step_file is not None:
        step_file.close()
        write_step_replay_meta_json(
            sections=model.sections,
            dt=model.params.dt,
            step_count=step_count + 1,
            people_count=len(model.people),
            output_path=step_meta_output_path,
        )

    return result, history


def build_replay_history_payload(
    sections: Dict[str, Segment],
    history: List[Snapshot],
) -> Dict[str, object]:
    def _routing_payload(section: Segment) -> Dict[str, object]:
        return {
            "map": dict(section.next_by_group),
            "default": section.next_default,
        }

    section_payload = [
        {
            "sid": section.sid,
            "section_type": section.section_type,
            "length": section.length,
            "width": section.width,
            "exit_width_cj": section.exit_width_cj,
            "routing": _routing_payload(section),
            "merge_lj": section.merge_lj,
            "row_capacity": section.row_capacity,
        }
        for section in sections.values()
    ]

    history_payload = []
    for step_index, snapshot in enumerate(history):
        agents = [asdict(person_state) for person_state in snapshot.people]
        history_payload.append(
            {
                "step": step_index,
                "time": snapshot.time,
                "agents": agents,
                "stats": {
                    "finished_count": snapshot.finished_count,
                    "total_people": snapshot.total_people,
                    "remaining_count": snapshot.total_people - snapshot.finished_count,
                    "section_counts": snapshot.section_counts,
                    "section_flow_density": snapshot.section_flow_density,
                    "section_intensity_qj": snapshot.section_intensity_qj,
                    "section_capacity_qj": snapshot.section_capacity_qj,
                    "section_D_vj": snapshot.section_flow_density,
                    "section_q_j": snapshot.section_intensity_qj,
                    "section_Q_j": snapshot.section_capacity_qj,
                },
            }
        )

    return {
        "format_version": 1,
        "sections": section_payload,
        "history": history_payload,
    }


def save_replay_history_json(
    sections: Dict[str, Segment],
    history: List[Snapshot],
    output_path: str = "artifacts/history.json",
) -> str:
    payload = build_replay_history_payload(sections, history)
    with open(output_path, "w", encoding="utf-8") as history_file:
        json.dump(payload, history_file, ensure_ascii=False, indent=2)
    return output_path


# =========================================================
# ТЕСТОВЫЙ СЦЕНАРИЙ
# =========================================================

def build_test_case_simple() -> tuple[dict[str, Segment], list[Person], SimulationParams]:
    sections: dict[str, Segment] = {
        "horizontal_1": Segment(
            sid="horizontal_1",
            section_type="horizontal",
            length=12.0,
            width=2.0,
            next_section_id=None,
        ),
    }

    people: list[Person] = [
        Person(
            pid=1,
            group="M0_7",
            section_id="horizontal_1",
            x=12.0,  # старт в начале участка
        ),
    ]

    params = SimulationParams(
        dt=1.0,
        max_time=600.0,
    )

    return sections, people, params


def format_rows_debug(people: List[Person], section: Segment) -> List[str]:
    rows = build_rows_on_section(people, section)
    lines: List[str] = []

    for row in rows:
        row_people = ", ".join(
            f"pid={person.pid}:{person.group}:place={person.place_in_row}"
            for person in row.people
        )
        lines.append(
            " | ".join(
                [
                    f"row={row.row_index}",
                    f"used_width={row.used_width:.2f}",
                    f"x_interval=[{row.row_left:.2f}, {row.row_right:.2f}]",
                    row_people,
                ]
            )
        )

    return lines
