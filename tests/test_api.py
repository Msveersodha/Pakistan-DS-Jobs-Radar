import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_meta(client):
    assert client.get("/health").json()["n_jobs"] == 492
    m = client.get("/meta").json()
    assert "Python" in m["skills"] and "Lahore" in m["cities"]


def test_match_and_filters(client):
    r = client.post("/match", json={"skills": ["Python", "SQL"], "top_k": 5,
                                    "filters": {"work_modes": ["Remote"]}})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all(i["work_mode"] == "Remote" for i in items)
    assert items[0]["match_score"] >= items[-1]["match_score"]


def test_match_validation(client):
    assert client.post("/match", json={}).status_code == 422


def test_search_job_similar_gap(client):
    s = client.post("/jobs/search", json={"filters": {"q": "python"}, "page_size": 3}).json()
    assert s["total"] > 0 and len(s["items"]) == 3
    jid = s["items"][0]["job_id"]
    assert client.get(f"/jobs/{jid}").json()["description"]
    assert len(client.get(f"/jobs/{jid}/similar?top_k=3").json()["items"]) == 3
    g = client.post("/skills/gap", json={"job_id": jid, "skills": ["Python"]}).json()
    assert "coverage" in g
    assert client.get("/jobs/999999").status_code == 404


def test_stats_and_skills(client):
    st = client.post("/stats", json={"filters": {"cities": ["Lahore"]}}).json()
    assert st["kpis"]["jobs"] > 0 and st["top_skills"]
    assert "Python" in client.post("/skills/extract", json={"text": "I know python and sql"}).json()["skills"]
    assert client.post("/skills/readiness", json={"skills": ["Python"], "role": "Data Scientist"}).json()["n_jobs"] > 0
    assert client.post("/skills/learning-path", json={"skills": ["Python"]}).json()["skills"]
