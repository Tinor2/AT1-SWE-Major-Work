# Threat Model & Security Plan

## 2.1 OWASP Vulnerability Assessment Table

The following table identifies specific weaknesses found in the Term 4 codebase,
maps them to OWASP Top 10 categories, and defines the architectural technique
used to patch each vulnerability.

| # | OWASP Category | Vulnerability Description | File(s) & Line(s) | Severity | Architectural Fix |
|---|---------------|--------------------------|-------------------|----------|-------------------|
| 1 | A03: Injection | `_columns()` uses an f-string to interpolate a table name directly into a `PRAGMA` SQL statement. While currently called with hardcoded values, this is a SQL injection vector if user input ever reaches it. | `pomodoro/models/analytics.py:22` | High | **Whitelist validation** — restrict `table` parameter to an explicit allowlist (`tasks`, `lists`, `user_tags`, `task_time_sessions`, `user_statistics`) before interpolation. PRAGMA does not support parameterised queries, so the allowlist is the correct architectural control. |
| 2 | A01: Broken Access Control | Tag DELETE and PUT endpoints verify ownership on GET, but the actual `UPDATE` and `DELETE` SQL statements omit `AND user_id = ?`. An authenticated user can modify or delete any tag by guessing the numeric `tag_id` (IDOR). | `pomodoro/routes/tasks.py:233-241` | High | **Parameterised ownership enforcement** — add `AND user_id = ?` (with `current_user.id`) to every `UPDATE` and `DELETE` statement in `manage_single_tag`. This enforces row-level access control at the query layer. |
| 3 | A08: Data Integrity | No CSRF tokens on any form. Flask-WTF is commented out in `requirements.txt`. An attacker can craft a malicious page that submits POST requests (delete tasks, change profile, create lists) on behalf of an authenticated user. | `requirements.txt:7-8`, all form templates | High | **Enable Flask-WTF CSRF protection** — uncomment Flask-WTF, enable `WTF_CSRF_ENABLED = True`, and embed `{{ csrf_token() }}` hidden fields in every `<form method="POST">`. For AJAX routes, send the token via `X-CSRFToken` header read from the cookie. |
| 4 | A02: Cryptographic Failures | `SECRET_KEY` is hardcoded as the string `'dev'`. An attacker who knows this value can forge Flask session cookies and impersonate any user. | `pomodoro/__init__.py:11` | Critical | **Environment-based secret management** — read `SECRET_KEY` from `os.environ`, falling back to `os.urandom(32)` for development. Never commit secrets to source control. |
| 5 | A08: Data Integrity | `pickle` import and `pickle.load()` deserialisation risk (Bandit B403/B301). If an attacker can replace `.pkl` files (path traversal, compromised deployment), they achieve Remote Code Execution. Hash verification has been implemented as a mitigation. | `pomodoro/routes/routine_suggestion.py:10,48-52` | Critical | **Hash verification before deserialization** — SHA-256 of each `.pkl` file is computed at load time and compared against a known-good hash stored in `MANIFEST.json`. The `_load_pkl()` wrapper (line 48) calls `_verify_hash()` (line 39) before `pickle.load()` (line 52), rejecting on mismatch. Longer term, migrate to ONNX or JSON-based model export. |

### Architectural Principles Applied

- **Defence in Depth**: Every fix applies controls at the query layer (parameterised queries, ownership checks), application layer (CSRF tokens, whitelist validation), and infrastructure layer (environment variables, hash verification).
- **Least Privilege**: All database queries are scoped to `current_user.id` — no query should ever access another user's rows.
- **Secure by Default**: CSRF is enabled by default via Flask-WTF. The secret key defaults to a cryptographically random value.

---

## 2.2 SAST & DAST Testing Plan

### Static Application Security Testing (SAST)

SAST tools analyse source code without executing the application, catching vulnerabilities early in the development cycle.

| Tool | What It Detects | How It Will Be Used |
|------|----------------|---------------------|
| **Bandit** | Python-specific security issues — SQL injection, hardcoded secrets, insecure deserialization, use of `exec`/`eval`, weak cryptography | Run against the entire `pomodoro/` package as a pre-commit hook and in CI. Configure `.bandit` to exclude false positives (e.g., the intentional `pickle` usage flagged for review). Target: zero high-severity findings. |
| **Flake8** with **flake8-security** | Code quality issues that often correlate with security bugs — unused imports, bare `except` clauses, mutable default arguments | Run as part of the standard linting pipeline (`flake8 pomodoro/`). The `E` and `W` error classes enforce clean code that reduces attack surface. |
| **Safety** | Known vulnerabilities in pinned dependencies | Run `safety check -r requirements.txt` in CI to block builds if any installed package has a published CVE. |
| **Bandit + `--format json`** | Automated reporting | Output Bandit results as JSON, parse with a CI script, and fail the pipeline if any `HIGH` or `CRITICAL` severity issue is found. |

**SAST Workflow:**
1. Developer runs `bandit -r pomodoro/ -f json -o bandit-report.json` locally before pushing.
2. CI pipeline runs `flake8` (lint) and `safety check` (dependency audit).
3. Bandit results are reviewed — any `HIGH` finding blocks the merge.

### Dynamic Application Security Testing (DAST)

DAST tests the running application from the outside, simulating real attacker behaviour.

| Technique | What It Verifies | How It Will Be Performed |
|-----------|-----------------|-------------------------|
| **Manual Penetration Testing — CSRF** | Confirm that forms without valid CSRF tokens are rejected | Attempt to submit POST requests (login, create task, delete list) using `curl` or a browser extension without a CSRF token. Verify the server returns `400 Bad Request`. |
| **Manual Penetration Testing — IDOR** | Confirm that users cannot access/modify other users' resources | Log in as User A, note a task/tag/list ID, log in as User B, and attempt to GET/PUT/DELETE that resource by ID. Verify all requests return `403 Forbidden` or `404 Not Found`. |
| **Manual Penetration Testing — SQL Injection** | Confirm parameterised queries prevent injection | Inject `' OR '1'='1` and `'; DROP TABLE tasks; --` into form fields (task content, search, login). Verify no data leakage or schema changes occur. |
| **Manual Penetration Testing — Open Redirect** | Confirm the `next` parameter cannot redirect to external domains | Visit `/auth/login?next=//evil.com` and verify the redirect is blocked or sanitised. |
| **Manual Penetration Testing — File Upload** | Confirm uploaded files are validated | Upload a `.svg` file renamed to `.jpg`, a 10MB image, and a `.php` file. Verify all are rejected by server-side validation. |
| **Browser DevTools — Security Headers** | Confirm all security headers are present | Inspect response headers in the Network tab. Verify `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Content-Security-Policy` are set. |
| **OWASP ZAP Baseline Scan** | Automated DAST scan for common web vulnerabilities | Run OWASP ZAP against the local Flask development server. Review the alert report for `Medium` and `High` findings. Address all findings before submission. |

**DAST Workflow:**
1. Run the Flask app locally (`flask run --port 8000`).
2. Execute manual penetration tests against each endpoint using the checklist above.
3. Run OWASP ZAP baseline scan against `http://localhost:8000`.
4. Document all findings in a spreadsheet with severity, reproduction steps, and fix status.
5. Re-test after fixes to confirm remediation.

### Testing Schedule

| Phase | Activity | When |
|-------|----------|------|
| Pre-commit | Bandit SAST scan | Every commit |
| CI Pipeline | Flake8 + Safety check | Every push to `main` |
| Feature Complete | Manual penetration test (full checklist) | Before each submission |
| Final | OWASP ZAP baseline scan | Final submission |
