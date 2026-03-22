from __future__ import annotations

from typing import Dict

ROW_STEP_X = 0.25  # сохранено, хотя на этапе 1 не используется

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
        },
    },
    "M0_3": {
        "label": "Люди трудоспособного возраста (18–60 лет)",
        "mobility_group": "M0",
        "geometry_source": "normative_P2.5",
        "a_geom": 0.46,
        "c_geom": 0.28,
        "f": 0.10,
        "movement": {
            "horizontal":  {"V0": 100.0, "ai": 0.295, "D0": 0.51},
            "door":        {"V0": 100.0, "ai": 0.295, "D0": 0.65},
            "stairs_down": {"V0": 100.0, "ai": 0.400, "D0": 0.89},
            "stairs_up":   {"V0": 60.0,  "ai": 0.305, "D0": 0.67},
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


def get_profile_color(profile_name: str) -> str:
    mobility_group = get_profile_mobility_group(profile_name)
    return MOBILITY_GROUP_COLORS.get(mobility_group, "#1f77b4")
