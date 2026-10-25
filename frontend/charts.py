"""Plotly figure builders (pure functions: stats dict -> Figure)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ["#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#14B8A6", "#F97316", "#64748B"]
CAT_COLORS = {
    "Languages": "#6366F1", "ML & AI": "#EC4899", "Libraries & Frameworks": "#06B6D4",
    "Data & BI": "#10B981", "Databases & Platforms": "#F59E0B", "Cloud & DevOps": "#8B5CF6",
    "Professional": "#94A3B8",
}
HAVE, MISSING = "#10B981", "#F97316"


def _style(fig: go.Figure, h: int = 340, title: Optional[str] = None, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=h, title=dict(text=title, x=0, font=dict(size=15)) if title else None,
        margin=dict(l=8, r=8, t=44 if title else 12, b=8), showlegend=legend,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12), legend=dict(orientation="h", y=-0.15),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)")
    return fig


def _top_with_other(rows: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    if len(rows) <= n:
        return rows
    other = sum(r["count"] for r in rows[n:])
    return rows[:n] + [{"label": "Other", "count": other}]


def hbar(rows: List[Dict[str, Any]], title: str, top: Optional[int] = None, color: str = PALETTE[0]) -> go.Figure:
    rows = _top_with_other(rows, top) if top else rows
    df = pd.DataFrame(rows).iloc[::-1]
    fig = go.Figure(go.Bar(x=df["count"], y=df["label"], orientation="h", marker_color=color,
                           text=df["count"], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x} jobs<extra></extra>"))
    fig.update_xaxes(visible=False)
    return _style(fig, max(260, 28 * len(df) + 70), title)


def donut(rows: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(rows)
    fig = go.Figure(go.Pie(labels=df["label"], values=df["count"], hole=0.55, sort=False,
                           marker=dict(colors=PALETTE), textinfo="percent",
                           hovertemplate="%{label}: %{value} jobs (%{percent})<extra></extra>"))
    return _style(fig, 300, title, legend=True)


def vbar(rows: List[Dict[str, Any]], title: str, color: str = PALETTE[1]) -> go.Figure:
    df = pd.DataFrame(rows)
    fig = go.Figure(go.Bar(x=df["label"], y=df["count"], marker_color=color, text=df["count"], textposition="outside",
                           hovertemplate="%{x}: %{y} jobs<extra></extra>"))
    fig.update_yaxes(visible=False)
    return _style(fig, 320, title)


def skills_bar(rows: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(rows).iloc[::-1]
    fig = go.Figure()
    for cat in [c for c in CAT_COLORS if c in set(df["category"])]:
        d = df[df["category"] == cat]
        fig.add_trace(go.Bar(x=d["share"], y=d["skill"], orientation="h", name=cat, marker_color=CAT_COLORS[cat],
                             customdata=d[["count"]], hovertemplate="%{y}: %{x}% of jobs (%{customdata[0]})<extra>" + cat + "</extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="% of jobs mentioning the skill", showgrid=True, gridcolor="rgba(128,128,128,0.18)")
    return _style(fig, max(320, 24 * len(df) + 90), title, legend=True)


def heatmap(z: List[List[float]], x: List[str], y: List[str], title: str, fmt: str = ".0f", suffix: str = "%",
            scale: str = "Blues") -> go.Figure:
    fig = go.Figure(go.Heatmap(z=z, x=x, y=y, colorscale=scale, texttemplate="%{z:" + fmt + "}",
                               hovertemplate="%{y} × %{x}: %{z}" + suffix + "<extra></extra>", showscale=False))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickangle=-40)
    return _style(fig, max(300, 38 * len(y) + 140), title)


def scatter_jobs(points: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(points).dropna(subset=["days_ago"])
    df["days_ago"] = df["days_ago"].clip(upper=120)
    df["jit"] = df["applicant_count"] + (df["job_id"] % 7 - 3) * 0.6
    fig = px.scatter(df, x="days_ago", y="jit", color="role", color_discrete_sequence=PALETTE,
                     hover_data={"job_title": True, "company_name": True, "applicant_count": True,
                                 "days_ago": ":.1f", "jit": False, "role": False})
    fig.update_traces(marker=dict(size=8, opacity=0.75, line=dict(width=0)))
    fig.update_xaxes(title="Days since posted (capped at 120)", showgrid=True, gridcolor="rgba(128,128,128,0.18)")
    fig.update_yaxes(title="Applicants (100 = 'over 100')")
    return _style(fig, 380, title, legend=True)


def stacked_mode_by_role(points: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(points)
    ct = pd.crosstab(df["role"], df["work_mode"], normalize="index").mul(100).round(1)
    ct = ct.loc[df["role"].value_counts().index]
    colors = {"Remote": "#10B981", "Hybrid": "#F59E0B", "On-site": "#6366F1", "Not specified": "#94A3B8"}
    fig = go.Figure()
    for mode in [m for m in colors if m in ct.columns]:
        fig.add_trace(go.Bar(y=ct.index, x=ct[mode], name=mode, orientation="h", marker_color=colors[mode],
                             hovertemplate="%{y}: %{x}% " + mode + "<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="% of jobs")
    return _style(fig, 340, title, legend=True)


def competition_bar(rows: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(rows).iloc[::-1]
    fig = go.Figure(go.Bar(x=df["avg_applicants"], y=df["role"], orientation="h", marker_color=PALETTE[3],
                           customdata=df[["jobs"]], text=df["avg_applicants"], textposition="outside",
                           hovertemplate="%{y}: %{x} avg applicants (%{customdata[0]} jobs)<extra></extra>"))
    fig.update_xaxes(visible=False)
    return _style(fig, max(260, 30 * len(df) + 70), title)


def demand_bar(rows: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(rows).iloc[::-1]
    fig = go.Figure()
    for flag, name, col in ((True, "You have it", HAVE), (False, "Gap", MISSING)):
        d = df[df["have"] == flag]
        fig.add_trace(go.Bar(x=d["share"], y=d["skill"], orientation="h", name=name, marker_color=col,
                             hovertemplate="%{y}: %{x}% of jobs<extra>" + name + "</extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="% of jobs asking for the skill")
    return _style(fig, max(320, 26 * len(df) + 90), title, legend=True)


def learn_bar(rows: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(rows).iloc[::-1]
    fig = go.Figure(go.Bar(x=df["jobs"], y=df["skill"], orientation="h", text=df["jobs"], textposition="outside",
                           marker_color=[CAT_COLORS.get(c, PALETTE[0]) for c in df["category"]],
                           hovertemplate="%{y}: needed in %{x} of your top matches<extra></extra>"))
    fig.update_xaxes(visible=False)
    return _style(fig, max(280, 28 * len(df) + 70), title)


def score_bars(items: List[Dict[str, Any]], title: str) -> go.Figure:
    df = pd.DataFrame(items).iloc[::-1]
    labels = (df["job_title"].str.slice(0, 38) + " · " + df["company_name"].str.slice(0, 18)).tolist()
    fig = go.Figure(go.Bar(x=df["match_score"], y=labels, orientation="h", text=df["match_score"].map("{:.0f}".format),
                           textposition="outside", cliponaxis=False,
                           marker=dict(color=df["match_score"], colorscale="Viridis", cmin=0, cmax=100),
                           hovertemplate="%{y}<br>Match %{x}<extra></extra>"))
    fig.update_xaxes(range=[0, 108], visible=False)
    return _style(fig, max(260, 30 * len(df) + 70), title)


def gauge(value: float, title: str) -> go.Figure:
    fig = go.Figure(go.Indicator(mode="gauge+number", value=value, number=dict(suffix="%"),
                                 title=dict(text=title, font=dict(size=14)),
                                 gauge=dict(axis=dict(range=[0, 100]), bar=dict(color=PALETTE[0]),
                                            steps=[dict(range=[0, 40], color="rgba(239,68,68,.25)"),
                                                   dict(range=[40, 70], color="rgba(245,158,11,.25)"),
                                                   dict(range=[70, 100], color="rgba(16,185,129,.25)")])))
    return _style(fig, 230)
