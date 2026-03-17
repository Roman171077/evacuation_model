from scenarios.test_case_1 import build_test_case_1
from src.simulation.simulation import EvacuationModel


if __name__ == "__main__":
    sections, people, params = build_test_case_1()
    model = EvacuationModel(sections, people, params)
    result = model.run(verbose=True)

    print("\nРЕЗУЛЬТАТ:")
    print(f"Общее время эвакуации: {result['total_evacuation_time_sec']:.2f} с")
    print(f"Эвакуировано: {result['finished_count']} из {result['total_people']}")

    print("\nВремя выхода по людям:")
    for p in sorted(people, key=lambda x: x.pid):
        print(f"Чел {p.pid:>2} | группа={p.group:<13} | вышел={p.finished} | t_exit={p.exit_time}")
