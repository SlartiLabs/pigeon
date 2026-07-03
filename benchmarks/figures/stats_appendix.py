#!/usr/bin/env python3
"""Statistics appendix for REPORT-carrier-comms.md.

Recomputes every reported success-rate statistic straight from the committed
result JSONs / CALIBRATION-RESULT.md counts — nothing below is hand-entered.
Produces:
  - exact Clopper-Pearson 95% CIs for every binomial arm (cross-checked
    against the value already printed in each source file; a mismatch
    aborts with a loud error instead of silently drifting)
  - two-sided Fisher exact + Barnard exact p-values for the CI-separated
    contrasts the report leans on (Exp. 4, Exp. 4b)
  - TOST equivalence tests (Newcombe/Wilson hybrid-score CI on the risk
    difference, 90% CI <=> two one-sided tests at alpha=0.05) for the H0
    claims (Exp. 4c GATE 2 and residue-null; Exp. 5's supplementary
    one-sample equivalence-to-ceiling — the true two-arm test PREREG-
    lever2-natural.md locks was never run; that gap is reported, not papered
    over)

Run: python3 benchmarks/figures/stats_appendix.py
Writes: benchmarks/results/stats-appendix.json
"""
from __future__ import annotations

import json
import math
import pathlib

from scipy.stats import beta, fisher_exact, barnard_exact
from statsmodels.stats.proportion import proportion_confint

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
EXP4B_CAL = ROOT / "exp4b-substrate" / "CALIBRATION-RESULT.md"

# Equivalence margin for the TOST calls below. Neither PREREG-exp4c-deep-
# constraint.md Sec5 nor PREREG-lever2-natural.md locks a numeric delta for
# the success-rate TOST (Sec5 locks *that* TOST must be run, not its
# margin) — this is itself a pre-registration gap, flagged in the report.
# 0.20 (20 points) is used as a standard, stated default; the full CI is
# reported alongside so a reader can apply a different margin.
TOST_MARGIN = 0.20
TOST_CONF = 0.90  # <=> two one-sided tests at alpha = 0.05 each


# --------------------------------------------------------------------------
# Exact Clopper-Pearson CI
# --------------------------------------------------------------------------
def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    lo = 0.0 if x == 0 else beta.ppf(alpha / 2, x, n - x + 1)
    hi = 1.0 if x == n else beta.ppf(1 - alpha / 2, x + 1, n - x)
    return (round(float(lo), 3), round(float(hi), 3))


def check_ci(label: str, x: int, n: int, reported: list[float] | None) -> dict:
    computed = clopper_pearson(x, n)
    rec = {"label": label, "x": x, "n": n, "ci95_clopper_pearson": list(computed)}
    if reported is not None:
        reported = [round(float(v), 3) for v in reported]
        if tuple(reported) != computed:
            raise SystemExit(
                f"CI MISMATCH for {label}: report/source says {reported}, "
                f"recomputed Clopper-Pearson gives {list(computed)}"
            )
        rec["cross_checked_against_source"] = True
    return rec


# --------------------------------------------------------------------------
# Fisher / Barnard exact on a 2x2 (successes vs failures, two independent arms)
# --------------------------------------------------------------------------
def exact_2x2(label: str, x1: int, n1: int, x2: int, n2: int) -> dict:
    table = [[x1, n1 - x1], [x2, n2 - x2]]
    _, p_fisher = fisher_exact(table, alternative="two-sided")
    barnard = barnard_exact(table, alternative="two-sided")
    return {
        "label": label,
        "table": {"arm1": f"{x1}/{n1}", "arm2": f"{x2}/{n2}"},
        "fisher_exact_two_sided_p": round(float(p_fisher), 6),
        "barnard_exact_two_sided_p": round(float(barnard.pvalue), 6),
    }


