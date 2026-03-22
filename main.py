from __future__ import annotations

import argparse
from typing import Dict, List, Optional, Tuple

from scenarios import build_rows_demo_case
from src.catalog import get_profile_movement_params
from src.model import (
    Person,
    PersonState,
    SectionVisual,
    Segment,
    SimulationParams,
    Snapshot,
)
from src.row_layout import (
    apply_row_geometry_on_section,
    build_rows_on_section,
    format_rows_debug,
)
from src.visualization import (
    HAS_MATPLOTLIB,
    build_section_layout_simple,
    can_render_realtime,
    compute_snapshot_visual_placements,
    matplotlib,
    plt,
    render_snapshot,
    show_realtime_evacuation,
)


# =========================================================
# РАСЧЕТНАЯ ЧАСТЬ
# ЭТАП 1: один человек, один участок, без плотности, без переходов
# =========================================================

def reset_model_state(people: List[Person]) -> None:
    for person in people:
        person.section_id = person.initial_section_id
        person.x = person.initial_x
        person.v = 0.0
        person.x_raw = person.x
        person.finished = False
        person.exit_time = None
        person.row_index = -1
        person.place_in_row = -1
        person.is_row_candidate = False
        person.can_fit_in_row = False


def compute_person_speed_stage1(person: Person, section: Segment) -> float:
    """
    На этапе 1 скорость постоянная:
    V_i_t = V0 / 60
    где V0 берется из таблицы профиля для данного типа участка.
    """
    movement_params = get_profile_movement_params(person.group, section.section_type)
    v0_mpm = float(movement_params["V0"])  # м/мин
    v_mps = v0_mpm / 60.0                  # м/с
    return max(0.01, v_mps)


