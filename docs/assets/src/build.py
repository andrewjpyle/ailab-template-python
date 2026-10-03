"""Build the README graphics for ailab-template-python.

Run from the repo root after vendoring the kit:

    uv run --with playwright --with pillow python docs/assets/src/render.py docs/assets/src docs/assets

Data-bearing graphics are built from committed captures in captures/ (never typed by hand).
Structural graphics carry a HOW IT WORKS footer. No machine-specific path appears here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import readme_kit as k  # noqa: E402

REPO = "ailab-template-python"
CAPTURES = HERE / "captures"


def load_results() -> tuple[dict, str]:
    """Real eval_results.json, loaded from its committed capture (cat of the file)."""
    cap = k.load_capture(CAPTURES / "eval_results.json")
    results = json.loads(cap["output"])
    run_date = cap["captured_at"][:10]
    return results, run_date


# ── 1. hero ──────────────────────────────────────────────────────────────────────────────────

def build_hero() -> str:
    wheel = k.wheel(
        ["install", "lint", "test", "eval", "demo", "scan"],
        center_top="MAKE", center_main="uv",
    )
    return k.hero(
        kicker="PYTHON AI-LAB TEMPLATE",
        title="A template where a number",
        accent="decides what ships",
        lede_html=(
            "Clone it and the loop is already real: an eval that fails CI on a regression, two "
            "swappable model seams, and a secret wall enforced twice."
        ),
        rules=[
            ("Eval gate, not a report",
             "A metric below its floor exits 1 and turns CI red, the way a failing test does."),
            ("Two Protocol seams",
             "A baseline, a local model and a hosted LLM are scored by exactly the same code."),
            ("A secret wall, enforced twice",
             "gitleaks and a fail-closed denylist, at the pre-push hook and again in CI."),
        ],
        pill="make install . test . eval . scan",
        right_html=wheel,
        footer_left=f"{REPO} . HOW IT WORKS",
    )


# ── 2. how it works (fixture -> protocol -> eval -> gate -> results) ────────────────────────────

def build_flow() -> str:
    y, h, w = 300, 150, 230
    xs = [56, 318, 580, 842, 1104]  # right edges: 286, 548, 810, 1072, 1334
    boxes = (
        k.box(xs[0], y, w, h, "FIXTURE",
              ["fixtures/*.jsonl", "data.load_jsonl", '{"text","label"} rows'])
        + k.box(xs[1], y, w, h, "CLASSIFIER PROTOCOL",
                ["predict(text) -> label", "keyword . majority", "llm-stub . your model"])
        + k.box(xs[2], y, w, h, "EVAL RUNNER",
                ["accuracy . macro-F1", "per-class P/R/F1", "confusion matrix"])
        + k.box(xs[3], y, w, h, "REGRESSION GATE",
                ["compare to the floors", "in eval_config.toml"])
        + k.box(xs[4], y, w, h, "RESULTS CONTRACT",
                ["eval_results.json", "schema_version 1", "CI uploads the artifact"], accent=True)
        + k.box(xs[3], 520, w, 92, "BELOW A FLOOR",
                ["exit 1 . CI turns red", "the merge is blocked"])
    )
    mid = y + h // 2  # 375
    arrows = [
        (286, mid, 316, mid),
        (548, mid, 578, mid),
        (810, mid, 840, mid),
        (1072, mid, 1102, mid),
        (xs[3] + w // 2, y + h, xs[3] + w // 2, 518, "regression", False, "right"),
    ]
    return k.flow(
        kicker="HOW IT WORKS",
        title_html=f"One dataset, one {k.em('number')}, one gate",
        subline="every stage is plain Python with zero core dependencies",
        boxes_html=boxes,
        arrow_specs=arrows,
        footer_left=f"{REPO} . HOW IT WORKS",
    )


# ── 3. anatomy of the real eval_results.json ────────────────────────────────────────────────────

def build_anatomy() -> str:
    r, run_date = load_results()
    m = r["metrics"]
    pc = r["per_class"]
    L = [
        ("h1", "eval_results.json"),
        ("i", "the versioned contract other tools read, built from a real run"),
        ("code", json.dumps({"schema_version": r["schema_version"], "lab": r["lab"]})[1:-1]),
        ("h2", "metrics"),
        ("b", f"accuracy {m['accuracy']}   macro_f1 {m['macro_f1']}   n {m['n']}"),
        ("code", f'"primary_metric": "{r["primary_metric"]}",  "threshold": {r["threshold"]}'),
        ("b", f"passed: {str(r['passed']).lower()}"),
        ("i", "true only when every configured floor is met"),
        ("h2", "per-class f1 (diagnostic, may change)"),
    ]
    for label, v in pc.items():
        L.append(("li", f"{label}: f1 {v['f1']}  (precision {v['precision']}, recall {v['recall']})"))
    L += [
        ("m", f"commit {r['commit'][:7]}   generated_at {r['generated_at']}"),
    ]
    notes = [
        (92, "schema_version pins the required keys; a breaking change bumps it"),
        (250, "the primary metric's floor is reported as threshold"),
        (300, "passed gates the build, not a chart someone can ignore"),
        (430, "per-class scores are extras and may change freely"),
    ]
    return k.anatomy(
        kicker="REAL RUN . KEYWORD BASELINE",
        doc_lines=L,
        notes=notes,
        footer_left=f"{REPO} . REAL RUN {run_date}",
    )


# ── 4. the two-layer secret wall ────────────────────────────────────────────────────────────────

def build_scan() -> str:
    boxes = (
        k.box(56, 230, 300, 110, "TRIGGER . LOCAL",
              ["pre-push git hook", "make hooks, once per clone"])
        + k.box(56, 390, 300, 110, "TRIGGER . CI",
                ["secret-scan job", "a required status check"])
        + k.box(470, 230, 400, 110, "LAYER 1 . GITLEAKS",
                [".gitleaks.toml: upstream + Doppler rules", "CI pins the release, verifies SHA-256"],
                accent=True)
        + k.box(470, 390, 400, 110, "LAYER 2 . DENYLIST",
                ["generic patterns committed (public)", "private patterns from AILAB_DENYLIST",
                 "no private patterns -> exit 2"],
                accent=True)
        + k.box(980, 300, 364, 130, "FAIL CLOSED",
                ["every tracked file AND full history", "a hit blocks the push or the CI check",
                 "a secret never reaches the remote"])
    )
    arrows = [
        (356, 285, 468, 285),
        (356, 445, 468, 445),
        (872, 285, 978, 330),
        (872, 445, 978, 400),
    ]
    return k.flow(
        kicker="SECRET WALL",
        title_html=f"Two layers, two gates, {k.em('fail closed')}",
        subline="both the pre-push hook and the required CI check run both layers",
        boxes_html=boxes,
        arrow_specs=arrows,
        footer_left=f"{REPO} . HOW IT WORKS",
    )


def main() -> int:
    pages = {
        "hero": build_hero(),
        "architecture": build_flow(),
        "anatomy": build_anatomy(),
        "secret-wall": build_scan(),
    }
    k.write_pages(HERE, pages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
