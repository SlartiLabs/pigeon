#!/usr/bin/env python3
"""Stage 2 cross-model figures — the two-sided law, replicated on Gemini (agy).

Renders, in the carrier-comms house style (monochrome ink + two restrained
accents), the four GATE-A cells of the two-sided law with a receiver swapped to
agy/Gemini:

    fig_s2_gateA.png   — necessity vs recoverability x pointers-only vs
                         with-derived, pass rates with exact Clopper-Pearson 95%
                         CIs. The necessity side should SEPARATE (residue needed),
                         the recoverability side should stay at CEILING both arms
                         (residue not needed) — the boundary transferring to a
                         second, architecturally different model.
    fig_s2_tokens.png  — the FAIR cross-model metric: canonical (o200k_base)
                         token volume per hop, since agy emits no native usage and
                         USD is confounded across two providers' pricing.

Data is read from clean result CSVs (default ~/stage2-clean + the committed
recoverability pointers-only ledger). Cells with no data are drawn as "pending"
rather than invented. Run with the miniconda python (scipy/matplotlib):

    python3 docs/benchmarks/figures/make_stage2_figures.py [--data DIR]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

# --- shared style (verbatim from make_carrier_comms_figures.py) --------------
INK = "#1A1A1A"
MUTE = "#8A8A8A"
FAINT = "#D6D6D6"
DERIVED = "#B5341F"   # with-derived / irreducible residue
BASE = "#3C6E9E"      # pointers-only / re-derivable
GOOD = "#2E7D5B"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK,
    "ytick.color": INK, "axes.linewidth": 1.0, "savefig.dpi": 300, "figure.dpi": 150,
})
HERE = pathlib.Path(__file__).resolve().parent
FIGDIR = HERE


def _despine(ax, keep=("left", "bottom")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if x == 0 else beta.ppf(alpha / 2, x, n - x + 1)
    hi = 1.0 if x == n else beta.ppf(1 - alpha / 2, x + 1, n - x)
    return (float(lo), float(hi))


def read_arm(path: pathlib.Path) -> dict | None:
    """Return {x, n, rows} from a results.csv (x = accept_rc==0 count)."""
    if not path or not path.is_file():
        return None
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows = [r for r in rows if r.get("accept_rc") not in (None, "")]
    if not rows:
        return None
    x = sum(1 for r in rows if str(r["accept_rc"]).strip() == "0")
    return {"x": x, "n": len(rows), "rows": rows}


def _committed_pointers_only(p: pathlib.Path) -> dict | None:
    """The recoverability pointers-only ledger has leading '#' comment lines."""
    if not p.is_file():
        return None
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("#")]
    rows = list(csv.DictReader(lines))
    rows = [r for r in rows if r.get("accept_rc") not in (None, "")]
    if not rows:
        return None
    x = sum(1 for r in rows if str(r["accept_rc"]).strip() == "0")
    return {"x": x, "n": len(rows), "rows": rows}


def load_cells(data: pathlib.Path) -> dict:
    """Pick the CLEANEST available config per cell and label it. Necessity uses
    the controlled all-agy pair (PO 0/8 vs WD 7/8, same config); recoverability
    uses the committed pointers-only 12/12 + the sonnet->agy with-derived arm,
    which is flagged `confound` because agy no-op/timeout dominated its misses."""
    home = pathlib.Path.home()
    def tag(c, cfg, confound=False):
        if c:
            c["cfg"] = cfg
            c["confound"] = confound
        return c
    return {
        ("necessity", "pointers-only"): tag(
            read_arm(data / "nec-po-allagy" / "results.csv"), "all-agy"),
        ("necessity", "with-derived"): tag(
            read_arm(home / "stage2" / "nec-wd-allagy" / "results.csv"), "all-agy"),
        ("recoverability", "pointers-only"): tag(_committed_pointers_only(
            HERE.parent / "substrates" / "exp5-natural"
            / "RESULTS-stage2-agy-pointers-only-N12.csv"), "sonnet→agy"),
        ("recoverability", "with-derived"): tag(
            read_arm(data / "exp5-with-derived" / "results.csv"), "sonnet→agy",
            confound=True),
    }


def fig_gate_a(cells: dict) -> None:
    sides = [("necessity", "Necessity side  (Fork-A: off-disk contract, 0%-recoverable)"),
             ("recoverability", "Recoverability side  (Exp-5: in-code cue, recoverable)")]
    arms = [("pointers-only", BASE), ("with-derived", DERIVED)]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.0))
    for ax, (side, title) in zip(axes, sides):
        xs = np.arange(len(arms))
        for i, (arm, color) in enumerate(arms):
            c = cells.get((side, arm))
            if not c:
                ax.text(i, 0.5, "pending\nclean re-run", ha="center", va="center",
                        color=MUTE, fontsize=10, style="italic")
                ax.bar(i, 0, width=0.6)
                continue
            p = c["x"] / c["n"]
            lo, hi = clopper_pearson(c["x"], c["n"])
            confound = c.get("confound")
            ax.bar(i, p, width=0.6, color=color, edgecolor=INK, linewidth=1.1,
                   zorder=3, alpha=0.45 if confound else 1.0,
                   hatch="///" if confound else None)
            ax.errorbar(i, p, yerr=[[p - lo], [hi - p]], fmt="none", ecolor=INK,
                        elinewidth=1.4, capsize=6, capthick=1.4, zorder=4)
            ax.text(i, min(hi + 0.05, 1.03), f"{c['x']}/{c['n']}", ha="center",
                    va="bottom", fontsize=11, fontweight="bold", color=INK)
            ax.text(i, -0.075, c.get("cfg", ""), ha="center", va="top",
                    fontsize=8, color=MUTE)
            if confound:
                ax.text(i, 0.14, "agy no-op /\ntimeout\nconfounded", ha="center",
                        va="center", fontsize=7.5, color=MUTE, style="italic")
        ax.set_xticks(xs)
        ax.set_xticklabels([a for a, _ in arms])
        ax.set_ylim(0, 1.15); ax.set_yticks(np.arange(0, 1.01, 0.25))
        ax.set_ylabel("pass rate (held-out grader)" if side == "necessity" else "")
        ax.set_title(title, fontsize=10.5, color=INK, pad=10)
        ax.axhline(1.0, color=FAINT, lw=1, zorder=1)
        _despine(ax)
    fig.suptitle("Stage 2 — the two-sided law, replicated on Gemini (agy as receiver)",
                 fontsize=13, fontweight="bold", y=0.99)
    fig.text(0.5, 0.035,
             "Necessity separates on Gemini (all-agy 0/8 → 7/8, Fisher p ≈ 0.0014); recoverable side recovers (12/12).",
             ha="center", fontsize=8.5, color=INK)
    fig.text(0.5, 0.010,
             "Hatched bar = agy no-op / timeout confounded — a GATE-C execution gap, not a residue effect.",
             ha="center", fontsize=8, color=MUTE, style="italic")
    fig.tight_layout(rect=(0, 0.065, 1, 0.955))
    out = FIGDIR / "fig_s2_gateA.png"
    fig.savefig(out); plt.close(fig)
    print("wrote", out)


def fig_tokens(data: pathlib.Path) -> None:
    """Canonical (o200k_base) token volume per hop — the fair cross-model unit."""
    recs = []
    for jf in glob.glob(str(data / "*" / "canon.json")):
        recs.extend(json.load(open(jf)).get("rows", []))
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    if not recs:
        ax.text(0.5, 0.5, "canonical recount pending\n(run canonical-retokenize.py --json on clean trials)",
                ha="center", va="center", color=MUTE, style="italic", fontsize=11)
        ax.axis("off")
    else:
        by_runner: dict[str, list[int]] = {}
        for r in recs:
            if r.get("canon_total"):
                by_runner.setdefault(r.get("runner", "?"), []).append(r["canon_total"])
        runners = sorted(by_runner)
        means = [float(np.mean(by_runner[k])) for k in runners]
        colors = [DERIVED if "agy" in k else BASE for k in runners]
        ax.bar(runners, means, color=colors, edgecolor=INK, linewidth=1.1)
        ax.set_ylabel("mean canonical tokens / hop (o200k_base)")
        ax.set_title("Fair cross-model volume — canonical recount (agy emits no native usage)",
                     fontsize=10.5)
        _despine(ax)
    fig.tight_layout()
    out = FIGDIR / "fig_s2_tokens.png"
    fig.savefig(out); plt.close(fig)
    print("wrote", out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=pathlib.Path,
                    default=pathlib.Path.home() / "stage2-clean")
    args = ap.parse_args()
    cells = load_cells(args.data)
    print("cells:", {f"{s}/{a}": (c and f"{c['x']}/{c['n']}") for (s, a), c in cells.items()})
    fig_gate_a(cells)
    fig_tokens(args.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
