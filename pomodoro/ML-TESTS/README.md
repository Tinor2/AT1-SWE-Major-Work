# ML-TESTS

Quick experiments for the Pomodoro statistics / ML system (see `Docs/STATISTICS_AND_ML_SYSTEM.md`).

## Productivity decision tree mockup

```bash
# From repo root, with venv active:
pip install scikit-learn numpy
python pomodoro/ML-TESTS/productivity_decision_tree.py
```

(`numpy` and `scikit-learn` are also listed in `requirements.txt` at the repo root.)

Uses **synthetic** user-day feature rows (not live DB data) to train a `DecisionTreeClassifier` and print metrics, feature importances, and a text tree summary.

Optional: set `SAVE_PLOT=1` to write `productivity_tree.png` from the CLI script (legacy).

## Matplotlib visualizer

```bash
source venv/bin/activate
pip install scikit-learn numpy matplotlib
python pomodoro/ML-TESTS/visualize_productivity_model.py
```

Writes:

- `pomodoro/ML-TESTS/output/productivity_dashboard.png` — class balance, feature importances, confusion matrix, summary
- `pomodoro/ML-TESTS/output/productivity_decision_tree.png` — full decision tree diagram
