# Data files
- `cleaned_data_science_jobs_pakistan.csv` – 492 cleaned LinkedIn job postings (Pakistan, scraped July 2024).
- `job_matcher_tfidf.joblib` – fitted `TfidfVectorizer` + job matrix (content-based matcher, no supervised labels).
  If your scikit-learn version cannot load it, the app silently re-fits the model from the CSV (`model_text` column),
  or run `python scripts/rebuild_model.py`.

Notes: applicant counts such as "Over 100 applicants" are stored as a lower bound of 100.
