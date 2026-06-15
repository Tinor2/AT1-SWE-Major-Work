"""
Predict the current user's productivity band and generate a text explanation.

Two-layer prediction:
  1. ML model (preferred): loads the per-user DecisionTreeClassifier
     trained by trainer.py and calls model.predict() + predict_proba()
     on the current feature vector. The returned band comes from the
     trained tree; confidence comes from the probability estimate.
  2. Heuristic fallback: if no model exists for the user yet (e.g. they
     haven't triggered a retrain), computes the band from the same
     formula used to generate training labels.

The heuristic score is always computed for the detailed breakdown UI
(score breakdown bars, factor labels), but the band shown at the top
of the "Projected Performance" panel comes from whichever path above
was taken. The frontend can check the "model_used" field in the JSON
response to know which path was used.

Scoring formula (matches trainer.py _score_from_features):
   core   = task_rate*20 + break_rate*12 + session_rate*15
            + focus_curve(focus_min) + consistency^2*15 + speed_bonus*18
            + active_day_ratio^0.7*15
  penalty = skip_rate*12 + pause_rate*6 + focus_penalty
  score  = clip(core - penalty, 0, 100)

  focus_curve(focus_min):
    base   = (focus_min/240)^0.5 * 20       — power curve, fast rise below 240
    bonus  = max(0, focus_min - 240)/240*50 — linear bonus above 4-hour cap
    penalty= (1 - focus_ratio)*15           — penalty for low focus

Security (SAST — bandit run 2026-06-14):
  - All database queries use parameterised ? placeholders (SQLi safe).
  - The model is loaded via trainer.load_model() which verifies SHA-256
    hash integrity before unpickling (A08: RCE via tampered pickle).
  - The route handler (routine_suggestion.py) catches all exceptions
    and returns JSON error responses, never leaking stack traces.

Output dict shape (returned as JSON to /api/productivity/prediction):
{
    "band":          "Good",
    "internal_band": "good",
    "score":         72.4,
    "confidence":    0.87,
    "motivational":  "You're on a roll — keep the momentum going!",
    "factors":       [...],
    "trained_at":    "2026-06-14T12:00:00Z",
    "seconds_since": 3600,
    "n_samples":     30,
    "is_synthetic":  False,
    "model_used":    True,
    "scores_breakdown": [...],
    "debug":         {...},
}
"""

import time
import numpy as np
from pomodoro.ml.feature_engineering import compute_features_for_user

INTERNAL_LABELS = ["bad", "poor", "average", "good", "excellent", "amazing"]

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

FACTOR_LABELS = {
    "session_completion_rate":  "Session completion",
    "task_completion_rate":     "Task completion",
    "break_completion_rate":    "Break management",
    "focus_minutes_per_day":    "Daily focus time",
    "consistency_score":        "Consistency",
    "break_skip_rate":          "Break skip rate",
    "session_pause_rate":       "Pause rate",
    "avg_task_completion_min":  "Task speed",
}


def _score_to_class(score: float) -> int:
    if score < 20: return 0
    if score < 40: return 1
    if score < 60: return 2
    if score < 80: return 3
    if score < 90: return 4
    return 5


