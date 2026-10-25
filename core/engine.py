"""Job matching + analytics engine shared by the FastAPI backend and the Streamlit app."""
from __future__ import annotations

import os
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from .preprocess import enrich
from .skills import ALL_SKILLS, CATEGORIES, SKILL_CATEGORY, extract_skills, normalize_skill_list

DEFAULT_DATA_DIR = Path(os.environ.get("JOBMATCH_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
CSV_NAME = "cleaned_data_science_jobs_pakistan.csv"
MODEL_NAME = "job_matcher_tfidf.joblib"

TFIDF_PARAMS = dict(max_features=50000, ngram_range=(1, 2), stop_words="english",
                    sublinear_tf=True, strip_accents="unicode")

DATA_NOTE = ("Dataset: LinkedIn scrape of data-science related jobs in Pakistan (July 2024). "
             "Applicant counts like 'Over 100' are stored as a lower bound of 100. "
             "'Posted' ages are relative to the scrape date.")

FILTER_KEYS = ("cities", "work_modes", "employment_types", "seniority", "roles", "companies",
               "required_skills", "max_days_ago", "max_applicants", "q")


def _py(x: Any) -> Any:
    """Make numpy / pandas values JSON friendly."""
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if np.isnan(x) else float(x)
    if isinstance(x, float) and np.isnan(x):
        return None
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, dict):
        return {k: _py(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_py(v) for v in x]
    return x


class JobEngine:
    def __init__(self, data_dir: Optional[os.PathLike] = None):
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        raw = pd.read_csv(self.data_dir / CSV_NAME)
        self.df = enrich(raw).reset_index(drop=True)
        self.model_source = "joblib"
        self.vectorizer, self.job_matrix = self._load_or_fit_model()
        # job x skill boolean matrix (fast filtering + analytics)
        self.skill_df = pd.DataFrame(
            {s: self.df["skills_found"].map(lambda l, s=s: s in l) for s in ALL_SKILLS}
        )
        self.skill_df = self.skill_df.loc[:, self.skill_df.sum() > 0]
        self._id_to_idx = {int(j): i for i, j in enumerate(self.df["job_id"])}
        self._search_blob = (self.df["job_title"].fillna("") + " " + self.df["company_name"].fillna("") + " "
                             + self.df["skills"].fillna("") + " " + self.df["description_clean"]).str.lower()

    # ------------------------------------------------------------------ model
    def _load_or_fit_model(self):
        path = self.data_dir / MODEL_NAME
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                bundle = joblib.load(path)
            vec, mat = bundle["vectorizer"], bundle["job_matrix"]
            ids_ok = [int(r["job_id"]) for r in bundle["job_records"]] == self.df["job_id"].tolist()
            if mat.shape[0] != len(self.df) or not ids_ok:
                raise ValueError("model rows do not match CSV rows")
            vec.transform(["python sql"])  # make sure unpickled vectorizer works in this sklearn version
            return vec, mat
        except Exception as exc:  # version mismatch, missing file, etc. -> rebuild from CSV
            warnings.warn(f"Could not use {MODEL_NAME} ({exc}); re-fitting TF-IDF from CSV.")
            self.model_source = "refit"
            vec = TfidfVectorizer(**TFIDF_PARAMS)
            mat = vec.fit_transform(self.df["model_text"].fillna(""))
            return vec, mat

    # ---------------------------------------------------------------- filters
    def _mask(self, f: Optional[Dict[str, Any]]) -> np.ndarray:
        f = f or {}
        d = self.df
        m = np.ones(len(d), dtype=bool)
        for key, col in (("cities", "city"), ("work_modes", "work_mode"), ("employment_types", "employment"),
                         ("seniority", "seniority"), ("roles", "role"), ("companies", "company_name")):
            vals = f.get(key)
            if vals:
                m &= d[col].isin(vals).to_numpy()
        if f.get("max_days_ago") is not None:
            m &= (d["days_ago"].fillna(1e9) <= float(f["max_days_ago"])).to_numpy()
        if f.get("max_applicants") is not None:
            m &= (d["applicant_count"] <= int(f["max_applicants"])).to_numpy()
        for s in normalize_skill_list(f.get("required_skills") or []):
            if s in self.skill_df.columns:
                m &= self.skill_df[s].to_numpy()
            else:
                m &= False
        q = (f.get("q") or "").strip().lower()
        if q:
            for tok in q.split():
                m &= self._search_blob.str.contains(tok, regex=False).to_numpy()
        return m

    # ------------------------------------------------------------------- meta
    def meta(self) -> Dict[str, Any]:
        d = self.df
        counts = lambda c: [k for k, _ in Counter(d[c]).most_common()]
        skill_counts = self.skill_df.sum().sort_values(ascending=False)
        return _py({
            "n_jobs": len(d),
            "cities": counts("city"),
            "work_modes": counts("work_mode"),
            "employment_types": counts("employment"),
            "seniority": counts("seniority"),
            "roles": counts("role"),
            "companies": counts("company_name"),
            "skills": list(skill_counts.index),
            "skill_categories": {s: SKILL_CATEGORY[s] for s in skill_counts.index},
            "categories": CATEGORIES,
            "max_days_ago": float(d["days_ago"].max()),
            "note": DATA_NOTE,
            "model_source": self.model_source,
            "vocab_size": int(len(self.vectorizer.vocabulary_)),
        })

    # ------------------------------------------------------------------- rows
    def _row(self, i: int, full: bool = False) -> Dict[str, Any]:
        r = self.df.iloc[i]
        out = {
            "job_id": int(r.job_id), "job_title": r.job_title, "company_name": r.company_name,
            "location": r.location, "city": r.city, "work_mode": r.work_mode, "employment": r.employment,
            "seniority": r.seniority, "role": r.role, "pay_text": r.pay_text, "time_posted": r.time_posted,
            "days_ago": r.days_ago, "is_repost": bool(r.is_repost), "applicants": r.applicants,
            "applicant_count": int(r.applicant_count), "applicant_count_type": r.applicant_count_type,
            "skills_found": list(r.skills_found),
            "snippet": (r.description_clean[:280] + "…") if len(r.description_clean) > 280 else r.description_clean,
        }
        if full:
            out["description"] = r.description_clean
            out["listed_skills"] = list(r.listed_skills)
        return _py(out)

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        i = self._id_to_idx.get(int(job_id))
        return None if i is None else self._row(i, full=True)

    # ----------------------------------------------------------------- search
    def search_jobs(self, filters: Optional[Dict[str, Any]] = None, sort_by: str = "newest",
                    page: int = 1, page_size: int = 25) -> Dict[str, Any]:
        m = self._mask(filters)
        d = self.df[m]
        sorters = {
            "newest": ("days_ago", True), "oldest": ("days_ago", False),
            "fewest_applicants": ("applicant_count", True), "most_applicants": ("applicant_count", False),
            "title": ("job_title", True), "company": ("company_name", True),
        }
        col, asc = sorters.get(sort_by, sorters["newest"])
        d = d.sort_values(col, ascending=asc, na_position="last", kind="stable")
        total = len(d)
        page = max(1, int(page)); page_size = max(1, min(int(page_size), 200))
        d = d.iloc[(page - 1) * page_size: page * page_size]
        items = [self._row(self._id_to_idx[int(j)]) for j in d["job_id"]]
        return {"total": int(total), "page": page, "page_size": page_size, "items": items}

    # ------------------------------------------------------------------ match
    def match(self, query: str = "", skills: Optional[List[str]] = None, filters: Optional[Dict[str, Any]] = None,
              top_k: int = 10, skill_weight: float = 0.3, min_score: float = 0.0,
              dedupe: bool = True) -> Dict[str, Any]:
        skills = normalize_skill_list(skills or [])
        text = f"{query or ''} {' '.join(skills)}".strip()
        if not text:
            return {"query_skills": [], "total_candidates": 0, "items": []}
        q_skills = list(dict.fromkeys(skills + extract_skills(text)))
        qvec = self.vectorizer.transform([text])
        cos = np.asarray((self.job_matrix @ qvec.T).todense()).ravel()
        cos_n = cos / cos.max() if cos.max() > 0 else cos
        qset = set(q_skills)
        cov = np.array([len(qset & set(s)) / max(len(s), 1) for s in self.df["skills_found"]])
        w = float(np.clip(skill_weight, 0, 1))
        score = (1 - w) * cos_n + w * cov
        m = self._mask(filters)
        idx = np.where(m)[0]
        idx = idx[np.argsort(-score[idx], kind="stable")]
        items = []
        seen = set()
        for i in idx:
            if score[i] * 100 < min_score:
                break
            key = (str(self.df["job_title"].iloc[i]).lower(), str(self.df["company_name"].iloc[i]).lower())
            if dedupe and key in seen:  # same role re-posted several times
                continue
            seen.add(key)
            row = self._row(int(i))
            jset = list(self.df["skills_found"].iloc[i])
            row.update({
                "match_score": round(float(score[i]) * 100, 1),
                "text_similarity": round(float(cos[i]), 4),
                "skill_coverage": round(float(cov[i]) * 100, 1),
                "matched_skills": [s for s in jset if s in qset],
                "missing_skills": [s for s in jset if s not in qset][:12],
            })
            items.append(row)
            if len(items) >= top_k:
                break
        return {"query_skills": q_skills, "total_candidates": int(m.sum()), "items": items}

    def similar(self, job_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        i = self._id_to_idx.get(int(job_id))
        if i is None:
            return []
        sims = np.asarray((self.job_matrix @ self.job_matrix[i].T).todense()).ravel()
        sims[i] = -1
        out = []
        for j in np.argsort(-sims)[:top_k]:
            row = self._row(int(j))
            row["similarity"] = round(float(sims[j]) * 100, 1)
            out.append(row)
        return out

    # ------------------------------------------------------------- skill tools
    def extract(self, text: str) -> List[str]:
        return extract_skills(text or "")

    def skill_gap(self, job_id: int, skills: List[str]) -> Optional[Dict[str, Any]]:
        i = self._id_to_idx.get(int(job_id))
        if i is None:
            return None
        have = set(normalize_skill_list(skills))
        need = list(self.df["skills_found"].iloc[i])
        matched = [s for s in need if s in have]
        missing = [s for s in need if s not in have]
        return {"job_id": int(job_id), "required": need, "matched": matched, "missing": missing,
                "coverage": round(100 * len(matched) / len(need), 1) if need else 0.0,
                "extra_skills": [s for s in have if s not in need]}

    def role_readiness(self, skills: List[str], role: Optional[str] = None,
                       filters: Optional[Dict[str, Any]] = None, top_n: int = 20) -> Dict[str, Any]:
        """Market demand for skills (optionally within a role) vs. the user's skills."""
        f = dict(filters or {})
        if role:
            f["roles"] = [role]
        m = self._mask(f)
        have = set(normalize_skill_list(skills))
        sub = self.skill_df[m]
        n = int(m.sum())
        if n == 0:
            return {"n_jobs": 0, "skills": [], "coverage_weighted": 0.0}
        share = (sub.sum() / n).sort_values(ascending=False).head(top_n)
        rows = [{"skill": s, "category": SKILL_CATEGORY[s], "share": round(float(v) * 100, 1),
                 "jobs": int(sub[s].sum()), "have": s in have} for s, v in share.items()]
        tot = sum(r["share"] for r in rows)
        got = sum(r["share"] for r in rows if r["have"])
        return {"n_jobs": n, "skills": rows, "coverage_weighted": round(100 * got / tot, 1) if tot else 0.0}

    def learning_path(self, skills: List[str], filters: Optional[Dict[str, Any]] = None,
                      top_jobs: int = 30, top_n: int = 12) -> Dict[str, Any]:
        """Missing skills ranked by how often they appear in the user's best-matching jobs."""
        res = self.match(skills=skills, filters=filters, top_k=top_jobs, skill_weight=0.5)
        have = set(res["query_skills"])
        weights: Counter = Counter()
        counts: Counter = Counter()
        for it in res["items"]:
            for s in it["skills_found"]:
                if s not in have:
                    weights[s] += it["match_score"] / 100
                    counts[s] += 1
        rows = [{"skill": s, "category": SKILL_CATEGORY[s], "jobs": counts[s],
                 "weighted_score": round(float(w), 2)} for s, w in weights.most_common(top_n)]
        return {"based_on_jobs": len(res["items"]), "skills": rows}

    # ------------------------------------------------------------------ stats
    @staticmethod
    def _counts(series: pd.Series, top: Optional[int] = None) -> List[Dict[str, Any]]:
        vc = series.value_counts()
        if top:
            vc = vc.head(top)
        return [{"label": str(k), "count": int(v)} for k, v in vc.items()]

    def stats(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        m = self._mask(filters)
        d = self.df[m]
        n = len(d)
        if n == 0:
            return {"n_jobs": 0}
        sk = self.skill_df[m]
        skill_rows = [{"skill": s, "category": SKILL_CATEGORY[s], "count": int(c), "share": round(100 * c / n, 1)}
                      for s, c in sk.sum().sort_values(ascending=False).items() if c > 0]

        top_roles = d["role"].value_counts().head(7).index.tolist()
        top_sk = [r["skill"] for r in skill_rows[:14]]
        heat = []
        for role in top_roles:
            sub = sk[(d["role"] == role).to_numpy()]
            heat.append([round(100 * float(sub[s].mean()), 1) if len(sub) else 0 for s in top_sk])
        co_sk = top_sk[:12]
        co = sk[co_sk].astype(int)
        cooc = (co.T @ co).to_numpy().tolist()

        def bucket(vals, edges, labels):
            return [{"label": lab, "count": int(((vals >= lo) & (vals < hi)).sum())}
                    for (lo, hi), lab in zip(zip(edges[:-1], edges[1:]), labels)]

        da = d["days_ago"].dropna()
        recency = bucket(da, [0, 1, 4, 8, 15, 29, 91, 1e9],
                         ["< 1 day", "1–3 days", "4–7 days", "1–2 weeks", "2–4 weeks", "1–3 months", "3+ months"])
        ac = d["applicant_count"]
        applicants = bucket(ac, [0, 1, 11, 26, 51, 100, 1e9],
                            ["0", "1–10", "11–25", "26–50", "51–99", "100+ (lower bound)"])
        comp = (d.groupby("role")["applicant_count"].agg(["mean", "count"]).reset_index()
                .sort_values("mean", ascending=False))
        comp_rows = [{"role": r.role, "avg_applicants": round(float(r["mean"]), 1), "jobs": int(r["count"])}
                     for _, r in comp.iterrows()]
        pay = d[d["pay_text"].notna()]
        points = d[["job_id", "job_title", "company_name", "role", "work_mode", "days_ago", "applicant_count"]]
        return _py({
            "n_jobs": n,
            "kpis": {
                "jobs": n,
                "companies": int(d["company_name"].nunique()),
                "cities": int((~d["city"].isin(["Pakistan (unspecified)", "Punjab (unspecified)", "Unspecified"]))
                              .groupby(d["city"]).any().sum()),
                "remote_share": round(100 * float((d["work_mode"] == "Remote").mean()), 1),
                "entry_share": round(100 * float(d["seniority"].isin(["Entry level", "Internship"]).mean()), 1),
                "median_applicants": float(ac.median()),
                "median_days_ago": float(da.median()) if len(da) else None,
                "with_pay": int(len(pay)),
                "with_listed_skills": int((~d["skills_missing"]).sum()),
            },
            "by_city": self._counts(d["city"]),
            "by_work_mode": self._counts(d["work_mode"]),
            "by_employment": self._counts(d["employment"]),
            "by_seniority": self._counts(d["seniority"]),
            "by_role": self._counts(d["role"]),
            "top_companies": self._counts(d["company_name"], 15),
            "top_skills": skill_rows,
            "skills_by_role": {"roles": top_roles, "skills": top_sk, "z": heat},
            "skill_cooccurrence": {"skills": co_sk, "z": cooc},
            "recency": recency,
            "applicant_buckets": applicants,
            "competition_by_role": comp_rows,
            "pay_jobs": [{"job_id": int(r.job_id), "job_title": r.job_title, "company_name": r.company_name,
                          "pay": r.pay_text, "work_mode": r.work_mode} for _, r in pay.iterrows()],
            "points": points.to_dict("records"),
        })


_ENGINE: Optional[JobEngine] = None


def get_engine(data_dir: Optional[os.PathLike] = None) -> JobEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = JobEngine(data_dir)
    return _ENGINE
