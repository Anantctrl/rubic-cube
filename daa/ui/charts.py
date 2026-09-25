"""Plotly charts for the comparison + benchmark tabs."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go


def comparison_bar(results: list[tuple[str, float]], metric: str) -> go.Figure:
    """Simple labelled bar chart: algorithm -> measured metric value."""
    labels = [r[0] for r in results]
    values = [r[1] for r in results]
    fig = px.bar(x=labels, y=values, color=labels, text=values,
                 labels={"x": "Algorithm", "y": metric})
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(showlegend=False, height=360,
                      margin=dict(l=10, r=10, t=30, b=10))
    return fig


def success_heatmap(rows: list[dict]) -> go.Figure:
    """3D-style scatter where x=scramble length, y=algorithm, size/colour = time."""
    fig = px.scatter(
        rows,
        x="length", y="algorithm", color="time_s", size="nodes",
        hover_data=["nodes", "generated", "found", "memory_mb"],
        title="Benchmark: nodes / time by scramble length",
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def combined_metrics(rows: list[dict]) -> go.Figure:
    """Per-algorithm summary of the four DAA headline metrics (subplots)."""
    algs = [r["algorithm"] for r in rows]
    keys = [
        ("time_s", "Time (s)"),
        ("nodes", "Nodes explored"),
        ("length", "Solution length"),
        ("memory_mb", "Memory (MB)"),
    ]
    fig = go.Figure()
    for i, (key, title) in enumerate(keys):
        trace = go.Bar(
            x=algs, y=[r[key] for r in rows], name=title,
            yaxis=f"y{i + 1 if i else ''}", offsetgroup=i,
        )
        fig.add_trace(trace)
    return fig


def iterations_plot(depth_series: list[int], time_series: list[float]) -> go.Figure:
    """IDDFS per-depth iteration table as a line chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=depth_series, y=time_series, mode="lines+markers",
                             name="time per depth pass"))
    fig.update_layout(height=300, xaxis_title="depth limit",
                      yaxis_title="time (s)", margin=dict(l=10, r=10, t=30, b=10))
    return fig