def _compute_score(feat_array: np.ndarray, active_ratio: float = 1.0) -> tuple:
    """
    Compute 0-100 productivity score.

    Weight rationale:
      task_rate         × 20  — completing tasks is the strongest positive signal
      break_rate        × 12  — completing breaks supports sustained focus
      session_rate      × 15  — finishing sessions shows commitment
      focus_curve       —      — power curve below 240 min + steep bonus above
      consistency       × 15  — even effort across days (squared, increased weight)
      speed_bonus       × 18  — faster task completion = higher efficiency
      active_day_ratio  × 15  — showing up regularly matters (non-linear)
    Penalties:
      skip_rate         × 12  — skipping breaks now penalises more heavily
      pause_rate        × 6   — pausing occasionally is normal
      focus_penalty     × 15  — low daily focus time drags score down
    """
    avg_min, task_rate, break_rate, session_rate, focus_min, consistency, skip_rate, pause_rate, _, _ = feat_array
    speed_bonus = max(0.0, 1.0 - min(avg_min, 120.0) / 120.0) * 18
    task_pt    = task_rate * 20
    break_pt   = break_rate * 12
    session_pt = session_rate * 15
    focus_ratio = min(focus_min / 240.0, 1.0)
    focus_base = focus_ratio ** 0.5 * 20
    focus_bonus = max(0.0, focus_min - 240.0) / 240.0 * 50
    focus_penalty = max(0.0, (1.0 - focus_ratio) * 15)
    focus_pt   = focus_base + focus_bonus
    cons_pt    = (consistency ** 2) * 15
    active_pt  = (active_ratio ** 0.7) * 15
    core = task_pt + break_pt + session_pt + focus_pt + cons_pt + speed_bonus + active_pt
    skip_pen   = skip_rate * 12
    pause_pen  = pause_rate * 6
    penalty    = skip_pen + pause_pen + focus_penalty
    score = float(np.clip(core - penalty, 0, 100))
    return score, core, penalty, task_pt, break_pt, session_pt, focus_pt, focus_base, focus_bonus, cons_pt, speed_bonus, active_pt, skip_pen, pause_pen, focus_penalty


def _value_label(feature: str, value: float) -> tuple[str, bool | None]:
    feature_weighting_dir = {
        # Stuctured as "feature_name" : [Good_thresh, Average_thresh]
        # (Anything below Average_thresh is Poor)
        "session_completion_rate":   [0.8, 0.4],
        "task_completion_rate":      [0.8, 0.4],
        "break_completion_rate":     [0.6, 0.3],
        "focus_minutes_per_day":     [0.5, 0.3],
        "consistency_score":         [0.85, 0.5],
        "break_skip_rate":           [0.2, 0.5],
        "session_pause_rate":        [0.1, 0.3],
        "avg_task_completion_min":   [25, 60],
    }

    NORMALIZE_TO_240 = {"focus_minutes_per_day"}
    LOWER_IS_BETTER = {"break_skip_rate", "session_pause_rate", "avg_task_completion_min"}
    good, poor = "Good", "Poor"

    thresh = feature_weighting_dir.get(feature)
    if thresh is None:
        return "Average", None
    good_th, avg_th = thresh

    if feature in NORMALIZE_TO_240:
        value = value / 240.0

    if feature in LOWER_IS_BETTER:
        if value < good_th:
            return good, True
        if value < avg_th:
            return "Average", None
        return poor, False
    else:
        if value >= good_th:
            return good, True
        if value >= avg_th:
            return "Average", None
        return poor, False


