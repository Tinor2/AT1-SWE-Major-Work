"""
Generate a pipeline flowchart showing the core ML logic:
data ingestion → feature engineering → training → prediction.

Usage:
    python -m pomodoro.ml.pipeline_flowchart [--output flowchart]
"""

from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from graphviz import Digraph

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def build_pipeline_flowchart():
    dot = Digraph("ML_Pipeline", format="png")
    dot.attr(rankdir="TB", nodesep="0.18", ranksep="0.45", splines="ortho")
    dot.attr("edge", fontsize="9")
    dot.attr("node", fontsize="9")
    dot.attr(dpi="200")

    # ── Start ──────────────────────────────────────────────────────────
    dot.node("start", "Start", shape="oval", style="filled",
             fillcolor="#333", fontcolor="white", margin="0.2,0.1")

    # ── Data ingestion ─────────────────────────────────────────────────
    dot.node("query", "Query database for\nuser session data",
             shape="box", style="filled", fillcolor="#FFF3CD",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("start", "query")

    dot.node("compute", "Compute daily metrics\n(task rate, break rate,\nfocus time, consistency, …)",
             shape="box", style="filled", fillcolor="#FFF3CD",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("query", "compute")

    dot.node("vector", "Build feature vector\n(10 values per day)",
             shape="box", style="filled", fillcolor="#FFF3CD",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("compute", "vector")

    # ── Decision: enough data? ─────────────────────────────────────────
    dot.node("enough", "Enough completed\nsessions?", shape="diamond",
             style="filled", fillcolor="#E8E8E8", penwidth="0.6",
             margin="0.1,0.06")
    dot.edge("vector", "enough")

    dot.node("synth", "Generate synthetic\nsample data",
             shape="box", style="filled", fillcolor="#F8D7DA",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("enough", "synth", xlabel="No\n(corrupted / missing)", fontsize="8")

    # ── Merge point after enough data check ────────────────────────────
    dot.node("merge", "Prepare training data\n(real or synthetic)",
             shape="box", style="filled", fillcolor="#D4EDDA",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("enough", "merge", xlabel="Yes", fontsize="8")
    dot.edge("synth", "merge")

    # ── Train decision tree (plain process) ──────────────────────────
    dot.node("train", "Train decision tree",
             shape="box", style="filled", fillcolor="#CCE5FF",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("merge", "train")

    # ── Save model ─────────────────────────────────────────────────────
    dot.node("save", "Save trained model\n(with integrity check)",
             shape="box", style="filled", fillcolor="#CCE5FF",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("train", "save")

    # ── Decision: model or fallback ────────────────────────────────────
    dot.node("model_exists", "Model available\nfor this user?", shape="diamond",
             style="filled", fillcolor="#E8E8E8", penwidth="0.6",
             margin="0.1,0.06")
    dot.edge("save", "model_exists")

    # ── Subroutine: predict via decision tree ──────────────────────────
    # HTML table with thin border-only cells on each side = ‖ ‖ symbol.
    dot.node("use_model", """<
<TABLE BORDER="1" CELLSPACING="0" CELLPADDING="3" BGCOLOR="#E2CCFF">
  <TR>
    <TD WIDTH="4"></TD>
    <TD WIDTH="4"></TD>
    <TD>Use model to predict band<BR/>(see tree structure diagram)</TD>
    <TD WIDTH="4"></TD>
    <TD WIDTH="4"></TD>
  </TR>
</TABLE>>""", shape="none")
    dot.node("use_formula", "Use formula\n(fallback score)",
             shape="box", style="filled", fillcolor="#F8D7DA",
             penwidth="0.6", margin="0.15,0.08")

    dot.edge("model_exists", "use_model", xlabel="Yes", fontsize="8")
    dot.edge("model_exists", "use_formula", xlabel="No \n(Corrupted/deleted\nuser data)", fontsize="8")

    # ── Converge to output ────────────────────────────────────────────
    dot.node("display", "Display band +\nfeedback to user",
             shape="box", style="filled", fillcolor="#D4EDDA",
             penwidth="0.6", margin="0.15,0.08")
    dot.edge("use_model", "display")
    dot.edge("use_formula", "display")

    # ── End ────────────────────────────────────────────────────────────
    dot.node("end", "End", shape="oval", style="filled",
             fillcolor="#333", fontcolor="white", margin="0.2,0.1")
    dot.edge("display", "end")

    # ── Render ─────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "pipeline_flowchart"
    dot.render(str(output_file), cleanup=True)
    print(f"Saved to {output_file}.png")


def main():
    parser = argparse.ArgumentParser(description="Generate ML pipeline flowchart")
    parser.add_argument("--output", type=str, default="pipeline_flowchart",
                        help="Output filename (without extension)")
    args = parser.parse_args()
    build_pipeline_flowchart()


if __name__ == "__main__":
    main()
