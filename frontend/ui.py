"""Shared UI helpers: CSS, chips, job cards, sidebar filters, shortlist state."""
from __future__ import annotations

import html
import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from . import data

CSS = """
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px;}
.chip {display:inline-block; padding:2px 10px; margin:2px 4px 2px 0; border-radius:999px; font-size:0.78rem;
       background:rgba(128,128,128,.16); white-space:nowrap;}
.chip-ok {background:rgba(16,185,129,.20); color:#059669;}
.chip-miss {background:rgba(249,115,22,.18); color:#EA580C;}
.chip-info {background:rgba(99,102,241,.18); color:#4F46E5;}
.hero {padding:1.1rem 1.4rem; border-radius:16px; margin-bottom:1rem;
       background:linear-gradient(120deg, rgba(99,102,241,.16), rgba(6,182,212,.14));}
.hero h2 {margin:0 0 .2rem 0;}
.hero p {margin:0; opacity:.8;}
div[data-testid="stMetric"] {background:rgba(128,128,128,.08); padding:.7rem .9rem; border-radius:12px;}
.small {font-size:.82rem; opacity:.75;}
</style>
"""

DAY_OPTIONS = {"Any time": None, "Last 24 hours": 1, "Last 3 days": 3, "Last week": 7, "Last 2 weeks": 14,
               "Last month": 30, "Last 3 months": 90}
STATUSES = ["Interested", "Applied", "Interviewing", "Offer", "Rejected"]


# ---------------------------------------------------------------- compat wrappers
def plot(fig, key: Optional[str] = None):
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:  # older Streamlit
        st.plotly_chart(fig, use_container_width=True, key=key)


def table(df: pd.DataFrame, **kw):
    try:
        return st.dataframe(df, width="stretch", hide_index=True, **kw)
    except TypeError:
        return st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def esc_md(s: str) -> str:
    """Stop Streamlit markdown from treating $ as LaTeX."""
    return (s or "").replace("$", "\\$")


def chips(items: List[str], kind: str = "") -> str:
    cls = f"chip chip-{kind}" if kind else "chip"
    return "".join(f'<span class="{cls}">{html.escape(str(i))}</span>' for i in items)


def show_chips(items: List[str], kind: str = ""):
    if items:
        st.markdown(chips(items, kind), unsafe_allow_html=True)


# ----------------------------------------------------------------------- state
def init_state():
    s = st.session_state
    s.setdefault("saved", {})
    s.setdefault("page", "📊 Dashboard")
    if "api_url" not in s:
        url = os.environ.get("API_URL", "")
        if not url:
            try:
                url = st.secrets.get("API_URL", "")
            except Exception:
                url = ""
        s["api_url"] = url


def api_url() -> str:
    return st.session_state.get("api_url", "") or ""


def my_skills() -> List[str]:
    return list(st.session_state.get("my_skills", []))


def go_to(page: str):
    st.session_state["page"] = page


def toggle_save(item: Dict[str, Any]):
    saved = st.session_state["saved"]
    jid = int(item["job_id"])
    if jid in saved:
        del saved[jid]
    else:
        saved[jid] = {"job_id": jid, "job_title": item["job_title"], "company_name": item["company_name"],
                      "city": item.get("city"), "work_mode": item.get("work_mode"), "role": item.get("role"),
                      "status": "Interested", "notes": ""}


def current_filters() -> Dict[str, Any]:
    s, f = st.session_state, {}
    for key, name in (("f_cities", "cities"), ("f_work", "work_modes"), ("f_emp", "employment_types"),
                      ("f_sen", "seniority"), ("f_roles", "roles")):
        if s.get(key):
            f[name] = list(s[key])
    days = DAY_OPTIONS.get(s.get("f_days", "Any time"))
    if days is not None:
        f["max_days_ago"] = days
    if s.get("f_apps", 100) < 100:
        f["max_applicants"] = int(s["f_apps"])
    return f


def filters_json(extra: Optional[Dict[str, Any]] = None) -> str:
    return json.dumps({**current_filters(), **(extra or {})}, sort_keys=True)


def reset_filters():
    s = st.session_state
    for k in ("f_cities", "f_work", "f_emp", "f_sen", "f_roles"):
        s[k] = []
    s["f_days"] = "Any time"
    s["f_apps"] = 100