def predict_for_user(user_id: int, db, days: int = 60) -> dict:
    # Check if user has at least 2 completed sessions
    row = db.execute(
        "SELECT COUNT(*) AS c FROM user_statistics WHERE user_id = ? AND event_type = 'session_end'",
        (user_id,)
    ).fetchone()
    has_min_sessions = row["c"] >= 2
    is_synthetic = not has_min_sessions

    features_dict = compute_features_for_user(user_id, training_window_days=days)

    avg_task_min  = features_dict.get("avg_task_completion_time_seconds", 3600) / 60.0
    task_rate     = features_dict.get("task_completion_rate", 0.5)
    break_rate    = features_dict.get("break_completion_rate", 0.5)
    session_rate  = features_dict.get("session_completion_rate", 0.5)
    focus_min     = features_dict.get("avg_daily_focus_time_seconds", 3600) / 60.0
    consistency   = features_dict.get("consistency_score", 0.5)
    skip_rate     = 1.0 - break_rate
    pause_rate    = features_dict.get("session_pause_rate", 0.0)
    active_ratio  = features_dict.get("active_day_ratio", 0.5)

    feat_values = np.array([
        avg_task_min,
        task_rate,
        break_rate,
        session_rate,
        focus_min,
        consistency,
        skip_rate,
        pause_rate,
        features_dict.get("preferred_hour", 12) / 23.0,
        features_dict.get("preferred_weekday", 3) / 6.0,
    ], dtype=float)

    # ── Attempt ML model inference ──────────────────────────────────────
    # If a trained model exists on disk, use it to predict the band.
    # The heuristic score is always computed for the breakdown UI.
    from pomodoro.ml import trainer as ml_trainer
    model, meta = ml_trainer.load_model(user_id)

    score, core, penalty, task_pt, break_pt, session_pt, focus_pt, focus_base, focus_bonus, cons_pt, speed_pt, active_pt, skip_pen, pause_pen, focus_penalty = \
        _compute_score(feat_values, active_ratio)

    if model is not None:
        predicted_class = int(model.predict(feat_values.reshape(1, -1))[0])
        proba = model.predict_proba(feat_values.reshape(1, -1))[0]
        proba_idx = int(np.where(model.classes_ == predicted_class)[0][0])
        confidence = round(float(proba[proba_idx]), 2)
        internal_label = INTERNAL_LABELS[predicted_class]
        display_label  = DISPLAY_BAND[internal_label]
        trained_at     = meta.get("trained_at_human", "unknown")
        seconds_since  = int(time.time() - meta.get("trained_at", time.time()))
        _prediction_source = "DecisionTree model"
    else:
        class_idx = _score_to_class(score)
        confidence = round(min(score / 100.0 + 0.3, 0.95), 2)
        internal_label = INTERNAL_LABELS[class_idx]
        display_label  = DISPLAY_BAND[internal_label]
        trained_at     = "realtime"
        seconds_since  = 0
        _prediction_source = "fallback formula"

    factors = []
    feat_display = {
        "session_completion_rate":  session_rate,
        "task_completion_rate":     task_rate,
        "break_completion_rate":    break_rate,
        "focus_minutes_per_day":    focus_min,
        "consistency_score":        consistency,
        "break_skip_rate":          skip_rate,
        "session_pause_rate":       pause_rate,
        "avg_task_completion_min":  avg_task_min,
    }
    for feat_key, human_label in FACTOR_LABELS.items():
        val = feat_display[feat_key]
        val_label, positive = _value_label(feat_key, val)
        factors.append({
            "label":    human_label,
            "value":    val_label,
            "positive": positive,
            "raw":      round(float(val), 3),
        })

    # ── Feature breakdown (what the decision tree actually uses) ─────────
    FEATURE_SPEC = [
        ("task",   "Task completion",  "task_completion_rate",     1.0,   False, 1, False),
        ("break",  "Break management", "break_completion_rate",    1.0,   False, 2, False),
        ("session","Session completion","session_completion_rate", 1.0,   False, 3, False),
        ("focus",  "Daily focus time", "focus_minutes_per_day",    240.0, False, 4, True),
        ("consistency","Consistency",  "consistency_score",        1.0,   False, 5, False),
        ("speed",  "Task speed",       "avg_task_completion_min",  120.0, True,  0, False),
        ("skip",   "Break skip rate",  "break_skip_rate",          1.0,   True,  6, False),
        ("pause",  "Pause rate",       "session_pause_rate",       1.0,   True,  7, False),
    ]

    breakdown = []
    for key, label, feat_key, max_val, lower_better, imp_idx, is_focus in FEATURE_SPEC:
        val = feat_display[feat_key]
        if lower_better:
            earned = max(0.0, max_val - min(val, max_val))
        else:
            earned = min(val, max_val) if max_val else val
        rating, positive = _value_label(feat_key, val)
        entry = {
            "key": key,
            "label": label,
            "earned": round(earned, 2 if max_val else 1),
            "max": max_val,
            "rating": rating,
            "positive": positive,
        }
        if is_focus:
            entry["type"] = "focus"
            entry["detail"] = f"raw {val:.0f} min"
        breakdown.append(entry)

    _print_insights(user_id, display_label, internal_label, factors, score, core, penalty,
                    task_pt, break_pt, session_pt, focus_pt, focus_base, focus_bonus, cons_pt, speed_pt, active_pt, skip_pen, pause_pen, focus_penalty, _prediction_source, breakdown)

    return {
        "band":          display_label,
        "internal_band": internal_label,
        "score":         round(score, 1),
        "confidence":    confidence,
        "motivational":  MOTIVATIONAL[display_label],
        "factors":       factors,
        "trained_at":    trained_at,
        "seconds_since": seconds_since,
        "n_samples":     days,
        "is_synthetic":  is_synthetic,
        "model_used":    model is not None,
        "scores_breakdown": breakdown,
        "debug": {
            "score":      round(score, 1),
            "core":       round(core, 1),
            "penalty":    round(penalty, 1),
            "task_pt":    round(task_pt, 1),
            "break_pt":   round(break_pt, 1),
            "session_pt": round(session_pt, 1),
            "focus_pt":   round(focus_pt, 1),
            "focus_base": round(focus_base, 1),
            "focus_bonus": round(focus_bonus, 1),
            "focus_penalty": round(focus_penalty, 1),
            "cons_pt":    round(cons_pt, 1),
            "speed_pt":   round(speed_pt, 1),
            "active_pt":  round(active_pt, 1),
            "skip_pen":   round(skip_pen, 1),
            "pause_pen":  round(pause_pen, 1),
            "active_ratio": round(active_ratio, 3),
        },
    }