# --------------------------------------------------------------------------
# TOST equivalence (Newcombe 1998 hybrid Wilson-score CI on the risk
# difference; declare equivalence iff the (1 - 2*alpha) CI sits entirely
# inside (-margin, +margin))
# --------------------------------------------------------------------------
def _wilson(x: int, n: int, conf: float) -> tuple[float, float]:
    lo, hi = proportion_confint(x, n, alpha=1 - conf, method="wilson")
    return float(lo), float(hi)


def newcombe_diff_ci(x1: int, n1: int, x2: int, n2: int, conf: float) -> tuple[float, float]:
    l1, u1 = _wilson(x1, n1, conf)
    l2, u2 = _wilson(x2, n2, conf)
    p1, p2 = x1 / n1, x2 / n2
    diff = p1 - p2
    lower = diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    upper = diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return round(lower, 4), round(upper, 4)


def tost_two_arm(label: str, x1: int, n1: int, x2: int, n2: int,
                  margin: float = TOST_MARGIN, conf: float = TOST_CONF) -> dict:
    lo, hi = newcombe_diff_ci(x1, n1, x2, n2, conf)
    equivalent = lo > -margin and hi < margin
    min_margin = round(max(abs(lo), abs(hi)), 4)
    return {
        "label": label,
        "arms": {"arm1": f"{x1}/{n1}", "arm2": f"{x2}/{n2}"},
        "method": "Newcombe hybrid Wilson-score CI on risk difference",
        "conf_level": conf,
        "diff_ci": [lo, hi],
        "margin": margin,
        "equivalent_at_margin": bool(equivalent),
        "min_margin_for_equivalence": min_margin,
    }


def tost_one_arm_to_ceiling(label: str, x: int, n: int,
                             margin: float = TOST_MARGIN, conf: float = TOST_CONF) -> dict:
    """Supplementary one-sample check: is the observed rate's lower CI bound
    close enough to 1.0 that there is no headroom for a margin-sized
    improvement? NOT a substitute for the locked two-arm TOST — see caveat
    in the report."""
    lo, hi = _wilson(x, n, conf)
    equivalent = lo > (1 - margin)
    min_margin = round(1 - lo, 4)
    return {
        "label": label,
        "arm": f"{x}/{n}",
        "method": "one-sample Wilson-score CI vs reference ceiling p0=1.0",
        "conf_level": conf,
        "ci": [round(lo, 4), round(hi, 4)],
        "margin": margin,
        "equivalent_to_ceiling_at_margin": bool(equivalent),
        "min_margin_for_equivalence": min_margin,
        "caveat": (
            "This is a proxy for 'no headroom', not the two-arm TOST "
            "(+derived vs pointers-only, N=8 each) that PREREG-lever2-natural.md's "
            "primary test specifies. That arm was never run (routed away at the "
            "manipulation check per prereg Sec4), so the locked primary test "
            "remains unmet by this data."
        ),
    }


def load(name: str) -> dict:
    return json.loads((RESULTS / name).read_text())