# --------------------------------------------------------------------- sidebar
def sidebar(meta: Dict[str, Any], pages: List[str]):
    s = st.sidebar
    s.title("🇵🇰 DS Jobs Radar")
    s.radio("Navigate", pages, key="page", label_visibility="collapsed")
    s.divider()
    s.subheader("🎯 My skills")
    s.multiselect("Skills you have", options=meta["skills"], key="my_skills", accept_new_options=True,
                  placeholder="Pick or type skills…", label_visibility="collapsed",
                  help="Shared across Matcher, Skill Planner and job cards.")
    s.divider()
    with s.expander("🔎 Global filters", expanded=True):
        st.multiselect("City", meta["cities"], key="f_cities", placeholder="All cities")
        st.multiselect("Work mode", meta["work_modes"], key="f_work", placeholder="Any")
        st.multiselect("Role family", meta["roles"], key="f_roles", placeholder="All roles")
        st.multiselect("Seniority", meta["seniority"], key="f_sen", placeholder="Any")
        st.multiselect("Employment", meta["employment_types"], key="f_emp", placeholder="Any")
        st.select_slider("Posted", list(DAY_OPTIONS), key="f_days", value="Any time")
        st.slider("Max applicants (100 = any)", 0, 100, 100, 5, key="f_apps")
        st.button("Reset filters", on_click=reset_filters)
    n = len(st.session_state["saved"])
    s.caption(f"⭐ {n} job{'s' if n != 1 else ''} in shortlist")


def connection_panel():
    client, warn = data.get_client(api_url())
    with st.sidebar.expander("⚙️ Backend connection"):
        st.caption(f"Mode: **{client.label}**")
        st.text_input("FastAPI URL (blank = built-in engine)", key="api_url",
                      placeholder="http://localhost:8000")
        if warn:
            st.warning(warn)
    return client


# ------------------------------------------------------------------------ cards
def _job_chips(item: Dict[str, Any], mine: List[str]):
    have = [s for s in item.get("skills_found", []) if s in mine]
    miss = [s for s in item.get("skills_found", []) if s not in mine]
    if mine:
        show_chips(have[:10], "ok")
        show_chips(miss[:8], "miss")
    else:
        show_chips(item.get("skills_found", [])[:12])


@st.dialog("Job details", width="large")
def job_dialog(job_id: int):
    j = data.job(api_url(), int(job_id))
    if not j:
        st.error("Job not found.")
        return
    mine = my_skills()
    st.subheader(j["job_title"])
    st.write(f"**{j['company_name']}** · {j['location']}")
    badges = [j["work_mode"], j["employment"], j["seniority"], j["role"], j["time_posted"], j["applicants"]]
    if j.get("pay_text"):
        badges.append("💰 " + j["pay_text"])
    show_chips([b for b in badges if b and b != "Not specified"], "info")
    if mine:
        g = data.gap(api_url(), j["job_id"], json.dumps(mine))
        c1, c2 = st.columns([1, 3])
        c1.metric("Skill coverage", f"{g['coverage']:.0f}%")
        with c2:
            st.caption("✅ You have")
            show_chips(g["matched"], "ok")
            st.caption("🎯 To learn")
            show_chips(g["missing"], "miss")
    else:
        st.caption("Skills detected in the posting")
        show_chips(j["skills_found"])
        st.info("Add your skills in the sidebar to see your coverage for this job.")
    if j.get("listed_skills"):
        with st.expander("Skills listed on LinkedIn"):
            st.write(", ".join(j["listed_skills"]))
    with st.container(height=280, border=True):
        st.markdown(esc_md(j["description"]))
    sim = data.similar(api_url(), j["job_id"], 5)
    if sim:
        st.markdown("**Similar jobs**")
        table(pd.DataFrame([{"Title": x["job_title"], "Company": x["company_name"], "City": x["city"],
                             "Similarity %": x["similarity"]} for x in sim]))
    saved = j["job_id"] in st.session_state["saved"]
    st.button("★ Remove from shortlist" if saved else "☆ Add to shortlist", key=f"dlg_save_{j['job_id']}",
              on_click=toggle_save, args=(j,))


def job_card(item: Dict[str, Any], key: str, show_match: bool = False):
    mine = my_skills()
    saved = int(item["job_id"]) in st.session_state["saved"]
    with st.container(border=True):
        left, right = st.columns([5, 2])
        with left:
            st.markdown(f"**{esc_md(item['job_title'])}**")
            meta_bits = [item["company_name"], item["city"], item["work_mode"], item["seniority"], item["time_posted"]]
            st.caption(esc_md(" · ".join(str(b) for b in meta_bits if b and b != "Not specified")))
            if show_match:
                show_chips(item.get("matched_skills", []), "ok")
                show_chips(item.get("missing_skills", [])[:8], "miss")
            else:
                _job_chips(item, mine)
        with right:
            if show_match:
                st.metric("Match", f"{item['match_score']:.0f}%")
                st.progress(min(max(item["match_score"] / 100, 0.0), 1.0))
                st.caption(f"text sim {item['text_similarity']:.2f} · skills {item['skill_coverage']:.0f}%")
            else:
                st.caption(f"👥 {item['applicants']}")
                if item.get("pay_text"):
                    st.caption(f"💰 {item['pay_text']}")
        b1, b2, _ = st.columns([1, 1, 4])
        if b1.button("Details", key=f"det_{key}"):
            job_dialog(int(item["job_id"]))
        b2.button("★ Saved" if saved else "☆ Save", key=f"sv_{key}", on_click=toggle_save, args=(item,))
