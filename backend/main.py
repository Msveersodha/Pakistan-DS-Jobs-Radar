"""FastAPI backend.  Run:  uvicorn backend.main:app --reload --port 8000
Interactive docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from core.engine import JobEngine
from .schemas import (GapRequest, LearningPathRequest, MatchRequest, ReadinessRequest, SearchRequest,
                      StatsRequest, TextRequest)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = JobEngine()
    yield


app = FastAPI(
    title="Pakistan Data-Science Jobs API",
    description="TF-IDF job matching, search and analytics over a LinkedIn scrape of Pakistani data-science jobs.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def eng() -> JobEngine:
    return app.state.engine


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "n_jobs": len(eng().df), "model_source": eng().model_source}


@app.get("/meta", tags=["system"])
def meta():
    """Filter options, skill list, dataset notes."""
    return eng().meta()


@app.post("/jobs/search", tags=["jobs"])
def search_jobs(req: SearchRequest):
    return eng().search_jobs(req.filters.model_dump(), req.sort_by, req.page, req.page_size)


@app.get("/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: int):
    job = eng().get_job(job_id)
    if job is None:
        raise HTTPException(404, f"job {job_id} not found")
    return job


@app.get("/jobs/{job_id}/similar", tags=["jobs"])
def similar_jobs(job_id: int, top_k: int = Query(5, ge=1, le=25)):
    if eng().get_job(job_id) is None:
        raise HTTPException(404, f"job {job_id} not found")
    return {"items": eng().similar(job_id, top_k)}


@app.post("/match", tags=["matching"])
def match(req: MatchRequest):
    """Rank jobs for a skills list and/or free text (resume, summary)."""
    if not req.query.strip() and not req.skills:
        raise HTTPException(422, "provide `query` text and/or `skills`")
    return eng().match(req.query, req.skills, req.filters.model_dump(), req.top_k,
                       req.skill_weight, req.min_score, req.dedupe)


@app.post("/skills/extract", tags=["skills"])
def extract_skills(req: TextRequest):
    return {"skills": eng().extract(req.text)}


@app.post("/skills/gap", tags=["skills"])
def skill_gap(req: GapRequest):
    out = eng().skill_gap(req.job_id, req.skills)
    if out is None:
        raise HTTPException(404, f"job {req.job_id} not found")
    return out


@app.post("/skills/readiness", tags=["skills"])
def readiness(req: ReadinessRequest):
    return eng().role_readiness(req.skills, req.role, req.filters.model_dump(), req.top_n)


@app.post("/skills/learning-path", tags=["skills"])
def learning_path(req: LearningPathRequest):
    return eng().learning_path(req.skills, req.filters.model_dump(), req.top_jobs, req.top_n)


@app.post("/stats", tags=["analytics"])
def stats(req: StatsRequest):
    """Dashboard aggregates for the (optionally filtered) job set."""
    return eng().stats(req.filters.model_dump())
