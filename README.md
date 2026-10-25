# 🇵🇰 Pakistan Data-Science Jobs Radar

FastAPI backend + Streamlit dashboard on top of your cleaned LinkedIn dataset (492 jobs) and TF-IDF job matcher.

## Features
| Page | What you can do |
|---|---|
| 📊 **Dashboard** | KPIs + 15 interactive Plotly charts (roles, cities, work mode, seniority, top skills by category, skill × role heat-map, skill co-occurrence, posting freshness, applicant competition, age-vs-competition scatter, remote share by role, pay). Everything reacts to sidebar filters; "drill into a skill" lists the jobs. |
| 🎯 **Matcher** | Pick skills / type a description / upload a resume (PDF or TXT) → live ranked matches. Sliders for result count, skill-overlap weight, minimum score; matched vs missing skill chips; CSV export. |
| 🗂️ **Explorer** | Full-text search, must-have skills, sorting, paging, table or card view, job-detail dialog (description, your skill coverage, similar jobs), CSV export. |
| 🧭 **Skill planner** | Role readiness gauge, demand-vs-you chart, "learn next" ranking from your best matches, what-if (add a skill → see score change), job-by-job gap. |
| ⭐ **Shortlist** | Save jobs, set status (Interested → Offer), write notes, export CSV. |

Global sidebar: *My skills*, city / work mode / role / seniority / employment / recency / max-applicants filters.

## Project layout
```
streamlit_app.py        # Streamlit entry point  (deploy this file)
frontend/               # UI: charts, cards, views/, API-or-local client
backend/main.py         # FastAPI app  (docs at /docs)
core/                   # engine shared by both: preprocessing, skills lexicon, TF-IDF matcher, analytics
data/                   # CSV + joblib model
tests/                  # pytest (engine + API)
```

## Run locally (VS Code terminal)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      Mac/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

# Terminal 1 – backend
uvicorn backend.main:app --reload --port 8000        # or run_backend.bat / run_backend.sh
# Terminal 2 – frontend
set API_URL=http://localhost:8000   (Windows)   |   export API_URL=http://localhost:8000
streamlit run streamlit_app.py                       # or run_frontend.bat / run_frontend.sh
```
No backend running? The app automatically falls back to the built-in engine (sidebar → ⚙️ Backend connection shows the mode).

## Deploy the frontend on Streamlit Community Cloud
1. Push this folder to a GitHub repo (keep the `data/` folder – about 5 MB).
2. share.streamlit.io → **New app** → pick the repo, main file **`streamlit_app.py`**.
3. Done – it runs **standalone** (the engine is bundled), no API needed.
4. *Optional*: host the FastAPI service (e.g. Render: `render.yaml` included, start command
   `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`) and add `API_URL = "https://…"` under
   App settings → Secrets. The app will then call your API.

## API quick reference (`/docs` has the interactive version)
`GET /health` · `GET /meta` · `POST /jobs/search` · `GET /jobs/{id}` · `GET /jobs/{id}/similar` · `POST /match` ·
`POST /skills/extract` · `POST /skills/gap` · `POST /skills/readiness` · `POST /skills/learning-path` · `POST /stats`

```bash
curl -X POST localhost:8000/match -H "Content-Type: application/json" \
  -d '{"skills":["Python","SQL","Machine Learning"],"top_k":5,"filters":{"work_modes":["Remote"]}}'
```

## How scoring works
`match = (1 − w) · cosine(TF-IDF(query), TF-IDF(job)) / max_cosine + w · (your skills ∩ job skills) / job skills`
(`w` = the "Weight on exact skill overlap" slider). Skills are detected from title + skills + description with a curated
lexicon in `core/skills.py` – add your own terms there.

## Limits (be upfront in your demo)
- Data is a **July 2024** LinkedIn scrape; "posted X days ago" is relative to that date.
- "Over 100 applicants" is stored as 100 (lower bound).
- No supervised labels exist, so this is a recommender + analytics tool, not a hiring-outcome predictor.
- Shortlist is kept in the browser session only – export it to keep it.

## Tests
`pytest -q`
