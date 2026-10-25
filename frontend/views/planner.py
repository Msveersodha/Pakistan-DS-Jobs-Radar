import json

import pandas as pd
import streamlit as st

from .. import charts, data
from ..ui import api_url, current_filters, my_skills, plot, show_chips, table


def render(meta):
    st.markdown('<div class="hero"><h2>🧭 Skill planner</h2><p>See how your skills line up with market demand, '
                'what to learn next, and how a new skill would change your matches.</p></div>', unsafe_allow_html=True)
    mine = my_skills()
    if not mine:
        st.info("👈 Add the skills you already have in the sidebar to start planning.")
        return
    sj, fj = json.dumps(mine), json.dumps(current_filters(), sort_keys=True)

    t1, t2, t3, t4 = st.tabs(["Role readiness", "Learn next", "What-if", "Job-by-job gap"])

    with t1:
        c1, c2 = st.columns([2, 1])
        role = c1.selectbox("Target role family", ["All roles"] + meta["roles"], key="pl_role")
        topn = c2.slider("Skills to compare", 8, 30, 18, key="pl_topn")
        r = data.readiness(api_url(), sj, None if role == "All roles" else role, fj, topn)
        if r["n_jobs"] == 0:
            st.warning("No jobs in this role with the current filters.")
        else:
            a, b = st.columns([1, 2])
            with a:
                plot(charts.gauge(r["coverage_weighted"], f"Demand-weighted readiness ({r['n_jobs']} jobs)"), key="pl_g")
                st.caption("Share of the top in-demand skills' weight that you already cover.")
                gaps = [x["skill"] for x in r["skills"] if not x["have"]][:6]
                if gaps:
                    st.markdown("**Biggest gaps**")
                    show_chips(gaps, "miss")
            with b:
                plot(charts.demand_bar(r["skills"], "Skill demand vs. what you have"), key="pl_d")

    with t2:
        lp = data.learning_path(api_url(), sj, fj, 30, 12)
        if not lp["skills"]:
            st.success("You already cover every skill in your top matches. 🎉")
        else:
            st.caption(f"Missing skills across your {lp['based_on_jobs']} best-matching jobs, most frequent first.")
            a, b = st.columns([1.3, 1])
            with a:
                plot(charts.learn_bar(lp["skills"], "Learn these next"), key="pl_l")
            with b:
                table(pd.DataFrame(lp["skills"]).rename(columns={"skill": "Skill", "category": "Category",
                                                                  "jobs": "In # top jobs"})[["Skill", "Category", "In # top jobs"]])

    with t3:
        lp = data.learning_path(api_url(), sj, fj, 30, 15)
        options = [x["skill"] for x in lp["skills"]] or meta["skills"]
        extra = st.multiselect("If I also learned…", options, default=options[:2], key="pl_if")
        base_args = dict(query="", skills=mine, filters=current_filters(), top_k=10, skill_weight=0.5,
                         min_score=0.0, dedupe=True)
        before = data.match(api_url(), json.dumps(base_args, sort_keys=True))
        after = data.match(api_url(), json.dumps({**base_args, "skills": mine + extra}, sort_keys=True))
        mean = lambda r: sum(i["match_score"] for i in r["items"]) / max(len(r["items"]), 1)
        strong = lambda r: sum(1 for i in r["items"] if i["match_score"] >= 60)
        c = st.columns(3)
        c[0].metric("Avg. top-10 match", f"{mean(after):.0f}%", f"{mean(after) - mean(before):+.1f} pts")
        c[1].metric("Strong matches (≥60%)", strong(after), f"{strong(after) - strong(before):+d}")
        c[2].metric("Best match", f"{after['items'][0]['match_score']:.0f}%" if after["items"] else "–")
        if after["items"]:
            plot(charts.score_bars(after["items"], "Top matches with the new skills"), key="pl_w")

    with t4:
        res = data.match(api_url(), json.dumps(dict(query="", skills=mine, filters=current_filters(), top_k=15,
                                                    skill_weight=0.5, min_score=0.0, dedupe=True), sort_keys=True))
        items = res["items"]
        if not items:
            st.info("No matching jobs for the current filters.")
            return
        labels = {i["job_id"]: f"{i['job_title']} — {i['company_name']} ({i['match_score']:.0f}%)" for i in items}
        jid = st.selectbox("Pick a job", list(labels), format_func=lambda x: labels[x], key="pl_job")
        g = data.gap(api_url(), jid, sj)
        a, b = st.columns([1, 3])
        with a:
            plot(charts.gauge(g["coverage"], "Skill coverage"), key="pl_jg")
        with b:
            st.markdown("**✅ You have**")
            show_chips(g["matched"], "ok") if g["matched"] else st.caption("none yet")
            st.markdown("**🎯 Missing**")
            show_chips(g["missing"], "miss") if g["missing"] else st.caption("nothing missing!")
            if g["extra_skills"]:
                st.markdown("**➕ Your other strengths**")
                show_chips(g["extra_skills"])
