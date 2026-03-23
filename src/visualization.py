from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from math import atan2, degrees, hypot
from typing import Dict, List, Tuple

HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None

if HAS_MATPLOTLIB:
    import matplotlib

    if sys.platform.startswith("win"):
        matplotlib.use("TkAgg")
    elif not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from matplotlib.lines import Line2D
    from matplotlib.patches import Ellipse
else:
    matplotlib = None
    plt = None

    class FuncAnimation:  # type: ignore[override]
        pass

    class Ellipse:  # type: ignore[override]
        def __init__(self, *args, **kwargs) -> None:
            pass

    class Line2D:  # type: ignore[override]
        def __init__(self, *args, **kwargs) -> None:
            pass

from src.rows_model import (
    MOBILITY_GROUP_COLORS,
    Person,
    Segment,
    Snapshot,
    build_rows_on_section,
    compute_person_row_centers,
    get_profile_color,
)


@dataclass
class SectionVisual:
    start: Tuple[float, float]
    end: Tuple[float, float]


@dataclass
class PersonVisualPlacement:
    pid: int
    section_id: str
    center: Tuple[float, float]
    length_m: float
    width_m: float
    color: str
    label: str
    row_index: int
    place_in_row: int


def require_matplotlib() -> None:
    if not HAS_MATPLOTLIB:
        raise ModuleNotFoundError(
            "matplotlib не установлен; расчетная часть доступна, визуализация недоступна."
        )


def build_section_layout_simple(sections: Dict[str, Segment]) -> Dict[str, SectionVisual]:
    if not sections:
        return {}

    referenced_sections = {
        section.next_section_id
        for section in sections.values()
        if section.next_section_id in sections
    }
    roots = [sid for sid in sections.keys() if sid not in referenced_sections]
    remaining = [sid for sid in sections.keys() if sid not in roots]
    chains: List[List[str]] = []
    visited: set[str] = set()

    def append_chain(start_sid: str) -> None:
        chain: List[str] = []
        sid = start_sid
        while sid not in visited and sid in sections:
            visited.add(sid)
            chain.append(sid)
            next_sid = sections[sid].next_section_id
            if next_sid is None or next_sid not in sections:
                break
            sid = next_sid
        if chain:
            chains.append(chain)

    for sid in roots:
        append_chain(sid)

    for sid in remaining:
        append_chain(sid)

    layout: Dict[str, SectionVisual] = {}
    base_y = 4.0
    chain_gap_y = 4.0

    for chain_index, chain in enumerate(chains):
        cursor_x = 0.0
        y = base_y + chain_index * chain_gap_y
        for sid in chain:
            section = sections[sid]
            layout[sid] = SectionVisual(
                start=(cursor_x, y),
                end=(cursor_x + section.length, y),
            )
            cursor_x += section.length

    return layout


def setup_axes(ax: plt.Axes, layout: Dict[str, SectionVisual]) -> None:
    require_matplotlib()
    xs: List[float] = []
    ys: List[float] = []

    for visual in layout.values():
        xs.extend([visual.start[0], visual.end[0]])
        ys.extend([visual.start[1], visual.end[1]])

    margin = 1.5
    ax.set_xlim(min(xs) - margin, max(xs) + margin + 2.0)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_sections(ax: plt.Axes, sections: Dict[str, Segment], layout: Dict[str, SectionVisual]) -> None:
    require_matplotlib()

    for sid, section in sections.items():
        visual = layout[sid]
        x0, y0 = visual.start
        x1, y1 = visual.end

        if section.section_type == "horizontal":
            color = "#8c8c8c"
            lw = 6
        elif section.section_type == "stairs_down":
            color = "#4d4d4d"
            lw = 7
        elif section.section_type == "door":
            color = "#262626"
            lw = 1
        else:
            color = "#8c8c8c"
            lw = 6

        ax.plot([x0, x1], [y0, y1], color=color, linewidth=lw, solid_capstyle="round")

        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops=dict(arrowstyle="->", lw=1.5, color="#404040"),
        )

        label_x = (x0 + x1) / 2
        label_y = (y0 + y1) / 2 + 0.35
        ax.text(
            label_x,
            label_y,
            f"{sid}\nL={section.length:.1f} м",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#222222",
        )

        if section.next_section_id is None:
            ex_x = x1 + 1.2
            ex_y = y1
            ax.plot(
                [x1, ex_x],
                [y1, ex_y],
                linestyle="--",
                linewidth=1.2,
                color="#6e6e6e",
            )
            ax.scatter([ex_x], [ex_y], s=120, marker="*", color="#2ca02c", zorder=6)
            ax.text(ex_x + 0.2, ex_y, "EXIT", va="center", ha="left", fontsize=10, color="#2ca02c")


