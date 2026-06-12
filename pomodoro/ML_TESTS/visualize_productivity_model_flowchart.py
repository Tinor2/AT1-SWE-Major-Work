# productivity_flowchart.py

from pathlib import Path
from graphviz import Digraph

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

def build_flowchart():
    dot = Digraph(
        "ProductivityFlowchart",
        format="png"
    )

    # Top-down flow
    dot.attr(rankdir="TB")
    dot.attr(nodesep="0.6")
    dot.attr(ranksep="0.8")

    # -------------------------
    # Start node
    # -------------------------

    dot.node(
        "start",
        "START",
        shape="ellipse"
    )

    # -------------------------
    # Decision nodes
    # -------------------------

    dot.node(
        "d1",
        "session_completion_rate\n≤ 0.85",
        shape="diamond"
    )

    dot.node(
        "d2",
        "focus_minutes_per_day\n≤ 27.5",
        shape="diamond"
    )

    dot.node(
        "d3",
        "avg_task_completion_min\n≤ 65.5",
        shape="diamond"
    )

    dot.node(
        "d4",
        "session_completion_rate\n≤ 0.45",
        shape="diamond"
    )

    dot.node(
        "d5",
        "task_completion_rate\n≤ 0.55",
        shape="diamond"
    )

    dot.node(
        "d6",
        "task_completion_rate\n≤ 0.80",
        shape="diamond"
    )

    dot.node(
        "d7",
        "consistency_score\n≤ 0.70",
        shape="diamond"
    )

    dot.node(
        "d8",
        "focus_minutes_per_day\n≤ 260",
        shape="diamond"
    )

    # -------------------------
    # Outcome nodes
    # -------------------------

    dot.node("poor", "POOR", shape="box")
    dot.node("average1", "AVERAGE", shape="box")
    dot.node("average2", "AVERAGE", shape="box")
    dot.node("average3", "AVERAGE", shape="box")

    dot.node("good1", "GOOD", shape="box")
    dot.node("good2", "GOOD", shape="box")

    dot.node("excellent1", "EXCELLENT", shape="box")
    dot.node("excellent2", "EXCELLENT", shape="box")

    dot.node("amazing", "AMAZING", shape="box")

    # -------------------------
    # Connections
    # -------------------------

    dot.edge("start", "d1")

    # Root split

    dot.edge("d1", "d2", label="Yes")
    dot.edge("d1", "d6", label="No")

    # Left branch

    dot.edge("d2", "d3", label="Yes")
    dot.edge("d2", "d5", label="No")

    dot.edge("d3", "d4", label="Yes")
    dot.edge("d3", "average1", label="No")

    dot.edge("d4", "poor", label="Yes")
    dot.edge("d4", "average2", label="No")

    dot.edge("d5", "average3", label="Yes")
    dot.edge("d5", "good1", label="No")

    # Right branch

    dot.edge("d6", "d7", label="Yes")
    dot.edge("d6", "d8", label="No")

    dot.edge("d7", "good2", label="Yes")
    dot.edge("d7", "excellent1", label="No")

    dot.edge("d8", "excellent2", label="Yes")
    dot.edge("d8", "amazing", label="No")

    OUTPUT_DIR.mkdir(exist_ok=True)

    output_file = OUTPUT_DIR / "productivity_flowchart"

    dot.render(
        str(output_file),
        cleanup=True
    )

    print(f"Saved flowchart to {output_file}.png")

if __name__ == "__main__":
    build_flowchart()
