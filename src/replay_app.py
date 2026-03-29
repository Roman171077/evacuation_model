from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List

import plotly.graph_objects as go
import streamlit as st

from src.rows_model import (
    Person,
    PersonState,
    Segment,
    Snapshot,
    compute_person_speed_components_stage1,
    update_person_local_density_on_sections,
    update_rows_and_flows_on_sections,
)
from src.visualization import (
    SectionVisual,
    build_section_layout_simple,
    compute_snapshot_visual_placements,
)


@dataclass
class ReplayData:
    sections: Dict[str, Segment]
    history: List[Snapshot]


def _compute_m(section_type: str, density: float) -> float:
    if section_type == "door" and density >= 0.5:
        return 1.25 - 0.05 * density
    return 1.0


def _to_person_state(agent_payload: Dict[str, object]) -> PersonState:
    return PersonState(
        pid=int(agent_payload.get("pid", 0)),
        group=str(agent_payload.get("group", "")),
        section_id=str(agent_payload.get("section_id", "")),
        x=float(agent_payload.get("x", 0.0)),
        v=float(agent_payload.get("v", 0.0)),
        speed_mps=float(agent_payload.get("speed_mps", agent_payload.get("v", 0.0))),
        v0_mpm=float(agent_payload.get("v0_mpm", 0.0)),
        d0=float(agent_payload.get("d0", 0.0)),
        ai=float(agent_payload.get("ai", 0.0)),
        m=float(agent_payload.get("m", 1.0)),
        section_type=str(agent_payload.get("section_type", "")),
        speed_section_type=str(agent_payload.get("speed_section_type", "")),
        row_index=int(agent_payload.get("row_index", -1)),
        place_in_row=int(agent_payload.get("place_in_row", -1)),
        flow_index=int(agent_payload.get("flow_index", -1)),
        place_in_flow=int(agent_payload.get("place_in_flow", -1)),
        flow_start_x=float(agent_payload.get("flow_start_x", 0.0)),
        flow_end_x=float(agent_payload.get("flow_end_x", 0.0)),
        flow_delta_x=float(agent_payload.get("flow_delta_x", 0.0)),
        flow_density=float(agent_payload.get("flow_density", 0.0)),
        local_density=float(agent_payload.get("local_density", 0.0)),
        other_flow_people_ids=[int(pid) for pid in agent_payload.get("other_flow_people_ids", [])],  # type: ignore[arg-type]
        finished=bool(agent_payload.get("finished", False)),
        exit_time=float(agent_payload["exit_time"]) if agent_payload.get("exit_time") is not None else None,
    )


def _load_sections_from_meta(meta_path: str) -> Dict[str, Segment]:
    with open(meta_path, "r", encoding="utf-8") as meta_file:
        meta_payload = json.load(meta_file)

    return {
        section_data["sid"]: Segment(
            sid=section_data["sid"],
            section_type=section_data["section_type"],
            length=float(section_data["length"]),
            width=float(section_data["width"]),
            exit_width_cj=float(section_data["exit_width_cj"]) if section_data.get("exit_width_cj") is not None else None,
            next_section_id=section_data.get("next_section_id"),
            next_by_group=dict(section_data.get("next_by_group", {})),
            next_default=section_data.get("next_default"),
            merge_lj=float(section_data.get("merge_lj", 0.0)),
            row_capacity=section_data.get("row_capacity"),
        )
        for section_data in meta_payload.get("sections", [])
    }


def _load_json_history(history_path: str) -> ReplayData:
    with open(history_path, "r", encoding="utf-8") as history_file:
        payload = json.load(history_file)

    sections = {
        section_data["sid"]: Segment(
            sid=section_data["sid"],
            section_type=section_data["section_type"],
            length=float(section_data["length"]),
            width=float(section_data["width"]),
            exit_width_cj=float(section_data["exit_width_cj"]) if section_data.get("exit_width_cj") is not None else None,
            next_section_id=section_data.get("next_section_id"),
            next_by_group=dict(section_data.get("next_by_group", {})),
            next_default=section_data.get("next_default"),
            merge_lj=float(section_data.get("merge_lj", 0.0)),
            row_capacity=section_data.get("row_capacity"),
        )
        for section_data in payload.get("sections", [])
    }

    history: List[Snapshot] = []
    for step_payload in payload.get("history", []):
        stats = step_payload.get("stats", {})
        people = [_to_person_state(agent_payload) for agent_payload in step_payload.get("agents", [])]
        history.append(
            Snapshot(
                time=float(step_payload.get("time", 0.0)),
                people=people,
                section_counts=dict(stats.get("section_counts", {})),
                section_flow_density={
                    sid: float(value)
                    for sid, value in dict(stats.get("section_flow_density", {})).items()
                },
                section_intensity_qj={
                    sid: float(value)
                    for sid, value in dict(stats.get("section_intensity_qj", {})).items()
                },
                section_capacity_qj={
                    sid: int(value)
                    for sid, value in dict(stats.get("section_capacity_qj", {})).items()
                },
                finished_count=int(stats.get("finished_count", 0)),
                total_people=int(stats.get("total_people", len(people))),
            )
        )

    return ReplayData(sections=sections, history=history)


