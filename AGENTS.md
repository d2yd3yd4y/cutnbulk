# cutnbulk

## Cursor Cloud specific instructions

The only application in this repo is `health_tracker/`, a local FastAPI + Jinja2 + SQLite
health tracking MVP (diet / workouts / body metrics / dashboard / weekly review). The UI text
is in Chinese.

### Environment
- Python 3.12 with a virtualenv at `health_tracker/.venv` (created by the startup update script).
  The `python3.12-venv` system package is required to create the venv and is already installed in
  the VM image.
- Dependencies are listed in `health_tracker/requirements.txt`.

### Run (dev mode)
Run from the `health_tracker/` directory (the app resolves `app/static`, `app/templates`,
`app/uploads` via relative paths, so the working directory matters):
```bash
cd health_tracker
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Then open http://127.0.0.1:8000 — routes: `/`, `/meals`, `/workouts`, `/body`, `/weekly`.

### Data / state
- A SQLite DB `health_tracker/health_tracker.db` is auto-created on first import (tables are
  created at import time in `main.py`). Delete the file to reset state; it is gitignored.
- Uploaded food photos are written to `health_tracker/app/uploads/` (gitignored).
- The food nutrition estimator (`app/services/food_ai_service.py`) is a local mock and needs no
  API key; it optionally checks `OPENAI_API_KEY` but never requires it, so the app runs offline.

### Lint / test / build
- There is no test suite, linter, or build step configured. Use
  `python -m compileall app main.py` (from `health_tracker/`) as a basic syntax check.
