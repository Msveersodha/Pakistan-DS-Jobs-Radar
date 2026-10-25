"""Cached data access for the UI. All functions are keyed on (api_url, JSON args) so that
Streamlit can cache them regardless of which client (API / local) answers."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import streamlit as st

from .client import make_client


def _j(x: Any) -> str:
    return json.dumps(x, sort_keys=True, default=str)


@st.cache_resource(show_spinner="Starting engine…")
def get_client(api_url: str):
    return make_client(api_url)


def _c(api_url: str):
    return get_client(api_url)[0]


@st.cache_data(show_spinner=False, ttl=3600)
def meta(api_url: str) -> Dict[str, Any]:
    return _c(api_url).meta()


@st.cache_data(show_spinner=False, ttl=900)
def stats(api_url: str, filters_json: str) -> Dict[str, Any]:
    return _c(api_url).stats(json.loads(filters_json))


@st.cache_data(show_spinner=False, ttl=900)
def search(api_url: str, filters_json: str, sort_by: str, page: int, page_size: int) -> Dict[str, Any]:
    return _c(api_url).search(json.loads(filters_json), sort_by, page, page_size)


@st.cache_data(show_spinner=False, ttl=900)
def all_results(api_url: str, filters_json: str, sort_by: str) -> List[Dict[str, Any]]:
    c, f, out, page = _c(api_url), json.loads(filters_json), [], 1
    while True:
        r = c.search(f, sort_by, page, 200)
        out += r["items"]
        if len(out) >= r["total"] or not r["items"]:
            return out
        page += 1


@st.cache_data(show_spinner=False, ttl=900)
def job(api_url: str, job_id: int):
    return _c(api_url).job(job_id)


@st.cache_data(show_spinner=False, ttl=900)
def similar(api_url: str, job_id: int, top_k: int = 5):
    return _c(api_url).similar(job_id, top_k)


@st.cache_data(show_spinner=False, ttl=900)
def match(api_url: str, args_json: str) -> Dict[str, Any]:
    return _c(api_url).match(**json.loads(args_json))


@st.cache_data(show_spinner=False, ttl=900)
def extract(api_url: str, text: str) -> List[str]:
    return _c(api_url).extract(text)


@st.cache_data(show_spinner=False, ttl=900)
def gap(api_url: str, job_id: int, skills_json: str):
    return _c(api_url).gap(job_id, json.loads(skills_json))


@st.cache_data(show_spinner=False, ttl=900)
def readiness(api_url: str, skills_json: str, role: Optional[str], filters_json: str, top_n: int):
    return _c(api_url).readiness(json.loads(skills_json), role, json.loads(filters_json), top_n)


@st.cache_data(show_spinner=False, ttl=900)
def learning_path(api_url: str, skills_json: str, filters_json: str, top_jobs: int, top_n: int):
    return _c(api_url).learning_path(json.loads(skills_json), json.loads(filters_json), top_jobs, top_n)