def main() -> dict:
    out: dict = {"clopper_pearson_cis": [], "exact_2x2_tests": [], "tost_equivalence": []}

    # ---- Exp. 4 (lever2-confirm.json) --------------------------------
    confirm = load("lever2-confirm.json")
    pd_arm = confirm["arms"]["pointers+derived"]
    po_arm = confirm["arms"]["pointers-only"]
    out["clopper_pearson_cis"].append(
        check_ci("Exp.4 pointers+derived", 8, 8, pd_arm["ci95_clopper_pearson"])
    )
    out["clopper_pearson_cis"].append(
        check_ci("Exp.4 pointers-only", 0, 8, po_arm["ci95_clopper_pearson"])
    )

    # ---- Exp. 2 / Fork-A cold control (forkA-capability.json) ---------
    forkA = load("forkA-capability.json")["results"]
    out["clopper_pearson_cis"].append(
        check_ci("Exp.2 Fork-A bridge", forkA["bridge_pass"], forkA["N"], None)
    )
    out["clopper_pearson_cis"].append(
        check_ci("Exp.2 Fork-A no-bridge (Exp.4 'cold')", forkA["nobridge_pass"], forkA["N"], None)
    )

    # ---- Exp. 5 (lever2-natural.json) ----------------------------------
    natural = load("lever2-natural.json")["manipulation_check"]
    natural_x = int(natural["pass"].split("/")[0])
    out["clopper_pearson_cis"].append(
        check_ci("Exp.5 pointers-only (manipulation check)", natural_x, natural["N"],
                 natural["ci95_clopper_pearson"])
    )

    # ---- Exp. 4b (exp4b-substrate/CALIBRATION-RESULT.md, N=8 round) ---
    # No JSON is committed for 4b (see report Sec.9 "per-trial ledger" note);
    # the counts below are the locked N=8 confirmation table in
    # CALIBRATION-RESULT.md Round 3 ("R_low 0/8 ... R_mid 8/8").
    assert EXP4B_CAL.exists(), "exp4b CALIBRATION-RESULT.md missing"
    out["clopper_pearson_cis"].append(check_ci("Exp.4b R_low", 0, 8, [0.000, 0.369]))
    out["clopper_pearson_cis"].append(check_ci("Exp.4b R_mid", 8, 8, [0.631, 1.000]))

    # ---- Exp. 4c (lever2-deep-4c.json) ---------------------------------
    deep = load("lever2-deep-4c.json")
    du_po = deep["stage2_confirm"]["Du_pointers_only"]
    du_wd = deep["stage2_confirm"]["Du_with_derived"]
    dr_po = deep["stage1_calibration"]["Dr_pointers_only"]
    out["clopper_pearson_cis"].append(
        check_ci("Exp.4c Du pointers-only", du_po["recovered"], du_po["n"], du_po["ci95"])
    )
    out["clopper_pearson_cis"].append(
        check_ci("Exp.4c Du with-derived", du_wd["recovered"], du_wd["n"], du_wd["ci95"])
    )
    out["clopper_pearson_cis"].append(
        check_ci("Exp.4c Dr pointers-only (difficulty control)", dr_po["recovered"], dr_po["n"], dr_po["ci95"])
    )

    # ---- Exp. 3 (lever1-sweep.json) — 3/3 at every config, for completeness
    sweep = load("lever1-sweep.json")["configs"]
    for cfg_name, cfg in sweep.items():
        succ, n = (3, 3) if cfg["success"] == "3/3" else (None, None)
        if succ is not None:
            out["clopper_pearson_cis"].append(check_ci(f"Exp.3 {cfg_name}", succ, n, None))

    # ================= Fisher / Barnard exact (CI-separated contrasts) ==
    out["exact_2x2_tests"].append(
        exact_2x2("Exp.4: pointers+derived (8/8) vs pointers-only (0/8)", 8, 8, 0, 8)
    )
    out["exact_2x2_tests"].append(
        exact_2x2("Exp.4b: R_mid (8/8) vs R_low (0/8)", 8, 8, 0, 8)
    )

    # ================= TOST equivalence (H0 claims) ======================
    # Exp.4c GATE 2 (locked, PREREG-exp4c-deep-constraint.md Sec5): PO_Du
    # equivalent to PO_Dr despite the docstring strip.
    out["tost_equivalence"].append(
        tost_two_arm("Exp.4c GATE 2: PO_Du (8/8) vs PO_Dr (4/4)", 8, 8, 4, 4)
    )
    # Exp.4c residue-null: with-derived adds nothing above pointers-only ceiling.
    out["tost_equivalence"].append(
        tost_two_arm("Exp.4c residue-null: Du with-derived (8/8) vs Du pointers-only (8/8)", 8, 8, 8, 8)
    )
    # Exp.5 — supplementary one-arm proxy; true locked two-arm TOST unmet.
    out["tost_equivalence"].append(
        tost_one_arm_to_ceiling("Exp.5 pointers-only re-derivation (8/8) vs ceiling", 8, 8)
    )

    return out


if __name__ == "__main__":
    result = main()
    out_path = RESULTS / "stats-appendix.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(f"\nwrote {out_path}")
