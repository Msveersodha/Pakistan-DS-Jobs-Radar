#!/usr/bin/env bash
# Uses the API if it is running on :8000, otherwise falls back to the built-in engine.
cd "$(dirname "$0")"
export API_URL="${API_URL:-http://localhost:8000}"
python -m streamlit run streamlit_app.py
