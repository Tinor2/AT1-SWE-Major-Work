# Statistics and Machine Learning System for Pomodoro App

## Overview

This document outlines the comprehensive statistics tracking and machine learning system for the Pomodoro + To-Do application. The system is designed to capture all user productivity events in a single database table, enabling flexible filtering for statistics and providing data for ML models to analyze productivity patterns and suggest optimal study routines.

## Database Schema Design

### Single Table Architecture

The system uses a **single comprehensive table** (`user_statistics`) to capture all productivity events, rather than separate tables for different time periods (daily, weekly, monthly). This approach provides:

- **Flexibility**: Filter and aggregate data in any way needed
- **Scalability**: Single source of truth for all analytics
- **Simplicity**: Easier to maintain and query
- **ML-Ready**: Clean, unified dataset for machine learning models

### user_statistics Table Structure

```sql
CREATE TABLE user_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN (
        'task_completion',
        'break_completion',
        'break_skip',
        'session_start',
        'session_end',
        'session_pause',
        'session_resume',
        'task_creation',
        'task_deletion',
        'list_creation',
        'list_deletion',
        'settings_change'
    )),
    task_id INTEGER,
    list_id INTEGER,
    timestamp INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
    duration_seconds INTEGER DEFAULT 0,
    break_type TEXT CHECK(break_type IN ('short_break', 'long_break', NULL)),
    session_number INTEGER DEFAULT 0,
    task_content TEXT,
    task_completion_time_seconds INTEGER,
    pomodoro_session_duration INTEGER,
    pomodoro_short_break_duration INTEGER,
    pomodoro_long_break_duration INTEGER,
    sessions_completed_in_set INTEGER,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (list_id) REFERENCES lists (id) ON DELETE CASCADE
);
```

### Field Descriptions

- **id**: Primary key
- **user_id**: Foreign key to users table
- **event_type**: Type of event (see Event Types section)
- **task_id**: Optional reference to related task
- **list_id**: Optional reference to related list
- **timestamp**: Unix timestamp of when the event occurred
- **duration_seconds**: Duration of the event (for sessions, breaks, etc.)
- **break_type**: Type of break ('short_break' or 'long_break')
- **session_number**: Which Pomodoro session in the current set
- **task_content**: Text content of the task (for task-related events)
- **task_completion_time_seconds**: Total time taken to complete a task
- **pomodoro_session_duration**: Duration setting for Pomodoro sessions
- **pomodoro_short_break_duration**: Duration setting for short breaks
- **pomodoro_long_break_duration**: Duration setting for long breaks
- **sessions_completed_in_set**: Number of sessions completed in current set
- **metadata**: JSON field for additional event-specific data
- **created_at**: Database record creation timestamp

## Event Types

### Task-Related Events

1. **task_creation**: When a new task is created
2. **task_completion**: When a task is marked as complete
3. **task_deletion**: When a task is deleted

### Break-Related Events

4. **break_completion**: When a break is completed (not skipped)
5. **break_skip**: When a break is skipped

### Session-Related Events

6. **session_start**: When a Pomodoro session starts
7. **session_end**: When a Pomodoro session ends
8. **session_pause**: When a session is paused
9. **session_resume**: When a paused session is resumed

### List-Related Events

10. **list_creation**: When a new list is created
11. **list_deletion**: When a list is deleted

### Settings Events

12. **settings_change**: When user changes Pomodoro settings

## Data Collection Strategy

### Task Completion Time Tracking

When a task is completed, the system will:

1. Calculate total time spent on the task from `task_time_sessions` table
2. Record the completion event with:
   - `event_type`: 'task_completion'
   - `task_id`: The completed task's ID
   - `task_completion_time_seconds`: Total time spent
   - `task_content`: Task text content
   - `timestamp`: When the task was completed

### Break Tracking

#### Completed Breaks

