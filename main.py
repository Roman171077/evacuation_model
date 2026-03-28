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
    save_replay_history_json,
    write_step_replay_meta_json,
    update_person_local_density_on_sections,
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
    'save_replay_history_json',
    'show_realtime_evacuation',
    'write_step_replay_meta_json',
    'update_person_local_density_on_sections',
    'update_people_position_state_on_sections',
    'update_rows_and_flows_on_sections',
]


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Демонстрация эвакуации с записью истории шагов.'
    )
    parser.add_argument(
        '--mode',
        choices=('realtime', 'snapshot', 'replay'),
        default='realtime',
        help='Параметр оставлен для совместимости CLI и игнорируется.',
    )
    parser.add_argument(
        '--playback-speed',
        type=float,
        default=1.0,
        help='Параметр оставлен для совместимости CLI и игнорируется.',
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

    print_input_data_summary(sections, people)

    result, history = run_simulation_with_history(
        (sections, people, params),
        snapshot_interval=args.snapshot_interval,
        verbose=False,
        step_output_path='artifacts/replay_steps.jsonl',
        step_meta_output_path='artifacts/replay_meta.json',
    )
    history_path = save_replay_history_json(sections, history)
    print(f'История шагов сохранена: {history_path}')
    print('Полный трейс сохранен: artifacts/replay_steps.jsonl + artifacts/replay_meta.json')
    print('Дополнительная визуализация отключена: сохраняются только данные расчета.')

    print(f"Время эвакуации: {float(result['travel_time_sec']):.2f} c")
    print(f"Эвакуировано: {int(result['finished_count'])}/{int(result['total_people'])}")


if __name__ == '__main__':
    main()
