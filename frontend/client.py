"""Two interchangeable clients.

* ApiClient   -> talks to the FastAPI backend over HTTP   (API_URL set)
* LocalClient -> calls the same engine in-process          (standalone / Streamlit Cloud)

Both expose exactly the same methods and return plain JSON-style dicts.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests


class ApiError(RuntimeError):
    pass


class LocalClient:
    mode = "standalone"
    label = "Built-in engine (no API server)"

    def __init__(self):
        from core.engine import get_engine
        self.e = get_engine()

    def health(self):
        return {"status": "ok", "n_jobs": len(self.e.df), "model_source": self.e.model_source}

    def meta(self):
        return self.e.meta()

    def search(self, filters, sort_by="newest", page=1, page_size=25):
        return self.e.search_jobs(filters, sort_by, page, page_size)

    def job(self, job_id):
        return self.e.get_job(job_id)

    def similar(self, job_id, top_k=5):
        return self.e.similar(job_id, top_k)

    def match(self, query="", skills=None, filters=None, top_k=10, skill_weight=0.3, min_score=0.0, dedupe=True):
        return self.e.match(query, skills or [], filters, top_k, skill_weight, min_score, dedupe)

    def extract(self, text):
        return self.e.extract(text)

    def gap(self, job_id, skills):
        return self.e.skill_gap(job_id, skills)

    def readiness(self, skills, role=None, filters=None, top_n=20):
        return self.e.role_readiness(skills, role, filters, top_n)

    def learning_path(self, skills, filters=None, top_jobs=30, top_n=12):
        return self.e.learning_path(skills, filters, top_jobs, top_n)

    def stats(self, filters=None):
        return self.e.stats(filters)


class ApiClient:
    mode = "api"

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base = base_url.rstrip("/")
        self.label = f"FastAPI backend · {self.base}"
        self.timeout = timeout
        self.s = requests.Session()

    def _req(self, method: str, path: str, **kw) -> Any:
        try:
            r = self.s.request(method, self.base + path, timeout=self.timeout, **kw)
        except requests.RequestException as exc:
            raise ApiError(f"Cannot reach API at {self.base}: {exc}") from exc
        if r.status_code == 404:
            return None
        if not r.ok:
            raise ApiError(f"{method} {path} -> {r.status_code}: {r.text[:200]}")
        return r.json()

    def health(self):
        return self._req("GET", "/health")

    def meta(self):
        return self._req("GET", "/meta")

    def search(self, filters, sort_by="newest", page=1, page_size=25):
        return self._req("POST", "/jobs/search", json={"filters": filters or {}, "sort_by": sort_by,
                                                      "page": page, "page_size": page_size})

    def job(self, job_id):
        return self._req("GET", f"/jobs/{int(job_id)}")

    def similar(self, job_id, top_k=5):
        out = self._req("GET", f"/jobs/{int(job_id)}/similar", params={"top_k": top_k})
        return (out or {}).get("items", [])

    def match(self, query="", skills=None, filters=None, top_k=10, skill_weight=0.3, min_score=0.0, dedupe=True):
        return self._req("POST", "/match", json={"query": query, "skills": skills or [], "filters": filters or {},
                                                 "top_k": top_k, "skill_weight": skill_weight,
                                                 "min_score": min_score, "dedupe": dedupe})

    def extract(self, text):
        return self._req("POST", "/skills/extract", json={"text": text})["skills"]

    def gap(self, job_id, skills):
        return self._req("POST", "/skills/gap", json={"job_id": int(job_id), "skills": skills})

    def readiness(self, skills, role=None, filters=None, top_n=20):
        return self._req("POST", "/skills/readiness", json={"skills": skills, "role": role,
                                                            "filters": filters or {}, "top_n": top_n})

    def learning_path(self, skills, filters=None, top_jobs=30, top_n=12):
        return self._req("POST", "/skills/learning-path", json={"skills": skills, "filters": filters or {},
                                                                 "top_jobs": top_jobs, "top_n": top_n})

    def stats(self, filters=None):
        return self._req("POST", "/stats", json={"filters": filters or {}})


def make_client(api_url: Optional[str]):
    """Return (client, warning). Falls back to the built-in engine if the API is unreachable."""
    api_url = (api_url or "").strip()
    if api_url:
        client = ApiClient(api_url)
        try:
            client.health()
            return client, None
        except ApiError as exc:
            return LocalClient(), f"{exc}. Using the built-in engine instead."
    return LocalClient(), None
