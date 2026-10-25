import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core import JobEngine
from core.skills import extract_skills


@pytest.fixture(scope="module")
def eng():
    return JobEngine()


def test_skill_extraction():
    s = extract_skills("Python, SQL, Power BI, C++ and R programming; NoSQL; Excel at teamwork")
    assert {"Python", "SQL", "Power BI", "C++", "R", "NoSQL"} <= set(s)
    assert "Excel" not in s and "Business Intelligence" not in s


def test_model_aligned_with_csv(eng):
    assert eng.job_matrix.shape[0] == len(eng.df) == 492


def test_match_ranking_and_dedupe(eng):
    r = eng.match(skills=["Python", "SQL"], top_k=15)
    scores = [i["match_score"] for i in r["items"]]
    assert scores == sorted(scores, reverse=True)
    keys = [(i["job_title"], i["company_name"]) for i in r["items"]]
    assert len(keys) == len(set(keys))


def test_filters(eng):
    r = eng.search_jobs({"work_modes": ["Remote"], "required_skills": ["Python"]}, page_size=200)
    assert r["total"] > 0 and all(i["work_mode"] == "Remote" and "Python" in i["skills_found"] for i in r["items"])


def test_similar_excludes_self(eng):
    assert all(i["job_id"] != 1 for i in eng.similar(1, 5))


def test_empty_filter_stats(eng):
    assert eng.stats({"cities": ["Nowhere"]})["n_jobs"] == 0
