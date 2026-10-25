"""Skill lexicon + extraction.

The LinkedIn `skills` column is sparse (about 40% empty) and messy, so skills are
extracted from title + skills + description with a curated regex lexicon.
Each entry: (canonical name, category, regex, case_sensitive)
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List

_B = r"(?<![A-Za-z0-9+#.])"   # left boundary that also protects C++, C#, .NET
_E = r"(?![A-Za-z0-9+#])"     # right boundary

LEXICON = [
    # --- Programming languages
    ("Python", "Languages", r"python", False),
    ("SQL", "Languages", r"sql", False),
    ("R", "Languages", r"R(?=\s*(?:programming|language|studio|,|/|;|\)|and\b|or\b))", True),
    ("Java", "Languages", r"java(?!\s*script)", False),
    ("JavaScript", "Languages", r"java\s*script", False),
    ("TypeScript", "Languages", r"type\s*script", False),
    ("C++", "Languages", r"C\+\+", True),
    ("C#", "Languages", r"C#", True),
    ("Scala", "Languages", r"scala", False),
    ("Julia", "Languages", r"julia", True),
    ("MATLAB", "Languages", r"matlab", False),
    ("SAS", "Languages", r"SAS", True),
    ("SPSS", "Languages", r"spss", False),
    ("PHP", "Languages", r"php", False),
    ("Bash/Shell", "Languages", r"bash|shell\s+script\w*", False),
    # --- Machine learning / AI
    ("Machine Learning", "ML & AI", r"(?i:machine[\s-]+learning)|ML", True),
    ("Deep Learning", "ML & AI", r"deep[\s-]+learning", False),
    ("NLP", "ML & AI", r"NLP|(?i:natural[\s-]+language[\s-]+processing)", True),
    ("Computer Vision", "ML & AI", r"computer[\s-]+vision", False),
    ("LLMs", "ML & AI", r"LLMs?|(?i:large[\s-]+language[\s-]+models?)", True),
    ("Generative AI", "ML & AI", r"(?i:generative[\s-]+ai)|Gen[\s-]?AI", True),
    ("RAG", "ML & AI", r"RAG|(?i:retrieval[\s-]+augmented)", True),
    ("Prompt Engineering", "ML & AI", r"prompt[\s-]+engineering", False),
    ("Artificial Intelligence", "ML & AI", r"AI|(?i:artificial[\s-]+intelligence)", True),
    ("Reinforcement Learning", "ML & AI", r"reinforcement[\s-]+learning", False),
    ("Time Series", "ML & AI", r"time[\s-]+series", False),
    ("Forecasting", "ML & AI", r"forecasting", False),
    ("Predictive Modeling", "ML & AI", r"predictive[\s-]+(?:model\w*|analytics)", False),
    ("Statistics", "ML & AI", r"statistic\w*", False),
    ("A/B Testing", "ML & AI", r"a/b[\s-]+test\w*|experimentation", False),
    ("Feature Engineering", "ML & AI", r"feature[\s-]+engineering", False),
    ("Recommendation Systems", "ML & AI", r"recommend(?:ation|er)s?[\s-]+(?:system|engine)s?", False),
    ("MLOps", "ML & AI", r"mlops|model[\s-]+deployment", False),
    # --- Libraries & frameworks
    ("pandas", "Libraries & Frameworks", r"pandas", False),
    ("NumPy", "Libraries & Frameworks", r"numpy", False),
    ("scikit-learn", "Libraries & Frameworks", r"scikit[\s-]?learn|sklearn", False),
    ("TensorFlow", "Libraries & Frameworks", r"tensorflow", False),
    ("PyTorch", "Libraries & Frameworks", r"pytorch", False),
    ("Keras", "Libraries & Frameworks", r"keras", False),
    ("Hugging Face", "Libraries & Frameworks", r"hugging\s?face", False),
    ("LangChain", "Libraries & Frameworks", r"lang\s?chain", False),
    ("OpenCV", "Libraries & Frameworks", r"opencv", False),
    ("XGBoost", "Libraries & Frameworks", r"xgboost|lightgbm", False),
    ("Matplotlib", "Libraries & Frameworks", r"matplotlib|seaborn", False),
    ("NLTK/spaCy", "Libraries & Frameworks", r"nltk|spacy", False),
    ("FastAPI", "Libraries & Frameworks", r"fastapi", False),
    ("Flask", "Libraries & Frameworks", r"flask", False),
    ("Django", "Libraries & Frameworks", r"django", False),
    ("Streamlit", "Libraries & Frameworks", r"streamlit", False),
    ("React", "Libraries & Frameworks", r"React(?:\.?js)?", True),
    ("Node.js", "Libraries & Frameworks", r"node\.?js", False),
    (".NET", "Libraries & Frameworks", r"\.NET", True),
    ("REST APIs", "Libraries & Frameworks", r"rest(?:ful)?[\s-]*apis?|apis?", False),
    # --- Data, analytics & BI
    ("Data Analysis", "Data & BI", r"data[\s-]+analy(?:sis|tics|sing|zing)", False),
    ("Data Visualization", "Data & BI", r"(?:data[\s-]+)?visuali[sz]ation", False),
    ("Power BI", "Data & BI", r"power[\s-]?bi", False),
    ("Tableau", "Data & BI", r"tableau", False),
    ("Looker", "Data & BI", r"looker", False),
    ("Excel", "Data & BI", r"(?:MS |Microsoft )?Excel(?!\s+(?:in|at|as|under|with))", True),
    ("Business Intelligence", "Data & BI", r"(?i:business[\s-]+intelligence)|(?<!Power )(?<!Power-)BI", True),
    ("Dashboards", "Data & BI", r"dashboards?", False),
    ("ETL", "Data & BI", r"ETL|ELT", True),
    ("Data Modeling", "Data & BI", r"data[\s-]+model\w*", False),
    ("Data Warehousing", "Data & BI", r"(?i:data[\s-]+warehous\w*)|DWH?", True),
    ("Data Mining", "Data & BI", r"data[\s-]+mining", False),
    ("Data Cleaning", "Data & BI", r"data[\s-]+(?:cleaning|cleansing|wrangling|preparation)", False),
    ("Big Data", "Data & BI", r"big[\s-]+data", False),
    ("Google Analytics", "Data & BI", r"google[\s-]+analytics", False),
    # --- Databases & data platforms
    ("PostgreSQL", "Databases & Platforms", r"postgres(?:ql)?", False),
    ("MySQL", "Databases & Platforms", r"mysql", False),
    ("SQL Server", "Databases & Platforms", r"sql[\s-]+server|mssql|t-sql", False),
    ("MongoDB", "Databases & Platforms", r"mongo(?:db)?", False),
    ("NoSQL", "Databases & Platforms", r"no[\s-]?sql", False),
    ("Oracle", "Databases & Platforms", r"oracle", False),
    ("Redis", "Databases & Platforms", r"redis", False),
    ("Elasticsearch", "Databases & Platforms", r"elasticsearch", False),
    ("Vector Databases", "Databases & Platforms", r"vector[\s-]+(?:database|db|store)s?|pinecone|faiss|chroma", False),
    ("Snowflake", "Databases & Platforms", r"snowflake", False),
    ("BigQuery", "Databases & Platforms", r"big[\s-]?query", False),
    ("Redshift", "Databases & Platforms", r"redshift", False),
    ("Spark", "Databases & Platforms", r"(?:py)?spark", False),
    ("Hadoop", "Databases & Platforms", r"hadoop|hive", False),
    ("Kafka", "Databases & Platforms", r"kafka", False),
    ("Airflow", "Databases & Platforms", r"airflow", False),
    ("dbt", "Databases & Platforms", r"dbt", True),
    ("Databricks", "Databases & Platforms", r"databricks", False),
    # --- Cloud & DevOps
    ("AWS", "Cloud & DevOps", r"AWS|(?i:amazon[\s-]+web[\s-]+services)", True),
    ("Azure", "Cloud & DevOps", r"azure", False),
    ("GCP", "Cloud & DevOps", r"GCP|(?i:google[\s-]+cloud)", True),
    ("Docker", "Cloud & DevOps", r"docker", False),
    ("Kubernetes", "Cloud & DevOps", r"kubernetes|k8s", False),
    ("Git", "Cloud & DevOps", r"git(?:hub|lab)?", False),
    ("CI/CD", "Cloud & DevOps", r"ci\s?/\s?cd", False),
    ("Linux", "Cloud & DevOps", r"linux|unix", False),
    ("Terraform", "Cloud & DevOps", r"terraform", False),
    ("Jenkins", "Cloud & DevOps", r"jenkins", False),
    # --- Professional skills
    ("Communication", "Professional", r"communication", False),
    ("Agile/Scrum", "Professional", r"agile|scrum", False),
    ("Project Management", "Professional", r"project[\s-]+management", False),
    ("Problem Solving", "Professional", r"problem[\s-]+solving", False),
]

_COMPILED = []
for _name, _cat, _pat, _cs in LEXICON:
    _flags = 0 if _cs else re.IGNORECASE
    _COMPILED.append((_name, re.compile(_B + r"(?:" + _pat + r")" + _E, _flags)))

SKILL_CATEGORY: Dict[str, str] = {name: cat for name, cat, _, _ in LEXICON}
ALL_SKILLS: List[str] = [name for name, *_ in LEXICON]
CATEGORIES: List[str] = list(dict.fromkeys(cat for _, cat, _, _ in LEXICON))

# fast alias lookup for free-text skills typed by users ("sklearn", "powerbi", ...)
_ALIASES = {n.lower(): n for n in ALL_SKILLS}


def extract_skills(text: str) -> List[str]:
    """Return canonical skills found in free text (stable lexicon order)."""
    if not text:
        return []
    return [name for name, rx in _COMPILED if rx.search(text)]


def normalize_skill_list(items: Iterable[str]) -> List[str]:
    """Map user-supplied skill strings to canonical names where possible."""
    out: List[str] = []
    for raw in items or []:
        s = (raw or "").strip()
        if not s:
            continue
        canon = _ALIASES.get(s.lower())
        if canon is None:
            found = extract_skills(s)
            canon = found[0] if found and len(found) == 1 else s
        if canon not in out:
            out.append(canon)
    return out
