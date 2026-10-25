import pandas as pd
import streamlit as st

from ..ui import STATUSES, esc_md, go_to, job_dialog


def render(meta):
    st.markdown('<div class="hero"><h2>⭐ My shortlist</h2><p>Track the jobs you care about. '
                'Edit status and notes inline, then export.</p></div>', unsafe_allow_html=True)
    saved = st.session_state["saved"]
    if not saved:
        st.info("Nothing saved yet. Use ☆ Save on any job card in Matcher or Explorer.")
        st.button("Go to Matcher", on_click=go_to, args=("🎯 Matcher",))
        return
    df = pd.DataFrame(saved.values())[["job_id", "job_title", "company_name", "city", "work_mode", "status", "notes"]]
    df["remove"] = False
    cols = st.columns(len(STATUSES))
    for c, s in zip(cols, STATUSES):
        c.metric(s, int((df["status"] == s).sum()))
    edited = st.data_editor(
        df, hide_index=True, key="shortlist_editor", disabled=["job_id", "job_title", "company_name", "city", "work_mode"],
        column_config={
            "status": st.column_config.SelectboxColumn("Status", options=STATUSES, required=True),
            "notes": st.column_config.TextColumn("Notes", width="large"),
            "remove": st.column_config.CheckboxColumn("Remove"),
            "job_id": None,
            "job_title": "Title", "company_name": "Company", "city": "City", "work_mode": "Mode",
        })
    for _, r in edited.iterrows():
        jid = int(r["job_id"])
        if jid in saved:
            if r["remove"]:
                del saved[jid]
            else:
                saved[jid]["status"], saved[jid]["notes"] = r["status"], r["notes"] or ""
    if edited["remove"].any():
        st.rerun()
    a, b = st.columns([2, 3])
    labels = {int(r["job_id"]): f"{r['job_title']} — {r['company_name']}" for _, r in edited.iterrows()}
    pick = a.selectbox("Open job", list(labels), format_func=lambda x: labels[x], key="sl_pick") if labels else None
    if pick is not None and b.button("Open details", key="sl_open"):
        job_dialog(int(pick))
    st.download_button("⬇️ Export shortlist (CSV)", edited.drop(columns=["remove"]).to_csv(index=False).encode(),
                       "shortlist.csv", "text/csv")
    st.caption("Shortlist lives in this browser session. Export it to keep it.")