When a user completes a break (doesn't skip it):

1. Record the break completion event with:
   - `event_type`: 'break_completion'
   - `break_type`: 'short_break' or 'long_break'
   - `duration_seconds`: Actual break duration
   - `session_number`: Current session number in the set
   - `timestamp`: When the break was completed

#### Skipped Breaks

When a user skips a break:

1. Record the break skip event with:
   - `event_type`: 'break_skip'
   - `break_type`: 'short_break' or 'long_break'
   - `duration_seconds`: 0 (since it was skipped)
   - `session_number`: Current session number in the set
   - `timestamp`: When the break was skipped

### Session Tracking

For each Pomodoro session:

1. **Session Start**: Record when user starts a focus session
2. **Session End**: Record when session completes (full duration)
3. **Session Pause**: Record when user pauses mid-session
4. **Session Resume**: Record when user resumes a paused session

Each session event includes:
- Current Pomodoro settings (session duration, break durations)
- Session number in current set
- Actual duration (for end events)

## Statistics Filtering

### Time-Based Filtering

The single table architecture allows flexible time-based filtering:

```sql
-- Daily statistics
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= strftime('%s', 'now', '-1 day')

-- Weekly statistics  
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= strftime('%s', 'now', '-7 days')

-- Monthly statistics
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= strftime('%s', 'now', '-30 days')

-- Custom date range
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND timestamp >= ? 
  AND timestamp <= ?
```

### Event Type Filtering

```sql
-- Task completions only
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type = 'task_completion'

-- Break events only
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type IN ('break_completion', 'break_skip')

-- Session events only
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type IN ('session_start', 'session_end', 'session_pause', 'session_resume')
```

### Combined Filtering

```sql
-- Completed short breaks in the last week
SELECT * FROM user_statistics 
WHERE user_id = ? 
  AND event_type = 'break_completion'
  AND break_type = 'short_break'
  AND timestamp >= strftime('%s', 'now', '-7 days')

-- Task completions with their completion times
SELECT task_content, task_completion_time_seconds, timestamp
FROM user_statistics 
WHERE user_id = ? 
  AND event_type = 'task_completion'
ORDER BY timestamp DESC
```

## Statistics Metrics

### Task Metrics

- **Average task completion time**: Mean time to complete tasks
- **Task completion rate**: Tasks completed vs. tasks created
- **Task completion time distribution**: Histogram of completion times
- **Tasks per day/week/month**: Count of completed tasks in time period

### Break Metrics

- **Break completion rate**: Completed breaks vs. total breaks
- **Break skip rate**: Skipped breaks vs. total breaks
- **Average break duration**: Mean duration of completed breaks
- **Break type distribution**: Short vs. long break completion rates

### Session Metrics

- **Session completion rate**: Completed sessions vs. started sessions
- **Session pause rate**: Paused sessions vs. total sessions
- **Average session duration**: Mean duration of completed sessions
- **Sessions per day/week/month**: Count of sessions in time period
- **Set completion rate**: Completed 4-session sets vs. started sets

### Productivity Metrics

- **Total focus time**: Sum of all completed session durations
- **Productivity score**: Composite metric based on multiple factors
- **Consistency score**: Variance in daily productivity
- **Optimal session duration**: Most productive session length

## Machine Learning Models

### Model 1: Productivity Categorization (Decision Tree)

**Purpose**: Categorize user productivity into levels from "bad" to "amazing"

**Features**:
- Average task completion time
- Task completion rate
- Break completion rate
- Session completion rate
- Total focus time per day
- Consistency score (variance in daily metrics)
- Break skip rate
- Session pause rate
- Time of day patterns
- Day of week patterns

**Target Classes**:
- Bad (0-20% productivity score)
- Poor (20-40% productivity score)
- Average (40-60% productivity score)
- Good (60-80% productivity score)
- Excellent (80-90% productivity score)
- Amazing (90-100% productivity score)

**Implementation Details**:
- Use scikit-learn DecisionTreeClassifier
- Train on historical user data
- Provide feature importance analysis
- Enable explainability for users

### Model 2: Optimal Routine Suggestion (Regression)

**Purpose**: Predict optimal changes to study routine for maximum productivity

**Features**:
- Current Pomodoro session duration
- Current short break duration
- Current long break duration
- Historical productivity metrics
- Time of day patterns
- Task complexity metrics
- Break completion patterns
- Session completion patterns

**Targets**:
- Optimal session duration (in minutes)
- Optimal short break duration (in minutes)
- Optimal long break duration (in minutes)
- Optimal number of sessions per day
- Optimal time of day for sessions

**Implementation Details**:
- Use scikit-learn regression models (RandomForestRegressor, GradientBoostingRegressor)
- Train on historical user data with productivity as target
- Provide confidence intervals for recommendations
- Enable A/B testing of recommendations

## Implementation Plan

### Phase 1 — Event Logging (Prerequisite — Must Be Done First)

**Status: NOT YET WIRED UP** — the `user_statistics` table exists in the schema but nothing currently writes to it.

#### 1.1 — Wire timer events in `pomodoro/routes/timer.py`

In each of the following route handlers, after `_save_state(...)` succeeds, insert a row into `user_statistics`:

| Route | Event type | Key fields to log |
|---|---|---|
| `start_timer` (idle → session) | `session_start` | `session_number`, `pomodoro_session_duration` |
| `start_timer` (paused → running) | `session_resume` | `duration_seconds` (elapsed before pause) |
| `pause_timer` | `session_pause` | `duration_seconds` (time spent before pause) |
| `skip_timer` (from session) | `session_end` | `duration_seconds`, `sessions_completed_in_set` |
| `skip_timer` (from break) | `break_skip` | `break_type` (short_break / long_break) |
| Natural phase completion — client calls `/timer/skip` after countdown | `session_end` or `break_completion` | as above |
| `reset_sets` | `settings_change` | `metadata: {"action": "reset_sets"}` |

Helper to add (in `timer.py`):

```python
def _log_event(db, user_id, event_type, **kwargs):
    """Insert one row into user_statistics. kwargs map to column names."""
    import time
    cols = ["user_id", "event_type", "timestamp"] + list(kwargs.keys())
    vals = [user_id, event_type, int(time.time())] + list(kwargs.values())
    placeholders = ",".join("?" * len(cols))
    db.execute(
        f"INSERT INTO user_statistics ({','.join(cols)}) VALUES ({placeholders})",
        vals
    )
    db.commit()
```

#### 1.2 — Wire task events in `pomodoro/routes/tasks.py`

| Action | Event type | Key fields |
|---|---|---|
| `add_task` | `task_creation` | `task_id`, `list_id`, `task_content` |
| `toggle_task` (→ done) | `task_completion` | `task_id`, `task_completion_time_seconds` (from `total_time_seconds`) |
| `delete_task` | `task_deletion` | `task_id` |

#### 1.3 — Wire list events in `pomodoro/routes/lists.py`

| Action | Event type |
|---|---|
| `create` | `list_creation` |
| `delete_list` | `list_deletion` |

#### 1.4 — Verify with a quick SQL check

After a few minutes of app use:
```sql
SELECT event_type, COUNT(*) FROM user_statistics GROUP BY event_type;
```
You should see session_start, task_creation, etc. If this is empty, nothing downstream will work.

---

### Phase 2 — Analytics Dashboard (Basic Stats — Already Partially Done)

The `analytics/index.html` template and `models/analytics.py` already render focus time, session counts, task completion rate, and the event log table.

**Remaining work:**
- Wire up chart rendering (Chart.js is already in `requirements.txt` as a frontend dependency via CDN) for daily focus time trends
- Add a 7/30/90-day period switcher to the event log table (the period switcher for the stat cards already exists)

---

### Phase 3 — ML Backend: Live Decision Tree

This is the core of the new work. The goal is a **per-user, auto-retraining decision tree** that classifies the user's recent productivity into one of **poor / average / good / excellent** and produces a human-readable explanation.

> Note: The existing mockup uses 6 bands (bad/poor/average/good/excellent/amazing). For the frontend display, these collapse to 4 user-facing labels: bad+poor → **Poor**, average → **Average**, good → **Good**, excellent+amazing → **Excellent**. The internal model still uses 6 bands.

#### 3.1 — New file: `pomodoro/ml/trainer.py`

This module owns model training. It is called on a schedule and also on demand (manual refresh button).

```python
# pomodoro/ml/trainer.py
"""
Per-user decision tree trainer.

Pulls feature rows from user_statistics, trains a DecisionTreeClassifier,
pickles the model + metadata to pomodoro/ml/models/<user_id>/,
and records training time.
"""

import os
import pickle
import time
from datetime import datetime
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

from pomodoro.ml.feature_engineering import (
    compute_features_for_user,
    compute_productivity_score,
)

# --- Directory layout -------------------------------------------------
# pomodoro/ml/models/<user_id>/model.pkl
# pomodoro/ml/models/<user_id>/meta.pkl   <- trained_at, accuracy, n_samples
# ----------------------------------------------------------------------

ML_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def _user_model_dir(user_id: int) -> str:
    path = os.path.join(ML_MODELS_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


def _model_path(user_id: int) -> str:
    return os.path.join(_user_model_dir(user_id), "model.pkl")


def _meta_path(user_id: int) -> str:
    return os.path.join(_user_model_dir(user_id), "meta.pkl")


def model_exists(user_id: int) -> bool:
    return os.path.exists(_model_path(user_id))


def load_model(user_id: int):
    """Return (clf, meta) or (None, None) if not trained yet."""
    mp = _model_path(user_id)
    if not os.path.exists(mp):
        return None, None
    with open(mp, "rb") as f:
        clf = pickle.load(f)
    with open(_meta_path(user_id), "rb") as f:
        meta = pickle.load(f)
    return clf, meta


def seconds_since_trained(user_id: int) -> float | None:
    """Returns elapsed seconds since last training, or None if never trained."""
    _, meta = load_model(user_id)
    if meta is None:
        return None
    return time.time() - meta["trained_at"]


def train_for_user(user_id: int, db) -> dict:
    """
    Build a feature matrix from user_statistics, train the decision tree,
    pickle it, return a result dict with accuracy + metadata.

    If there is not enough real data (< 10 rows), falls back to synthetic data
    from the existing mockup so the UI is never broken.
    """
    from pomodoro.ml.feature_engineering import (
        compute_features_for_user,
        compute_productivity_score,
    )

    # --- Build feature rows from DB (one row per day) -----------------
    rows = _build_feature_rows(user_id, db)

    if len(rows) < 10:
        # Not enough real data — use synthetic fallback
        from pomodoro.ML_TESTS.productivity_decision_tree import (  # noqa
            generate_synthetic_dataset,
        )
        X, y = generate_synthetic_dataset(n_samples=300, seed=user_id)
        n_real = 0
    else:
        X = np.array([r["features"] for r in rows])
        y = np.array([r["label"] for r in rows])
        n_real = len(rows)

    # --- Train --------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    clf = DecisionTreeClassifier(
        max_depth=5,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_train)
    acc = accuracy_score(y_test, clf.predict(X_test)) if len(X_test) > 0 else 0.0

    # --- Persist -------------------------------------------------------
    with open(_model_path(user_id), "wb") as f:
        pickle.dump(clf, f)
    meta = {
        "trained_at": time.time(),
        "accuracy": acc,
        "n_samples": len(X),
        "n_real_samples": n_real,
        "trained_at_human": datetime.utcnow().isoformat() + "Z",
    }
    with open(_meta_path(user_id), "wb") as f:
        pickle.dump(meta, f)

    print(
        f"[ML] User {user_id}: trained on {len(X)} samples "
        f"({n_real} real), test accuracy={acc:.2f}"
    )
    return meta


def _build_feature_rows(user_id: int, db) -> list[dict]:
    """
    Aggregate user_statistics into daily feature rows.
    Each row = one calendar day's worth of activity.
    Returns list of {"features": np.ndarray, "label": int}.
    """
    # Pull all relevant events for this user
    events = db.execute(
        """
        SELECT event_type, timestamp, duration_seconds,
               task_completion_time_seconds, break_type
        FROM user_statistics
        WHERE user_id = ?
        ORDER BY timestamp ASC
        """,
        (user_id,),
    ).fetchall()

    if not events:
        return []

    # Group by calendar day (UTC)
    from collections import defaultdict
    days: dict[str, list] = defaultdict(list)
    for ev in events:
        day = datetime.utcfromtimestamp(ev["timestamp"]).strftime("%Y-%m-%d")
        days[day].append(ev)

    rows = []
    for day, day_events in days.items():
        feats = _day_features(day_events)
        score = _score_from_features(feats)
        label = _score_to_class(score)
        rows.append({"features": feats, "label": label})

    return rows


def _day_features(events: list) -> np.ndarray:
    """Compute the 10 feature values for one day's events."""
    sessions_started = sum(1 for e in events if e["event_type"] == "session_start")
    sessions_ended   = sum(1 for e in events if e["event_type"] == "session_end")
    breaks_done      = sum(1 for e in events if e["event_type"] == "break_completion")
    breaks_skipped   = sum(1 for e in events if e["event_type"] == "break_skip")
    tasks_created    = sum(1 for e in events if e["event_type"] == "task_creation")
    tasks_completed  = sum(1 for e in events if e["event_type"] == "task_completion")
    pauses           = sum(1 for e in events if e["event_type"] == "session_pause")

    focus_seconds = sum(
        (e["duration_seconds"] or 0)
        for e in events
        if e["event_type"] == "session_end"
    )

    completion_times = [
        e["task_completion_time_seconds"]
        for e in events
        if e["event_type"] == "task_completion"
        and e["task_completion_time_seconds"]
    ]
    avg_task_min = (
        np.mean(completion_times) / 60.0 if completion_times else 60.0
    )

    task_rate    = tasks_completed / max(tasks_created + tasks_completed, 1)
    break_rate   = breaks_done / max(breaks_done + breaks_skipped, 1)
    session_rate = sessions_ended / max(sessions_started, 1)
    focus_min    = focus_seconds / 60.0
    pause_rate   = pauses / max(sessions_started, 1)
    skip_rate    = breaks_skipped / max(breaks_done + breaks_skipped, 1)

    # Temporal features — derive from first event of day
    first_ts = events[0]["timestamp"]
    dt = datetime.utcfromtimestamp(first_ts)
    peak_hour_norm  = dt.hour / 23.0
    weekday_norm    = dt.weekday() / 6.0

    # Consistency score placeholder for single-day (1.0 — needs multi-day context)
    consistency = 1.0

    return np.array(
        [
            avg_task_min,    # 0
            task_rate,       # 1
            break_rate,      # 2
            session_rate,    # 3
            focus_min,       # 4
            consistency,     # 5
            skip_rate,       # 6
            pause_rate,      # 7
            peak_hour_norm,  # 8
            weekday_norm,    # 9
        ],
        dtype=float,
    )


def _score_from_features(f: np.ndarray) -> float:
    """Same heuristic as the mockup — produces 0-100."""
    avg_min, task_rate, break_rate, session_rate, focus_min, consistency, skip_rate, pause_rate, _, _ = f
    speed_bonus = max(0.0, 1.0 - min(avg_min, 120.0) / 120.0) * 15
    core = (
        task_rate * 22
        + break_rate * 12
        + session_rate * 22
        + min(focus_min / 240.0, 1.0) * 20
        + consistency * 10
        + speed_bonus
    )
    penalties = skip_rate * 18 + pause_rate * 12
    return float(np.clip(core - penalties, 0, 100))


def _score_to_class(score: float) -> int:
    if score < 20: return 0
    if score < 40: return 1
    if score < 60: return 2
    if score < 80: return 3
    if score < 90: return 4
    return 5
```

#### 3.2 — New file: `pomodoro/ml/predictor.py`

This module owns **prediction and explanation** for a single user at the current moment. It is what the API endpoint and the scheduler both call.

```python
# pomodoro/ml/predictor.py
"""
Predict the current user's productivity band and generate a text explanation.

Output dict shape (also returned as JSON to the frontend):
{
    "band":         "good",              # poor | average | good | excellent
    "internal_band": "good",            # full 6-band label
    "score":        72.4,               # 0-100 heuristic
    "confidence":   0.81,
    "motivational": "You're on a roll — keep the momentum going!",
    "factors": [
        {"label": "Session completion", "value": "High",   "positive": True},
        {"label": "Task completion",    "value": "Medium", "positive": True},
        {"label": "Break management",   "value": "Low",    "positive": False},
        ...
    ],
    "trained_at":    "2025-06-11T10:32:00Z",
    "seconds_since": 1420,
    "n_samples":     47,
    "is_synthetic":  False,
}
"""

import time
import numpy as np
from pomodoro.ml.trainer import load_model, train_for_user, model_exists
from pomodoro.ml.feature_engineering import compute_features_for_user

INTERNAL_LABELS = ["bad", "poor", "average", "good", "excellent", "amazing"]

# Map internal 6-band → user-facing 4-band
DISPLAY_BAND = {
    "bad":       "Poor",
    "poor":      "Poor",
    "average":   "Average",
    "good":      "Good",
    "excellent": "Excellent",
    "amazing":   "Excellent",
}

MOTIVATIONAL = {
    "Poor":      "Every session counts — start small and build the habit.",
    "Average":   "Solid foundation. Focus on completing more breaks to level up.",
    "Good":      "You're on a roll — keep the momentum going!",
    "Excellent": "Outstanding consistency. You're at the top of your game!",
}

# Feature names aligned with the 10-element feature vector
FEATURE_NAMES = [
    "avg_task_completion_min",
    "task_completion_rate",
    "break_completion_rate",
    "session_completion_rate",
    "focus_minutes_per_day",
    "consistency_score",
    "break_skip_rate",
    "session_pause_rate",
    "peak_hour_norm",
    "weekday_index_norm",
]

# Human-readable labels for each feature shown in the UI factor list
FACTOR_LABELS = {
    "session_completion_rate":  "Session completion",
    "task_completion_rate":     "Task completion",
    "break_completion_rate":    "Break management",
    "focus_minutes_per_day":    "Daily focus time",
    "consistency_score":        "Consistency",
    "break_skip_rate":          "Break skip rate",    # lower is better
    "session_pause_rate":       "Pause rate",         # lower is better
    "avg_task_completion_min":  "Task speed",
}

# For each factor, define thresholds for Low / Medium / High text
def _value_label(feature: str, value: float) -> tuple[str, bool]:
    """Return ("High"/"Medium"/"Low", is_positive: bool)."""
    LOWER_IS_BETTER = {"break_skip_rate", "session_pause_rate", "avg_task_completion_min"}
    if feature in LOWER_IS_BETTER:
        if value < 0.15 or (feature == "avg_task_completion_min" and value < 25):
            return "Low", True    # Low pause/skip rate = good
        if value < 0.4 or (feature == "avg_task_completion_min" and value < 60):
            return "Medium", None
        return "High", False
    else:
        if value >= 0.75:
            return "High", True
        if value >= 0.45:
            return "Medium", None
        return "Low", False


def predict_for_user(user_id: int, db) -> dict:
    """
    Return the prediction dict for the current user.
    Auto-trains if no model exists yet.
    """
    if not model_exists(user_id):
        train_for_user(user_id, db)

    clf, meta = load_model(user_id)

    # Build current feature vector from live DB
    features_dict = compute_features_for_user(user_id)

    # Map to array in correct order
    feat_array = np.array(
        [
            features_dict.get("avg_task_completion_time_seconds", 60) / 60.0,
            features_dict.get("task_completion_rate", 0.5),
            features_dict.get("break_completion_rate", 0.5),
            features_dict.get("session_completion_rate", 0.5),
            features_dict.get("avg_daily_focus_time_seconds", 0) / 60.0,
            features_dict.get("consistency_score", 0.5),
            1.0 - features_dict.get("break_completion_rate", 0.5),  # skip rate
            features_dict.get("break_skip_streak", 0) / 20.0,       # pause rate proxy
            features_dict.get("preferred_hour", 12) / 23.0,
            features_dict.get("preferred_weekday", 3) / 6.0,
        ],
        dtype=float,
    ).reshape(1, -1)

    # Predict
    pred_class = int(clf.predict(feat_array)[0])
    proba = clf.predict_proba(feat_array)[0]
    class_idx = list(clf.classes_).index(pred_class)
    confidence = float(proba[class_idx])

    internal_label = INTERNAL_LABELS[pred_class]
    display_label  = DISPLAY_BAND[internal_label]

    # Build factor list from the 8 human-readable features
    factors = []
    feat_values = {
        "session_completion_rate":  feat_array[0][3],
        "task_completion_rate":     feat_array[0][1],
        "break_completion_rate":    feat_array[0][2],
        "focus_minutes_per_day":    feat_array[0][4],
        "consistency_score":        feat_array[0][5],
        "break_skip_rate":          feat_array[0][6],
        "session_pause_rate":       feat_array[0][7],
        "avg_task_completion_min":  feat_array[0][0],
    }
    for feat_key, human_label in FACTOR_LABELS.items():
        val = feat_values[feat_key]
        val_label, positive = _value_label(feat_key, val)
        factors.append({
            "label":    human_label,
            "value":    val_label,
            "positive": positive,  # True=green, False=red, None=neutral
            "raw":      round(float(val), 3),
        })

    # Console/terminal output
    _print_insights(user_id, display_label, internal_label, factors, confidence)

    seconds_since = time.time() - meta["trained_at"]

    return {
        "band":          display_label,
        "internal_band": internal_label,
        "confidence":    round(confidence, 2),
        "motivational":  MOTIVATIONAL[display_label],
        "factors":       factors,
        "trained_at":    meta["trained_at_human"],
        "seconds_since": int(seconds_since),
        "n_samples":     meta.get("n_samples", 0),
        "is_synthetic":  meta.get("n_real_samples", 0) < 10,
    }


def _print_insights(user_id, display_label, internal_label, factors, confidence):
    """Print a formatted summary to stdout/terminal."""
    divider = "=" * 55
    print(f"\n{divider}")
    print(f"  [ML] Productivity Insight — User {user_id}")
    print(f"  Rating    : {display_label.upper()} ({internal_label})")
    print(f"  Confidence: {confidence:.0%}")
    print(f"  Factors:")
    for f in factors:
        symbol = "✓" if f["positive"] is True else ("✗" if f["positive"] is False else "–")
        print(f"    {symbol}  {f['label']:28s}  {f['value']}")
    print(divider)
```

#### 3.3 — Retraining schedule: `pomodoro/ml/scheduler.py`

The model should retrain **once per hour** per user (not every 15 min — 15-min intervals produce almost identical data and waste compute; once per hour is sufficient for a Pomodoro session's worth of new events to accumulate).

On the analytics page load and on manual refresh, the model also retrains on demand if the last training was more than 1 hour ago.

```python
# pomodoro/ml/scheduler.py
"""
Background retraining scheduler.
Uses a simple thread-based APScheduler (no Celery required).

Add to create_app() in pomodoro/__init__.py:
    from .ml.scheduler import start_scheduler
    start_scheduler(app)
"""

import threading
import time

_scheduler_thread = None
_stop_event = threading.Event()

RETRAIN_INTERVAL_SECONDS = 3600  # 1 hour


def _retrain_all_users(app):
    """Retrain model for every user who has recent activity."""
    with app.app_context():
        from pomodoro.db import get_db
        from pomodoro.ml.trainer import train_for_user, seconds_since_trained

        db = get_db()
        # Only retrain users with events in the last 24 hours
        active_users = db.execute(
            """
            SELECT DISTINCT user_id FROM user_statistics
            WHERE timestamp >= ?
            """,
            (int(time.time()) - 86400,),
        ).fetchall()

        for row in active_users:
            uid = row["user_id"]
            since = seconds_since_trained(uid)
            if since is None or since >= RETRAIN_INTERVAL_SECONDS:
                try:
                    train_for_user(uid, db)
                except Exception as e:
                    print(f"[ML Scheduler] Failed to retrain user {uid}: {e}")


def _scheduler_loop(app):
    while not _stop_event.is_set():
        _retrain_all_users(app)
        _stop_event.wait(RETRAIN_INTERVAL_SECONDS)


def start_scheduler(app):
    """Start the background retraining thread. Call once from create_app()."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(app,),
        daemon=True,
        name="ml-retrain-scheduler",
    )
    _scheduler_thread.start()
    print("[ML Scheduler] Started — retraining every 1 hour.")
```

**Wire into `pomodoro/__init__.py`** — add at the bottom of `create_app()`:
```python
from .ml.scheduler import start_scheduler
start_scheduler(app)
```

#### 3.4 — Update `pomodoro/routes/routine_suggestion.py`

Replace the placeholder `/api/productivity/routine-suggestion` endpoint with a new `/api/productivity/prediction` endpoint that calls `predictor.predict_for_user` and also supports a `POST /api/productivity/retrain` for the manual refresh button.

```python
# Replace contents of routine_suggestion.py with:

from flask import Blueprint, jsonify
from flask_login import login_required, current_user

routine_bp = Blueprint('routine_suggestion', __name__, url_prefix='/api/productivity')


@routine_bp.route('/prediction', methods=['GET'])
@login_required
def get_prediction():
    """Return current productivity prediction for the logged-in user."""
    from pomodoro.db import get_db
    from pomodoro.ml.predictor import predict_for_user
    try:
        result = predict_for_user(current_user.id, get_db())
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routine_bp.route('/retrain', methods=['POST'])
@login_required
def retrain():
    """Force retrain the model for the current user (manual refresh button)."""
    from pomodoro.db import get_db
    from pomodoro.ml.trainer import train_for_user
    from pomodoro.ml.predictor import predict_for_user
    try:
        train_for_user(current_user.id, get_db())
        result = predict_for_user(current_user.id, get_db())
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

---

### Phase 4 — Frontend: "Projected Performance" Panel

#### 4.1 — Where it goes

In `pomodoro/templates/analytics/index.html`, **insert the Projected Performance panel immediately above** the "Recent focus sessions" panel (i.e. above the `<div class="panel analytics-panel">` that has `<h2>Recent focus sessions</h2>`).

#### 4.2 — HTML block to insert

```html
<!-- ═══════════════════════════════════════════════════════════
     PROJECTED PERFORMANCE PANEL
     Insert directly above the "Recent focus sessions" panel
     ═══════════════════════════════════════════════════════════ -->
<div class="panel analytics-panel projected-performance-panel" id="projectedPerformancePanel">
    <div class="pp-header">
        <h2 class="panel-title">Projected Performance</h2>
        <button class="btn btn-sm btn-secondary pp-refresh-btn" id="ppRefreshBtn"
                title="Retrain model with latest data">
            ↻ Refresh
        </button>
    </div>

    <!-- Staleness indicator — faint text, updated by JS -->
    <p class="pp-last-updated" id="ppLastUpdated">Loading…</p>

    <!-- Loading state -->
    <div class="pp-loading" id="ppLoading">
        <div class="pp-spinner"></div>
        <span>Analysing your productivity data…</span>
    </div>

    <!-- Result state (hidden until loaded) -->
    <div class="pp-result" id="ppResult" style="display:none;">
        <!-- Band label -->
        <div class="pp-band-wrap">
            <span class="pp-band" id="ppBand">—</span>
        </div>

        <!-- Motivational sentence -->
        <p class="pp-motivational" id="ppMotivational"></p>

        <!-- Factor breakdown list -->
        <ul class="pp-factors" id="ppFactors"></ul>

        <!-- Synthetic data notice -->
        <p class="pp-synthetic-notice" id="ppSyntheticNotice" style="display:none;">
            ⚠ Not enough real data yet — showing estimate based on defaults.
            Keep using the app to get personalised insights.
        </p>
    </div>

    <!-- Error state -->
    <div class="pp-error" id="ppError" style="display:none;">
        <p>Unable to load prediction. <a href="#" id="ppRetryLink">Try again</a></p>
    </div>
</div>
```

#### 4.3 — CSS to add to `pomodoro/static/css/analytics.css`

```css
/* ── Projected Performance Panel ─────────────────────────── */

.projected-performance-panel {
    margin-bottom: 1.5rem;
}

.pp-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.25rem;
}

.pp-last-updated {
    color: var(--text-secondary, #888);
    font-size: 0.8rem;
    margin: 0 0 1.25rem 0;
    opacity: 0.7;
}

/* Loading spinner */
.pp-loading {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1.5rem 0;
    color: var(--text-secondary, #888);
}

.pp-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-color, #e2e8f0);
    border-top-color: var(--primary-color, #e53e3e);
    border-radius: 50%;
    animation: pp-spin 0.8s linear infinite;
}

@keyframes pp-spin {
    to { transform: rotate(360deg); }
}

/* Band label */
.pp-band-wrap {
    text-align: center;
    padding: 0.5rem 0 0.25rem;
}

.pp-band {
    font-size: 2.75rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    display: inline-block;
}

/* Band colours */
.pp-band[data-band="Poor"]      { color: #ef4444; }
.pp-band[data-band="Average"]   { color: #f97316; }
.pp-band[data-band="Good"]      { color: #22c55e; }
.pp-band[data-band="Excellent"] { color: #3b82f6; }

/* Motivational sentence */
.pp-motivational {
    text-align: center;
    font-size: 0.95rem;
    color: var(--text-secondary, #666);
    margin: 0.25rem 0 1.25rem;
    font-style: italic;
}

/* Factor list */
.pp-factors {
    list-style: none;
    padding: 0;
    margin: 0 auto;
    max-width: 420px;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}

.pp-factor {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    background: var(--bg-secondary, #f8fafc);
    font-size: 0.9rem;
}

.pp-factor-label {
    color: var(--text-primary, #333);
    font-weight: 500;
}

.pp-factor-value {
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.82rem;
}

.pp-factor-value.positive {
    background: #dcfce7;
    color: #16a34a;
}

.pp-factor-value.negative {
    background: #fee2e2;
    color: #dc2626;
}

.pp-factor-value.neutral {
    background: var(--bg-tertiary, #e2e8f0);
    color: var(--text-secondary, #666);
}

/* Synthetic data notice */
.pp-synthetic-notice {
    text-align: center;
    font-size: 0.8rem;
    color: var(--text-secondary, #888);
    margin-top: 1rem;
    padding: 0.5rem;
    background: var(--bg-secondary, #f8fafc);
    border-radius: 6px;
    border: 1px dashed var(--border-color, #e2e8f0);
}

/* Refresh button micro-animation */
.pp-refresh-btn.loading {
    opacity: 0.6;
    pointer-events: none;
}

.pp-refresh-btn.loading::before {
    content: "";
    display: inline-block;
    width: 10px;
    height: 10px;
    border: 1.5px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: pp-spin 0.6s linear infinite;
    margin-right: 0.35rem;
    vertical-align: middle;
}
```

#### 4.4 — JavaScript to add to `pomodoro/templates/analytics/index.html`

Add inside `{% block scripts %}` at the bottom of the analytics template.

```javascript
<script>
(function () {
    // ── DOM refs ────────────────────────────────────────────────
    const panel        = document.getElementById('projectedPerformancePanel');
    const loading      = document.getElementById('ppLoading');
    const result       = document.getElementById('ppResult');
    const errorEl      = document.getElementById('ppError');
    const bandEl       = document.getElementById('ppBand');
    const motivEl      = document.getElementById('ppMotivational');
    const factorsEl    = document.getElementById('ppFactors');
    const lastUpdEl    = document.getElementById('ppLastUpdated');
    const syntheticEl  = document.getElementById('ppSyntheticNotice');
    const refreshBtn   = document.getElementById('ppRefreshBtn');
    const retryLink    = document.getElementById('ppRetryLink');

    // ── Helpers ─────────────────────────────────────────────────
    function showState(state) {
        loading.style.display = state === 'loading' ? 'flex' : 'none';
        result.style.display  = state === 'result'  ? 'block' : 'none';
        errorEl.style.display = state === 'error'   ? 'block' : 'none';
    }

    function formatAge(seconds) {
        if (seconds < 60)   return 'Updated just now';
        if (seconds < 3600) return `Updated ${Math.floor(seconds / 60)} min ago`;
        if (seconds < 86400) return `Updated ${Math.floor(seconds / 3600)}h ago`;
        return `Updated ${Math.floor(seconds / 86400)}d ago`;
    }

    function render(data) {
        // Band
        bandEl.textContent = data.band;
        bandEl.setAttribute('data-band', data.band);

        // Motivational
        motivEl.textContent = data.motivational;

        // Staleness
        lastUpdEl.textContent = formatAge(data.seconds_since);

        // Factors
        factorsEl.innerHTML = '';
        (data.factors || []).forEach(f => {
            const li = document.createElement('li');
            li.className = 'pp-factor';

            const labelSpan = document.createElement('span');
            labelSpan.className = 'pp-factor-label';
            labelSpan.textContent = f.label;

            const valueSpan = document.createElement('span');
            const cls = f.positive === true  ? 'positive'
                      : f.positive === false ? 'negative'
                      :                        'neutral';
            valueSpan.className = `pp-factor-value ${cls}`;
            valueSpan.textContent = f.value;

            li.appendChild(labelSpan);
            li.appendChild(valueSpan);
            factorsEl.appendChild(li);
        });

        // Synthetic notice
        syntheticEl.style.display = data.is_synthetic ? 'block' : 'none';

        showState('result');
    }

    // ── Fetch prediction ────────────────────────────────────────
    async function loadPrediction(forceRetrain = false) {
        showState('loading');
        refreshBtn.classList.add('loading');

        const url    = forceRetrain
            ? '/api/productivity/retrain'
            : '/api/productivity/prediction';
        const method = forceRetrain ? 'POST' : 'GET';

        try {
            const res  = await fetch(url, { method });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            render(data);
        } catch (err) {
            console.error('[PP] Prediction fetch failed:', err);
            showState('error');
        } finally {
            refreshBtn.classList.remove('loading');
        }
    }

    // ── Auto-refresh every 60 min (matches retraining schedule) ─
    function scheduleAutoRefresh() {
        setInterval(() => loadPrediction(false), 60 * 60 * 1000);
    }

    // ── Event listeners ─────────────────────────────────────────
    refreshBtn.addEventListener('click', () => loadPrediction(true));
    retryLink.addEventListener('click',  (e) => { e.preventDefault(); loadPrediction(false); });

    // ── Init ────────────────────────────────────────────────────
    loadPrediction(false);
    scheduleAutoRefresh();
})();
</script>
```

---

### Phase 5 — Explanation Quality (Post-MVP)

Once the core pipeline is working, the explanation logic in `predictor.py` can be made smarter by inspecting the actual decision path the tree took for this user's feature vector (using `clf.decision_path(feat_array)`). This gives the exact sequence of nodes and thresholds that led to the prediction, so the factor list can show the *actual* split values that were decisive rather than general thresholds.

---

## Summary: Files to Create / Modify

### New files

| File | Purpose |
|---|---|
| `pomodoro/ml/trainer.py` | Per-user model training, pickle persistence |
| `pomodoro/ml/predictor.py` | Prediction + explanation + terminal output |
| `pomodoro/ml/scheduler.py` | Hourly background retraining thread |

### Modified files

| File | Change |
|---|---|
| `pomodoro/__init__.py` | Add `start_scheduler(app)` at end of `create_app()` |
| `pomodoro/routes/routine_suggestion.py` | Replace placeholder with real `/prediction` + `/retrain` endpoints |
| `pomodoro/routes/timer.py` | Add `_log_event()` calls after each state change |
| `pomodoro/routes/tasks.py` | Add `_log_event()` calls on task create/complete/delete |
| `pomodoro/routes/lists.py` | Add `_log_event()` calls on list create/delete |
| `pomodoro/templates/analytics/index.html` | Insert PP panel HTML + JS block |
| `pomodoro/static/css/analytics.css` | Add PP panel CSS |

---

## Implementation Order (Step-by-Step)

Follow this order to avoid building on unverified foundations:

```
Step 1  Phase 1.1–1.3   Wire _log_event into timer, task, list routes
Step 2  Phase 1.4       Verify user_statistics is receiving rows via SQL check
Step 3  Phase 3.1       Create pomodoro/ml/trainer.py
Step 4  Phase 3.2       Create pomodoro/ml/predictor.py
Step 5                  Test: run predict_for_user(user_id, db) in Flask shell
                        → should print insights to terminal
Step 6  Phase 3.3       Create pomodoro/ml/scheduler.py + wire into create_app()
Step 7  Phase 3.4       Update routine_suggestion.py with real endpoints
Step 8                  Test: curl /api/productivity/prediction → JSON response
Step 9  Phase 4.2–4.3   Add HTML + CSS to analytics template
Step 10 Phase 4.4       Add JavaScript to analytics template
Step 11                 End-to-end test in browser
Step 12 Phase 5         (Optional) Improve explanation with decision_path()
```

---

## Decision Tree Retrain Frequency — Rationale

| Interval | Pros | Cons |
|---|---|---|
| Every 15 min | Very fresh | Almost no new data between runs; wasteful |
| **Every 1 hour** ✓ | Captures a full Pomodoro set of new events | Slight lag |
| Every 24 hours | Clean daily aggregates | Stale during active sessions |

One hour is the right balance: a user doing 4 Pomodoro sessions generates ~8 events per hour (4 session_start, 4 session_end, breaks, tasks), which is meaningful new signal without unnecessary compute.

Manual refresh (the button) is always available for users who want instant re-evaluation.

---

## Data Privacy and Security

- All statistics data is tied to `user_id` with proper foreign key constraints
- Data is automatically deleted when user account is deleted (CASCADE)
- No personally identifiable information in statistics table
- Timestamps use Unix format for consistency
- Metadata field can store additional context without schema changes

## Performance Considerations

### Database Indexing

The table includes strategic indexes for common query patterns:
- `idx_user_statistics_user_id`: Fast user-specific queries
- `idx_user_statistics_timestamp`: Time-based filtering
- `idx_user_statistics_event_type`: Event type filtering
- `idx_user_statistics_user_timestamp`: Combined user + time queries
- `idx_user_statistics_user_event`: Combined user + event type queries
- `idx_user_statistics_task_id`: Task-specific queries

### Query Optimization

- Use timestamp ranges for time-based filtering
- Filter by user_id first to reduce dataset size
- Use appropriate indexes for event type queries
- Consider materialized views for complex aggregations
- Implement caching for frequently accessed statistics

## Future Enhancements

### Additional Event Types

- **Task modification**: When task content is edited
- **Tag assignment**: When tags are added/removed from tasks
- **List activation**: When user switches active list
- **Goal setting**: When user sets productivity goals
- **Achievement unlock**: When user achieves milestones

### Advanced Analytics

- **Heatmaps**: Productivity patterns by time of day/day of week
- **Trend analysis**: Long-term productivity trends
- **Correlation analysis**: Relationships between different metrics
- **Predictive analytics**: Predict future productivity based on patterns

### ML Model Enhancements

- **Time series forecasting**: Predict future productivity
- **Anomaly detection**: Identify unusual productivity patterns
- **Clustering**: Group similar productivity patterns
- **Reinforcement learning**: Optimize recommendations based on user feedback

## Conclusion

This comprehensive statistics and ML system provides a solid foundation for understanding user productivity patterns and providing actionable insights. The single-table architecture ensures flexibility and simplicity while the modular implementation plan allows for incremental development and testing.
