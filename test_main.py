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
)


class MainRowBuildingTests(unittest.TestCase):
    def test_wheelchair_and_three_m0_3_are_split_into_two_rows(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0, exit_width=1.2)
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
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0, exit_width=1.0)
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
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0, exit_width=1.0)
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

    def test_step_prevents_back_row_from_passing_front_row(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=1.0, exit_width=1.0)
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
                exit_width=1.2,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=8.0,
                width=2.0,
                exit_width=1.2,
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

    def test_demo_input_data_builder_is_exported_from_input_component(self):
        self.assertEqual(build_rows_demo_case.__module__, "src.input_data_component")

    def test_run_simulation_with_history_supports_demo_multi_segment_case(self):
        scenario = build_rows_demo_case()

        result, history = run_simulation_with_history(scenario, snapshot_interval=0.5, verbose=False)

        self.assertEqual(result["finished_count"], result["total_people"])
        self.assertGreater(result["modeled_path_length_m"], 50.0)
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
                exit_width=1.2,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=8.0,
                width=2.0,
                exit_width=1.2,
            ),
        }

        layout = build_section_layout_simple(sections)

        self.assertEqual(layout["horizontal_1"].start, (0.0, 4.0))
        self.assertEqual(layout["horizontal_1"].end, (12.0, 4.0))
        self.assertEqual(layout["horizontal_2"].start, (12.0, 4.0))
        self.assertEqual(layout["horizontal_2"].end, (20.0, 4.0))

    def test_visual_placements_keep_people_of_same_row_on_same_x_band(self):
        section = Segment("horizontal_1", "horizontal", length=12.0, width=2.0, exit_width=1.2)
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
                exit_width=1.2,
                next_section_id="horizontal_2",
            ),
            "horizontal_2": Segment(
                "horizontal_2",
                "horizontal",
                length=10.0,
                width=2.0,
                exit_width=1.2,
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
