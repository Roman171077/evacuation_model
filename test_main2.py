import unittest

from main import (
    Person,
    Segment,
    PersonState,
    Snapshot,
    SimulationParams,
    SinglePersonSingleSegmentModel,
    apply_row_geometry_on_section,
    build_rows_on_section,
    compute_snapshot_visual_placements,
)


class Main2RowBuildingTests(unittest.TestCase):
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
        self.assertAlmostEqual(people[2].x, 7.03)

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

    def test_same_row_does_not_let_faster_people_overtake_wheelchair(self):
        section = Segment("horizontal_1", "horizontal", length=50.0, width=2.0, exit_width=1.2)
        people = [
            Person(pid=1, group="M4_WHEELCHAIR", section_id="horizontal_1", x=40.00),
            Person(pid=2, group="M0_3", section_id="horizontal_1", x=45.00),
            Person(pid=3, group="M0_3", section_id="horizontal_1", x=45.50),
            Person(pid=4, group="M0_3", section_id="horizontal_1", x=46.00),
            Person(pid=5, group="M0_3", section_id="horizontal_1", x=48.00),
            Person(pid=6, group="M0_3", section_id="horizontal_1", x=46.50),
            Person(pid=7, group="M0_3", section_id="horizontal_1", x=47.00),
            Person(pid=8, group="M0_3", section_id="horizontal_1", x=47.50),
            Person(pid=9, group="M0_3", section_id="horizontal_1", x=48.00),
            Person(pid=10, group="M0_3", section_id="horizontal_1", x=48.50),
            Person(pid=11, group="M0_3", section_id="horizontal_1", x=49.00),
            Person(pid=12, group="M0_3", section_id="horizontal_1", x=49.70),
        ]
        params = SimulationParams(dt=0.1, max_time=60.0)
        model = SinglePersonSingleSegmentModel({"horizontal_1": section}, people, params)

        apply_row_geometry_on_section(model.people, section)
        for _ in range(150):
            model.step()
            model.time += model.params.dt

            wheelchair = next(person for person in people if person.pid == 1)
            active_people = [person for person in people if not person.finished and person.pid != 1]
            self.assertFalse(
                any(person.x < wheelchair.x - 1e-9 for person in active_people),
                "Более быстрые M0_3 не должны обгонять кресло-коляску по координате x.",
            )

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
        from main import SectionVisual
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


if __name__ == "__main__":
    unittest.main()
