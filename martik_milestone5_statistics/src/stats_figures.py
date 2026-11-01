#!/usr/bin/env python3
"""Figures for Milestone 5 (run after stats_analysis.py):  python src/stats_figures.py  ->  figures/s5_*.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf

import stats_analysis as sa

FIG = sa.ROOT / "figures"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GREY, INK, INK2, GRID, SURF = "#9c9b95", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "font.size": 10, "axes.titlesize": 10.5, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "axes.edgecolor": GREY, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK})


def tidy(ax, grid="x"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, labelsize=9)
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)


def save(fig, name, title):
    fig.suptitle(title, x=0.0, ha="left", y=1.04, fontsize=12.5, fontweight="bold")
    fig.savefig(FIG / f"{name}.png", dpi=150, bbox_inches="tight", facecolor=SURF); plt.close(fig)


def forest(ax, labels, est, lo, hi, colors, fmt="{:+.0f}%", zero=0):
    y = np.arange(len(labels))[::-1]
    for yi, e, l, h, c in zip(y, est, lo, hi, colors):
        ax.plot([l, h], [yi, yi], color=c, lw=2.2, solid_capstyle="round"); ax.plot(e, yi, "o", color=c, ms=7)
        ax.text(h + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.015, yi, f"{fmt.format(e)}  ({fmt.format(l)} to {fmt.format(h)})", va="center", fontsize=8.5, color=INK2)
    ax.axvline(zero, color=INK, lw=1); ax.set_yticks(y); ax.set_yticklabels(labels); tidy(ax)


def main():
    FIG.mkdir(exist_ok=True)
    data = sa.load()
    t1, det = sa.t1_promotions(data)
    pooled = sa.t1_pooled_fruit(det)
    # 1 promotions
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    ax.set_xlim(-45, 95)
    labs = [f"{r.promo_id} {r.categories.split(';')[0]}{' +' if ';' in r.categories else ''}\n{r.discount_pct:.0f}% off, {r.accounts} accounts" for r in t1.itertuples()]
    cols = [BLUE if r.t_p < 0.05 else GREY for r in t1.itertuples()]
    forest(ax, labs, t1.uplift_pct, t1.ci_low_pct, t1.ci_high_pct, cols)
    ax.set_xlabel("Change in promoted-category volume vs baseline weeks (%), 95% bootstrap interval")
    ax.text(0.99, 0.02, "blue: p < 0.05 before Holm correction\nnone passes after correction", transform=ax.transAxes, ha="right", fontsize=8.5, color=INK2)
    save(fig, "s5_01_promotions", "Only the two January fruit promotions look like they worked, and the evidence is thin")
    # 2 M-Pesa
    t2 = sa.t2_mpesa(data)["table"].iloc[:5]
    fig, ax = plt.subplots(figsize=(9.2, 3.4)); ax.set_xlim(-62, 16)
    labs = ["Naive: all account orders", "Adjusted for segment", "Same customer (fixed effects)", "Customer-level paired check", "Walk-ins: M-Pesa vs cash"]
    cols = [ORANGE, BLUE, BLUE, BLUE, BLUE]
    forest(ax, labs, t2.pct_diff, t2.ci_low_pct, t2.ci_high_pct, cols, fmt="{:+.1f}%")
    ax.set_xlabel("M-Pesa order value relative to other methods (%), 95% interval")
    save(fig, "s5_02_mpesa", "M-Pesa orders look 38% smaller, but that is who pays by M-Pesa, not what M-Pesa does")
    # 3 season
    t3, w, hac = sa.t3_season(data)
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    ax.plot(w.week_start, w.revenue_kes / 1e3, color=GREY, lw=1)
    for name, c in [("Peak", ORANGE), ("Low", BLUE)]:
        s = w[w.season == name]; ax.scatter(s.week_start, s.revenue_kes / 1e3, s=18, color=c, label=f"{name} season weeks", zorder=3)
    ax.set_ylabel("Weekly revenue (KES thousand)"); ax.legend(frameon=False, loc="upper left", fontsize=9); tidy(ax, "y")
    ax.set_ylim(top=1400)
    ax.text(0.99, 0.98, f"Peak weeks earn {t3['peak_vs_low_ratio']:.2f}x low weeks\n95% CI {t3['ci_low']:.2f} to {t3['ci_high']:.2f}, after removing a {t3['trend_pct_per_year']:.0f}%/yr trend",
            transform=ax.transAxes, ha="right", va="top", fontsize=9, color=INK2)
    save(fig, "s5_03_season", "Peak-season weeks earn about 1.8 times what low-season weeks earn")
    # 4 late
    t4, r4 = sa.t4_late(data)
    t4 = t4.sort_values("late_pct")
    fig, ax = plt.subplots(figsize=(9.2, 3.8)); ax.set_xlim(60, 108)
    y = np.arange(len(t4))
    for yi, r in zip(y, t4.itertuples()):
        ax.plot([r.ci_low_pct, r.ci_high_pct], [yi, yi], color=BLUE, lw=2.2); ax.plot(r.late_pct, yi, "o", color=BLUE, ms=7)
        ax.text(r.ci_high_pct + 1, yi, f"{r.late_pct:.0f}%   ({r.customers} acct{'s' if r.customers > 1 else ''})", va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(t4.segment); tidy(ax); ax.set_xlabel("Paid invoices settled after the due date (%), 95% Wilson interval (treats invoices as independent, so too narrow)")
    save(fig, "s5_04_late_payment", "Hotels and schools almost always pay after the due date; caterers and fast food least")
    # 5 assumptions
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 3.5))
    d = det["P01"]; stats.probplot(d, plot=axs[0]); axs[0].set_title("T1 (P01): account changes")
    o = data["orders"].merge(data["payments"][["order_id", "method"]], on="order_id"); o = o[o.is_account == 1]
    stats.probplot(np.log(o.order_total_kes.sample(3000, random_state=42)), plot=axs[1]); axs[1].set_title("T2: log order value (sample)")
    plot_acf(hac.resid, lags=12, ax=axs[2], color=BLUE, vlines_kwargs={"colors": BLUE}); axs[2].set_title("T3: autocorrelation of weekly residuals")
    for a in axs:
        tidy(a, "both")
        for ln in a.get_lines():
            if ln.get_marker() == "o" and ln.get_linestyle() == "None" and ln.get_color() in ("b", "#1f77b4"):
                ln.set_color(BLUE); ln.set_markersize(3)
            elif ln.get_linestyle() == "-" and ln.get_color() == "r":
                ln.set_color(ORANGE)
    save(fig, "s5_05_assumption_checks", "Assumption checks: roughly normal for T1 and T2, but weekly revenue is autocorrelated, so T3 uses robust errors")
    print("figures written")


if __name__ == "__main__":
    main()
