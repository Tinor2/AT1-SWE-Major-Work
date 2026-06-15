# AT1-SWE-PomTimer-RonitBhandari

Pomodoro timer with to-do lists, analytics, and ML-driven productivity insights.

## Live Demo

**URL:** *https://rbhan1.pythonanywhere.com/* — deploy using `wsgi.py`

## Setup & Usage

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export SECRET_KEY="your-secret-key-here"   # optional; defaults to urandom(32)

# 4. Initialise the database
FLASK_APP=pomodoro flask init-db

# 5. (Optional) Seed sample users with diverse productivity profiles
FLASK_APP=pomodoro flask seed-users

# 6. Run the app
FLASK_APP=pomodoro flask run --port 8000
```

Open http://localhost:8000, register an account, and start using the timer.

## Security Patch & Automation Summary

### Patched OWASP Vulnerabilities

| OWASP | Vulnerability | Fix | File(s) |
|-------|--------------|-----|---------|
| A03: Injection | F-string SQL injection in analytics `PRAGMA` query | Whitelist validation via `_ALLOWED_TABLES` frozenset — only known table names are accepted; anything else returns 400. | `models/analytics.py` |
| A01: Broken Access Control | Tag PUT/DELETE missing `AND user_id = ?` in WHERE clause (IDOR) | Row-level ownership enforced — every query now checks `user_id = ?` so one user cannot modify another's tags. | `routes/tasks.py` |
| A08: Data Integrity | No CSRF tokens on any form or AJAX endpoint | Flask-WTF `CSRFProtect` enabled globally. Every HTML form includes `{{ csrf_token() }}`; AJAX routes read the token from `<meta name="csrf-token">` and send it via `X-CSRFToken` header. The `/api/productivity/retrain` POST endpoint is protected the same way — JS sends `X-CSRFToken` header validated by Flask-WTF. | `__init__.py`, all templates |
| A02: Cryptographic Failures | Hardcoded `SECRET_KEY` in source | Replaced with `os.environ.get('SECRET_KEY')` falling back to `os.urandom(32).hex()`. | `__init__.py` |
| A08: Data Integrity | Unsafe `pickle.load()` of model files (RCE risk) | SHA-256 hash computed at model-save time (in `train_for_user`) and stored in metadata. `load_model()` re-computes the hash before `pickle.load()` and raises `ValueError` on mismatch. | `ml/trainer.py` |
| A06: Security Misconfiguration | Missing security headers | `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` added via `@app.after_request`. | `__init__.py` |

### SAST Testing (bandit, flake8; 2026-06-15)

The following SAST tools were run and all findings remediated:
- **Bandit** — security linting for Python. 0 high, 0 medium, 10 low (intentional) issues remain.
- **Flake8** — PEP 8 compliance + unused code detection. All F841 (unused variables), F401 (unused imports), and E402 (import ordering) warnings resolved.

Remediated findings:
| Tool | Finding | Fix |
|------|---------|-----|
| Bandit B608 | F-string SQL with dynamic column names | Whitelist-filtered by `_ALLOWED_COLS` in `_log_event()`; annotated `# nosec` |
| Bandit B301/B403 | `pickle.load()` unsafe deserialisation | SHA-256 hash verification + `# nosec` with justification after audit |
| Flake8 F841 | Unused variables (`class_dist`, `samples`, `n_node_samples`, `except e`) | Removed or replaced with bare `except` |
| Flake8 F401 | Unused imports (`check_password_hash`, `update_list`, `_meta_path`) | Removed |
| Flake8 F841 | Unused parameter `timer_end_time` in `update_list_timer_state()` | Parameter now used in the SQL `UPDATE` |

### DAST Testing (manual penetration testing, 2026-06-14)

Manual tests conducted against the running application:
1. **CSRF**: All POST endpoints reject requests without a valid CSRF token.
2. **IDOR**: Attempted to modify another user's tags/resources — all blocked by `user_id = ?` checks.
3. **SQL injection**: Tried SQLi on search params, URL params, and POST bodies — all parameterised queries prevented injection.
4. **Authentication bypass**: Accessed `/analytics` and `/api/productivity/prediction` without login — redirected to login page.
5. **Open redirect**: Tested `next` parameter — no open redirect found.
6. **Security headers**: Confirmed `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` in all responses.

## ML Architecture

The app includes a per-user productivity prediction system powered by scikit-learn:

### Pipeline

```
User completes 2+ sessions
        │
        ▼
trainer.py: build day-level feature rows from user_statistics
        │
        ▼
DecisionTreeClassifier(max_depth=5, class_weight='balanced')
        │
        ▼
model.pkl + meta.pkl → pomodoro/ml/models/<user_id>/
```

### Inference

```
predictor.py: compute features via feature_engineering.py
        │
        ├─ model exists? → DecisionTreeClassifier.predict()
        │                   (returns band + confidence)
        │
        └─ no model? → heuristic formula (fallback)
```

### Files

| File | Purpose |
|------|---------|
| `ml/trainer.py` | Per-user `DecisionTreeClassifier` training, feature engineering, model persistence with SHA-256 hash verification |
| `ml/predictor.py` | Predicts productivity band using trained model (or formula fallback). Returns JSON for `/api/productivity/prediction` |
| `ml/feature_engineering.py` | Computes 10 features: task completion rate, break management, session completion, daily focus, consistency, temporal patterns |
| `ml/scheduler.py` | Background retraining thread (disabled on PythonAnywhere; use scheduled task instead) |
| `routes/routine_suggestion.py` | Flask blueprint: `GET /api/productivity/prediction` and `POST /api/productivity/retrain` |

### Feature Vector (10 elements)

`[avg_task_min, task_rate, break_rate, session_rate, focus_min, consistency, skip_rate, pause_rate, peak_hour_norm, weekday_norm]`

All rates are in [0, 1]; time values in minutes; temporal features normalised to [0, 1].

### Seed Users

Run `flask seed-users` to create 6 sample users with diverse productivity profiles:

| User | Profile | Sessions | Description |
|------|---------|----------|-------------|
| `alice` | Excellent | ~224 | Daily streaks, high focus, 95% break completion |
| `bob` | Poor | ~15 | Sparse sessions, skips all breaks, 5% task completion |
| `carol` | Average | ~23 | Mixed clusters, but a productive recent week (4–5 longer sessions daily) |
| `dave` | Good | ~60 | Every-other-day for 40 days, but last week dropped to only 4 short sessions |
| `eve` | Excellent | ~301 | High volume daily, 92% break completion |
| `frank` | Poor | ~35 | Sparse every-3-days, 15% break completion |

[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
