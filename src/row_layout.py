from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.model import Person, Row, Segment


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



def create_new_row(row_index: int, person: Person, min_center_x: Optional[float] = None) -> Row:
    if min_center_x is not None and person.x < min_center_x:
        person.x = min_center_x

    person_left, person_right = get_person_interval_x(person)
    row = Row(
        row_index=row_index,
        row_left=person_left,
        row_right=person_right,
        used_width=0.0,
        people=[],
    )
    add_person_to_row(row, person)
    return row



def build_rows_on_section(
    people: List[Person],
    section: Segment,
    reposition_rows: bool = False,
) -> List[Row]:
    if not people:
        return []

    people_sorted = sorted(people, key=lambda p: (p.x, p.pid))
    rows: List[Row] = []

    for person in people_sorted:
        person.is_row_candidate = False
        person.can_fit_in_row = False
        person.row_index = -1
        person.place_in_row = -1

        if not rows:
            rows.append(create_new_row(0, person))
            continue

        current_row = rows[-1]
        candidate = is_candidate_for_row(current_row, person)
        width_ok = can_fit_into_row(current_row, person, section) if candidate else False

        person.is_row_candidate = candidate
        person.can_fit_in_row = width_ok

        if candidate and width_ok:
            add_person_to_row(current_row, person)
        else:
            min_center_x = None
            if reposition_rows:
                min_center_x = current_row.row_right + max(person.c_geom, person.a_geom) / 2.0

            rows.append(create_new_row(len(rows), person, min_center_x=min_center_x))

    return rows



def apply_row_geometry_on_section(people: List[Person], section: Segment) -> List[Row]:
    """
    Перестраивает людей по рядам и при необходимости сдвигает задние ряды назад по x,
    чтобы ряды не пересекались.
    """
    return build_rows_on_section(people, section, reposition_rows=True)



def compute_person_row_centers(row: Row, section: Segment) -> Dict[int, float]:
    del section
    centers: Dict[int, float] = {}
    current_offset = -row.used_width / 2.0

    for person in row.people:
        center_offset = current_offset + person.a_geom / 2.0
        centers[person.pid] = center_offset
        current_offset += person.a_geom

    return centers



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
