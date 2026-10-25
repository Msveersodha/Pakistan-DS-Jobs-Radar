"""Re-fit the TF-IDF model from the CSV (use if your scikit-learn version can't load the .joblib).
    python scripts/rebuild_model.py
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.engine import CSV_NAME, MODEL_NAME, TFIDF_PARAMS  # noqa: E402

df = pd.read_csv(ROOT / "data" / CSV_NAME)
vec = TfidfVectorizer(**TFIDF_PARAMS)
mat = vec.fit_transform(df["model_text"].fillna(""))
records = df[["job_id", "job_title", "company_name", "location", "skills", "time_posted"]].to_dict("records")
joblib.dump({"model_type": "tfidf_content_matcher", "vectorizer": vec, "job_matrix": mat, "job_records": records,
             "text_columns": ["job_title", "skills", "description", "type_info", "location"], "n_jobs": len(df),
             "notes": "Re-fitted by scripts/rebuild_model.py"}, ROOT / "data" / MODEL_NAME, compress=3)
print("saved", mat.shape)
