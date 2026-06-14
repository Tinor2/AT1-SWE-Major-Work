#!/usr/bin/env python3
"""
Mockup: productivity categorization with scikit-learn DecisionTreeClassifier.

Aligned with Docs/STATISTICS_AND_ML_SYSTEM.md (Model 1).
Uses synthetic data until user_statistics-driven features are wired up.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, export_text

# Feature columns (one row = one user-day aggregate)
FEATURE_NAMES = [
    "avg_task_completion_min",   # lower often better (faster completion)
    "task_completion_rate",      # 0–1
    "break_completion_rate",     # 0–1
    "session_completion_rate",   # 0–1
    "focus_minutes_per_day",     # total focus time
    "consistency_score",         # 0–1 (higher = steadier habits)
    "break_skip_rate",           # 0–1 (lower is better)
    "session_pause_rate",        # 0–1 (lower is better)
    "peak_hour_norm",            # 0–1 (preferred work hour / 23)
    "weekday_index_norm",        # 0–1 (Mon=0 … Sun=6, normalized)
]

PRODUCTIVITY_LABELS = [
    "bad",       # 0–20% productivity score
    "poor",      # 20–40%
    "average",   # 40–60%
    "good",      # 60–80%
    "excellent", # 80–90%
    "amazing",   # 90–100%
]


def _productivity_score_row(row: np.ndarray, active_day_ratio: float = 1.0) -> float:
    """Heuristic 0–100 score from features (for synthetic label generation)."""
    (
        avg_min,
        task_rate,
        break_rate,
        session_rate,
        focus_min,
        consistency,
        skip_rate,
        pause_rate,
        _,
        _,
    ) = row

    # Faster tasks (capped), higher rates, more focus, consistency; penalize skip/pause
    speed_bonus = max(0.0, 1.0 - min(avg_min, 120.0) / 120.0) * 15
    focus_ratio = min(focus_min / 240.0, 1.0)
    focus_base  = focus_ratio ** 0.5 * 20
    focus_bonus = max(0.0, focus_min - 240.0) / 240.0 * 50
    focus_penalty = max(0.0, (1.0 - focus_ratio) * 15)
    core = (
        task_rate * 20
        + break_rate * 12
        + session_rate * 25
        + focus_base + focus_bonus
        + (consistency ** 2) * 15
        + speed_bonus
        + (active_day_ratio ** 0.7) * 15
    )
    penalties = skip_rate * 12 + pause_rate * 6 + focus_penalty
    return float(np.clip(core - penalties, 0, 100))


def score_to_class(score: float) -> int:
    if score < 20:
        return 0
    if score < 40:
        return 1
    if score < 60:
        return 2
    if score < 80:
        return 3
    if score < 90:
        return 4
    return 5


def class_names_for_clf(clf: DecisionTreeClassifier) -> list[str]:
    """Labels aligned with clf.classes_ (sklearn export/plot require exact length)."""
    return [PRODUCTIVITY_LABELS[int(c)] for c in clf.classes_]


# Hand-tuned centroids so every productivity band appears in synthetic data
_CLASS_CENTROIDS: dict[int, list[float]] = {
    0: [85, 0.1, 0.2, 0.15, 15, 0.2, 0.7, 0.6, 0.5, 0.5],
    1: [70, 0.25, 0.35, 0.3, 45, 0.35, 0.5, 0.45, 0.4, 0.5],
    2: [45, 0.5, 0.55, 0.55, 120, 0.55, 0.3, 0.25, 0.45, 0.3],
    3: [30, 0.72, 0.78, 0.82, 200, 0.72, 0.12, 0.1, 0.5, 0.3],
    4: [22, 0.88, 0.88, 0.92, 260, 0.85, 0.08, 0.06, 0.5, 0.2],
    5: [15, 0.98, 0.95, 0.98, 320, 0.92, 0.02, 0.02, 0.5, 0.2],
}


def _random_feature_row(rng: np.random.Generator) -> np.ndarray:
    task_rate = rng.beta(2, 2)
    break_rate = rng.beta(2, 2)
    session_rate = rng.beta(2, 2)
    focus_min = rng.integers(0, 360)
    consistency = rng.beta(3, 2)
    skip_rate = rng.beta(1.5, 4)
    pause_rate = rng.beta(1.5, 4)
    avg_min = rng.integers(5, 90)
    peak_hour = rng.integers(0, 24)
    weekday = rng.integers(0, 7)
    return np.array(
        [
            avg_min,
            task_rate,
            break_rate,
            session_rate,
            focus_min,
            consistency,
            skip_rate,
            pause_rate,
            peak_hour / 23.0,
            weekday / 6.0,
        ],
        dtype=float,
    )


def _ensure_all_classes(
    X: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
    min_per_class: int = 25,
) -> tuple[np.ndarray, np.ndarray]:
    """Add rows so each of the 6 bands is represented (needed for tree export)."""
    extra_X: list[np.ndarray] = []
    extra_y: list[int] = []

    for class_id, centroid in _CLASS_CENTROIDS.items():
        deficit = min_per_class - int(np.sum(y == class_id))
        for _ in range(max(0, deficit)):
            row = np.array(centroid, dtype=float)
            row += rng.normal(0, 0.03, size=row.shape)
            row[1:8] = np.clip(row[1:8], 0, 1)
            extra_X.append(row)
            extra_y.append(class_id)

    if not extra_X:
        return X, y
    X2 = np.vstack([X, np.array(extra_X)])
    y2 = np.concatenate([y, np.array(extra_y, dtype=int)])
    return X2, y2


def generate_synthetic_dataset(n_samples: int = 400, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = np.array([_random_feature_row(rng) for _ in range(n_samples)])

    scores = np.array([_productivity_score_row(X[i]) for i in range(n_samples)])
    y = np.array([score_to_class(s) for s in scores], dtype=int)
    return _ensure_all_classes(X, y, rng)


def train_mockup(
    max_depth: int = 5,
    min_samples_leaf: int = 8,
) -> tuple[DecisionTreeClassifier, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X, y = generate_synthetic_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    clf = DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)
    return clf, X_train, X_test, y_train, y_test


def print_feature_importances(clf: DecisionTreeClassifier) -> None:
    print("\n--- Feature importances ---")
    importances = clf.feature_importances_
    order = np.argsort(importances)[::-1]
    for idx in order:
        if importances[idx] > 0:
            print(f"  {FEATURE_NAMES[idx]:28s} {importances[idx]:.4f}")


def demo_prediction(clf: DecisionTreeClassifier) -> None:
    print("\n--- Sample predictions ---")
    examples = [
        ("Low productivity day", [75, 0.2, 0.3, 0.25, 30, 0.3, 0.6, 0.5, 0.4, 0.5]),
        ("Solid day", [35, 0.7, 0.75, 0.8, 180, 0.75, 0.15, 0.1, 0.45, 0.3]),
        ("Amazing day", [20, 0.95, 0.9, 0.95, 300, 0.9, 0.05, 0.05, 0.5, 0.2]),
    ]
    for name, feats in examples:
        pred = int(clf.predict([feats])[0])
        proba = clf.predict_proba([feats])[0]
        label = PRODUCTIVITY_LABELS[pred]
        class_idx = int(np.where(clf.classes_ == pred)[0][0])
        conf = float(proba[class_idx])
        print(f"  {name}: {label} (confidence {conf:.2f})")


def maybe_save_plot(clf: DecisionTreeClassifier) -> None:
    if os.environ.get("SAVE_PLOT") != "1":
        return
    try:
        import matplotlib.pyplot as plt
        from sklearn.tree import plot_tree
    except ImportError:
        return
    try:
        import matplotlib.pyplot as plt
        from sklearn.tree import plot_tree
    except ImportError:
        print("\n(Skip plot: install matplotlib and set SAVE_PLOT=1)")
        return

    fig, ax = plt.subplots(figsize=(20, 10))
    plot_tree(
        clf,
        feature_names=FEATURE_NAMES,
        class_names=class_names_for_clf(clf),
        filled=True,
        rounded=True,
        ax=ax,
        fontsize=8,
    )
    out = os.path.join(os.path.dirname(__file__), "productivity_tree.png")
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    plt.close()
    print(f"\nTree plot saved to {out}")


def main() -> int:
    print("Productivity categorization — Decision Tree mockup")
    print("=" * 55)

    clf, _X_train, X_test, _y_train, y_test = train_mockup()
    y_pred = clf.predict(X_test)

    print(f"\nTest accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print("\n--- Classification report ---")
    # labels= all 6 classes: test split may not include every band
    print(
        classification_report(
            y_test,
            y_pred,
            labels=list(range(len(PRODUCTIVITY_LABELS))),
            target_names=PRODUCTIVITY_LABELS,
            zero_division=0,
        )
    )

    print_feature_importances(clf)
    print("\n--- Decision tree (text, depth-limited export) ---")
    tree_rules = export_text(
        clf,
        feature_names=FEATURE_NAMES,
        # class_names=class_names_for_clf(clf),
        max_depth=4,
    )
    print(tree_rules)

    demo_prediction(clf)
    maybe_save_plot(clf)

    print("\nDone. Replace synthetic data with aggregates from user_statistics when ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
