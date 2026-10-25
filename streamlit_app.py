"""Streamlit frontend.   streamlit run streamlit_app.py
Works standalone (built-in engine) or against the FastAPI backend (set API_URL)."""
import streamlit as st

st.set_page_config(page_title="Pakistan DS Jobs Radar", page_icon="📊", layout="wide")

from frontend import data, ui  # noqa: E402
from frontend.views import about, dashboard, explorer, matcher, planner, shortlist  # noqa: E402

PAGES = {
    "📊 Dashboard": dashboard,
    "🎯 Matcher": matcher,
    "🗂️ Explorer": explorer,
    "🧭 Skill planner": planner,
    "⭐ Shortlist": shortlist,
    "ℹ️ About": about,
}

ui.init_state()
st.markdown(ui.CSS, unsafe_allow_html=True)
try:
    client = ui.connection_panel()
    meta = data.meta(ui.api_url())
except Exception as exc:  # API went away mid-session
    st.error(f"Backend error: {exc}")
    st.stop()

ui.sidebar(meta, list(PAGES))
PAGES[st.session_state["page"]].render(meta)
