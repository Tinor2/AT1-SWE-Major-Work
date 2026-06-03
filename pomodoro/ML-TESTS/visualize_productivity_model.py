#!/usr/bin/env python3
"""
Matplotlib visualizer for the productivity decision-tree mockup.

Generates PNG charts in pomodoro/ML-TESTS/output/
Run from repo root (venv active):
    python pomodoro/ML-TESTS/visualize_productivity_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score
from sklearn.tree import plot_tree

# Same folder — import training helpers from mockup script
_ML_DIR = Path(__file__).resolve().parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from productivity_decision_tree import (  # noqa: E402
    FEATURE_NAMES,
    PRODUCTIVITY_LABELS,
    class_names_for_clf,
    train_mockup,
)

OUTPUT_DIR = _ML_DIR / "output"

# Band colours (bad → amazing)
CLASS_COLORS = [
    "#ef4444",
    "#f97316",
    "#eab308",
    "#22c55e",
    "#3b82f6",
    "#a855f7",
]


def _style_axes(ax, title: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.tick_params(labelsize=9)


def plot_feature_importances(clf, ax) -> None:
    importances = clf.feature_importances_
    order = np.argsort(importances)
    names = [FEATURE_NAMES[i] for i in order]
    values = importances[order]
    colors = plt.cm.viridis(values / max(values.max(), 1e-9))

    ax.barh(names, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Importance")
    _style_axes(ax, "Feature importances")


def plot_class_distribution(y, ax) -> None:
    counts = [int(np.sum(y == c)) for c in range(len(PRODUCTIVITY_LABELS))]
    bars = ax.bar(
        PRODUCTIVITY_LABELS,
        counts,
        color=CLASS_COLORS,
        edgecolor="white",
        linewidth=0.8,
    )
    ax.bar_label(bars, fontsize=8)
    ax.set_ylabel("Samples")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    _style_axes(ax, "Training set — class balance")


def plot_confusion_matrix(clf, X_test, y_test, ax) -> None:
    labels = list(range(len(PRODUCTIVITY_LABELS)))
    disp = ConfusionMatrixDisplay.from_estimator(
        clf,
        X_test,
        y_test,
        labels=labels,
        display_labels=PRODUCTIVITY_LABELS,
        cmap="Blues",
        ax=ax,
        colorbar=False,
    )
    disp.ax_.set_xticklabels(
        PRODUCTIVITY_LABELS, rotation=35, ha="right", fontsize=8
    )
    disp.ax_.set_yticklabels(PRODUCTIVITY_LABELS, fontsize=8)
    _style_axes(ax, "Confusion matrix (test set)")


def plot_decision_tree(clf, ax) -> None:
    plot_tree(
        clf,
        feature_names=FEATURE_NAMES,
        class_names=class_names_for_clf(clf),
        filled=True,
        rounded=True,
        ax=ax,
        fontsize=7,
        proportion=True,
        impurity=True,
    )
    _style_axes(ax, "Decision tree structure")


def plot_summary_metrics(clf, y_test, y_pred, ax) -> None:
    acc = accuracy_score(y_test, y_pred)
    depth = clf.get_depth()
    leaves = clf.get_n_leaves()
    n_classes = len(clf.classes_)

    lines = [
        "Productivity classifier (mockup)",
        "",
        f"Test accuracy: {acc:.1%}",
        f"Tree depth: {depth}",
        f"Leaf nodes: {leaves}",
        f"Classes learned: {n_classes} / {len(PRODUCTIVITY_LABELS)}",
        "",
        "Bands: bad → amazing",
        "(see STATISTICS_AND_ML_SYSTEM.md)",
    ]
    ax.axis("off")
    ax.text(
        0.05,
        0.95,
        "\n".join(lines),
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=11,
        family="monospace",
        bbox=dict(boxstyle="round", facecolor="#f1f5f9", edgecolor="#cbd5e1"),
    )


def build_dashboard(
    clf,
    X_train,
    y_train,
    X_test,
    y_test,
    y_pred,
    *,
    show: bool = False,
) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(18, 14))
    fig.suptitle(
        "Pomodoro productivity model — decision tree visualizer",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.28)

    ax_dist = fig.add_subplot(gs[0, 0])
    ax_imp = fig.add_subplot(gs[0, 1])
    ax_cm = fig.add_subplot(gs[1, 0])
    ax_info = fig.add_subplot(gs[1, 1])

    plot_class_distribution(y_train, ax_dist)
    plot_feature_importances(clf, ax_imp)
    plot_confusion_matrix(clf, X_test, y_test, ax_cm)
    plot_summary_metrics(clf, y_test, y_pred, ax_info)

    dashboard_path = OUTPUT_DIR / "productivity_dashboard.png"
    fig.savefig(dashboard_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # Full-page tree (readable on its own)
    fig_tree, ax_tree = plt.subplots(figsize=(22, 12))
    plot_decision_tree(clf, ax_tree)
    tree_path = OUTPUT_DIR / "productivity_decision_tree.png"
    fig_tree.savefig(tree_path, dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig_tree)

    if show:
        plt.show()

    return dashboard_path


def main() -> int:
    print("Training mockup model…")
    clf, X_train, X_test, y_train, y_test = train_mockup()
    y_pred = clf.predict(X_test)

    print("Building matplotlib figures…")
    dashboard = build_dashboard(
        clf, X_train, y_train, X_test, y_test, y_pred, show=False
    )

    print(f"Saved: {dashboard}")
    print(f"Saved: {OUTPUT_DIR / 'productivity_decision_tree.png'}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
