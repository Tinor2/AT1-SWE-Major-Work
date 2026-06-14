# AT1-SWE-PomTimer-RonitBhandari

Pomodoro timer with to-do lists, analytics, and ML-driven productivity insights.

## Live Demo

**URL:** *https://yourusername.pythonanywhere.com* (coming soon — deploy with `wsgi.py`)

## Setup & Usage

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export SECRET_KEY="your-secret-key-here"   # optional; defaults to random

# 4. Run the app
FLASK_APP=pomodoro flask run --port 8000 --debug
```

Open http://localhost:8000, register an account, and start using the timer.

## Security Patch & Automation Summary

The following OWASP vulnerabilities were identified and patched in the Term 4 codebase:

| OWASP | Vulnerability | Fix | File(s) |
|-------|--------------|-----|---------|
| A03: Injection | `PRAGMA` f-string SQL injection | Whitelist validation via `_ALLOWED_TABLES` frozenset | `models/analytics.py` |
| A01: Broken Access Control | Tag PUT/DELETE missing `AND user_id = ?` (IDOR) | Row-level ownership enforced in all queries | `routes/tasks.py` |
| A08: Data Integrity | No CSRF tokens | Flask-WTF enabled, tokens in all forms + AJAX | `__init__.py`, all templates |
| A02: Cryptographic Failures | Hardcoded `SECRET_KEY` | `os.environ.get('SECRET_KEY')` with `os.urandom` fallback | `__init__.py` |
| A08: Data Integrity | Pickle deserialisation (RCE risk) | SHA-256 hash verification before `pickle.load()` via `MANIFEST.json` | `ml/trainer.py` |

**Automation:**
- ML model retraining runs in a background scheduler (APScheduler) — trains per-user decision trees on `user_statistics` data
- SAST: Bandit (security), Flake8 (lint), Safety (dependency audit)
- DAST: Manual penetration testing checklist covering CSRF, IDOR, SQL injection, open redirect, security headers

## ML Architecture

- `ml/trainer.py` — Per-user `DecisionTreeClassifier`, trains on aggregated daily feature rows
- `ml/predictor.py` — Predicts productivity band (Poor/Average/Good/Excellent), returns JSON for the analytics frontend
- `ml/feature_engineering.py` — Computes features (`task_completion_rate`, `session_completion_rate`, `consistency_score`, etc.)
- `ml/scheduler.py` — Scheduled retraining every hour

[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
