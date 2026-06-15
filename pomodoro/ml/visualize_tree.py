import textwrap
from pathlib import Path
import pickle
import os
import argparse
import sys
from graphviz import Digraph
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from pomodoro.ml.trainer import _model_path, _meta_path

INTERNAL_LABELS = ["bad", "poor", "average", "good", "excellent", "amazing"]

DISPLAY_BAND = {
    "bad":       "Poor",
    "poor":      "Poor",
    "average":   "Average",
    "good":      "Good",
    "excellent": "Excellent",
    "amazing":   "Excellent",
}

FEATURE_NAMES = [
    "avg_task_completion_min",   # 0
    "task_completion_rate",      # 1
    "break_completion_rate",     # 2
    "session_completion_rate",   # 3
    "focus_minutes_per_day",     # 4
    "consistency_score",         # 5
    "skip_rate",                 # 6
    "pause_rate",                # 7
    "peak_hour_norm",            # 8
    "weekday_norm",              # 9
]

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _majority_label(class_counts: np.ndarray) -> tuple[str, int]:
    class_id = int(np.argmax(class_counts))
    internal = INTERNAL_LABELS[class_id]
    display = DISPLAY_BAND[internal]
    return display, class_id


def _class_distribution_str(class_counts: np.ndarray) -> str:
    parts = []
    for i, count in enumerate(class_counts):
        if count > 0:
            internal = INTERNAL_LABELS[i]
            display = DISPLAY_BAND[internal]
            parts.append(f"{display}={int(count)}")
    return "  ".join(parts)


def build_flowchart(user_id: int = 22):
    mp = _model_path(user_id)
    if not os.path.exists(mp):
        print(f"No model found for user {user_id}")
        return

    with open(mp, "rb") as f:
        clf = pickle.load(f)

    tree = clf.tree_
    n_nodes = tree.node_count
    children_left = tree.children_left
    children_right = tree.children_right
    feature = tree.feature
    threshold = tree.threshold
    values = tree.value
    n_node_samples = tree.n_node_samples

    print(f"User {user_id}: {n_nodes} nodes, depth={tree.max_depth}")

    dot = Digraph(
        f"DecisionTree_User{user_id}",
        format="png",
    )
    dot.attr(rankdir="TB", nodesep="0.08", ranksep="0.4")
    dot.attr("edge", fontsize="13")
    dot.attr("node", fontsize="13")
    dot.attr(dpi="150")

    # ── Subroutine entry (matches pipeline flowchart) ─────────────────
    dot.node("subroutine", """<
<TABLE BORDER="1" CELLSPACING="0" CELLPADDING="3" BGCOLOR="#E2CCFF">
  <TR>
    <TD WIDTH="4"></TD>
    <TD WIDTH="4"></TD>
    <TD>Use model to predict band<BR/>(see pipeline flowchart)</TD>
    <TD WIDTH="4"></TD>
    <TD WIDTH="4"></TD>
  </TR>
</TABLE>>""", shape="none")
    dot.edge("subroutine", "n0")

    queue = [0]
    visited = set()

    while queue:
        node_id = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)

        is_leaf = children_left[node_id] == -1
        class_counts = values[node_id][0]

        node_name = f"n{node_id}"

        if is_leaf:
            display_label, _ = _majority_label(class_counts)
            class_dist = _class_distribution_str(class_counts)
            samples = int(n_node_samples[node_id])

            node_label = (f"<<B>{display_label}</B>>")

            if display_label == "Poor":
                fillcolor = "#FF6B6B"
            elif display_label == "Average":
                fillcolor = "#FFEAA7"
            elif display_label == "Good":
                fillcolor = "#96CEB4"
            else:
                fillcolor = "#4ECDC4"

            dot.node(node_name, node_label, shape="box", style="filled",
                     fillcolor=fillcolor, penwidth="0.8", margin="0.06,0.02")
        else:

# ... (rest of imports)

# ... (inside build_flowchart, inside the else block for nodes)
            feat_name = FEATURE_NAMES[feature[node_id]]
            # Wrap text manually with <BR/>
            wrapped_feat_name = "<BR/>".join(textwrap.wrap(feat_name.replace('_', ' '), width=10))
            thr = threshold[node_id]
            if thr == int(thr):
                thr = int(thr)
            else:
                thr = round(thr, 2)

            node_label = (
                f"<<B>{wrapped_feat_name}</B><BR/>"
                f"≤ {thr}>"
            )

            dot.node(node_name, node_label, shape="diamond",
                     style="filled", fillcolor="#F0F0F0", width="1.6", height="1.6", fixedsize="true", fontsize="13")

            left_id = children_left[node_id]
            right_id = children_right[node_id]

            if left_id != -1:
                dot.edge(node_name, f"n{left_id}", label="Y",
                         fontsize="13", labeldistance="0.6")
                queue.append(left_id)

            if right_id != -1:
                dot.edge(node_name, f"n{right_id}", label="N",
                         fontsize="13", labeldistance="0.6")
                queue.append(right_id)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"decision_tree_user_{user_id}"
    dot.render(str(output_file), cleanup=True)
    print(f"Saved to {output_file}.png")


def main():
    parser = argparse.ArgumentParser(description="Visualise a trained decision tree")
    parser.add_argument("--user", type=int, default=22,
                        help="User ID whose model to visualise (default: 22)")
    args = parser.parse_args()
    build_flowchart(args.user)


if __name__ == "__main__":
    main()
