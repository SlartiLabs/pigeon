#!/usr/bin/env python3
"""Stage 5 pilot figure — pointers-only pinned to the no-code guessing floor (GATE 3).

Two panels: (left) pass rate with exact Clopper-Pearson CIs — no-code baseline vs
pointers-only, showing they coincide (the substrate is guessable, not recovered);
(right) cost per arm, showing pointers-only paid 2-4x more to reach the same answer.
House style, 300 DPI.
"""
from __future__ import annotations
import csv, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

INK="#1A1A1A"; MUTE="#8A8A8A"; FAINT="#D6D6D6"; DERIVED="#B5341F"; BASE="#3C6E9E"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":11,"text.color":INK,
    "axes.edgecolor":INK,"axes.labelcolor":INK,"xtick.color":INK,"ytick.color":INK,
    "axes.linewidth":1.0,"savefig.dpi":300,"figure.dpi":150})
HERE=pathlib.Path(__file__).resolve().parent
DATA=HERE.parent/"results"/"stage5"

def cp(x,n,a=0.05):
    lo=0.0 if x==0 else beta.ppf(a/2,x,n-x+1); hi=1.0 if x==n else beta.ppf(1-a/2,x+1,n-x)
    return float(lo),float(hi)

def load(name):
    rows=[r for r in csv.DictReader([l for l in (DATA/name).read_text().splitlines() if not l.startswith("#")])]
    x=sum(1 for r in rows if r["accept_rc"]=="0"); n=len(rows)
    costs=[float(r["cost_usd"]) for r in rows if r["cost_usd"] not in ("","NA")]
    return x,n,costs

def _despine(ax,keep=("left","bottom")):
    for s in ("top","right","left","bottom"): ax.spines[s].set_visible(s in keep)

def main():
    nc=load("no-code-N4.csv"); po=load("pointers-only-N4.csv")
    arms=[("no-code\nbaseline (floor)",nc,MUTE),("pointers-only",po,BASE)]
    fig,(ax,ax2)=plt.subplots(1,2,figsize=(10.4,4.8))
    for i,(lbl,(x,n,_),col) in enumerate(arms):
        p=x/n; lo,hi=cp(x,n)
        ax.bar(i,p,width=0.55,color=col,edgecolor=INK,linewidth=1.1,zorder=3)
        ax.errorbar(i,p,yerr=[[p-lo],[hi-p]],fmt="none",ecolor=INK,elinewidth=1.4,capsize=6,capthick=1.4,zorder=4)
        ax.text(i,min(hi+0.04,1.03),f"{x}/{n}",ha="center",va="bottom",fontweight="bold")
    ax.set_xticks([0,1]); ax.set_xticklabels([a[0] for a in arms]); ax.set_ylim(0,1.15)
    ax.set_yticks(np.arange(0,1.01,0.25)); ax.set_ylabel("pass rate (held-out grader)")
    ax.axhline(1.0,color=FAINT,lw=1,zorder=1)
    ax.set_title("pointers-only sits ON the guessing floor",fontsize=10.5)
    ax.annotate("no separation\n= substrate guessable\n(GATE 3: redesign)",xy=(1,1.0),xytext=(0.5,0.55),
                ha="center",fontsize=8.5,color=DERIVED,style="italic")
    _despine(ax)
    # cost panel
    for i,(lbl,(x,n,costs),col) in enumerate(arms):
        if costs:
            m=float(np.mean(costs))
            ax2.bar(i,m,width=0.55,color=col,edgecolor=INK,linewidth=1.1)
            ax2.text(i,m+0.01,f"${m:.2f}",ha="center",va="bottom",fontsize=9)
    ax2.set_xticks([0,1]); ax2.set_xticklabels([a[0] for a in arms])
    ax2.set_ylabel("mean cost / trial (USD)"); ax2.set_title("...but paid more to get there",fontsize=10.5)
    _despine(ax2)
    fig.suptitle("Stage 5 pilot — the deep-real substrate is defeated by training priors",
                 fontsize=12.5,fontweight="bold",y=0.99)
    fig.text(0.5,0.005,"No-code floor = pointers-only = 4/4: the ISO-4217 minor-units fact is guessable, "
             "so the substrate cannot isolate genuine artifact-recovery. Redesign toward a prior-independent fact.",
             ha="center",fontsize=8,color=MUTE)
    fig.tight_layout(rect=(0,0.04,1,0.95))
    out=HERE/"fig_s5_gate3.png"; fig.savefig(out); print("wrote",out)

if __name__=="__main__": raise SystemExit(main())
