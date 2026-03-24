from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List

import plotly.graph_objects as go
import streamlit as st

from src.rows_model import PersonState, Segment, Snapshot
from src.visualization import (
    SectionVisual,
    build_section_layout_simple,
    compute_snapshot_visual_placements,
)


@dataclass
class ReplayData:
    sections: Dict[str, Segment]
    history: List[Snapshot]


def load_replay_data(history_path: str) -> ReplayData:
    with open(history_path, "r", encoding="utf-8") as history_file:
        payload = json.load(history_file)

    sections = {
        section_data["sid"]: Segment(
            sid=section_data["sid"],
            section_type=section_data["section_type"],
            length=float(section_data["length"]),
            width=float(section_data["width"]),
            next_section_id=section_data.get("next_section_id"),
            merge_lj=float(section_data.get("merge_lj", 0.0)),
            row_capacity=section_data.get("row_capacity"),
        )
        for section_data in payload.get("sections", [])
    }

    history: List[Snapshot] = []
    for step_payload in payload.get("history", []):
        stats = step_payload.get("stats", {})
        people = [PersonState(**agent_payload) for agent_payload in step_payload.get("agents", [])]
        history.append(
            Snapshot(
                time=float(step_payload.get("time", 0.0)),
                people=people,
                section_counts=dict(stats.get("section_counts", {})),
                finished_count=int(stats.get("finished_count", 0)),
                total_people=int(stats.get("total_people", len(people))),
            )
        )

    return ReplayData(sections=sections, history=history)


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
    fig.add_trace(
        go.Scatter(
            x=[placement.center[0] for placement in placements],
            y=[placement.center[1] for placement in placements],
            mode="markers+text",
            text=[placement.label for placement in placements],
            textposition="middle center",
            textfont=dict(size=9, color="#111827"),
            marker=dict(
                size=[max(14, int(placement.width_m * 28)) for placement in placements],
                color=[placement.color for placement in placements],
                line=dict(width=1, color="#111827"),
                opacity=0.9,
            ),
            hovertemplate=(
                "pid=%{customdata[0]}<br>section=%{customdata[1]}"
                "<br>row=%{customdata[2]} place=%{customdata[3]}<extra></extra>"
            ),
            customdata=[
                [placement.pid, placement.section_id, placement.row_index, placement.place_in_row]
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

    history_path = st.text_input("Путь к history.json", value="artifacts/history.json")

    if not os.path.exists(history_path):
        st.warning("Файл history не найден. Сначала запустите `python main.py`, чтобы сформировать artifacts/history.json.")
        return

    replay_data = load_replay_data(history_path)
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
            st.json(snapshot.section_counts)
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
