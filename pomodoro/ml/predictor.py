"""
Predict the current user's productivity band and generate a text explanation.

Output dict shape (also returned as JSON to the frontend):
{
    "band":         "good",
    "internal_band": "good",
    "score":        72.4,
    "confidence":   0.81,
    "motivational": "You're on a roll — keep the momentum going!",
    "factors": [
        {"label": "Session completion", "value": "High",   "positive": True},
        {"label": "Task completion",    "value": "Medium", "positive": True},
        {"label": "Break management",   "value": "Low",    "positive": False},
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


def _value_label(feature: str, value: float) -> tuple[str, bool | None]:
    LOWER_IS_BETTER = {"break_skip_rate", "session_pause_rate", "avg_task_completion_min"}
    if feature in LOWER_IS_BETTER:
        if value < 0.15 or (feature == "avg_task_completion_min" and value < 25):
            return "Low", True
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
    if not model_exists(user_id):
        train_for_user(user_id, db)

    clf, meta = load_model(user_id)

    features_dict = compute_features_for_user(user_id)

    feat_array = np.array(
        [
            features_dict.get("avg_task_completion_time_seconds", 60) / 60.0,
            features_dict.get("task_completion_rate", 0.5),
            features_dict.get("break_completion_rate", 0.5),
            features_dict.get("session_completion_rate", 0.5),
            features_dict.get("avg_daily_focus_time_seconds", 0) / 60.0,
            features_dict.get("consistency_score", 0.5),
            1.0 - features_dict.get("break_completion_rate", 0.5),
            features_dict.get("break_skip_streak", 0) / 20.0,
            features_dict.get("preferred_hour", 12) / 23.0,
            features_dict.get("preferred_weekday", 3) / 6.0,
        ],
        dtype=float,
    ).reshape(1, -1)

    pred_class = int(clf.predict(feat_array)[0])
    proba = clf.predict_proba(feat_array)[0]
    class_idx = list(clf.classes_).index(pred_class)
    confidence = float(proba[class_idx])

    internal_label = INTERNAL_LABELS[pred_class]
    display_label  = DISPLAY_BAND[internal_label]

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
            "positive": positive,
            "raw":      round(float(val), 3),
        })

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
