#!/usr/bin/env python3
"""Generate Tier-A benchmark figures from the recorded results.

Data are the committed per-arm cost numbers (all from claude total_cost_usd).
Run: python3 docs/benchmarks/figures/make_figures.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pathlib

OUT = pathlib.Path(__file__).parent
C_NAIVE = "#4C78A8"   # naive / hand-rolled
C_PIGEON = "#E45756"  # pigeon
C_SOLO = "#9D9D9D"    # solo

# ---- Figure 1: total cost by arm, per repo -------------------------------
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
# cookiecutter
ax = axes[0]
arms = ["solo\n(1 agent)", "naive\n(2 agents)", "pigeon\n(2 agents)"]
costs = [0.4394, 0.4016, 0.6397]
colors = [C_SOLO, C_NAIVE, C_PIGEON]
bars = ax.bar(arms, costs, color=colors)
ax.set_title("cookiecutter (small files)\nfeature across 2 modules")
ax.set_ylabel("cost per task (USD, claude total_cost_usd)")
ax.set_ylim(0, 1.35)
for b, c in zip(bars, costs):
    ax.text(b.get_x() + b.get_width()/2, c + 0.015, f"${c:.3f}", ha="center", fontsize=9)
ax.axhline(0.4016, color=C_NAIVE, ls=":", lw=1, alpha=0.6)
# marshmallow
ax = axes[1]
arms = ["naive\n(3 agents)", "pigeon\n(3 agents)"]
costs = [1.1117, 1.2016]
bars = ax.bar(arms, costs, color=[C_NAIVE, C_PIGEON])
ax.set_title("marshmallow (large files)\nfeature across 2 large modules, 3-agent chain")
ax.set_ylabel("cost per task (USD)")
ax.set_ylim(0, 1.35)
for b, c in zip(bars, costs):
    ax.text(b.get_x() + b.get_width()/2, c + 0.015, f"${c:.3f}", ha="center", fontsize=9)
ax.axhline(1.1117, color=C_NAIVE, ls=":", lw=1, alpha=0.6)
fig.suptitle("Figure 1 — Cost per successful task by arm (all arms succeeded)", fontweight="bold")
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(OUT / "fig1_cost_by_arm.png", dpi=130)
plt.close(fig)

# ---- Figure 2: pigeon cost penalty vs task scale (amortization) ----------
fig, ax = plt.subplots(figsize=(7, 4.4))
# x = naive total cost (proxy for task heaviness/scale), y = pigeon penalty vs naive
x = [0.4016, 1.1117]
y = [59.3, 8.1]
labels = ["cookiecutter\n(small, 2-agent)", "marshmallow\n(large, 3-agent)"]
ax.plot(x, y, "-o", color=C_PIGEON, lw=2, ms=9)
for xi, yi, l in zip(x, y, labels):
    ax.annotate(f"{l}\n+{yi:.0f}%", (xi, yi), textcoords="offset points",
                xytext=(10, 8), fontsize=9)
ax.axhline(0, color="k", lw=1)
ax.fill_between([0.2, 1.3], -5, 0, color="green", alpha=0.06)
ax.text(1.25, -3.5, "savings region\n(never reached)", ha="right", va="center",
        fontsize=8, color="green")
ax.set_xlabel("task scale  →  (naive-arm cost, USD, as a heaviness proxy)")
ax.set_ylabel("pigeon cost penalty vs naive (%)")
ax.set_title("Figure 2 — Pigeon's overhead is ~fixed: penalty shrinks with task\n"
             "scale (59% → 8%) but never crosses into savings", fontweight="bold")
ax.set_xlim(0.2, 1.3)
ax.set_ylim(-6, 70)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "fig2_overhead_amortization.png", dpi=130)
plt.close(fig)

# ---- Figure 3: per-step cost breakdown (marshmallow 3-agent chain) --------
fig, ax = plt.subplots(figsize=(7.5, 4.4))
steps = ["plan", "implement", "review"]
naive = [0.4555, 0.2760, 0.3802]
pigeon = [0.4419, 0.4434, 0.3163]
import numpy as np
xpos = np.arange(len(steps))
w = 0.38
b1 = ax.bar(xpos - w/2, naive, w, label="naive (hand-rolled)", color=C_NAIVE)
b2 = ax.bar(xpos + w/2, pigeon, w, label="pigeon", color=C_PIGEON)
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.008,
                f"${b.get_height():.2f}", ha="center", fontsize=8)
ax.set_xticks(xpos); ax.set_xticklabels(steps)
ax.set_ylabel("cost per step (USD)")
ax.set_ylim(0, 0.55)
ax.legend()
ax.set_title("Figure 3 — marshmallow per-step cost: pigeon's overhead\n"
             "concentrates in the implement step (pack+retrieve+handoff load)",
             fontweight="bold")
fig.tight_layout()
fig.savefig(OUT / "fig3_marshmallow_per_step.png", dpi=130)
plt.close(fig)

print("wrote:", *(p.name for p in sorted(OUT.glob("*.png"))))