def interpolate_position_on_section(section: Segment, visual: SectionVisual, local_x: float) -> Tuple[float, float]:
    """
    local_x — расстояние до конца участка.
    local_x = length -> начало участка
    local_x = 0      -> конец участка
    """
    x0, y0 = visual.start
    x1, y1 = visual.end

    if section.length <= 0:
        return visual.end

    progress = (section.length - local_x) / section.length
    progress = max(0.0, min(1.0, progress))

    px = x0 + (x1 - x0) * progress
    py = y0 + (y1 - y0) * progress
    return px, py


def perpendicular_unit_vector(visual: SectionVisual) -> Tuple[float, float]:
    dx = visual.end[0] - visual.start[0]
    dy = visual.end[1] - visual.start[1]
    length = hypot(dx, dy)

    if length <= 1e-9:
        return 0.0, 1.0

    return -dy / length, dx / length


def compute_snapshot_visual_placements(
    snapshot: Snapshot,
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
) -> List[PersonVisualPlacement]:
    placements: List[PersonVisualPlacement] = []
    section_people: Dict[str, List[Person]] = {sid: [] for sid in sections.keys()}
    snapshot_state_by_pid = {person_state.pid: person_state for person_state in snapshot.people}

    for person_state in snapshot.people:
        if person_state.finished or person_state.section_id == "EXIT":
            continue

        person = Person(
            pid=person_state.pid,
            group=person_state.group,
            section_id=person_state.section_id,
            x=person_state.x,
        )
        section_people[person.section_id].append(person)

    for sid, people in section_people.items():
        if not people:
            continue

        section = sections[sid]
        visual = layout[sid]
        nx, ny = perpendicular_unit_vector(visual)
        rows = build_rows_on_section(people, section)

        for row in rows:
            centers = compute_person_row_centers(row, section)
            for person in row.people:
                px, py = interpolate_position_on_section(section, visual, person.x)
                lateral_offset = centers[person.pid]
                center = (px + nx * lateral_offset, py + ny * lateral_offset)
                person_state = snapshot_state_by_pid.get(person.pid)
                row_index = person.row_index if person_state is None else person_state.row_index
                place_in_row = person.place_in_row if person_state is None else person_state.place_in_row
                placements.append(
                    PersonVisualPlacement(
                        pid=person.pid,
                        section_id=sid,
                        center=center,
                        length_m=person.c_geom,
                        width_m=person.a_geom,
                        color=get_profile_color(person.group),
                        label=f"{person.pid}\nR{row_index}:{place_in_row}",
                        row_index=row_index,
                        place_in_row=place_in_row,
                    )
                )

    return placements


def draw_people(ax: plt.Axes, snapshot: Snapshot, sections: Dict[str, Segment], layout: Dict[str, SectionVisual]) -> None:
    require_matplotlib()
    placements = compute_snapshot_visual_placements(snapshot, sections, layout)

    for placement in placements:
        section_visual = layout[placement.section_id]
        dx = section_visual.end[0] - section_visual.start[0]
        dy = section_visual.end[1] - section_visual.start[1]
        angle_deg = 0.0 if abs(dx) + abs(dy) <= 1e-9 else degrees(atan2(dy, dx))

        ellipse = Ellipse(
            xy=placement.center,
            width=placement.length_m,
            height=placement.width_m,
            angle=angle_deg,
            facecolor=placement.color,
            edgecolor="black",
            linewidth=0.8,
            alpha=0.85,
            zorder=10,
        )
        ax.add_patch(ellipse)
        ax.text(
            placement.center[0],
            placement.center[1],
            placement.label,
            ha="center",
            va="center",
            fontsize=7,
            color="#111111",
            zorder=11,
        )


def build_flow_summary_lines(snapshot: Snapshot, sections: Dict[str, Segment]) -> List[str]:
    flow_members_by_section: Dict[str, Dict[int, List[Tuple[int, int]]]] = {
        sid: {} for sid in sections.keys()
    }

    for person in snapshot.people:
        if person.finished or person.section_id == "EXIT":
            continue
        if person.section_id not in flow_members_by_section:
            continue
        if person.flow_index < 0:
            continue

        section_flows = flow_members_by_section[person.section_id]
        section_flows.setdefault(person.flow_index, []).append((person.place_in_flow, person.pid))

    lines = ["Потоки по участкам:"]

    for sid in sections.keys():
        section_flows = flow_members_by_section[sid]
        if not section_flows:
            lines.append(f"{sid}: —")
            continue

        lines.append(f"{sid}:")
        for flow_index in sorted(section_flows.keys()):
            ordered_people = [
                pid
                for _place, pid in sorted(
                    section_flows[flow_index],
                    key=lambda item: (item[0], item[1]),
                )
            ]
            flow_members = ", ".join(str(pid) for pid in ordered_people)
            lines.append(f"  F{flow_index}: {flow_members}")

    return lines


