from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

from src.rows_model import (
    Person,
    Segment,
    SimulationParams,
    format_rows_debug,
    get_profile_label,
    get_profile_mobility_group,
)


ROWS_DEMO_SECTION_SPECS: tuple[dict[str, object], ...] = (
    {
        'sid': 'horizontal_1',
        'section_type': 'horizontal',
        'length': 25.0,
        'width': 2.0,
        'exit_width_cj': 1.2,
        'next_by_group': {
            'M4_WHEELCHAIR': 'ramp_accessible_1',
        },
        'next_default': 'horizontal_2',
    },
    {
        'sid': 'horizontal_2',
        'section_type': 'horizontal',
        'length': 25.0,
        'width': 2.0,
        'exit_width_cj': 1.0,
        'next_section_id': None,
    },
    {
        'sid': 'ramp_accessible_1',
        'section_type': 'ramp_down',
        'length': 18.0,
        'width': 1.8,
        'exit_width_cj': 1.8,
        'next_section_id': None,
    },
)


ROWS_DEMO_PERSON_SPECS: tuple[dict[str, object], ...] = (
    {'pid': 1, 'group': 'M4_WHEELCHAIR', 'section_id': 'horizontal_1', 'x': 17.05},
    {'pid': 2, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 17.35},
    {'pid': 3, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 17.65},
    {'pid': 4, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 18.05},
    {'pid': 5, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 18.35},
    {'pid': 6, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 18.65},
    {'pid': 7, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 14.10},
    {'pid': 8, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 14.40},
    {'pid': 9, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 14.70},
    {'pid': 10, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 15.10},
    {'pid': 11, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 15.40},
    {'pid': 12, 'group': 'M0_3', 'section_id': 'horizontal_1', 'x': 15.70},
)


ROWS_DEMO_PARAMS = SimulationParams(dt=1.0, max_time=120.0)


def build_rows_demo_case() -> tuple[dict[str, Segment], list[Person], SimulationParams]:
    sections = {
        str(section_spec['sid']): Segment(**section_spec)
        for section_spec in ROWS_DEMO_SECTION_SPECS
    }
    people = [Person(**person_spec) for person_spec in ROWS_DEMO_PERSON_SPECS]
    params = SimulationParams(dt=ROWS_DEMO_PARAMS.dt, max_time=ROWS_DEMO_PARAMS.max_time)
    return sections, people, params


def build_people_summary_lines(people: Iterable[Person]) -> list[str]:
    counts = Counter(person.group for person in people)
    lines: list[str] = []

    for group, count in sorted(counts.items()):
        lines.append(
            ' - '
            f'{group} ({get_profile_label(group)}, группа {get_profile_mobility_group(group)}): '
            f'{count} чел.'
        )

    return lines


def print_input_data_summary(sections: Mapping[str, Segment], people: list[Person]) -> None:
    first_section = next(iter(sections.values()))

    print('\nВВОДНЫЕ ДАННЫЕ:')
    print('Характеристика участков:')
    for section in sections.values():
        print(f'Участок: {section.sid}')
        print(f'Тип участка: {section.section_type}')
        print(f'Длина участка: {section.length:.2f} м')
        print(f'Ширина участка для рядов: {section.width:.2f} м')
        if section.exit_width_cj is not None:
            print(f'Ширина выхода c_j: {section.exit_width_cj:.2f} м')
        else:
            print(f'Ширина выхода c_j: {section.width:.2f} м (fallback к ширине участка)')
        if section.next_by_group:
            for group, next_sid in sorted(section.next_by_group.items()):
                print(f'Следующий участок для {group}: {next_sid}')
        print(f'Следующий участок (по умолчанию): {section.next_default or "EXIT"}')
        if section.merge_lj > 0:
            print(f'Координата места слияния: {section.merge_lj:.2f} м')
        print('---')

    print('Характеристика людей:')
    print(f'Всего людей: {len(people)}')
    for line in build_people_summary_lines(people):
        print(line)

    print('Формирование рядов на стартовом участке по текущим вводным:')
    starting_people = [person for person in people if person.section_id == first_section.sid]
    for line in format_rows_debug(starting_people, first_section):
        print(line)
