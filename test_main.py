import unittest
import json
import os
import tempfile
from unittest.mock import patch

from src.visualization import build_flow_summary_lines
from src.replay_app import _build_flow_membership_rows
from main import (
    Person,
    PersonState,
    SectionVisual,
    Segment,
    SimulationParams,
    SinglePersonSingleSegmentModel,
    Snapshot,
    apply_row_geometry_on_section,
    build_rows_demo_case,
    build_rows_on_section,
    build_section_layout_simple,
    compute_snapshot_visual_placements,
    parse_cli_args,
    run_simulation_with_history,
    save_replay_history_json,
    update_person_local_density_on_sections,
    update_people_position_state_on_sections,
    update_rows_and_flows_on_sections,
)


class MainRowBuildingTests(unittest.TestCase):
    def test_parse_cli_args_accepts_replay_mode(self):
        with patch("sys.argv", ["main.py", "--mode", "replay"]):
            args = parse_cli_args()
        self.assertEqual(args.mode, "replay")

    def test_wheelchair_and_three_m0_3_are_split_into_two_rows(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.10),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=5.15),
            Person(pid=4, group="M0_3", section_id="horizontal_1", x=5.90),
        ]

        rows = build_rows_on_section(people, section)

        self.assertEqual(len(rows), 2)
        self.assertEqual([p.pid for p in rows[0].people], [1, 2, 3])
        self.assertEqual([p.pid for p in rows[1].people], [4])
        self.assertEqual((people[0].row_index, people[0].place_in_row), (0, 0))
        self.assertEqual((people[1].row_index, people[1].place_in_row), (0, 1))
        self.assertEqual((people[2].row_index, people[2].place_in_row), (0, 2))
        self.assertEqual((people[3].row_index, people[3].place_in_row), (1, 0))

    def test_person_starts_new_row_when_width_is_exceeded(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.10),
        ]

        rows = build_rows_on_section(people, section)

        self.assertEqual(len(rows), 2)
        self.assertTrue(people[1].is_row_candidate)
        self.assertFalse(people[1].can_fit_in_row)
        self.assertEqual(people[1].row_index, 1)

    def test_apply_row_geometry_shifts_new_rows_from_previous_row_right_boundary(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=5.00),
        ]

        rows = apply_row_geometry_on_section(people, section)

        self.assertEqual(len(rows), 3)
        self.assertAlmostEqual(people[0].x, 5.00)
        self.assertAlmostEqual(people[1].x, 6.45, places=2)
        self.assertAlmostEqual(people[2].x, 7.44, places=2)
        self.assertEqual(rows[0].longitudinal_shift, 0.0)
        self.assertAlmostEqual(rows[1].longitudinal_shift, 1.45, places=2)
        self.assertAlmostEqual(rows[2].longitudinal_shift, 2.44, places=2)

        for front_row, back_row in zip(rows, rows[1:]):
            self.assertGreaterEqual(back_row.row_left, front_row.row_right + 0.25 - 1e-9)

    def test_apply_row_geometry_avoids_overlap_for_mixed_c_geom(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.2)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.02),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=5.04),
            Person(pid=4, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.06),
        ]

        rows = apply_row_geometry_on_section(people, section)

        self.assertGreaterEqual(len(rows), 2)
        for front_row, back_row in zip(rows, rows[1:]):
            self.assertGreaterEqual(back_row.row_left, front_row.row_right + 0.25 - 1e-9)

    def test_build_rows_keeps_multiple_people_with_same_x_in_back_row(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0)
        people = [
            Person(pid=pid, group="M0_3", section_id="horizontal_1", x=5.00)
            for pid in range(1, 10)
        ]

        rows = build_rows_on_section(people, section)

        self.assertEqual(len(rows), 3)
        self.assertEqual(len(rows[0].people), 4)
        self.assertEqual(len(rows[1].people), 4)
        self.assertGreater(len(rows[1].people), 1)
        self.assertEqual(len(rows[2].people), 1)
        self.assertEqual([person.pid for person in rows[1].people], [5, 6, 7, 8])

    def test_step_moves_people_only_by_speed_without_row_constraints(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.20),
        ]
        params = SimulationParams(dt=2.0, max_time=10.0)
        model = SinglePersonSingleSegmentModel({"horizontal_1": section}, people, params)

        apply_row_geometry_on_section(model.people, section)
        model.step()

        self.assertLess(people[0].x, 5.00)
        self.assertLess(people[1].x, 5.20)

    def test_person_transitions_to_next_section_with_remaining_distance(self):
        sections = {
            "horizontal_1": Segment(
                "horizontal_1",
                "horizontal",
                length=10.0,
                width=2.0,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=8.0,
                width=2.0,
                merge_lj=1.5,
            ),
        }
        people = [Person(pid=1, group="M0_3", section_id="horizontal_1", x=0.2)]
        params = SimulationParams(dt=1.0, max_time=10.0)
        model = SinglePersonSingleSegmentModel(sections, people, params)

        model.step()

        self.assertFalse(people[0].finished)
        self.assertEqual(people[0].section_id, "horizontal_2")
        self.assertAlmostEqual(people[0].x, 5.03, places=2)

    def test_position_state_for_single_person_on_section(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0)
        person = Person(pid=1, group="M0_3", section_id="horizontal_1", x=5.0)

        state = update_people_position_state_on_sections([person], {"horizontal_1": section})

        self.assertEqual(len(state["horizontal_1"]["rows"]), 1)
        self.assertEqual(len(state["horizontal_1"]["flows"]), 0)
        self.assertEqual(person.row_index, -1)
        self.assertEqual(person.place_in_row, -1)
        self.assertTrue(person.is_alone_on_section)
        self.assertTrue(person.is_single_in_row)
        self.assertFalse(person.is_in_flow)
        self.assertEqual(person.flow_index, -1)
        self.assertEqual(person.place_in_flow, -1)
        self.assertEqual(person.flow_member_count, 0)
        self.assertEqual(person.flow_delta_x, 0.0)
        self.assertEqual(person.other_flow_people_ids, [])

    def test_position_state_for_multiple_people_in_one_row(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0)
        people = [
            Person(pid=1, group="M0_3", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.05),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=5.10),
        ]

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})

        self.assertEqual(len(state["horizontal_1"]["rows"]), 1)
        self.assertEqual(len(state["horizontal_1"]["flows"]), 1)
        for expected_place, person in enumerate(people):
            self.assertEqual(person.row_index, 0)
            self.assertEqual(person.place_in_row, expected_place)
            self.assertFalse(person.is_alone_on_section)
            self.assertFalse(person.is_single_in_row)
            self.assertTrue(person.is_in_flow)
            self.assertEqual(person.flow_index, 0)
            self.assertAlmostEqual(person.flow_delta_x, 0.10, places=6)
            self.assertEqual(person.other_flow_people_ids, [pid for pid in [1, 2, 3] if pid != person.pid])

    def test_flow_breaks_on_gap_over_threshold_and_single_person_is_not_a_flow(self):
        section = Segment("horizontal_1", "horizontal", length=20.0, width=2.0)
        people = [
            Person(pid=1, group="M0_3", section_id="horizontal_1", x=4.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=4.10),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=4.20),
            Person(pid=4, group="M0_3", section_id="horizontal_1", x=5.80),
        ]

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})
        flows = state["horizontal_1"]["flows"]

        self.assertEqual(len(flows), 1)
        self.assertEqual([person.pid for person in flows[0].people], [1, 2, 3])
        self.assertTrue(people[0].is_in_flow)
        self.assertTrue(people[1].is_in_flow)
        self.assertTrue(people[2].is_in_flow)
        self.assertFalse(people[3].is_in_flow)
        self.assertEqual(people[3].flow_index, -1)

    def test_position_state_for_multiple_rows_without_flow(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=2.0),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=6.0),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=9.5),
        ]

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})

        self.assertEqual(len(state["horizontal_1"]["rows"]), 3)
        self.assertEqual(len(state["horizontal_1"]["flows"]), 0)
        for expected_row, person in enumerate(people):
            self.assertEqual(person.row_index, expected_row)
            self.assertTrue(person.is_single_in_row)
            self.assertFalse(person.is_alone_on_section)
            self.assertFalse(person.is_in_flow)
            self.assertEqual(person.flow_index, -1)
            self.assertEqual(person.flow_delta_x, 0.0)
            self.assertEqual(person.other_flow_people_ids, [])

    def test_flow_summary_lines_list_people_in_each_flow(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
        ]

        update_people_position_state_on_sections(people, {"horizontal_1": section})
        snapshot = Snapshot(
            time=0.0,
            people=[
                PersonState(
                    pid=person.pid,
                    group=person.group,
                    section_id=person.section_id,
                    x=person.x,
                    flow_index=person.flow_index,
                    place_in_flow=person.place_in_flow,
                    finished=person.finished,
                )
                for person in people
            ],
            section_counts={"horizontal_1": 3},
            finished_count=0,
            total_people=3,
        )

        lines = build_flow_summary_lines(snapshot, {"horizontal_1": section})
        self.assertEqual(lines[0], "Локальные потоки и одиночные люди по участкам:")
        self.assertEqual(lines[1], "horizontal_1:")
        self.assertEqual(lines[2], "  В потоке:")
        self.assertIn("pid=1", lines[3])
        self.assertIn("другие в потоке=2, 3", lines[3])
        self.assertIn("pid=2", lines[3])
        self.assertIn("другие в потоке=1, 3", lines[3])
        self.assertIn("pid=3", lines[3])
        self.assertIn("другие в потоке=1, 2", lines[3])

    def test_flow_summary_lines_show_dash_when_section_has_no_flow(self):
        sections = {
            "horizontal_1": Segment("horizontal_1", "horizontal", length=12.0, width=2.0),
            "horizontal_2": Segment("horizontal_2", "horizontal", length=10.0, width=2.0),
        }
        people = [
            Person(pid=1, group="M0_3", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.05),
        ]

        update_people_position_state_on_sections(people, sections)
        snapshot = Snapshot(
            time=0.0,
            people=[
                PersonState(
                    pid=person.pid,
                    group=person.group,
                    section_id=person.section_id,
                    x=person.x,
                    flow_index=person.flow_index,
                    place_in_flow=person.place_in_flow,
                    finished=person.finished,
                )
                for person in people
            ],
            section_counts={"horizontal_1": 2, "horizontal_2": 0},
            finished_count=0,
            total_people=2,
        )

        self.assertEqual(
            build_flow_summary_lines(snapshot, sections),
            [
                "Локальные потоки и одиночные люди по участкам:",
                "horizontal_1:",
                "  В потоке:",
                "    F0: pid=1 (x=5.00 м, D=0.000, другие в потоке=2), pid=2 (x=5.05 м, D=0.000, другие в потоке=1)",
                "  Вне потока: —",
                "horizontal_2: —",
            ],
        )

    def test_position_state_for_consecutive_rows_forming_flow(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
        ]

        original_x = people[0].x

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})
        flows = state["horizontal_1"]["flows"]

        self.assertEqual(len(state["horizontal_1"]["rows"]), 3)
        self.assertEqual(len(flows), 1)
        self.assertAlmostEqual(flows[0].start_x, original_x)
        self.assertAlmostEqual(flows[0].end_x, original_x)
        self.assertAlmostEqual(flows[0].delta_x, 0.0)
        for expected_row, person in enumerate(people):
            self.assertEqual(person.row_index, expected_row)
            self.assertTrue(person.is_in_flow)
            self.assertEqual(person.flow_index, 0)
            self.assertEqual(person.place_in_flow, expected_row)
            self.assertEqual(person.flow_member_count, 3)
            self.assertEqual(len(person.other_flow_people_ids), 2)
            self.assertAlmostEqual(person.flow_start_x, original_x)
            self.assertAlmostEqual(person.flow_end_x, original_x)
            self.assertAlmostEqual(person.flow_delta_x, 0.0)
            self.assertEqual(person.other_flow_people_ids, [pid for pid in [1, 2, 3] if pid != person.pid])

    def test_position_state_for_mixed_group_flow(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M1_PREGNANT", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
        ]

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})
        flows = state["horizontal_1"]["flows"]

        self.assertEqual(len(flows), 1)
        self.assertEqual([person.group for person in flows[0].people], ["M4_WHEELCHAIR", "M1_PREGNANT", "M4_WHEELCHAIR"])
        for person in people:
            self.assertTrue(person.is_in_flow)
            self.assertEqual(person.flow_index, 0)
            self.assertEqual(person.flow_member_count, 3)
            self.assertEqual(len(person.other_flow_people_ids), 2)

    def test_flow_delta_x_uses_unshifted_row_projection_for_density(self):
        section = Segment("horizontal_1", "horizontal", length=20.0, width=2.0)
        people = [
            Person(pid=7, group="M0_3", section_id="horizontal_1", x=14.10),
            Person(pid=8, group="M0_3", section_id="horizontal_1", x=14.40),
            Person(pid=9, group="M0_3", section_id="horizontal_1", x=14.70),
            Person(pid=10, group="M0_3", section_id="horizontal_1", x=15.10),
            Person(pid=11, group="M0_3", section_id="horizontal_1", x=15.40),
            Person(pid=12, group="M0_3", section_id="horizontal_1", x=15.70),
        ]
        original_x = {person.pid: person.x for person in people}

        section_state = update_rows_and_flows_on_sections(people, {"horizontal_1": section})
        flows = section_state["horizontal_1"]["flows"]

        self.assertEqual(len(flows), 1)
        self.assertAlmostEqual(flows[0].start_x, original_x[7], places=6)
        self.assertAlmostEqual(flows[0].end_x, original_x[12], places=6)
        self.assertAlmostEqual(flows[0].delta_x, original_x[12] - original_x[7], places=6)
        self.assertGreater(people[-1].x - people[0].x, flows[0].delta_x)

        update_person_local_density_on_sections(people, {"horizontal_1": section}, section_state)
        expected_density = (5 * 0.10) / (section.width * (original_x[12] - original_x[7]))
        self.assertAlmostEqual(people[0].flow_density, expected_density, places=6)

    def test_local_density_is_computed_for_each_person_from_other_people_area(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M1_PREGNANT", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
        ]

        section_state = update_rows_and_flows_on_sections(people, {"horizontal_1": section})
        update_person_local_density_on_sections(people, {"horizontal_1": section}, section_state)

        self.assertAlmostEqual(people[0].flow_delta_x, 0.0, places=9)
        self.assertAlmostEqual(people[1].flow_delta_x, 0.0, places=9)
        self.assertAlmostEqual(people[2].flow_delta_x, 0.0, places=9)
        self.assertAlmostEqual(people[1].local_density, 0.0, places=9)
        self.assertAlmostEqual(people[0].local_density, 0.0, places=9)
        self.assertAlmostEqual(people[0].flow_density, people[0].local_density, places=9)

    def test_position_state_rebuilds_after_transition_to_new_section(self):
        sections = {
            "horizontal_1": Segment(
                "horizontal_1",
                "horizontal",
                length=10.0,
                width=1.0,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=10.0,
                width=1.0,
            ),
        }
        people = [
            Person(pid=1, group="M0_3", section_id="horizontal_1", x=0.2),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_2", x=8.8),
        ]
        params = SimulationParams(dt=1.0, max_time=5.0)
        model = SinglePersonSingleSegmentModel(sections, people, params)

        update_people_position_state_on_sections(model.people, model.sections)
        model.step()

        self.assertEqual(people[0].section_id, "horizontal_2")
        self.assertEqual(people[1].section_id, "horizontal_2")
        self.assertEqual(people[1].row_index, -1)
        self.assertEqual(people[0].row_index, -1)
        self.assertFalse(people[0].is_in_flow)
        self.assertFalse(people[1].is_in_flow)
        self.assertGreater(people[0].x, people[1].x)

    def test_same_coordinate_rows_keep_flow_when_shift_step_stays_within_threshold(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=8.0),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=8.0),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=8.0),
        ]
        params = SimulationParams(dt=1.0, max_time=5.0)
        model = SinglePersonSingleSegmentModel({"horizontal_1": section}, people, params)

        update_rows_and_flows_on_sections(model.people, model.sections)
        self.assertEqual(people[1].flow_index, 0)
        self.assertEqual(people[1].other_flow_people_ids, [1, 3])
        gap_01 = (people[1].x - people[1].c_geom / 2.0) - (people[0].x + people[0].c_geom / 2.0)
        gap_12 = (people[2].x - people[2].c_geom / 2.0) - (people[1].x + people[1].c_geom / 2.0)
        self.assertAlmostEqual(gap_01, 0.25)
        self.assertAlmostEqual(gap_12, 0.25)

        model.step()

        self.assertFalse(people[1].is_in_flow)
        self.assertEqual(people[1].flow_index, -1)
        self.assertEqual(people[1].other_flow_people_ids, [])
        self.assertFalse(people[0].is_in_flow)
        self.assertFalse(people[2].is_in_flow)
        self.assertEqual(people[0].other_flow_people_ids, [])
        self.assertEqual(people[2].other_flow_people_ids, [])

    def test_rows_with_gap_over_threshold_do_not_merge_into_flow_on_next_step(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.0),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.8),
        ]
        params = SimulationParams(dt=1.0, max_time=5.0)
        model = SinglePersonSingleSegmentModel({"horizontal_1": section}, people, params)

        update_rows_and_flows_on_sections(model.people, model.sections)
        self.assertEqual(people[0].flow_index, -1)
        self.assertEqual(people[1].flow_index, -1)

        model.step()

        self.assertFalse(people[0].is_in_flow)
        self.assertFalse(people[1].is_in_flow)
        self.assertEqual(people[0].flow_index, -1)
        self.assertEqual(people[1].flow_index, -1)

    def test_build_snapshot_stores_row_and_flow_state_fields(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.0),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.0),
        ]
        model = SinglePersonSingleSegmentModel({"horizontal_1": section}, people, SimulationParams())

        update_rows_and_flows_on_sections(model.people, model.sections)
        snapshot = run_simulation_with_history(({"horizontal_1": section}, people, SimulationParams(dt=0.1, max_time=0.0)), snapshot_interval=0.1, verbose=False)[1][0]
        people_state = {person.pid: person for person in snapshot.people}

        self.assertEqual(people_state[1].x, people[0].x)
        self.assertEqual(people_state[1].v, people[0].v)
        self.assertEqual(people_state[1].row_index, people[0].row_index)
        self.assertEqual(people_state[1].place_in_row, people[0].place_in_row)
        self.assertEqual(people_state[1].flow_index, people[0].flow_index)
        self.assertEqual(people_state[1].place_in_flow, people[0].place_in_flow)
        self.assertEqual(people_state[1].flow_start_x, people[0].flow_start_x)
        self.assertEqual(people_state[1].flow_end_x, people[0].flow_end_x)
        self.assertEqual(people_state[1].flow_delta_x, people[0].flow_delta_x)
        self.assertEqual(people_state[1].other_flow_people_ids, people[0].other_flow_people_ids)

    def test_demo_input_data_builder_is_exported_from_input_component(self):
        self.assertEqual(build_rows_demo_case.__module__, "src.input_data_component")

    def test_run_simulation_with_history_supports_demo_multi_segment_case(self):
        scenario = build_rows_demo_case()

        result, history = run_simulation_with_history(scenario, snapshot_interval=0.5, verbose=False)

        self.assertGreaterEqual(result["finished_count"], 0)
        self.assertGreaterEqual(result["modeled_path_length_m"], 50.0)
        self.assertGreaterEqual(len(history), 1)
        self.assertIn("horizontal_1", history[0].section_counts)
        self.assertIn("horizontal_2", history[0].section_counts)


    def test_flow_membership_rows_include_other_flow_people_ids(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
        ]

        update_people_position_state_on_sections(people, {"horizontal_1": section})
        snapshot = Snapshot(
            time=0.0,
            people=[
                PersonState(
                    pid=person.pid,
                    group=person.group,
                    section_id=person.section_id,
                    x=person.x,
                    flow_index=person.flow_index,
                    place_in_flow=person.place_in_flow,
                    other_flow_people_ids=list(person.other_flow_people_ids),
                    finished=person.finished,
                )
                for person in people
            ],
            section_counts={"horizontal_1": 3},
            finished_count=0,
            total_people=3,
        )

        rows = _build_flow_membership_rows(snapshot, {"horizontal_1": section})

        self.assertEqual(len(rows), 3)
        self.assertIn("pid других людей в потоке", rows[0])
        self.assertEqual(rows[0]["pid других людей в потоке"], "2, 3")
        self.assertEqual(rows[1]["pid других людей в потоке"], "1, 3")
        self.assertEqual(rows[2]["pid других людей в потоке"], "1, 2")

    def test_visual_api_is_exported_from_separate_module(self):
        self.assertEqual(compute_snapshot_visual_placements.__module__, "src.visualization")

    def test_save_replay_history_json_exports_expected_shape(self):
        scenario = build_rows_demo_case()
        sections, _, _ = scenario
        _, history = run_simulation_with_history(scenario, snapshot_interval=0.5, verbose=False)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = f"{temp_dir}/history.json"
            saved_path = save_replay_history_json(sections, history, output_path=output_path)
            self.assertEqual(saved_path, output_path)

            with open(saved_path, "r", encoding="utf-8") as history_file:
                payload = json.load(history_file)

        self.assertEqual(payload["format_version"], 1)
        self.assertTrue(payload["sections"])
        self.assertTrue(payload["history"])
        first_step = payload["history"][0]
        self.assertEqual(first_step["step"], 0)
        self.assertIn("agents", first_step)
        self.assertIn("stats", first_step)
        self.assertIn("remaining_count", first_step["stats"])

    def test_run_simulation_with_history_writes_full_step_trace_jsonl_and_meta(self):
        scenario = build_rows_demo_case()

        with tempfile.TemporaryDirectory() as temp_dir:
            steps_path = os.path.join(temp_dir, "replay_steps.jsonl")
            meta_path = os.path.join(temp_dir, "replay_meta.json")
            result, _history = run_simulation_with_history(
                scenario,
                snapshot_interval=0.5,
                verbose=False,
                step_output_path=steps_path,
                step_meta_output_path=meta_path,
            )

            self.assertTrue(os.path.exists(steps_path))
            self.assertTrue(os.path.exists(meta_path))

            with open(meta_path, "r", encoding="utf-8") as meta_file:
                meta = json.load(meta_file)
            self.assertEqual(meta["format_version"], 1)
            self.assertEqual(meta["people_count"], result["total_people"])
            self.assertGreaterEqual(meta["step_count"], 1)
            self.assertIn("sections", meta)

            with open(steps_path, "r", encoding="utf-8") as steps_file:
                lines = [json.loads(line) for line in steps_file]

            self.assertEqual(len(lines), meta["step_count"])
            self.assertEqual(lines[0]["step"], 0)
            self.assertIn("people", lines[0])
            self.assertIn("stats", lines[0])
            first_person = lines[0]["people"][0]
            self.assertIn("row_index", first_person)
            self.assertIn("flow_delta_x", first_person)

    def test_build_section_layout_simple_keeps_multi_segment_chain(self):
        sections = {
            "horizontal_1": Segment(
                "horizontal_1",
                "horizontal",
                length=12.0,
                width=2.0,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=8.0,
                width=2.0,
            ),
        }

        layout = build_section_layout_simple(sections)

        self.assertEqual(layout["horizontal_1"].start, (0.0, 4.0))
        self.assertEqual(layout["horizontal_1"].end, (12.0, 4.0))
        self.assertEqual(layout["horizontal_2"].start, (12.0, 4.0))
        self.assertEqual(layout["horizontal_2"].end, (20.0, 4.0))

    def test_visual_placements_keep_people_of_same_row_on_same_x_band(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0)
        snapshot = Snapshot(
            time=0.0,
            people=[
                PersonState(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00, row_index=0, place_in_row=0, finished=False, exit_time=None),
                PersonState(pid=2, group="M0_3", section_id="horizontal_1", x=5.10, row_index=0, place_in_row=1, finished=False, exit_time=None),
                PersonState(pid=3, group="M0_3", section_id="horizontal_1", x=5.15, row_index=0, place_in_row=2, finished=False, exit_time=None),
                PersonState(pid=4, group="M0_3", section_id="horizontal_1", x=5.90, row_index=1, place_in_row=0, finished=False, exit_time=None),
            ],
            section_counts={"horizontal_1": 4},
            finished_count=0,
            total_people=4,
        )
        layout = {"horizontal_1": SectionVisual(start=(0.0, 4.0), end=(12.0, 4.0))}

        placements = compute_snapshot_visual_placements(snapshot, {"horizontal_1": section}, layout)
        placements_by_pid = {placement.pid: placement for placement in placements}

        self.assertEqual(placements_by_pid[1].row_index, 0)
        self.assertEqual(placements_by_pid[2].row_index, 0)
        self.assertEqual(placements_by_pid[3].row_index, 0)
        self.assertEqual(placements_by_pid[4].row_index, 1)
        self.assertLess(abs(placements_by_pid[1].center[0] - placements_by_pid[2].center[0]), 0.15)
        self.assertLess(abs(placements_by_pid[2].center[0] - placements_by_pid[3].center[0]), 0.15)
        self.assertLess(placements_by_pid[4].center[0], placements_by_pid[1].center[0])

    def test_visual_placements_support_people_on_multiple_sections(self):
        sections = {
            "horizontal_1": Segment(
                "horizontal_1",
                "horizontal",
                length=12.0,
                width=2.0,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=10.0,
                width=2.0,
            ),
        }
        snapshot = Snapshot(
            time=1.0,
            people=[
                PersonState(pid=1, group="M0_3", section_id="horizontal_1", x=4.0, finished=False, exit_time=None),
                PersonState(pid=2, group="M0_3", section_id="horizontal_2", x=9.0, finished=False, exit_time=None),
            ],
            section_counts={"horizontal_1": 1, "horizontal_2": 1},
            finished_count=0,
            total_people=2,
        )
        layout = build_section_layout_simple(sections)

        placements = compute_snapshot_visual_placements(snapshot, sections, layout)
        placements_by_pid = {placement.pid: placement for placement in placements}

        self.assertIn(1, placements_by_pid)
        self.assertIn(2, placements_by_pid)
        self.assertLess(placements_by_pid[1].center[0], layout["horizontal_1"].end[0])
        self.assertGreater(placements_by_pid[2].center[0], layout["horizontal_2"].start[0])


if __name__ == "__main__":
    unittest.main()
