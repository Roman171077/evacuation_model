from __future__ import annotations

import argparse
import os

from src.rows_model import (
    MOBILITY_GROUP_COLORS,
    FLOW_PROFILES,
    Person,
    PersonState,
    Row,
    Segment,
    SimulationParams,
    SinglePersonSingleSegmentModel,
    Snapshot,
    apply_row_geometry_on_section,
    build_rows_demo_case,
    build_rows_on_section,
    build_snapshot,
    build_test_case_simple,
    compute_person_row_centers,
    compute_person_speed_stage1,
    format_rows_debug,
    get_profile,
    get_profile_area,
    get_profile_color,
    get_profile_geom_width,
    get_profile_label,
    get_profile_mobility_group,
    get_profile_movement_params,
    reset_model_state,
    ROW_STEP_X,
    run_simulation,
    run_simulation_with_history,
)
from src.visualization import (
    HAS_MATPLOTLIB,
    SectionVisual,
    PersonVisualPlacement,
    animate_evacuation,
    build_section_layout_simple,
    can_render_realtime,
    compute_snapshot_visual_placements,
    matplotlib,
    plot_snapshot_at_time,
    plt,
    render_snapshot,
    show_realtime_evacuation,
)


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


def main() -> None:
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
            os.makedirs("artifacts", exist_ok=True)
            output_path = "artifacts/rows_demo.png"
            fig.savefig(output_path, dpi=160, bbox_inches="tight")
            print(f"Схема сохранена: {output_path}")

        print(f"Время эвакуации: {float(result['travel_time_sec']):.2f} c")
        print(f"Эвакуировано: {int(result['finished_count'])}/{int(result['total_people'])}")
    else:
        print("matplotlib не установлен; сохранение схемы пропущено.")


if __name__ == "__main__":
    main()
