@echo off
cd /d "%~dp0"
if not exist .venv (
  echo First run: creating Python environment...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
if not exist .env copy .env.example .env >nul
.venv\Scripts\python.exe app.py
pause
