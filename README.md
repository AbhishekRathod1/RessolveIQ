# ResolveIQ

ResolveIQ is an AI-powered enterprise IT support and workflow automation platform. This repository is an early development milestone and is not production-ready.

## Backend quick start

From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --app-dir backend --reload
```

The health endpoint is available at <http://127.0.0.1:8000/api/health>. Interactive API documentation is available at <http://127.0.0.1:8000/docs>.

## Run backend tests

```powershell
python -m pytest backend\tests
```
