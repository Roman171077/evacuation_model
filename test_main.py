import unittest

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
    run_simulation_with_history,
    update_people_position_state_on_sections,
)


class MainRowBuildingTests(unittest.TestCase):
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

    def test_apply_row_geometry_moves_new_rows_back_along_x(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=5.00),
        ]

        rows = apply_row_geometry_on_section(people, section)

        self.assertEqual(len(rows), 3)
        self.assertAlmostEqual(people[0].x, 5.00)
        self.assertAlmostEqual(people[1].x, 6.20)
        self.assertAlmostEqual(people[2].x, 6.94)

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

    def test_step_prevents_back_row_from_passing_front_row(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.20),
        ]
        params = SimulationParams(dt=2.0, max_time=10.0)
        model = SinglePersonSingleSegmentModel({"horizontal_1": section}, people, params)

        apply_row_geometry_on_section(model.people, section)
        model.step()

        front_person = min(people, key=lambda person: person.x)
        back_person = max(people, key=lambda person: person.x)

        self.assertGreaterEqual(
            back_person.x - back_person.c_geom / 2.0,
            front_person.x + front_person.c_geom / 2.0 - 1e-9,
        )

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
        self.assertEqual(person.row_index, 0)
        self.assertEqual(person.place_in_row, 0)
        self.assertTrue(person.is_alone_on_section)
        self.assertTrue(person.is_single_in_row)
        self.assertFalse(person.is_in_flow)
        self.assertEqual(person.flow_index, -1)
        self.assertEqual(person.place_in_flow, -1)
        self.assertEqual(person.flow_member_count, 0)
        self.assertEqual(person.flow_delta_x, 0.0)

    def test_position_state_for_multiple_people_in_one_row(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0)
        people = [
            Person(pid=1, group="M0_3", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=5.05),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=5.10),
        ]

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})

        self.assertEqual(len(state["horizontal_1"]["rows"]), 1)
        self.assertEqual(len(state["horizontal_1"]["flows"]), 0)
        for expected_place, person in enumerate(people):
            self.assertEqual(person.row_index, 0)
            self.assertEqual(person.place_in_row, expected_place)
            self.assertFalse(person.is_alone_on_section)
            self.assertFalse(person.is_single_in_row)
            self.assertFalse(person.is_in_flow)
            self.assertEqual(person.flow_index, -1)
            self.assertEqual(person.flow_delta_x, 0.0)

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

    def test_position_state_for_consecutive_rows_forming_flow(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=2, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
            Person(pid=3, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00),
        ]

        state = update_people_position_state_on_sections(people, {"horizontal_1": section})
        flows = state["horizontal_1"]["flows"]

        self.assertEqual(len(state["horizontal_1"]["rows"]), 3)
        self.assertEqual(len(flows), 1)
        self.assertAlmostEqual(flows[0].start_x, people[0].x)
        self.assertAlmostEqual(flows[0].end_x, people[2].x)
        self.assertAlmostEqual(flows[0].delta_x, people[2].x - people[0].x)
        for expected_row, person in enumerate(people):
            self.assertEqual(person.row_index, expected_row)
            self.assertTrue(person.is_in_flow)
            self.assertEqual(person.flow_index, 0)
            self.assertEqual(person.place_in_flow, expected_row)
            self.assertEqual(person.flow_member_count, 3)
            self.assertAlmostEqual(person.flow_start_x, people[0].x)
            self.assertAlmostEqual(person.flow_end_x, people[2].x)
            self.assertAlmostEqual(person.flow_delta_x, people[2].x - people[0].x)

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
        self.assertEqual(people[1].row_index, 0)
        self.assertEqual(people[0].row_index, 1)
        self.assertTrue(people[0].is_in_flow)
        self.assertTrue(people[1].is_in_flow)
        self.assertEqual(people[0].flow_index, 0)
        self.assertEqual(people[1].flow_index, 0)
        self.assertEqual(people[0].flow_member_count, 2)
        self.assertEqual(people[1].flow_member_count, 2)
        self.assertGreater(people[0].x, people[1].x)
        self.assertAlmostEqual(people[0].flow_start_x, people[1].x)
        self.assertAlmostEqual(people[0].flow_end_x, people[0].x)

    def test_demo_input_data_builder_is_exported_from_input_component(self):
        self.assertEqual(build_rows_demo_case.__module__, "src.input_data_component")

    def test_run_simulation_with_history_supports_demo_multi_segment_case(self):
        scenario = build_rows_demo_case()

        result, history = run_simulation_with_history(scenario, snapshot_interval=0.5, verbose=False)

        self.assertEqual(result["finished_count"], result["total_people"])
        self.assertGreaterEqual(result["modeled_path_length_m"], 50.0)
        self.assertGreater(len(history), 1)
        self.assertIn("horizontal_1", history[0].section_counts)
        self.assertIn("horizontal_2", history[0].section_counts)

    def test_visual_api_is_exported_from_separate_module(self):
        self.assertEqual(compute_snapshot_visual_placements.__module__, "src.visualization")

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
                PersonState(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=5.00, finished=False, exit_time=None),
                PersonState(pid=2, group="M0_3", section_id="horizontal_1", x=5.10, finished=False, exit_time=None),
                PersonState(pid=3, group="M0_3", section_id="horizontal_1", x=5.15, finished=False, exit_time=None),
                PersonState(pid=4, group="M0_3", section_id="horizontal_1", x=5.90, finished=False, exit_time=None),
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
