import pandas as pd
import streamlit as st

from .. import charts, data
from ..ui import api_url, filters_json, job_card, plot, table


def render(meta):
    st.markdown('<div class="hero"><h2>📊 Market dashboard</h2><p>Every chart reacts to the filters in the sidebar. '
                'Hover for details; use the tabs to dig deeper.</p></div>', unsafe_allow_html=True)
    s = data.stats(api_url(), filters_json())
    if not s or s.get("n_jobs", 0) == 0:
        st.warning("No jobs match the current filters. Try resetting them in the sidebar.")
        return
    k = s["kpis"]
    c = st.columns(6)
    c[0].metric("Jobs", k["jobs"])
    c[1].metric("Companies", k["companies"])
    c[2].metric("Remote", f"{k['remote_share']:.0f}%")
    c[3].metric("Entry / intern", f"{k['entry_share']:.0f}%")
    c[4].metric("Median applicants", f"{k['median_applicants']:.0f}", help="Counts of 'Over 100' are stored as 100.")
    c[5].metric("Median age", f"{k['median_days_ago']:.0f} d" if k["median_days_ago"] is not None else "–",
                help="Days since posted, relative to the scrape date (July 2024).")

    t1, t2, t3, t4 = st.tabs(["Overview", "Skills", "Competition & timing", "Work mode & pay"])

    with t1:
        a, b, c3 = st.columns([1.2, 1, 1.2])
        with a:
            plot(charts.hbar(s["by_role"], "Jobs by role family"), key="d_role")
        with b:
            plot(charts.donut(s["by_work_mode"], "Work mode"), key="d_mode")
        with c3:
            plot(charts.hbar(s["by_city"], "Jobs by city", top=8, color=charts.PALETTE[1]), key="d_city")
        a, b, c3 = st.columns(3)
        with a:
            plot(charts.hbar(s["by_seniority"], "Seniority", color=charts.PALETTE[2]), key="d_sen")
        with b:
            plot(charts.hbar(s["by_employment"], "Employment type", color=charts.PALETTE[5]), key="d_emp")
        with c3:
            plot(charts.hbar(s["top_companies"][:10], "Top hiring companies", color=charts.PALETTE[3]), key="d_co")

    with t2:
        cats = [c for c in meta["categories"]]
        default = [c for c in cats if c != "Professional"]
        l, r = st.columns([3, 1])
        picked = l.multiselect("Skill categories", cats, default=default, key="dash_cats")
        topn = r.slider("Show top", 5, 40, 20, key="dash_topn")
        rows = [x for x in s["top_skills"] if x["category"] in picked][:topn]
        if rows:
            plot(charts.skills_bar(rows, "Most requested skills"), key="d_skills")
        else:
            st.info("Pick at least one category.")
        sbr = s["skills_by_role"]
        a, b = st.columns(2)
        with a:
            if sbr["roles"]:
                plot(charts.heatmap(sbr["z"], sbr["skills"], sbr["roles"], "Skill demand by role (% of role's jobs)"),
                     key="d_heat")
        with b:
            co = s["skill_cooccurrence"]
            plot(charts.heatmap(co["z"], co["skills"], co["skills"], "Skills that appear together (job count)",
                                fmt="d", suffix=" jobs", scale="Purples"), key="d_co2")
        st.markdown("##### 🔍 Drill into a skill")
        sk_names = [x["skill"] for x in s["top_skills"]]
        pick = st.selectbox("Show jobs that require…", sk_names, key="drill_skill")
        if pick:
            res = data.search(api_url(), filters_json({"required_skills": [pick]}), "newest", 1, 8)
            st.caption(f"{res['total']} matching jobs (showing {len(res['items'])})")
            for it in res["items"]:
                job_card(it, key=f"dr_{it['job_id']}")

    with t3:
        a, b = st.columns(2)
        with a:
            plot(charts.vbar(s["recency"], "How fresh are the postings?"), key="d_rec")
        with b:
            plot(charts.vbar(s["applicant_buckets"], "Applicants per job", color=charts.PALETTE[3]), key="d_app")
        a, b = st.columns([1, 1.4])
        with a:
            plot(charts.competition_bar(s["competition_by_role"], "Avg. applicants by role"), key="d_comp")
        with b:
            plot(charts.scatter_jobs(s["points"], "Age vs. competition (each dot = one job)"), key="d_sc")
        st.caption("Applicant counts of 'Over 100' are stored as 100, so averages are lower bounds. "
                   "Low-applicant + recent jobs (bottom-left) are the best bets.")

    with t4:
        a, b = st.columns([1.3, 1])
        with a:
            plot(charts.stacked_mode_by_role(s["points"], "Remote vs on-site by role"), key="d_mr")
        with b:
            st.markdown(f"##### 💰 Jobs with listed pay ({k['with_pay']})")
            if s["pay_jobs"]:
                table(pd.DataFrame(s["pay_jobs"])[["job_title", "company_name", "pay", "work_mode"]]
                      .rename(columns={"job_title": "Title", "company_name": "Company", "pay": "Pay",
                                       "work_mode": "Mode"}))
            else:
                st.info("None of the filtered jobs list pay (most LinkedIn postings don't).")
