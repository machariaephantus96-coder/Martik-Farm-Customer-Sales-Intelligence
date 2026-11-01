#!/usr/bin/env python3
"""Figures for Milestone 6 (run after forecast_model.py):  python src/forecast_figures.py  ->  figures/m6_*.png"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import forecast_model as fm

FIG = fm.ROOT / "figures"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GREY, INK, INK2, GRID, SURF = "#9c9b95", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF, "font.size": 10, "axes.titlesize": 10.5, "axes.titleweight": "bold",
                     "axes.titlelocation": "left", "axes.edgecolor": GREY, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK})


def tidy(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0, labelsize=9); ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)


def save(fig, name, title):
    fig.suptitle(title, x=0.0, ha="left", y=1.04, fontsize=12.5, fontweight="bold")
    fig.savefig(FIG / f"{name}.png", dpi=150, bbox_inches="tight", facecolor=SURF); plt.close(fig)


def weekly_total(part, h):
    g = part[part.h == h].groupby("target_week").agg(actual=("actual", "sum"), model=("model", "sum"), b4=("b4_ly_growth", lambda x: x.sum(skipna=False)), avg4=("b2_avg4", "sum"))
    return g


def main():
    FIG.mkdir(exist_ok=True)
    r = fm.run(); q, ev, val, tst, vall = r["q"], r["ev"], r["val"], r["test"], r["val_all"]
    tot = q.sum(axis=1) / 1e3
    # 1 splits
    fig, ax = plt.subplots(figsize=(9.5, 3.4)); ax.plot(tot.index, tot, color=INK, lw=1.4)
    for a, b, c, lab in [(tot.index[0], fm.TRAIN_END, GREY, "Train"), (fm.TRAIN_END, fm.VAL_END, BLUE, "Validation"), (fm.VAL_END, tot.index[-1], ORANGE, "Test")]:
        ax.axvspan(a, b, color=c, alpha=0.13, lw=0); ax.text(a + (b - a) / 2, tot.max() * 1.06, lab, ha="center", color=INK2, fontsize=9.5, fontweight="bold")
    ax.set_ylim(top=tot.max() * 1.14); ax.set_ylabel("Units sold per week (thousand)"); tidy(ax)
    save(fig, "m6_01_splits", "Time-ordered splits: the model never sees the weeks it is scored on")
    # 2 actual vs forecast at 4 weeks ahead, validation and test
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.7), sharey=True)
    for ax, part, name in [(axs[0], vall, "Validation: Oct 2025 - Mar 2026 (includes the peak)"), (axs[1], tst, "Test (Apr-Sep 2026)")]:
        g = weekly_total(part, 4) / 1e3
        ax.plot(g.index, g.actual, color=INK, lw=1.6, label="Actual"); ax.plot(g.index, g.model, color=BLUE, lw=1.6, label="Model")
        ax.plot(g.index, g.b4, color=ORANGE, lw=1.3, ls="--", label="Last year x growth (exists from Dec 2025)")
        ax.set_title(name); tidy(ax); ax.tick_params(axis="x", labelrotation=30)
    axs[0].set_ylabel("Units per week (thousand)"); axs[0].legend(frameon=False, fontsize=8.5, loc="lower left")
    save(fig, "m6_02_actual_vs_forecast", "Forecasts made 4 weeks ahead: the model undershoots the peak and overshoots in low weeks")
    # 3 by horizon (test)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for col, lab, c, ls in [("model", "Model", BLUE, "-"), ("b4_ly_growth", "Last year x growth", ORANGE, "--"), ("b2_avg4", "4-week average", GREY, "-")]:
        y = [100 * fm.wape(g.actual, g[col]) for _, g in tst.groupby("h")]
        ax.plot(fm.HORIZONS, y, marker="o", color=c, ls=ls, lw=2); ax.text(4.08, y[-1] + {"Model": -0.6, "Last year x growth": 0.6}.get(lab, 0), f"{lab} {y[-1]:.1f}%", va="center", fontsize=9, color=c if c != GREY else INK2)
    ax.set_xticks(fm.HORIZONS); ax.set_xticklabels([f"{h} wk" for h in fm.HORIZONS]); ax.set_xlim(0.8, 5.6); ax.set_ylim(0, 22)
    ax.set_xlabel("Forecast horizon"); ax.set_ylabel("WAPE on test (%), lower is better"); tidy(ax)
    save(fig, "m6_03_by_horizon", "The model keeps its accuracy out to 4 weeks; the 4-week average falls behind quickly")
    # 4 by category (test)
    rows = []
    for c, g in tst.groupby("category"):
        rows.append(dict(category=c, share=g.actual.sum() / tst.actual.sum(), model=100 * fm.wape(g.actual, g.model), b4=100 * fm.wape(g.actual, g.b4_ly_growth), avg4=100 * fm.wape(g.actual, g.b2_avg4)))
    cat = pd.DataFrame(rows).sort_values("share"); y = np.arange(len(cat))
    fig, ax = plt.subplots(figsize=(8.5, 4)); ax.scatter(cat.avg4, y, color=GREY, s=36, label="4-week average", zorder=3)
    ax.scatter(cat.b4, y, color=ORANGE, s=36, label="Last year x growth", zorder=3); ax.scatter(cat.model, y, color=BLUE, s=48, label="Model", zorder=4)
    for yi, (a, b, c) in enumerate(zip(cat.avg4, cat.b4, cat.model)):
        ax.plot([min(a, b, c), max(a, b, c)], [yi, yi], color=GRID, lw=2, zorder=1)
    ax.set_yticks(y); ax.set_yticklabels([f"{c} ({s:.0%})" for c, s in zip(cat.category, cat.share)]); ax.set_xlabel("WAPE on test (%), lower is better")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right"); tidy(ax, "x")
    save(fig, "m6_04_by_category", "Most categories are forecast within 9-18%; small, noisy leafy greens is the weak spot (25%)")
    # 5 by week type
    d = pd.concat([vall, tst]).copy(); cal = r["cal"]; d["season"] = d.target_week.map(cal.season); d["holiday"] = np.where(d.target_week.map(cal.holiday_days) > 0, "Holiday week", "No holiday")
    groups = [("Low season", d[d.season == "Low"]), ("Normal", d[d.season == "Normal"]), ("Peak season", d[d.season == "Peak"]), ("Holiday week", d[d.holiday == "Holiday week"])]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.5))
    xs = np.arange(len(groups))
    axs[0].bar(xs - 0.2, [100 * fm.wape(g.actual, g.model) for _, g in groups], 0.38, color=BLUE, label="Model")
    axs[0].bar(xs + 0.2, [100 * fm.wape(g.actual, g.b2_avg4) for _, g in groups], 0.38, color=GREY, label="4-week average")
    axs[0].set_title("Error (WAPE %)"); axs[0].legend(frameon=False, fontsize=8.5)
    bias = [100 * fm.bias(g.actual, g.model) for _, g in groups]
    axs[1].bar(xs, bias, 0.5, color=[ORANGE if b < -10 else BLUE for b in bias]); axs[1].axhline(0, color=INK, lw=1)
    for x, b in zip(xs, bias):
        axs[1].text(x, b + (1 if b >= 0 else -1), f"{b:+.0f}%", ha="center", va="bottom" if b >= 0 else "top", fontsize=9)
    axs[1].set_title("Model bias (+ = over-forecasts, - = under-forecasts)"); axs[1].set_ylim(-22, 16)
    for a in axs:
        a.set_xticks(xs); a.set_xticklabels([n for n, _ in groups]); tidy(a)
    save(fig, "m6_05_error_by_week_type", "The model beats the 4-week average except in the peak, where it under-forecasts by 14%")
    # 6 next 4 weeks
    nf = pd.read_csv(fm.OUT / "next_4_weeks.csv", parse_dates=["target_week"]).groupby("target_week")[["forecast", "low80", "high80"]].sum() / 1e3
    fig, ax = plt.subplots(figsize=(9.5, 3.6)); recent = tot.iloc[-26:]
    ax.plot(recent.index, recent, color=INK, lw=1.6, label="Actual (last 26 weeks)")
    ly = tot.reindex(nf.index - pd.Timedelta(weeks=52)); ax.scatter(nf.index, ly.values, color=GREY, s=34, zorder=3, label="Same week last year")
    ax.plot(nf.index, nf.forecast, color=BLUE, marker="o", lw=2, label="Recommended forecast (model + last year blend)"); ax.fill_between(nf.index, nf.low80, nf.high80, color=BLUE, alpha=0.18, lw=0, label="80% range")
    ax.set_ylabel("Units per week (thousand)"); ax.legend(frameon=False, fontsize=8.5, loc="upper left"); tidy(ax)
    save(fig, "m6_06_next_4_weeks", f"Next 4 weeks (start of the peak): about {nf.forecast.min()*1000:,.0f} to {nf.forecast.max()*1000:,.0f} units a week, 80% range roughly +/-20%")
    print("figures written")


if __name__ == "__main__":
    main()