def _load_jsonl_history(steps_path: str, meta_path: str) -> ReplayData:
    sections = _load_sections_from_meta(meta_path)
    history: List[Snapshot] = []

    with open(steps_path, "r", encoding="utf-8") as steps_file:
        for line in steps_file:
            step_payload = json.loads(line)
            stats = step_payload.get("stats", {})
            people = [_to_person_state(agent_payload) for agent_payload in step_payload.get("people", [])]
            history.append(
                Snapshot(
                    time=float(step_payload.get("time", 0.0)),
                    people=people,
                    section_counts=dict(stats.get("section_counts", {})),
                    section_flow_density={
                        sid: float(value)
                        for sid, value in dict(stats.get("section_flow_density", {})).items()
                    },
                    section_intensity_qj={
                        sid: float(value)
                        for sid, value in dict(stats.get("section_intensity_qj", {})).items()
                    },
                    section_capacity_qj={
                        sid: int(value)
                        for sid, value in dict(stats.get("section_capacity_qj", {})).items()
                    },
                    finished_count=int(stats.get("finished_count", 0)),
                    total_people=int(stats.get("total_people", len(people))),
                )
            )

    return ReplayData(sections=sections, history=history)


def _recompute_snapshot_position_state(snapshot: Snapshot, sections: Dict[str, Segment]) -> None:
    active_people = [
        Person(
            pid=person.pid,
            group=person.group,
            section_id=person.section_id,
            x=person.x,
            v=person.v,
            finished=person.finished,
            exit_time=person.exit_time,
        )
        for person in snapshot.people
        if not person.finished
    ]

    if active_people:
        section_state = update_rows_and_flows_on_sections(active_people, sections)
        update_person_local_density_on_sections(active_people, sections, section_state)

    state_by_pid = {person.pid: person for person in active_people}
    for person_state in snapshot.people:
        source = state_by_pid.get(person_state.pid)
        if source is None:
            person_state.row_index = -1
            person_state.place_in_row = -1
            person_state.flow_index = -1
            person_state.place_in_flow = -1
            person_state.flow_start_x = 0.0
            person_state.flow_end_x = 0.0
            person_state.flow_delta_x = 0.0
            person_state.flow_density = 0.0
            person_state.local_density = 0.0
            person_state.other_flow_people_ids = []
            continue

        person_state.row_index = source.row_index
        person_state.place_in_row = source.place_in_row
        person_state.flow_index = source.flow_index
        person_state.place_in_flow = source.place_in_flow
        person_state.flow_start_x = source.flow_start_x
        person_state.flow_end_x = source.flow_end_x
        person_state.flow_delta_x = source.flow_delta_x
        person_state.flow_density = source.flow_density
        person_state.local_density = source.local_density
        if source.section_id in sections:
            section = sections[source.section_id]
            speed_components = compute_person_speed_components_stage1(source, section)
            person_state.section_type = str(speed_components["section_type"])
            person_state.speed_section_type = str(speed_components["speed_section_type"])
            person_state.v0_mpm = float(speed_components["V0"])
            person_state.d0 = float(speed_components["D0"])
            person_state.ai = float(speed_components["ai"])
            person_state.m = float(speed_components["m"])
        else:
            person_state.section_type = ""
            person_state.speed_section_type = ""
        person_state.other_flow_people_ids = list(source.other_flow_people_ids)


def load_replay_data(history_path: str, meta_path: str) -> ReplayData:
    replay_data = _load_jsonl_history(history_path, meta_path) if history_path.endswith(".jsonl") else _load_json_history(history_path)
    for snapshot in replay_data.history:
        if not snapshot.section_flow_density:
            snapshot.section_flow_density = {
                sid: 0.0 for sid in replay_data.sections.keys()
            }
        _recompute_snapshot_position_state(snapshot, replay_data.sections)
    return replay_data


