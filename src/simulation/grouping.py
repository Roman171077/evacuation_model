from typing import List

from src.model.person import Person
from src.utils.constants import ROW_STEP_X


def build_local_groups(sorted_people: List[Person]) -> List[List[Person]]:
    """Build chain-based local groups with neighbor distance < 0.25 m."""
    if not sorted_people:
        return []

    groups: List[List[Person]] = []
    current_group: List[Person] = [sorted_people[0]]

    for i in range(1, len(sorted_people)):
        prev_person = sorted_people[i - 1]
        person = sorted_people[i]

        if abs(person.x - prev_person.x) < ROW_STEP_X:
            current_group.append(person)
        else:
            groups.append(current_group)
            current_group = [person]

    groups.append(current_group)
    return groups