def _print_insights(user_id, display_label, internal_label, factors, score, core, penalty,
                    task_pt, break_pt, session_pt, focus_pt, focus_base, focus_bonus, cons_pt, speed_pt, active_pt, skip_pen, pause_pen, focus_penalty, source="fallback formula", breakdown=None):
    divider = "=" * 60
    print(f"\n{divider}")
    print(f"  [ML] Productivity — User {user_id}  [{source}]")
    print(f"  Rating      : {display_label.upper()} ({internal_label})")
    print(f"  Score       : {score:.1f}  (core: {core:.1f}, penalty: {penalty:.1f})")
    print(f"  Breakdown   :")
    if breakdown:
        for entry in breakdown:
            if entry['key'] == 'total':
                continue
            val = entry['earned']
            mx = entry['max']
            rating = entry.get('rating') or ''
            key = entry['key']
            if isinstance(mx, (int, float)) and mx > 0:
                print(f"    {key:12s} {str(val):>8}/{mx}  ({rating})")
            else:
                print(f"    {key:12s} {str(val):>8}      ({rating})")
    else:
        print(f"    Task rate    {task_pt:6.1f} / 20  ({factors[1]['value']})")
        print(f"    Break rate   {break_pt:6.1f} / 12  ({factors[2]['value']})")
        print(f"    Session rate {session_pt:6.1f} / 22  ({factors[0]['value']})")
        print(f"    Focus time   {focus_pt:6.1f}      (base={focus_base:.1f} bonus={focus_bonus:.1f} pen={focus_penalty:.1f})  ({factors[3]['value']})")
        print(f"    Consistency  {cons_pt:6.1f} / 15  ({factors[4]['value']})")
        print(f"    Speed bonus  {speed_pt:6.1f} / 18  ({factors[7]['value']})")
        print(f"    Active days  {active_pt:6.1f} / 15")
        print(f"    Skip penalty {skip_pen:6.1f} / 12  ({factors[5]['value']})")
        print(f"    Pause pen.   {pause_pen:6.1f} /  6  ({factors[6]['value']})")
    print(f"  Raw features :")
    print(f"    task_rate={factors[1]['raw']} break_rate={factors[2]['raw']} session_rate={factors[0]['raw']}")
    print(f"    focus_min={factors[3]['raw']} consistency={factors[4]['raw']}")
    print(f"    skip_rate={factors[5]['raw']} pause_rate={factors[6]['raw']} avg_min={factors[7]['raw']}")
    print(divider)
