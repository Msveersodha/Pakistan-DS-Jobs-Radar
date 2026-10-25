import json

import pandas as pd
import streamlit as st

from .. import charts, data
from ..ui import api_url, current_filters, job_card, my_skills, plot, show_chips


def _read_upload(f) -> str:
    if f is None:
        return ""
    if f.name.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            return "\n".join((p.extract_text() or "") for p in PdfReader(f).pages)
        except Exception as exc:  # corrupt / scanned PDF
            st.warning(f"Could not read PDF text: {exc}")
            return ""
    return f.read().decode("utf-8", errors="ignore")


def _add_skills(new):
    cur = list(st.session_state.get("my_skills", []))
    st.session_state["my_skills"] = cur + [s for s in new if s not in cur]


def render(meta):
    st.markdown('<div class="hero"><h2>🎯 Job matcher</h2><p>Rank jobs by TF-IDF similarity to your skills / resume, '
                'blended with exact skill coverage. Results update live as you change anything.</p></div>',
                unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")
    with left:
        text = st.text_area("Describe your ideal job or paste your resume / summary (optional)", height=130,
                            key="mt_text", placeholder="e.g. Fresh CS graduate with RAG, vector DB and FastAPI experience "
                                                       "looking for an ML / data science role…")
        up = st.file_uploader("…or upload a resume (PDF / TXT)", type=["pdf", "txt"], key="mt_upload")
        doc_text = _read_upload(up)
        full_text = f"{text}\n{doc_text}".strip()
        if full_text:
            found = data.extract(api_url(), full_text)
            if found:
                st.caption("Skills detected in your text")
                show_chips(found, "info")
                st.button("➕ Add detected skills to My skills", on_click=_add_skills, args=(found,))
    with right:
        top_k = st.slider("How many results", 5, 50, 10, key="mt_k")
        w = st.slider("Weight on exact skill overlap", 0, 100, 30, 5, key="mt_w",
                      help="0% = pure text similarity (TF-IDF cosine). 100% = only the share of the job's skills you have.")
        min_score = st.slider("Minimum match score", 0, 90, 0, 5, key="mt_min")
        dedupe = st.toggle("Hide re-posted duplicates", True, key="mt_dd")

    skills = my_skills()
    if not skills and not full_text:
        st.info("👈 Add skills in the sidebar (or type / upload text above) to see your matches.")
        return

    args = dict(query=full_text[:8000], skills=skills, filters=current_filters(), top_k=top_k,
                skill_weight=w / 100, min_score=float(min_score), dedupe=dedupe)
    res = data.match(api_url(), json.dumps(args, sort_keys=True))
    items = res["items"]
    c = st.columns(4)
    c[0].metric("Candidates after filters", res["total_candidates"])
    c[1].metric("Results", len(items))
    c[2].metric("Best match", f"{items[0]['match_score']:.0f}%" if items else "–")
    c[3].metric("Skills used", len(res["query_skills"]))
    if not items:
        st.warning("No jobs above the minimum score with these filters. Lower the minimum or relax filters.")
        return

    tab_cards, tab_chart, tab_table = st.tabs(["Job cards", "Score chart", "Table / export"])
    with tab_cards:
        for i, it in enumerate(items):
            job_card(it, key=f"m_{i}_{it['job_id']}", show_match=True)
    with tab_chart:
        plot(charts.score_bars(items[:20], "Top matches"), key="m_chart")
        st.caption("Match = (1 − w) × text similarity (scaled so the best document is 1) + w × share of the job's skills you cover.")
    with tab_table:
        df = pd.DataFrame([{
            "Match %": it["match_score"], "Title": it["job_title"], "Company": it["company_name"],
            "City": it["city"], "Mode": it["work_mode"], "Level": it["seniority"], "Posted": it["time_posted"],
            "Applicants": it["applicants"], "Matched skills": ", ".join(it["matched_skills"]),
            "Missing skills": ", ".join(it["missing_skills"]),
        } for it in items])
        st.dataframe(df, hide_index=True)
        st.download_button("⬇️ Download matches (CSV)", df.to_csv(index=False).encode(), "my_job_matches.csv", "text/csv")
