"""Feature enrichment on top of the already-cleaned CSV."""
from __future__ import annotations

import re
import unicodedata
from typing import List

import numpy as np
import pandas as pd

from .skills import extract_skills

CITY_ALIASES = {
    "karachi division": "Karachi",
    "lahore division": "Lahore",
    "lahore district": "Lahore",
    "pakistan": "Pakistan (unspecified)",
    "punjab": "Punjab (unspecified)",
    "apj": "Unspecified",
}

ROLE_RULES = [
    ("Data Scientist", r"data\s*scien"),
    ("ML / AI Engineer", r"machine learning|\bml\b|\bai\b|artificial|\bnlp\b|\bllm\b|deep learning|computer vision|gen\s?ai|generative"),
    ("Data Engineer", r"data\s*engineer|\betl\b|big data|warehouse|pipeline|databricks|\bdwh\b"),
    ("Data / BI Analyst", r"data\s*analy|analytics|business analyst|\bbi\b|power bi|tableau|insight|reporting|visuali"),
    ("Security", r"security|cyber|penetration|soc analyst"),
    ("Sales & Marketing", r"sales|marketing|business development|account manager|customer|recruit|talent"),
    ("Research & Education", r"research|professor|lecturer|instructor|teacher|trainer|tutor"),
    ("Software Engineer", r"software|developer|backend|back-end|full[\s-]?stack|front[\s-]?end|python|engineer|devops|programmer|\bweb\b|\.net|java"),
]


def _ascii(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_city(loc: str) -> str:
    if not isinstance(loc, str) or not loc.strip():
        return "Unspecified"
    first = _ascii(loc.split(",")[0]).strip()
    return CITY_ALIASES.get(first.lower(), first)


def work_mode(t: str) -> str:
    t = t or ""
    for mode in ("Remote", "Hybrid", "On-site"):
        if mode.lower() in t.lower():
            return mode
    return "Not specified"


def employment(t: str) -> str:
    t = t or ""
    for label, pat in (("Contract", r"contract"), ("Part-time", r"part-time"), ("Temporary", r"temporary"),
                       ("Volunteer", r"volunteer"), ("Full-time", r"full-time"), ("Internship", r"internship")):
        if re.search(pat, t, re.I):
            return label
    return "Not specified"


def seniority(t: str) -> str:
    t = t or ""
    for label, pat in (("Internship", r"internship"), ("Entry level", r"entry level"), ("Associate", r"associate"),
                       ("Mid-Senior level", r"mid-senior"), ("Director", r"director"), ("Executive", r"executive")):
        if re.search(pat, t, re.I):
            return label
    return "Not specified"


def pay_text(t: str) -> str | None:
    t = (t or "").strip()
    head = re.split(r"\s*\b(?:Remote|On-site|Hybrid|Full-time|Part-time|Contract|Internship|Temporary|Volunteer|Entry|Associate|Mid-Senior|Director|Executive)", t)[0].strip()
    return head if head and re.match(r"^(\$|PKR|Rs|USD|\d)", head) else None


def role_category(title: str) -> str:
    t = (title or "").lower()
    for label, pat in ROLE_RULES:
        if re.search(pat, t):
            return label
    return "Other"


def days_ago(t: str) -> float:
    m = re.search(r"(\d+)\s+(minute|hour|day|week|month)", t or "", re.I)
    if not m:
        return np.nan
    n, unit = int(m.group(1)), m.group(2).lower()
    return n * {"minute": 1 / 1440, "hour": 1 / 24, "day": 1, "week": 7, "month": 30}[unit]


def clean_linkedin_skills(s) -> List[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    s = re.sub(r"\)(?=[A-Z])", "), ", s)
    parts = [re.sub(r"^and\s+", "", p.strip()) for p in re.split(r",", s)]
    return [p for p in parts if p]


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["job_id"] = d["job_id"].astype(int)
    d["city"] = d["location"].map(normalize_city)
    d["work_mode"] = d["type_info"].map(work_mode)
    d["employment"] = d["type_info"].map(employment)
    d["seniority"] = d["type_info"].map(seniority)
    d["pay_text"] = d["type_info"].map(pay_text)
    d["role"] = d["job_title"].map(role_category)
    d["is_repost"] = d["time_posted"].fillna("").str.contains("Reposted", case=False)
    d["days_ago"] = d["time_posted"].map(days_ago)
    d["description_clean"] = d["description"].fillna("").str.replace(r"^\s*About the job\s*", "", regex=True)
    d["listed_skills"] = d["skills"].map(clean_linkedin_skills)
    # skills are extracted from title + LinkedIn skills + description
    src = (d["job_title"].fillna("") + " . " + d["skills"].fillna("") + " . " + d["description_clean"])
    d["skills_found"] = src.map(extract_skills)
    d["applicant_count"] = d["applicant_count"].fillna(0).astype(int)
    return d
