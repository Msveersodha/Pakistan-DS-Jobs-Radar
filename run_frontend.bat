@echo off
cd /d "%~dp0"
if "%API_URL%"=="" set API_URL=http://localhost:8000
python -m streamlit run streamlit_app.py
