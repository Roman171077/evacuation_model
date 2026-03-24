from __future__ import annotations

import argparse
import os

from src.input_data_component import build_rows_demo_case, print_input_data_summary
from src.rows_model import (
    FLOW_PROFILES,
    FLOW_ROW_GAP_THRESHOLD,
    Flow,
    MOBILITY_GROUP_COLORS,
    Person,
    PersonState,
    ROW_STEP_X,
    Segment,
    SimulationParams,
    SinglePersonSingleSegmentModel,
    Snapshot,
    apply_row_geometry_on_section,
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
    run_simulation,
    run_simulation_with_history,
    update_people_position_state_on_sections,
    update_rows_and_flows_on_sections,
)
from src.visualization import (
    HAS_MATPLOTLIB,
    PersonVisualPlacement,
    SectionVisual,
    animate_evacuation,
    build_section_layout_simple,
    can_render_realtime,
    compute_snapshot_visual_placements,
    export_step_replay_html,
    matplotlib,
    plot_snapshot_at_time,
    plt,
    render_snapshot,
    show_realtime_evacuation,
)

__all__ = [
    'FLOW_PROFILES',
    'FLOW_ROW_GAP_THRESHOLD',
    'Flow',
    'HAS_MATPLOTLIB',
    'MOBILITY_GROUP_COLORS',
    'Person',
    'PersonState',
    'PersonVisualPlacement',
    'ROW_STEP_X',
    'SectionVisual',
    'Segment',
    'SimulationParams',
    'SinglePersonSingleSegmentModel',
    'Snapshot',
    'animate_evacuation',
    'apply_row_geometry_on_section',
    'build_rows_demo_case',
    'build_rows_on_section',
    'build_section_layout_simple',
    'build_snapshot',
    'build_test_case_simple',
    'can_render_realtime',
    'compute_person_row_centers',
    'compute_person_speed_stage1',
    'compute_snapshot_visual_placements',
    'export_step_replay_html',
    'format_rows_debug',
    'get_profile',
    'get_profile_area',
    'get_profile_color',
    'get_profile_geom_width',
    'get_profile_label',
    'get_profile_mobility_group',
    'get_profile_movement_params',
    'main',
    'matplotlib',
    'parse_cli_args',
    'plot_snapshot_at_time',
    'plt',
    'print_input_data_summary',
    'render_snapshot',
    'reset_model_state',
    'run_simulation',
    'run_simulation_with_history',
    'show_realtime_evacuation',
    'update_people_position_state_on_sections',
    'update_rows_and_flows_on_sections',
]


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Демонстрация геометрии рядов и эвакуации с визуализацией в реальном времени.'
    )
    parser.add_argument(
        '--mode',
        choices=('realtime', 'snapshot', 'replay'),
        default='realtime',
        help='realtime — анимация, snapshot — один кадр, replay — html-плеер по шагам.',
    )
    parser.add_argument(
        '--playback-speed',
        type=float,
        default=1.0,
        help='Скорость проигрывания анимации относительно модельного времени.',
    )
    parser.add_argument(
        '--snapshot-interval',
        type=float,
        default=0.1,
        help='Шаг между кадрами истории, с.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_cli_args()
    sections, people, params = build_rows_demo_case()

    if HAS_MATPLOTLIB and matplotlib is not None:
        print(f'matplotlib backend = {matplotlib.get_backend()}')

    print_input_data_summary(sections, people)

    layout = build_section_layout_simple(sections)
    result, history = run_simulation_with_history(
        (sections, people, params),
        snapshot_interval=args.snapshot_interval,
        verbose=False,
    )

    if HAS_MATPLOTLIB:
        if args.mode == 'realtime' and can_render_realtime():
            print(
                'Запуск анимации в реальном времени '
                f'(скорость воспроизведения x{args.playback_speed:.2f}).'
            )
            _fig, _anim = show_realtime_evacuation(
                history,
                sections,
                layout,
                playback_speed=args.playback_speed,
            )
        elif args.mode == 'replay':
            output_path = export_step_replay_html(
                history=history,
                sections=sections,
                layout=layout,
            )
            print(f'Покадровый replay сохранен: {output_path}')
            print('Открой файл в браузере: доступны шаг назад/вперед, пауза и ползунок.')
        else:
            if args.mode == 'realtime' and not can_render_realtime():
                print(
                    'Интерактивный backend matplotlib недоступен; '
                    'переключаюсь на покадровый replay в HTML.'
                )
                output_path = export_step_replay_html(
                    history=history,
                    sections=sections,
                    layout=layout,
                )
                print(f'Покадровый replay сохранен: {output_path}')
                print('Открой файл в браузере: доступны шаг назад/вперед, пауза и ползунок.')
            else:
                snapshot = history[-1]
                fig, ax = plt.subplots(figsize=(13, 6))
                render_snapshot(ax, snapshot, sections, layout)
                os.makedirs('artifacts', exist_ok=True)
                output_path = 'artifacts/rows_demo.png'
                fig.savefig(output_path, dpi=160, bbox_inches='tight')
                print(f'Схема сохранена: {output_path}')

    else:
        print('matplotlib не установлен; сохранение схемы пропущено.')

    print(f"Время эвакуации: {float(result['travel_time_sec']):.2f} c")
    print(f"Эвакуировано: {int(result['finished_count'])}/{int(result['total_people'])}")


if __name__ == '__main__':
    main()
