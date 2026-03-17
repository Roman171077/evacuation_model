from typing import List

from src.model.person import Person
from src.model.segment import Segment
from src.model.simulation_params import SimulationParams
from src.utils.constants import MOBILITY_GROUPS, SECTION_TYPE_SPEED_FACTOR


def effective_person_area(person: Person, winter: bool) -> float:
    area = person.f
    if winter and person.group == "M0":
        area *= 1.25
    return area


def compute_local_density(group_people: List[Person], section: Segment, winter: bool) -> float:
    n_people = len(group_people)
    if n_people < 2:
        return 0.0

    x_values = [person.x for person in group_people]
    delta_x = max(x_values) - min(x_values)
    if delta_x <= 0:
        return 10.0

    f_avg = sum(effective_person_area(person, winter) for person in group_people) / n_people
    return ((n_people - 1) * f_avg) / (section.width * delta_x)


def compute_section_density(section_people: List[Person], section: Segment, winter: bool) -> float:
    if not section_people:
        return 0.0
    if section.length <= 0 or section.width <= 0:
        return 0.0

    f_avg = sum(effective_person_area(person, winter) for person in section_people) / len(section_people)
    return (len(section_people) * f_avg) / (section.length * section.width)


def base_speed_mps(person: Person, section: Segment) -> float:
    base_speed = MOBILITY_GROUPS[person.group]["base_speed"]
    speed_factor = SECTION_TYPE_SPEED_FACTOR.get(section.section_type, 1.0)
    return base_speed * speed_factor


def density_reduction_factor(density: float) -> float:
    if density <= 0:
        return 1.0
    if density < 0.3:
        return 1.0
    if density < 0.6:
        return max(0.80, 1.0 - 0.40 * (density - 0.3) / 0.3)
    if density < 1.0:
        return max(0.45, 0.80 - 0.35 * (density - 0.6) / 0.4)
    if density < 1.5:
        return max(0.15, 0.45 - 0.30 * (density - 1.0) / 0.5)
    return 0.10


def compute_person_speed(person: Person, section: Segment, local_density: float) -> float:
    return max(0.01, base_speed_mps(person, section) * density_reduction_factor(local_density))


def compute_intensity_q_m_per_min(section_people: List[Person], section: Segment, density: float) -> float:
    if not section_people:
        return 0.0

    representative_speed_mps = (
        sum(compute_person_speed(person, section, density) for person in section_people)
        / len(section_people)
    )
    representative_speed_mpm = representative_speed_mps * 60.0
    return representative_speed_mpm * density


def compute_capacity_people_per_step(
    section_people: List[Person], section: Segment, params: SimulationParams
) -> int:
    if not section_people:
        return 0

    density = compute_section_density(section_people, section, params.winter_clothing)
    intensity = compute_intensity_q_m_per_min(section_people, section, density)
    f_avg = sum(
        effective_person_area(person, params.winter_clothing) for person in section_people
    ) / len(section_people)
    if f_avg <= 0:
        return 0

    q_step = (intensity * section.exit_width * params.dt) / (f_avg * 60.0)
    section.transfer_credit += q_step
    allowed = int(section.transfer_credit)
    section.transfer_credit -= allowed
    return max(0, allowed)
