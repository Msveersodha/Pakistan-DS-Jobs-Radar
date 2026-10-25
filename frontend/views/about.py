import streamlit as st

from .. import data
from ..ui import api_url


def render(meta):
    st.markdown('<div class="hero"><h2>ℹ️ About</h2><p>How this app works and what its limits are.</p></div>',
                unsafe_allow_html=True)
    client, warn = data.get_client(api_url())
    c = st.columns(4)
    c[0].metric("Jobs", meta["n_jobs"])
    c[1].metric("TF-IDF vocabulary", meta["vocab_size"])
    c[2].metric("Skills tracked", len(meta["skills"]))
    c[3].metric("Model loaded from", meta.get("model_source", "?"))
    st.markdown(f"""
**Data.** {meta['note']}

**Matching model.** A content-based retriever: `TfidfVectorizer` (1–2-grams, English stop-words, sublinear TF) over each
job's title, skills, description, job type and location. Your skills/resume are vectorised the same way and compared with
cosine similarity. The *Match score* blends that similarity with exact **skill coverage** (share of the job's detected
skills you have); the blend weight is the slider on the Matcher page.

**Skill extraction.** LinkedIn's `skills` column is empty for ~40% of jobs, so skills are detected with a curated regex
lexicon over title + skills + description (see `core/skills.py`).

**Not a prediction model.** The dataset has no hire/relevance labels, so nothing here is supervised — it is a
recommender and an analytics dashboard. Treat results as leads, not guarantees. Postings are historical (July 2024).

**Connection.** Currently running in **{client.label}**. Interactive API docs (when using the backend):
`<API_URL>/docs`.
""")
    if warn:
        st.warning(warn)
