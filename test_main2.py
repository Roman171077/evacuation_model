import unittest

from main2 import (
    Person,
    Segment,
    SimulationParams,
    EvacuationModel,
    compute_capacity_people_per_step,
    compute_person_speed,
    compute_section_flow_density,
)


class Main2MethodologyTests(unittest.TestCase):
    def test_person_moves_by_x_equals_x_prev_minus_v_dt(self):
        section = Segment("s1", "horizontal", length=10.0, width=2.0, exit_width=1.2)
        person = Person(pid=1, group="M0_7", section_id="s1", x=5.0)
        params = SimulationParams(dt=1.0, max_time=10.0)

        model = EvacuationModel({"s1": section}, [person], params)
        model.step()

        expected_v = compute_person_speed(person, section, local_density=0.0)
        self.assertAlmostEqual(person.v, expected_v, places=9)
        self.assertAlmostEqual(person.x, 5.0 - expected_v * params.dt, places=9)

    def test_transition_uses_lj_formula(self):
        sections = {
            "s1": Segment("s1", "horizontal", length=1.0, width=2.0, exit_width=5.0, next_section_id="s2"),
            "s2": Segment("s2", "horizontal", length=5.0, width=2.0, exit_width=5.0, merge_lj=1.5),
        }
        person = Person(pid=1, group="M0_7", section_id="s1", x=0.1)
        params = SimulationParams(dt=1.0, max_time=10.0)

        model = EvacuationModel(sections, [person], params)
        model.step()

        expected_x_raw = 0.1 - compute_person_speed(person, sections["s1"], 0.0) * params.dt
        expected_x_new = expected_x_raw + sections["s2"].length - sections["s2"].merge_lj
        self.assertEqual(person.section_id, "s2")
        self.assertAlmostEqual(person.x_raw, expected_x_raw, places=9)
        self.assertAlmostEqual(person.x, expected_x_new, places=9)

    def test_capacity_formula_allows_everyone_when_m_not_greater_than_q(self):
        section = Segment("s1", "horizontal", length=1.0, width=2.0, exit_width=5.0)
        people = [Person(pid=1, group="M0_7", section_id="s1", x=0.1)]
        params = SimulationParams(dt=1.0, max_time=10.0)

        allowed = compute_capacity_people_per_step(people, section, params)
        self.assertGreaterEqual(allowed, 1)

        model = EvacuationModel({"s1": section}, people, params)
        model.step()
        self.assertTrue(people[0].finished)

    def test_queue_coordinates_and_order_are_preserved_when_capacity_is_insufficient(self):
        section = Segment("s1", "horizontal", length=1.0, width=0.4, exit_width=0.0)
        section.transfer_credit = 1.0
        people = [
            Person(pid=10, group="M0_7", section_id="s1", x=0.10),
            Person(pid=7, group="M0_7", section_id="s1", x=0.20),
            Person(pid=2, group="M0_7", section_id="s1", x=0.30),
        ]
        params = SimulationParams(dt=1.0, max_time=10.0)

        model = EvacuationModel({"s1": section}, people, params)
        model.step()

        waiting = [p for p in people if not p.finished]
        self.assertEqual([p.pid for p in waiting], [7, 2])
        self.assertAlmostEqual(waiting[0].x, 0.25, places=9)
        self.assertAlmostEqual(waiting[1].x, 0.50, places=9)

    def test_flow_density_matches_p75_formula(self):
        section = Segment("s1", "horizontal", length=10.0, width=2.0, exit_width=1.2)
        people = [
            Person(pid=1, group="M0_7", section_id="s1", x=9.0),
            Person(pid=2, group="M0_7", section_id="s1", x=8.0),
        ]
        params = SimulationParams(dt=0.5, max_time=10.0)

        density = compute_section_flow_density(people, section, params)
        expected = (2 * people[0].f * params.dt) / (section.length * section.width)
        self.assertAlmostEqual(density, expected, places=9)

    def test_two_streams_merge_without_losing_people(self):
        sections = {
            "a": Segment("a", "horizontal", length=1.0, width=2.0, exit_width=5.0, next_section_id="c"),
            "b": Segment("b", "horizontal", length=1.0, width=2.0, exit_width=5.0, next_section_id="c"),
            "c": Segment("c", "horizontal", length=6.0, width=2.0, exit_width=5.0),
        }
        people = [
            Person(pid=1, group="M0_7", section_id="a", x=0.10),
            Person(pid=2, group="M3_ODA", section_id="b", x=0.10),
        ]
        params = SimulationParams(dt=1.0, max_time=10.0)

        model = EvacuationModel(sections, people, params)
        model.step()

        self.assertEqual(sum(1 for p in people if p.section_id == "c"), 2)
        self.assertEqual(sum(1 for p in people if p.finished), 0)
        self.assertCountEqual([p.pid for p in people], [1, 2])


if __name__ == "__main__":
    unittest.main()
