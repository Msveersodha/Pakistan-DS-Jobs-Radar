import math

import pandas as pd
import streamlit as st

from .. import data
from ..ui import api_url, filters_json, job_card, job_dialog, table

SORTS = {"Newest": "newest", "Fewest applicants": "fewest_applicants", "Most applicants": "most_applicants",
         "Oldest": "oldest", "Title A–Z": "title", "Company A–Z": "company"}


def render(meta):
    st.markdown('<div class="hero"><h2>🗂️ Job explorer</h2><p>Search and filter all listings. '
                'Open any job for the full description, skill gap and similar roles.</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1.2])
    q = c1.text_input("Search title, company, skills, description", key="ex_q", placeholder="e.g. pytorch, remote…")
    must = c2.multiselect("Must include skills", meta["skills"], key="ex_must")
    sort = c3.selectbox("Sort by", list(SORTS), key="ex_sort")
    size = c4.selectbox("Per page", [10, 25, 50], index=1, key="ex_size")

    extra = {}
    if q.strip():
        extra["q"] = q.strip()
    if must:
        extra["required_skills"] = must
    fj = filters_json(extra)
    first = data.search(api_url(), fj, SORTS[sort], 1, size)
    total = first["total"]
    pages = max(1, math.ceil(total / size))
    cc1, cc2 = st.columns([1, 3])
    page = cc1.number_input("Page", 1, pages, 1, key="ex_page")
    cc2.markdown(f"**{total}** jobs match · page {page} of {pages}")
    if total == 0:
        st.warning("No jobs found. Loosen the search or filters.")
        return
    res = first if page == 1 else data.search(api_url(), fj, SORTS[sort], int(page), size)
    items = res["items"]

    view = st.radio("View", ["Table", "Cards"], horizontal=True, key="ex_view", label_visibility="collapsed")
    if view == "Table":
        df = pd.DataFrame([{
            "ID": it["job_id"], "Title": it["job_title"], "Company": it["company_name"], "City": it["city"],
            "Mode": it["work_mode"], "Level": it["seniority"], "Posted": it["time_posted"],
            "Applicants": it["applicant_count"], "Skills": ", ".join(it["skills_found"][:6]),
        } for it in items])
        table(df)
        labels = {it["job_id"]: f"{it['job_title']} — {it['company_name']}" for it in items}
        pick = st.selectbox("Open a job", [None] + list(labels), format_func=lambda x: "Select…" if x is None else labels[x],
                            key="ex_pick")
        if pick is not None and st.button("Open details", key="ex_open"):
            job_dialog(int(pick))
    else:
        for it in items:
            job_card(it, key=f"ex_{it['job_id']}")

    all_items = data.all_results(api_url(), fj, SORTS[sort])
    exp = pd.DataFrame([{k: (", ".join(v) if isinstance(v, list) else v) for k, v in it.items() if k != "snippet"}
                        for it in all_items])
    st.download_button(f"⬇️ Download all {len(all_items)} results (CSV)", exp.to_csv(index=False).encode(),
                       "jobs_filtered.csv", "text/csv")