def draw_status_box(ax: plt.Axes, snapshot: Snapshot, sections: Dict[str, Segment]) -> None:
    require_matplotlib()
    active_count = snapshot.total_people - snapshot.finished_count

    lines = [
        f"t = {snapshot.time:.1f} c",
        f"В здании: {active_count}",
        f"Эвакуировано: {snapshot.finished_count}/{snapshot.total_people}",
        "",
        "По участкам:",
    ]

    for sid in sections.keys():
        lines.append(f"{sid}: {snapshot.section_counts.get(sid, 0)}")

    text = "\n".join(lines)

    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="white", edgecolor="#999999", alpha=0.92),
        zorder=20,
    )


def draw_flow_box(ax: plt.Axes, snapshot: Snapshot, sections: Dict[str, Segment]) -> None:
    require_matplotlib()
    lines = build_flow_summary_lines(snapshot, sections)
    text = "\n".join(lines)

    ax.text(
        0.73,
        0.98,
        text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="white", edgecolor="#999999", alpha=0.92),
        zorder=20,
    )


def draw_group_legend(ax: plt.Axes) -> None:
    require_matplotlib()
    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=color,
            markeredgecolor="black",
            markersize=8,
            label=mobility_group,
        )
        for mobility_group, color in MOBILITY_GROUP_COLORS.items()
    ]
    ax.legend(handles=handles, loc="lower left", framealpha=0.92, fontsize=8)


def render_snapshot(
    ax: plt.Axes,
    snapshot: Snapshot,
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
) -> None:
    require_matplotlib()
    ax.clear()
    setup_axes(ax, layout)
    draw_sections(ax, sections, layout)
    draw_people(ax, snapshot, sections, layout)
    draw_status_box(ax, snapshot, sections)
    draw_flow_box(ax, snapshot, sections)
    draw_group_legend(ax)
    ax.set_title("Геометрическое формирование рядов на участке", fontsize=12)


def find_nearest_snapshot(history: List[Snapshot], time_sec: float) -> Snapshot:
    return min(history, key=lambda snap: abs(snap.time - time_sec))


def plot_snapshot_at_time(
    history: List[Snapshot],
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
    time_sec: float,
) -> None:
    require_matplotlib()
    snapshot = find_nearest_snapshot(history, time_sec)
    fig, ax = plt.subplots(figsize=(13, 6))
    render_snapshot(ax, snapshot, sections, layout)
    output_path = "artifacts/rows_demo.png"
    os.makedirs("artifacts", exist_ok=True)
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    print(f"Схема сохранена: {output_path}")


def animate_evacuation(
    history: List[Snapshot],
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
    interval_ms: int = 300,
) -> Tuple[plt.Figure, FuncAnimation]:
    require_matplotlib()
    fig, ax = plt.subplots(figsize=(13, 6))

    def update(frame_index: int):
        snapshot = history[frame_index]
        render_snapshot(ax, snapshot, sections, layout)

    anim = FuncAnimation(
        fig,
        update,
        frames=len(history),
        interval=interval_ms,
        repeat=False,
        blit=False,
    )

    return fig, anim


def can_render_realtime() -> bool:
    if not HAS_MATPLOTLIB or matplotlib is None:
        return False

    backend = matplotlib.get_backend().lower()
    non_interactive_backends = {
        "agg",
        "pdf",
        "ps",
        "svg",
        "pgf",
        "cairo",
        "template",
        "module://matplotlib_inline.backend_inline",
    }
    return backend not in non_interactive_backends


def show_realtime_evacuation(
    history: List[Snapshot],
    sections: Dict[str, Segment],
    layout: Dict[str, SectionVisual],
    playback_speed: float = 1.0,
) -> Tuple[plt.Figure, FuncAnimation]:
    require_matplotlib()
    if playback_speed <= 0:
        raise ValueError("playback_speed должен быть больше 0.")

    if len(history) >= 2:
        snapshot_dt = max(history[1].time - history[0].time, 1e-3)
    else:
        snapshot_dt = 0.1

    interval_ms = max(1, int(snapshot_dt * 1000 / playback_speed))
    fig, anim = animate_evacuation(
        history=history,
        sections=sections,
        layout=layout,
        interval_ms=interval_ms,
    )
    plt.show()
    return fig, anim
