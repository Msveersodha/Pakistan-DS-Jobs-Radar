from typing import List, Optional

from pydantic import BaseModel, Field


class Filters(BaseModel):
    cities: List[str] = []
    work_modes: List[str] = []
    employment_types: List[str] = []
    seniority: List[str] = []
    roles: List[str] = []
    companies: List[str] = []
    required_skills: List[str] = []
    max_days_ago: Optional[float] = None
    max_applicants: Optional[int] = None
    q: Optional[str] = None


class SearchRequest(BaseModel):
    filters: Filters = Filters()
    sort_by: str = Field("newest", pattern="^(newest|oldest|fewest_applicants|most_applicants|title|company)$")
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=200)


class MatchRequest(BaseModel):
    query: str = ""
    skills: List[str] = []
    filters: Filters = Filters()
    top_k: int = Field(10, ge=1, le=100)
    skill_weight: float = Field(0.3, ge=0, le=1)
    min_score: float = Field(0, ge=0, le=100)
    dedupe: bool = True


class TextRequest(BaseModel):
    text: str


class GapRequest(BaseModel):
    job_id: int
    skills: List[str] = []


class ReadinessRequest(BaseModel):
    skills: List[str] = []
    role: Optional[str] = None
    filters: Filters = Filters()
    top_n: int = Field(20, ge=1, le=50)


class LearningPathRequest(BaseModel):
    skills: List[str] = []
    filters: Filters = Filters()
    top_jobs: int = Field(30, ge=5, le=100)
    top_n: int = Field(12, ge=1, le=30)


class StatsRequest(BaseModel):
    filters: Filters = Filters()
