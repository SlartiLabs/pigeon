#!/usr/bin/env python3
"""Carrier-comms report figures (new — Lever 1/2 program).

Conceptual figures (1, 2, 7-frame) need no run data. Data figures (8, 9) read the
recorded screen/confirm results. Run: python3 benchmarks/figures/make_carrier_comms_figures.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pathlib

OUT = pathlib.Path(__file__).parent

# --- shared style: high data-ink, monochrome ink + two restrained accents ----
INK = "#1A1A1A"
MUTE = "#8A8A8A"
FAINT = "#D6D6D6"
DERIVED = "#B5341F"   # irreducible residue (the one thing worth carrying)
BASE = "#3C6E9E"      # baseline / re-derivable
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": INK,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.linewidth": 1.0,
    "savefig.dpi": 200,
    "figure.dpi": 120,
})


def _despine(ax, keep=("left", "bottom")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


# =====================================================================
# FIGURE 1 — System schematic
# =====================================================================
def fig1_schematic():
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    ax.set_xlim(0, 100); ax.set_ylim(0, 106); ax.axis("off")

    def box(x, y, w, h, label, sub="", fc="white", ec=INK, lw=1.6, fs=11):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0.6,rounding_size=2.4",
                     fc=fc, ec=ec, lw=lw, mutation_aspect=0.9))
        ax.text(x + w/2, y + h/2 + (2.2 if sub else 0), label,
                ha="center", va="center", fontsize=fs, fontweight="bold")
        if sub:
            ax.text(x + w/2, y + h/2 - 3.0, sub, ha="center", va="center",
                    fontsize=8.5, color=MUTE)

    # --- carriers (CLI agents) across the top ---
    carriers = [("claude", "architect"), ("opencode", "implementer"), ("agy", "reviewer")]
    cw, ch, cy = 22, 13, 80
    cx = [8, 39, 70]
    for (name, role), x in zip(carriers, cx):
        box(x, cy, cw, ch, name, f"CLI agent · {role}")

    # --- handoff channel between carriers (pointers + derived residue) ---
    for x0, x1 in [(cx[0]+cw, cx[1]), (cx[1]+cw, cx[2])]:
        ax.add_patch(FancyArrowPatch((x0+0.5, cy+ch/2), (x1-0.5, cy+ch/2),
                     arrowstyle="-|>", mutation_scale=16, lw=2.2, color=INK,
                     shrinkA=0, shrinkB=0))
        ax.text((x0+x1)/2, cy+ch/2+2.4, "handoff", ha="center", va="bottom",
                fontsize=7.6, color=INK)
    # channel annotation: the two buckets
    ax.add_patch(FancyBboxPatch((30.5, cy-13.5), 39, 9.2,
                 boxstyle="round,pad=0.4,rounding_size=1.6",
                 fc="#FBF4F2", ec=DERIVED, lw=1.3))
    ax.text(50, cy-6.4, "pointers  +  derived residue", ha="center", va="center",
            fontsize=9.6, fontweight="bold", color=DERIVED)
    ax.text(50, cy-9.8, "carry only what can't be re-derived", ha="center",
            va="center", fontsize=8.3, color=MUTE)
    ax.add_patch(FancyArrowPatch((50, cy-4.0), (50, cy-0.5),
                 arrowstyle="-|>", mutation_scale=12, lw=1.4, color=DERIVED))

    # --- shared working tree band (re-derivable: pack) ---
    twy, twh = 36, 12
    ax.add_patch(FancyBboxPatch((6, twy), 88, twh,
                 boxstyle="round,pad=0.6,rounding_size=2.4",
                 fc="#F4F7FA", ec=BASE, lw=1.6))
    ax.text(50, twy+twh-3.4, "shared working tree", ha="center",
            fontsize=11, fontweight="bold", color=BASE)
    ax.text(50, twy+3.6, "any carrier can read / grep — re-reading code is cheap",
            ha="center", fontsize=8.8, color=MUTE)
    # dashed "point at it" lines from carriers to the tree
    for x in cx:
        ax.add_patch(FancyArrowPatch((x+cw/2, cy-0.3), (x+cw/2, twy+twh+0.3),
                     arrowstyle="-", lw=1.1, color=BASE, ls=(0, (4, 3)), alpha=0.8))
    ax.text(94.4, twy+twh/2, "pack\n(re-derivable)", ha="right", va="center",
            fontsize=8.4, color=BASE, rotation=0)

    # --- durable board (.pigeon/memory) ---
    bdy, bdh = 16, 11
    ax.add_patch(FancyBboxPatch((6, bdy), 88, bdh,
                 boxstyle="round,pad=0.6,rounding_size=2.4",
                 fc="white", ec=INK, lw=1.6))
    ax.text(50, bdy+bdh-3.2, ".pigeon/memory  —  durable board", ha="center",
            fontsize=10.5, fontweight="bold")
    ax.text(50, bdy+3.2, "handoffs · metrics · distilled decisions — persists across sessions",
            ha="center", fontsize=8.6, color=MUTE)
    ax.add_patch(FancyArrowPatch((20, twy-0.3), (20, bdy+bdh+0.3),
                 arrowstyle="-|>", mutation_scale=11, lw=1.2, color=INK, alpha=0.7))
    ax.add_patch(FancyArrowPatch((80, bdy+bdh+0.3), (80, twy-0.3),
                 arrowstyle="-|>", mutation_scale=11, lw=1.2, color=INK, alpha=0.7))
    ax.text(20.7, (twy+bdy+bdh)/2, "append", ha="left", va="center", fontsize=7.8, color=MUTE)
    ax.text(79.3, (twy+bdy+bdh)/2, "resolve", ha="right", va="center", fontsize=7.8, color=MUTE)

    # --- the channel/board split note ---
    ax.text(50, 6.5,
            "channel = transient, per-spawn (Lever 1 compresses it)      "
            "board = durable, queryable",
            ha="center", fontsize=8.6, color=INK)

    # --- title + subtitle (own headroom above the carrier boxes at y=93) ---
    ax.text(50, 104.5, "Figure 1 — Carrier-comms system schematic",
            ha="center", va="center", fontsize=13.5, fontweight="bold")
    ax.text(50, 99.0, "carriers are separate processes with no shared memory — "
            "the contract is the filesystem, not anyone's context window",
            ha="center", va="center", fontsize=8.8, style="italic", color=MUTE)
    fig.tight_layout()
    fig.savefig(OUT / "fig5_system_schematic.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =====================================================================
# FIGURE 2 — The two ceilings
# =====================================================================
def fig2_ceilings():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.4))

    # --- Left: overhead amortization -> parity from above ---
    x = np.linspace(0.4, 10, 400)
    overhead = 8 + 70 * np.exp(-0.62 * x)   # % over baseline, decaying to ~parity
    axL.plot(x, overhead, color=DERIVED, lw=2.6)
    axL.axhline(0, color=INK, lw=1.0)
    axL.axhline(8, color=MUTE, ls=(0, (5, 3)), lw=1.3)
    axL.text(9.8, 11.5, "parity floor", ha="right", fontsize=9, color=MUTE)
    # observed anchors
    axL.scatter([1.1, 6.6], [52, 8.1], s=46, color=INK, zorder=5)
    axL.annotate("cookiecutter\n+46–59%", (1.1, 52), (2.0, 60),
                 fontsize=8.6, color=INK, ha="left",
                 arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.9))
    axL.annotate("marshmallow\n+8.1%", (6.6, 8.1), (5.0, 26),
                 fontsize=8.6, color=INK, ha="left",
                 arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.9))
    axL.set_xlabel("task size  (work tokens →)")
    axL.set_ylabel("coordination overhead  (% over baseline)")
    axL.set_title("Cost ≈ Σ work + N·overhead\noverhead amortizes, never crosses to savings",
                  fontsize=10.5)
    axL.set_ylim(-4, 78); axL.set_xticks([])
    _despine(axL)

    # --- Right: Lever-1 rate-distortion U-curve ---
    c = np.linspace(0.6, 10, 400)           # channel tokens (compression: less <- -> more)
    cost = 0.9 + 1.7*np.exp(-1.3*(c-0.6)) + 0.075*(c-0.6)**2   # U: re-derive tax + overhead
    knee_i = int(np.argmin(cost))
    axR.plot(c, cost, color=INK, lw=2.6)
    axR.scatter([c[knee_i]], [cost[knee_i]], s=70, color=DERIVED, zorder=6)
    axR.annotate("knee\n(min channel that\nholds success)", (c[knee_i], cost[knee_i]),
                 (c[knee_i]+1.6, cost[knee_i]+0.9), fontsize=8.6, color=DERIVED, ha="left",
                 arrowprops=dict(arrowstyle="-|>", color=DERIVED, lw=1.2))
    axR.axhspan(cost[knee_i], cost[knee_i]+0.18, color=FAINT, alpha=0.7)
    axR.text(9.8, cost[knee_i]+0.30, "equivalence margin", ha="right", fontsize=8.2, color=MUTE)
    # regions
    axR.text(1.2, 3.6, "too terse →\nreceiver re-derives,\nre-explores", fontsize=8.0,
             color=MUTE, ha="left", va="top")
    axR.text(9.7, 3.6, "← bloated\nchannel\n(N·overhead)", fontsize=8.0,
             color=MUTE, ha="right", va="top")
    axR.set_xlabel("channel tokens per spawn  (compression ←   → verbosity)")
    axR.set_ylabel("receiver total cost  (USD-weighted)")
    axR.set_title("Lever-1 rate–distortion U-curve\nminimize channel s.t. success held — stop at the knee",
                  fontsize=10.5)
    axR.set_ylim(0.6, 3.8); axR.set_xticks([])
    _despine(axR)

    fig.suptitle("Figure 2 — The two ceilings", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "fig6_two_ceilings.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =====================================================================
# FIGURE 7 — Lever-1 rate-distortion frontier (framework; Phase-3 pending)
# =====================================================================
def fig7_frontier():
    # Real sweep data (marshmallow slug, N=3/config). channel = pack+handoff+scaffold.
    ch =   [4659, 6092, 8706]            # mean channel tokens (pack 1k, 2k, 4k)
    succ = [1.0, 1.0, 1.0]               # held-out success (3/3 at every config)
    cost = [0.855, 1.006, 1.123]         # mean measured USD
    labels = ["pack 1k", "pack 2k", "pack 4k (default)"]

    fig, ax = plt.subplots(figsize=(7.4, 4.7))
    ax2 = ax.twinx()
    # success (held at 1.0 across the whole range)
    ax.plot(ch, succ, "-o", color=DERIVED, lw=2.2, ms=8, zorder=6, label="held-out success")
    # cost (rises with channel)
    ax2.plot(ch, cost, "--D", color=BASE, lw=2.0, ms=7, mfc="white", zorder=6)
    for x, c, lb in zip(ch, cost, labels):
        ax2.annotate(lb, (x, c), (x, c+0.07), fontsize=8.0, color=BASE, ha="center")
    # the tested window is entirely on the over-provisioned (right) arm; the
    # too-terse left arm (where success breaks) is below 1k pack and UNTESTED.
    # Do NOT mark a knee — it was inferred, not measured.
    ax.scatter([ch[0]], [1.0], s=150, facecolor="none", edgecolor=DERIVED, lw=2.2, zorder=7)
    ax.annotate("smallest tested (pack 1k):\nsuccess still 3/3 →\ndefault is over-provisioned",
                (ch[0], 1.0), (ch[0]+700, 0.62), fontsize=8.4, color=DERIVED, ha="left",
                arrowprops=dict(arrowstyle="-|>", color=DERIVED, lw=1.2))
    ax.axvspan(3800, ch[0], color=FAINT, alpha=0.55)
    ax.text(3860, 0.30, "left arm /​ knee\nlive below 1k pack\n— UNTESTED",
            ha="left", fontsize=7.8, color=MUTE)
    ax.set_xlabel("channel tokens per spawn  (pack + handoff + scaffold)")
    ax.set_ylabel("held-out success rate", color=DERIVED)
    ax2.set_ylabel("mean net cost per task  (USD, measured)", color=BASE)
    ax.set_ylim(0, 1.12); ax2.set_ylim(0, 1.5); ax.set_xlim(3800, 9400)
    ax.tick_params(axis="y", colors=DERIVED); ax2.tick_params(axis="y", colors=BASE)
    ax.spines["top"].set_visible(False); ax2.spines["top"].set_visible(False)
    ax.set_title("Figure 7 — Lever-1: tested window is all over-provisioned\n"
                 "success holds 3/3 across [1k,4k] pack; the knee is below 1k (untested)",
                 fontsize=11.5, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig7_lever1_frontier.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =====================================================================
# FIGURE 8 — Lever-2 three-arm comparison (the result)
# =====================================================================
def fig8_three_arm():
    # arms: cold (Fork-A cross-model no-bridge), pointers-only (same-model null),
    # pointers+derived (same-model). Clopper-Pearson 95% CIs.
    arms = ["cold\n(cross-model,\nno bridge)", "pointers-only\n(same-model,\nnull)",
            "pointers + derived\n(same-model,\nresidue carried)"]
    succ = [0/5, 0/8, 8/8]
    n =    [5, 8, 8]
    # exact 95% CIs (Clopper-Pearson)
    ci_lo = [0.0, 0.0, 0.631]
    ci_hi = [0.522, 0.369, 1.0]
    cost = [None, 0.436, 0.417]   # mean USD over N=8 (cold arm cost not comparable substrate)
    colors = [MUTE, BASE, DERIVED]

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.6),
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    x = np.arange(len(arms))
    # panel A: success rate + CI
    for i in range(len(arms)):
        axA.bar(x[i], succ[i], width=0.62, color=colors[i], zorder=3)
        axA.plot([x[i], x[i]], [ci_lo[i], ci_hi[i]], color=INK, lw=1.6, zorder=5)
        axA.plot([x[i]-0.07, x[i]+0.07], [ci_lo[i]]*2, color=INK, lw=1.6, zorder=5)
        axA.plot([x[i]-0.07, x[i]+0.07], [ci_hi[i]]*2, color=INK, lw=1.6, zorder=5)
        axA.text(x[i], 1.05, f"{int(succ[i]*n[i])}/{n[i]}", ha="center",
                 fontsize=12, fontweight="bold", color=colors[i])
    axA.set_xticks(x); axA.set_xticklabels(arms, fontsize=8.8)
    axA.set_ylabel("held-out contract success rate")
    axA.set_ylim(0, 1.16); axA.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axA.axhline(0, color=INK, lw=1.0)
    axA.set_title("(a) success — the constraint survives only with the residue", fontsize=10)
    _despine(axA)

    # panel B: mean cost (the two same-model arms — USD comparable)
    xb = np.arange(2)
    cb = [cost[1], cost[2]]; lab = ["pointers-only", "pointers + derived"]
    bars = axB.bar(xb, cb, width=0.55, color=[BASE, DERIVED], zorder=3)
    for b, c in zip(bars, cb):
        axB.text(b.get_x()+b.get_width()/2, c+0.008, f"${c:.3f}", ha="center", fontsize=9.5)
    axB.set_xticks(xb); axB.set_xticklabels(lab, fontsize=9)
    axB.set_ylabel("mean cost per run  (USD, measured, N=8)")
    axB.set_ylim(0, 0.6)
    axB.set_title("(b) cost — residue is a quality win at parity-or-better\n(the null arm flails, then fails)", fontsize=10)
    _despine(axB)

    fig.suptitle("Figure 8 — Lever-2 three-arm comparison   "
                 "(CONFIRM, N=8 · exact 95% CIs · CIs cleanly separated)",
                 fontsize=12.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "fig8_lever2_three_arm.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =====================================================================
# FIGURE 9 — USD delta: N=3 screen vs N=8 confirm (the −18% did not replicate)
# =====================================================================
def fig9_usd_weighting():
    # Real measured mean USD per arm — no fabricated/hardcoded deltas.
    # Screen (N=3):  derived 0.383 vs pointers-only 0.465  (results/lever2-screen.json)
    # Confirm (N=8): derived 0.417 vs pointers-only 0.436  (results/lever2-confirm.json)
    screen_derived, screen_po = 0.383, 0.465
    confirm_derived, confirm_po = 0.417, 0.436
    screen_delta = (screen_derived - screen_po) / screen_po
    confirm_delta = (confirm_derived - confirm_po) / confirm_po

    fig, ax = plt.subplots(figsize=(7.6, 5.3))
    cats = ["N=3 screen", "N=8 confirm"]
    deltas = [screen_delta, confirm_delta]
    colors = [MUTE, DERIVED]
    bars = ax.bar(cats, deltas, width=0.45, color=colors, zorder=3)
    ax.axhline(0, color=INK, lw=1.1)
    # noise band: a same-model N=8 delta this small is not distinguishable from 0
    ax.axhspan(-0.10, 0.10, color=FAINT, alpha=0.6, zorder=1)
    ax.text(-0.42, 0.085, "±10% noise band", ha="left", va="top", fontsize=7.8, color=MUTE)
    for b, d in zip(bars, deltas):
        ax.text(b.get_x()+b.get_width()/2, d + (0.012 if d > 0 else -0.018),
                f"{d:+.1%}", ha="center", va="bottom" if d > 0 else "top",
                fontsize=12, fontweight="bold", color=INK)
    ax.annotate("did NOT replicate at N=8", (0, screen_delta), (0.5, -0.30),
                ha="center", fontsize=9.2, color=INK, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=MUTE, lw=1.1,
                                 connectionstyle="arc3,rad=0.15"))
    ax.set_ylabel("Δ net USD  (pointers+derived vs pointers-only)")
    ax.set_ylim(-0.34, 0.10); ax.set_yticks([-0.30, -0.20, -0.10, 0, 0.10])
    ax.set_yticklabels(["-30%", "-20%", "-10%", "0", "+10%"])
    ax.set_title("Figure 9 — cost delta: screen vs confirm\n"
                 "the screen's apparent −18% USD win is a screen artifact — N=8 shows parity",
                 fontsize=11.5, fontweight="bold")
    ax.text(0.5, -0.325, "screen: $0.383 vs $0.465 (N=3, no CI overlap check run)   ·   "
            "confirm: $0.417 vs $0.436 (N=8, within noise)", ha="center", fontsize=7.8,
            color=MUTE, transform=ax.transData)
    _despine(ax)
    fig.tight_layout()
    fig.savefig(OUT / "fig9_usd_weighting.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =====================================================================
# FIGURE 10 — Exp. 4c: does the sharp step survive DEPTH?
# =====================================================================
def fig10_exp4c_depth():
    # Exp.4 floor (trace genuinely absent) vs Exp.4c cells (deep constraint, trace
    # present but rationale stripped/documented/carried-as-residue). All pointers-only
    # unless noted. Data: results/lever2-confirm.json, results/lever2-deep-4c.json.
    cats = ["Exp.4 floor\npointers-only\n(trace absent)",
            "Exp.4c Du\npointers-only\n(rationale stripped)",
            "Exp.4c Dr\npointers-only\n(rationale documented,\nn=12 control)",
            "Exp.4c Du\nwith-derived\n(residue carried)"]
    succ_n = [(0, 8), (12, 12), (12, 12), (12, 12)]
    ci_lo = [0.0, 0.735, 0.735, 0.735]
    ci_hi = [0.369, 1.0, 1.0, 1.0]
    colors = [MUTE, BASE, BASE, DERIVED]

    fig, ax = plt.subplots(figsize=(9.2, 6.0))
    x = np.arange(len(cats))
    rate = [s / n for s, n in succ_n]
    ax.bar(x, rate, width=0.58, color=colors, zorder=3)
    for i in range(len(cats)):
        ax.plot([x[i], x[i]], [ci_lo[i], ci_hi[i]], color=INK, lw=1.6, zorder=5)
        ax.plot([x[i]-0.07, x[i]+0.07], [ci_lo[i]]*2, color=INK, lw=1.6, zorder=5)
        ax.plot([x[i]-0.07, x[i]+0.07], [ci_hi[i]]*2, color=INK, lw=1.6, zorder=5)
        s, n = succ_n[i]
        ax.text(x[i], 1.06, f"{s}/{n}", ha="center", fontsize=12,
                fontweight="bold", color=colors[i])
    ax.axvline(0.5, color=INK, ls=(0, (4, 3)), lw=1.1, zorder=2)
    ax.text(0.5, 1.42, "R* — the step\n(trace absent → present)", ha="center",
            fontsize=8.0, color=MUTE)
    ax.annotate("stripping the docstring\ndid not reduce recovery\n(Du = Dr)", (1.5, 1.06),
                (1.5, 1.30), ha="center", fontsize=8.0, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.9))
    ax.annotate("residue adds nothing\nabove ceiling, H0\n(TOST-confirmed ±0.20, N=12, §8a)",
                (3, 1.06), (3.35, 0.55), ha="left", fontsize=7.8, color=DERIVED,
                arrowprops=dict(arrowstyle="-|>", color=DERIVED, lw=1.1))
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=8.4)
    ax.set_ylabel("held-out recoverability (pointers-only unless noted)")
    ax.set_ylim(-0.05, 1.58); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_title("Figure 10 — Exp. 4c: the sharp step survives depth\n"
                 "dedup-before-aggregate (code present, rationale stripped) recovers at ceiling, same as Exp.4's floor is 0/8",
                 fontsize=11, fontweight="bold", pad=14)
    _despine(ax)
    fig.tight_layout()
    fig.savefig(OUT / "fig10_exp4c_depth.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# =====================================================================
# FIGURE 11 — the two-sided bounded law (all regimes, one figure)
# =====================================================================
def fig11_bounded_law():
    # pointers-only recoverability across every tested recoverability regime,
    # ordered absent -> present/salient. Sources: lever2-confirm.json (Exp.4),
    # exp4b-substrate/CALIBRATION-RESULT.md (Exp.4b ladder), lever2-natural.json
    # (Exp.5 = R_high), lever2-deep-4c.json (Exp.4c Du).
    cats = ["absent\n(Exp.4\nFork-A)", "absent, findable\n(Exp.4b\nR_low)",
            "present, deep\n+ stripped\n(Exp.4c Du,\nn=12)", "present, distant\n(Exp.4b R_mid2,\nn=4)",
            "present,\nnon-salient\n(Exp.4b R_mid)", "present, salient\n(Exp.4b/5\nR_high)"]
    succ_n = [(0, 8), (0, 8), (12, 12), (4, 4), (8, 8), (8, 8)]
    ci_lo = [0.0, 0.0, 0.735, 0.398, 0.631, 0.631]
    ci_hi = [0.369, 0.369, 1.0, 1.0, 1.0, 1.0]
    # residue verdict per regime: necessary (trace absent) vs unnecessary (trace present)
    necessary = [True, True, False, False, False, False]
    colors = [DERIVED if nec else BASE for nec in necessary]

    fig, ax = plt.subplots(figsize=(11.0, 6.6))
    x = np.arange(len(cats))
    rate = [s / n for s, n in succ_n]
    ax.bar(x, rate, width=0.6, color=colors, zorder=3)
    for i in range(len(cats)):
        ax.plot([x[i], x[i]], [ci_lo[i], ci_hi[i]], color=INK, lw=1.6, zorder=5)
        ax.plot([x[i]-0.07, x[i]+0.07], [ci_lo[i]]*2, color=INK, lw=1.6, zorder=5)
        ax.plot([x[i]-0.07, x[i]+0.07], [ci_hi[i]]*2, color=INK, lw=1.6, zorder=5)
        s, n = succ_n[i]
        ax.text(x[i], 1.07, f"{s}/{n}", ha="center", fontsize=11.5,
                fontweight="bold", color=colors[i])
    ax.axvline(1.5, color=INK, ls=(0, (4, 3)), lw=1.3, zorder=2)
    ax.text(1.5, 1.42, "R* — the sharp step\n(trace absent → present)", ha="center",
            fontsize=9.2, fontweight="bold", color=INK)
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=8.2)
    ax.set_ylabel("pointers-only held-out recoverability")
    ax.set_ylim(-0.02, 1.58); ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.axhline(0, color=INK, lw=1.0)
    ax.set_title("Figure 11 — the two-sided bounded law, one figure\n"
                 "residue value is a sharp step on trace presence, not a gradient on salience or depth",
                 fontsize=11.5, fontweight="bold", pad=14)
    _despine(ax)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.30)
    fig.text(0.27, 0.045, "residue NECESSARY here (8/8 vs 0/8, Exp.4)", ha="center",
              fontsize=8.6, color=DERIVED, fontweight="bold")
    fig.text(0.68, 0.045,
              "residue overhead here — re-derived for free\n"
              "(H0 point estimates; not TOST-confirmed at N=4–8, §8a)",
              ha="center", fontsize=8.2, color=BASE, fontweight="bold")
    fig.savefig(OUT / "fig11_bounded_law.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig1_schematic()
    fig2_ceilings()
    fig7_frontier()
    fig8_three_arm()
    fig9_usd_weighting()
    fig10_exp4c_depth()
    fig11_bounded_law()
    print("wrote fig5_system_schematic, fig6_two_ceilings, fig7_lever1_frontier, "
          "fig8_lever2_three_arm, fig9_usd_weighting, fig10_exp4c_depth, fig11_bounded_law")