def _build_flow_membership_rows(snapshot: Snapshot, sections: Dict[str, Segment]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for sid in sections.keys():
        section_people = [
            person
            for person in snapshot.people
            if not person.finished and person.section_id == sid
        ]
        section_people.sort(key=lambda person: (person.flow_index < 0, person.flow_index, person.place_in_flow, person.x, person.pid))

        for person in section_people:
            section_type = sections[sid].section_type
            m = person.m if person.m > 0 else _compute_m(section_type, max(0.0, person.local_density))
            other_flow_people = (
                ", ".join(str(pid) for pid in person.other_flow_people_ids)
                if person.other_flow_people_ids
                else "—"
            )
            rows.append(
                {
                    "section": sid,
                    "section_type": section_type,
                    "speed_section_type": person.speed_section_type or section_type,
                    "pid": str(person.pid),
                    "flow": f"F{person.flow_index}" if person.flow_index >= 0 else "—",
                    "status": "в потоке" if person.flow_index >= 0 else "вне потока",
                    "x, м": f"{person.x:.2f}",
                    "speed_mps": f"{person.speed_mps:.3f}",
                    "v0_mpm": f"{person.v0_mpm:.1f}",
                    "ai": f"{person.ai:.3f}",
                    "d0": f"{person.d0:.3f}",
                    "m": f"{m:.3f}",
                    "D потока, м²/м²": f"{person.local_density:.3f}",
                    "pid других людей в потоке": other_flow_people,
                }
            )

    return rows


def build_frame_figure(
    snapshot: Snapshot,
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
) -> go.Figure:
    fig = go.Figure()

    for sid, section in sections.items():
        visual = layout[sid]
        fig.add_trace(
            go.Scatter(
                x=[visual.start[0], visual.end[0]],
                y=[visual.start[1], visual.end[1]],
                mode="lines",
                line=dict(color="#4b5563", width=7),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_annotation(
            x=(visual.start[0] + visual.end[0]) / 2,
            y=visual.start[1] + 0.45,
            text=f"{sid}<br>L={section.length:.1f} м",
            showarrow=False,
            font=dict(size=11, color="#111827"),
            align="center",
        )

    placements = compute_snapshot_visual_placements(snapshot, sections, layout)
    person_state_by_pid = {person.pid: person for person in snapshot.people}
    for placement in placements:
        fig.add_shape(
            type="rect",
            x0=placement.center[0] - placement.length_m / 2,
            x1=placement.center[0] + placement.length_m / 2,
            y0=placement.center[1] - placement.width_m / 2,
            y1=placement.center[1] + placement.width_m / 2,
            line=dict(color="#111827", width=1),
            fillcolor=placement.color,
            opacity=0.9,
            layer="above",
        )

    fig.add_trace(
        go.Scatter(
            x=[placement.center[0] for placement in placements],
            y=[placement.center[1] for placement in placements],
            mode="text",
            text=[placement.label for placement in placements],
            textposition="middle center",
            textfont=dict(size=9, color="#111827"),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[placement.center[0] for placement in placements],
            y=[placement.center[1] for placement in placements],
            mode="markers",
            marker=dict(size=10, color="rgba(0,0,0,0)"),
            hovertemplate=(
                "pid=%{customdata[0]}<br>section=%{customdata[1]}"
                "<br>row=%{customdata[2]} place=%{customdata[3]}"
                "<br>flow=%{customdata[4]} place=%{customdata[5]}"
                "<br>D потока=%{customdata[6]:.3f}"
                "<br>другие pid в потоке=%{customdata[7]}<extra></extra>"
            ),
            customdata=[
                [
                    placement.pid,
                    placement.section_id,
                    placement.row_index,
                    placement.place_in_row,
                    person_state_by_pid[placement.pid].flow_index,
                    person_state_by_pid[placement.pid].place_in_flow,
                    person_state_by_pid[placement.pid].flow_density,
                    (", ".join(str(pid) for pid in person_state_by_pid[placement.pid].other_flow_people_ids)
                     if person_state_by_pid[placement.pid].other_flow_people_ids
                     else "—"),
                ]
                for placement in placements
            ],
            showlegend=False,
        )
    )

    xs = [point for visual in layout.values() for point in (visual.start[0], visual.end[0])]
    ys = [point for visual in layout.values() for point in (visual.start[1], visual.end[1])]
    margin = 1.6
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white",
        title="Покадровый replay эвакуации",
        height=520,
        xaxis=dict(visible=False, range=[min(xs) - margin, max(xs) + margin + 1.0]),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1, range=[min(ys) - margin, max(ys) + margin]),
    )
    return fig


def main() -> None:
    st.set_page_config(page_title="Evacuation Replay", layout="wide")
    st.title("Покадровый replay эвакуации")

    history_path = st.text_input("Путь к history (json/jsonl)", value="artifacts/replay_steps.jsonl")
    meta_path = st.text_input("Путь к replay_meta.json", value="artifacts/replay_meta.json")

    if not os.path.exists(history_path):
        st.warning(
            "Файл history не найден. Сначала запустите `python main.py`, "
            "чтобы сформировать artifacts/replay_steps.jsonl."
        )
        return

    if history_path.endswith(".jsonl") and not os.path.exists(meta_path):
        st.warning(
            "Для JSONL-режима нужен файл meta. Запустите `python main.py`, "
            "чтобы сформировать artifacts/replay_meta.json."
        )
        return

    replay_data = load_replay_data(history_path, meta_path)
    if not replay_data.history:
        st.info("История пуста: нет шагов для отображения.")
        return

    max_step = len(replay_data.history) - 1
    if "current_step" not in st.session_state:
        st.session_state.current_step = 0
    if "is_playing" not in st.session_state:
        st.session_state.is_playing = False

    st.session_state.current_step = max(0, min(max_step, int(st.session_state.current_step)))

    prev_col, play_col, next_col, speed_col = st.columns([1, 1, 1, 2])
    with prev_col:
        if st.button("◀ Шаг назад", use_container_width=True):
            st.session_state.is_playing = False
            st.session_state.current_step = max(0, st.session_state.current_step - 1)
    with play_col:
        play_label = "⏸ Пауза" if st.session_state.is_playing else "▶ Пуск"
        if st.button(play_label, use_container_width=True):
            st.session_state.is_playing = not st.session_state.is_playing
    with next_col:
        if st.button("Шаг вперед ▶", use_container_width=True):
            st.session_state.is_playing = False
            st.session_state.current_step = min(max_step, st.session_state.current_step + 1)
    with speed_col:
        frame_delay = st.slider("Задержка между шагами, мс", min_value=50, max_value=2000, value=250, step=50)

    if max_step == 0:
        st.caption("Доступен только один шаг (0).")
        selected_step = 0
    else:
        selected_step = st.slider("Шаг", min_value=0, max_value=max_step, value=st.session_state.current_step)
    if selected_step != st.session_state.current_step:
        st.session_state.is_playing = False
        st.session_state.current_step = selected_step

    snapshot = replay_data.history[st.session_state.current_step]
    layout = build_section_layout_simple(replay_data.sections)
    figure = build_frame_figure(snapshot, replay_data.sections, layout)
    st.plotly_chart(figure, use_container_width=True)

    remaining_count = snapshot.total_people - snapshot.finished_count
    info_cols = st.columns(4)
    info_cols[0].metric("Шаг", f"{st.session_state.current_step + 1} / {len(replay_data.history)}")
    info_cols[1].metric("Время модели", f"{snapshot.time:.2f} с")
    info_cols[2].metric("Эвакуировано", f"{snapshot.finished_count}/{snapshot.total_people}")
    info_cols[3].metric("Осталось", remaining_count)

    with st.expander("Люди по участкам"):
        if snapshot.section_counts:
            section_rows = []
            for sid in replay_data.sections.keys():
                section_rows.append(
                    {
                        "Участок": sid,
                        "Людей, чел.": snapshot.section_counts.get(sid, 0),
                        "Dvj(t), м²/м²": round(snapshot.section_flow_density.get(sid, 0.0), 4),
                    }
                )
            st.dataframe(section_rows, use_container_width=True, hide_index=True)
        else:
            st.write("Нет активных людей на участках.")

    with st.expander("Локальные потоки и одиночные люди"):
        flow_rows = _build_flow_membership_rows(snapshot, replay_data.sections)
        if flow_rows:
            st.dataframe(flow_rows, use_container_width=True, hide_index=True)
        else:
            st.write("Нет активных людей на участках.")

    if st.session_state.is_playing:
        if st.session_state.current_step >= max_step:
            st.session_state.is_playing = False
        else:
            time.sleep(frame_delay / 1000.0)
            st.session_state.current_step = min(max_step, st.session_state.current_step + 1)
            st.rerun()


if __name__ == "__main__":
    main()
