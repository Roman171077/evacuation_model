from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

from src.rows_model import Person, Segment, format_rows_debug, get_profile_label, get_profile_mobility_group


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
    section = next(iter(sections.values()))

    print('\nВВОДНЫЕ ДАННЫЕ:')
    print('Характеристика участка:')
    print(f'Участок: {section.sid}')
    print(f'Тип участка: {section.section_type}')
    print(f'Длина участка: {section.length:.2f} м')
    print(f'Ширина участка для рядов: {section.width:.2f} м')
    print(f'Ширина выхода: {section.exit_width:.2f} м')

    print('Характеристика людей:')
    print(f'Всего людей: {len(people)}')
    for line in build_people_summary_lines(people):
        print(line)

    print('Формирование рядов по текущим вводным:')
    for line in format_rows_debug(people, section):
        print(line)