class SinglePersonSingleSegmentModel:
    def __init__(self, sections: Dict[str, Segment], people: List[Person], params: SimulationParams):
        if len(sections) != 1:
            raise ValueError("На этапе 1 должен быть только один участок.")
        if not people:
            raise ValueError("В сценарии должен быть хотя бы один человек.")

        self.sections = sections
        self.people = people
        self.params = params
        self.time = 0.0

    def section(self) -> Segment:
        return next(iter(self.sections.values()))

    def person(self) -> Person:
        return self.people[0]

    def all_finished(self) -> bool:
        return all(person.finished for person in self.people)

    def step(self) -> None:
        """
        Этап без плотности:
        1) свободное движение каждого человека,
        2) затем геометрическое восстановление рядов на участке,
           чтобы люди не проходили сквозь впереди стоящие ряды.
        """
        section = self.section()

        for person in self.people:
            if person.finished:
                continue

            person.v = compute_person_speed_stage1(person, section)

            x_prev = person.x
            person.x_raw = x_prev - person.v * self.params.dt

            if person.x_raw > 0:
                person.x = person.x_raw
                continue

            if person.v > 0:
                dt_to_exit = x_prev / person.v
                dt_to_exit = min(max(dt_to_exit, 0.0), self.params.dt)
            else:
                dt_to_exit = self.params.dt

            person.x = 0.0
            person.finished = True
            person.exit_time = self.time + dt_to_exit
            person.section_id = "EXIT"

        active_people = [
            person for person in self.people
            if not person.finished and person.section_id == section.sid
        ]
        apply_row_geometry_on_section(active_people, section)

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

        section = self.section()

        return {
            "segment_length_m": section.length,
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



def run_simulation(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    verbose: bool = True,
) -> Dict[str, float | int | Dict[int, float | None]]:
    sections, people, params = scenario
    reset_model_state(people)
    model = SinglePersonSingleSegmentModel(sections, people, params)
    apply_row_geometry_on_section(
        [p for p in model.people if not p.finished and p.section_id == model.section().sid],
        model.section(),
    )
    return model.run(verbose=verbose)


# =========================================================
# ИСТОРИЯ СОСТОЯНИЙ / СНИМКИ
# =========================================================

def build_snapshot(model: SinglePersonSingleSegmentModel, snapshot_time: Optional[float] = None) -> Snapshot:
    people_state = [
        PersonState(
            pid=person.pid,
            group=person.group,
            section_id=person.section_id,
            x=person.x,
            finished=person.finished,
            exit_time=person.exit_time,
        )
        for person in model.people
    ]

    section_counts: Dict[str, int] = {sid: 0 for sid in model.sections.keys()}

    for person in model.people:
        if not person.finished and person.section_id in section_counts:
            section_counts[person.section_id] += 1

    return Snapshot(
        time=round(model.time if snapshot_time is None else snapshot_time, 3),
        people=people_state,
        section_counts=section_counts,
        finished_count=sum(1 for person in model.people if person.finished),
        total_people=len(model.people),
    )



def run_simulation_with_history(
    scenario: Tuple[Dict[str, Segment], List[Person], SimulationParams],
    snapshot_interval: float = 1.0,
    verbose: bool = True,
) -> Tuple[Dict[str, float | int | Dict[int, float | None]], List[Snapshot]]:
    sections, people, params = scenario
    reset_model_state(people)

    model = SinglePersonSingleSegmentModel(sections, people, params)
    apply_row_geometry_on_section(
        [p for p in model.people if not p.finished and p.section_id == model.section().sid],
        model.section(),
    )
    history: List[Snapshot] = [build_snapshot(model, 0.0)]

    next_snapshot_time = snapshot_interval

    while not model.all_finished() and model.time < model.params.max_time:
        model.step()
        model.time += model.params.dt

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

    result = {
        "segment_length_m": model.section().length,
        "speed_m_per_s": max((person.v for person in model.people), default=0.0),
        "travel_time_sec": max(
            (
                person.exit_time
                for person in model.people
                if person.exit_time is not None
            ),
            default=model.time,
        ),
        "finished_count": sum(1 for person in model.people if person.finished),
        "total_people": len(model.people),
        "exit_times": {person.pid: person.exit_time for person in model.people},
    }

    if not history or history[-1].time < model.time - 1e-9:
        history.append(build_snapshot(model, round(model.time, 3)))

    return result, history



def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Демонстрация геометрии рядов и эвакуации с визуализацией в реальном времени."
    )
    parser.add_argument(
        "--mode",
        choices=("realtime", "snapshot"),
        default="realtime",
        help="realtime — анимация по истории, snapshot — сохранить один статический кадр.",
    )
    parser.add_argument(
        "--playback-speed",
        type=float,
        default=1.0,
        help="Скорость проигрывания анимации относительно модельного времени.",
    )
    parser.add_argument(
        "--snapshot-interval",
        type=float,
        default=0.1,
        help="Шаг между кадрами истории, с.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_cli_args()
    sections, people, params = build_rows_demo_case()

    if HAS_MATPLOTLIB and matplotlib is not None:
        print(f"matplotlib backend = {matplotlib.get_backend()}")

    section = next(iter(sections.values()))

    print("\nРЕЗУЛЬТАТ ГЕОМЕТРИЧЕСКОГО ФОРМИРОВАНИЯ ПОТОКА:")
    print(f"Участок: {section.sid}")
    print(f"Тип участка: {section.section_type}")
    print(f"Длина участка: {section.length:.2f} м")
    print(f"Ширина участка для рядов: {section.width:.2f} м")
    print("Состав примера: впереди M4_WHEELCHAIR, сзади три M0_3")
    for line in format_rows_debug(people, section):
        print(line)

    layout = build_section_layout_simple(sections)
    result, history = run_simulation_with_history(
        (sections, people, params),
        snapshot_interval=args.snapshot_interval,
        verbose=False,
    )

    if HAS_MATPLOTLIB:
        if args.mode == "realtime" and can_render_realtime():
            print(
                "Запуск анимации в реальном времени "
                f"(скорость воспроизведения x{args.playback_speed:.2f})."
            )
            _fig, _anim = show_realtime_evacuation(
                history,
                sections,
                layout,
                playback_speed=args.playback_speed,
            )
        else:
            if args.mode == "realtime" and not can_render_realtime():
                print(
                    "Интерактивный backend matplotlib недоступен; "
                    "сохраняю последний кадр вместо анимации."
                )

            snapshot = history[-1]
            fig, ax = plt.subplots(figsize=(13, 6))
            render_snapshot(ax, snapshot, sections, layout)
            import os
            os.makedirs("artifacts", exist_ok=True)
            output_path = "artifacts/rows_demo.png"
            fig.savefig(output_path, dpi=160, bbox_inches="tight")
            print(f"Схема сохранена: {output_path}")

        print(f"Время эвакуации: {float(result['travel_time_sec']):.2f} c")
        print(f"Эвакуировано: {int(result['finished_count'])}/{int(result['total_people'])}")
    else:
        print("matplotlib не установлен; сохранение схемы пропущено.")
