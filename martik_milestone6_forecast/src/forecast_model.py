#!/usr/bin/env python3
"""Milestone 6: weekly demand forecast by product category, 1 to 4 weeks ahead.

  Target      billed quantity per week per category (data_clean/weekly_sales.csv), 8 categories (Grains & Legumes is too sparse: 0.3% of revenue)
  Horizon     1, 2, 3, 4 weeks ahead from the last completed week (purchasing planning is about a month)
  Baselines   B1 naive (last week)  B2 4-week average  B3 same week last year  B4 same week last year x recent growth
  Model       gradient boosting on ratios to the recent level, with known-in-advance calendar features (season label, holidays, promotions).
              It gets NO last-year values: the first year has none, so they would be empty in training. It must learn seasonality from the labels.
  Splits      by TARGET week, in time order:  train 7 Oct 2024 - 29 Sep 2025 | validation 6 Oct 2025 - 30 Mar 2026 | test 6 Apr - 21 Sep 2026
              model choice uses validation only; the test period is scored once, with the model refitted on train + validation
  Metric      WAPE = sum |forecast - actual| / sum actual (lower is better), plus bias = sum (forecast - actual) / sum actual

Run after src/clean_data.py:   python src/forecast_model.py     ->  forecast/*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

ROOT = Path(__file__).resolve().parents[1]
CLEAN, OUT = ROOT / "data_clean", ROOT / "forecast"
SEED, HORIZONS = 42, [1, 2, 3, 4]
CATS = ["Alliums", "Fruit", "Herbs & Spices", "Leafy Greens", "Peppers & Chillies", "Potato Products", "Roots & Tubers", "Vegetables"]
TRAIN_END, VAL_END = pd.Timestamp("2025-09-29"), pd.Timestamp("2026-03-30")      # last target week of train / validation
SEASONS = ["Peak", "Low", "Normal"]
PROMO_CATS = {"P01": ["Fruit"], "P02": ["Vegetables", "Leafy Greens"], "P03": ["Herbs & Spices"], "P04": ["Fruit"], "P05": ["Potato Products", "Roots & Tubers"]}
CONFIGS = [dict(loss=l, max_depth=d, learning_rate=lr, max_iter=n, min_samples_leaf=20, l2_regularization=1.0)
           for l in ("squared_error", "absolute_error") for d, lr, n in [(3, 0.05, 150), (4, 0.05, 250), (6, 0.03, 250)]]
FEATURES = ["h", "cat", "last_r", "mean4_r", "mean13_r", "t_peak", "t_low", "t_normal", "o_peak", "o_low", "t_hol", "t_sin", "t_cos", "t_promo", "scale"]


# ------------------------------------------------------------------ data
def load():
    w = pd.read_csv(CLEAN / "weekly_sales.csv", parse_dates=["week_start"])
    full = w[w.category == "ALL"].sort_values("week_start").iloc[1:-1]                 # drop the two partial end weeks
    weeks = pd.DatetimeIndex(full.week_start.values)
    q = w[w.category.isin(CATS)].pivot(index="week_start", columns="category", values="billed_qty").reindex(weeks)[CATS]
    cal = full.set_index("week_start")[["season", "holiday_days"]]
    promos = pd.read_csv(CLEAN / "promotions.csv", parse_dates=["start_date", "end_date"])
    promo = pd.DataFrame(0.0, index=weeks, columns=CATS)                               # share of the week's 7 days inside a promotion for that category
    for r in promos.itertuples():
        for c in PROMO_CATS[r.promo_id]:
            for wk in weeks:
                days = pd.date_range(wk, periods=7)
                promo.loc[wk, c] = max(promo.loc[wk, c], ((days >= r.start_date) & (days <= r.end_date)).mean())
    assert q.notna().all().all(), "gaps in weekly series"
    return q, cal, promo


def make_rows(q, cal, promo, future=None):
    """One row per (category, forecast origin, horizon). Features use only weeks <= origin, plus calendar facts known in advance
    (season label, public holidays, planned promotions) for the target week. `future` supplies those facts for weeks beyond the data."""
    n = len(q); A = q.values; rows = []
    cal_all = cal.copy()
    if future is not None:
        cal_all = pd.concat([cal, future["cal"]]); promo_all = pd.concat([promo, future["promo"]])
    else:
        promo_all = promo
    dates = list(cal_all.index)
    origins = range(12, n) if future is not None else range(12, n - 1)
    for o in origins:
        for h in HORIZONS:
            t = o + h
            if future is None and t >= n:
                continue
            td = dates[t]
            for j, c in enumerate(CATS):
                hist = A[: o + 1, j]
                scale = max(hist[-8:].mean(), 1e-6)
                ly = A[t - 52, j] if t - 52 >= 0 else np.nan                      # same week last year (always <= origin because h < 52)
                ly8 = A[o - 59: o - 51, j].mean() if o - 59 >= 0 else np.nan        # the 8 weeks a year before the last 8 weeks
                s_t, s_o = cal_all.season.iloc[t], cal_all.season.iloc[o]
                woy = td.isocalendar().week
                rows.append(dict(
                    category=c, origin=o, h=h, target_idx=t, target_week=td, scale=scale, cat=j,
                    actual=A[t, j] if t < n else np.nan,
                    last_r=hist[-1] / scale, mean4_r=hist[-4:].mean() / scale, mean13_r=hist[-13:].mean() / scale,
                    ly_r=ly / scale, yoy=np.clip(scale / ly8, 0.3, 3) if ly8 == ly8 else np.nan,
                    t_peak=s_t == "Peak", t_low=s_t == "Low", t_normal=s_t == "Normal", o_peak=s_o == "Peak", o_low=s_o == "Low",
                    t_hol=cal_all.holiday_days.iloc[t], t_sin=np.sin(2 * np.pi * woy / 52), t_cos=np.cos(2 * np.pi * woy / 52),
                    t_promo=promo_all.iloc[t, j],
                    b1_naive=hist[-1], b2_avg4=hist[-4:].mean(), b3_ly=ly,
                    b4_ly_growth=ly * np.clip(scale / ly8, 0.3, 3) if ly8 == ly8 and ly == ly else np.nan))
    d = pd.DataFrame(rows)
    d[["t_peak", "t_low", "t_normal", "o_peak", "o_low"]] = d[["t_peak", "t_low", "t_normal", "o_peak", "o_low"]].astype(float)
    d["split"] = np.where(d.target_week <= TRAIN_END, "train", np.where(d.target_week <= VAL_END, "validation", "test"))
    d["y_ratio"] = d["actual"] / d["scale"]
    return d


# ------------------------------------------------------------------ metrics
def wape(a, f):
    return float(np.abs(f - a).sum() / a.sum())


def bias(a, f):
    return float((f - a).sum() / a.sum())


def fit(rows, cfg, seed=SEED):
    m = HistGradientBoostingRegressor(random_state=seed, categorical_features=[FEATURES.index("cat")], **cfg)
    m.fit(rows[FEATURES], rows["y_ratio"])
    return m


def predict(m, rows):
    return np.clip(m.predict(rows[FEATURES]), 0, None) * rows["scale"].values


def score_table(d, cols):
    out = []
    for name in cols:
        ok = d[name].notna()
        out.append(dict(method=name, rows=int(ok.sum()), wape=wape(d.actual[ok], d[name][ok]), bias=bias(d.actual[ok], d[name][ok])))
    return pd.DataFrame(out)


def total_wape(d, col):
    g = d.groupby(["h", "target_week"]).agg(actual=("actual", "sum"), f=(col, "sum")).reset_index()
    return wape(g.actual, g.f)


def block_bootstrap_diff(d, col_a, col_b, block=4, n=5000, seed=SEED):
    """95% CI for WAPE(col_a) - WAPE(col_b), resampling blocks of consecutive target weeks (errors in neighbouring weeks are related)."""
    wk = np.sort(d.target_week.unique()); blocks = [wk[i:i + block] for i in range(0, len(wk), block)]
    by = {b[0]: d[d.target_week.isin(b)] for b in blocks}
    ids = [b[0] for b in blocks]; rng = np.random.default_rng(seed); diffs = []
    pre = {k: (v.actual.sum(), np.abs(v[col_a] - v.actual).sum(), np.abs(v[col_b] - v.actual).sum()) for k, v in by.items()}
    for _ in range(n):
        s = np.array([pre[ids[i]] for i in rng.integers(0, len(ids), len(ids))])
        diffs.append(s[:, 1].sum() / s[:, 0].sum() - s[:, 2].sum() / s[:, 0].sum())
    return np.percentile(diffs, [2.5, 97.5])


# ------------------------------------------------------------------ main experiment
def run():
    q, cal, promo = load()
    d = make_rows(q, cal, promo)
    base_cols = ["b1_naive", "b2_avg4", "b3_ly", "b4_ly_growth"]
    train, val, test = (d[d.split == s] for s in ("train", "validation", "test"))

    # --- model selection on validation only
    sel = []
    for i, cfg in enumerate(CONFIGS):
        m = fit(train, cfg)
        sel.append(dict(config=i, **cfg, validation_wape=wape(val.actual, predict(m, val))))
    sel = pd.DataFrame(sel).sort_values("validation_wape")
    best = CONFIGS[int(sel.iloc[0].config)]
    m_val = fit(train, best); d.loc[val.index, "model"] = predict(m_val, val)

    # --- best baseline on validation (decided before looking at the test set)
    vb = val.dropna(subset=base_cols)
    base_val = pd.DataFrame({c: [wape(vb.actual, vb[c])] for c in base_cols}).T.rename(columns={0: "validation_wape"})
    best_base = base_val.validation_wape.idxmin()

    # --- final model: train + validation, scored once on test
    m_final = fit(d[d.split != "test"], best); d.loc[test.index, "model"] = predict(m_final, test)
    d["blend"] = 0.5 * d["model"] + 0.5 * d["b4_ly_growth"]            # simple 50/50 blend, added after seeing the validation peak weakness (see README)
    val_all = d[d.split == "validation"].copy()                          # every validation week, including those where last-year baselines do not exist yet
    ev = d[d.split.isin(["validation", "test"]) & d.model.notna()].copy()
    ev = ev.dropna(subset=base_cols)
    tst = ev[ev.split == "test"]
    perm = permutation_importance(m_val, val[FEATURES], val["y_ratio"], n_repeats=10, random_state=SEED, scoring="neg_mean_absolute_error")
    imp = pd.Series(perm.importances_mean, index=FEATURES).sort_values(ascending=False)
    return dict(q=q, cal=cal, promo=promo, d=d, ev=ev, val_all=val_all, val=ev[ev.split == "validation"], test=tst, selection=sel, best_cfg=best,
                base_val=base_val, best_base=best_base, importance=imp, m_final=m_final, base_cols=base_cols)


def next_four_weeks(res):
    """Forecast the 4 weeks after the data ends (origin = last full week, 21 Sep 2026) with the final model refitted on ALL data.
    Calendar facts for those weeks are copied from the same weeks one year earlier (364 days back): this is an assumption, see README."""
    q, cal, promo = res["q"], res["cal"], res["promo"]
    last = q.index[-1]
    fdates = [last + pd.Timedelta(weeks=h) for h in HORIZONS]
    prev = [x - pd.Timedelta(weeks=52) for x in fdates]
    fcal = pd.DataFrame({"season": cal.loc[prev, "season"].values, "holiday_days": cal.loc[prev, "holiday_days"].values}, index=pd.DatetimeIndex(fdates))
    fpromo = pd.DataFrame(0.0, index=pd.DatetimeIndex(fdates), columns=CATS)
    all_rows = make_rows(q, cal, promo)
    m_all = fit(all_rows, res["best_cfg"])
    fut = make_rows(q, cal, promo, future={"cal": fcal, "promo": fpromo})
    fut = fut[(fut.origin == len(q) - 1)].copy()
    fut["forecast"] = predict(m_all, fut)
    # 80% interval from the validation + test ratio errors of the final model
    fut["model_only"] = fut["forecast"]
    fut["forecast"] = 0.5 * fut["model_only"] + 0.5 * fut["b4_ly_growth"]     # recommended: the 50/50 blend (the model alone is weakest in the peak)
    ev = res["ev"]; r = (ev.actual / ev.blend).replace([np.inf, -np.inf], np.nan).dropna()
    lo, hi = r.quantile(0.10), r.quantile(0.90)
    fut["low80"], fut["high80"] = fut.forecast * lo, fut.forecast * hi
    fut["baseline_avg4"] = fut["b2_avg4"]; fut["baseline_last_year_x_growth"] = fut["b4_ly_growth"]
    return fut[["category", "h", "target_week", "forecast", "low80", "high80", "model_only", "baseline_avg4", "baseline_last_year_x_growth"]], (float(lo), float(hi))


def main():
    OUT.mkdir(exist_ok=True)
    res = run()
    ev, tst, val = res["ev"], res["test"], res["val"]
    cols = res["base_cols"] + ["model", "blend"]
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print("config selection (validation WAPE):\n", res["selection"].round(4).to_string(index=False))
    print("\nbaselines on validation:\n", res["base_val"].round(4), "\nbest baseline:", res["best_base"])
    for name, part in [("VALIDATION (model trained on train only)", val), ("TEST (model trained on train + validation)", tst)]:
        print(f"\n{name}  rows={len(part)}\n", score_table(part, cols).round(4).to_string(index=False))
        print("  total-level WAPE:", {c: round(total_wape(part, c), 4) for c in cols})
    lo, hi = block_bootstrap_diff(tst, "model", res["best_base"])
    print(f"\nTEST WAPE(model) - WAPE({res['best_base']}) 95% CI: {lo:.4f} to {hi:.4f}")
    va = res["val_all"]; cal = res["cal"]; va["season"] = va.target_week.map(cal.season)
    print("\nFULL validation (all %d rows, incl. the whole Oct-Dec 2025 peak), model vs baselines that always exist:" % len(va))
    for sname, g in [("all", va)] + list(va.groupby("season")):
        print(f"  {sname:7s} weeks={g.target_week.nunique():2d} model WAPE={wape(g.actual, g.model):.3f} (bias {bias(g.actual, g.model):+.3f})  avg4={wape(g.actual, g.b2_avg4):.3f}  naive={wape(g.actual, g.b1_naive):.3f}")
    print("\npermutation importance:\n", res["importance"].round(4).head(8))
    res["selection"].to_csv(OUT / "model_selection_validation.csv", index=False)
    pd.concat([score_table(val, cols).assign(split="validation"), score_table(tst, cols).assign(split="test")]).to_csv(OUT / "scores_overall.csv", index=False)
    ev[["category", "target_week", "origin", "h", "split", "actual", "model", "blend"] + res["base_cols"]].to_csv(OUT / "backtest_forecasts.csv", index=False)
    nf, (qlo, qhi) = next_four_weeks(res); nf.to_csv(OUT / "next_4_weeks.csv", index=False)
    print("\nnext 4 weeks (total):", nf.groupby("target_week")[["forecast", "low80", "high80"]].sum().round(0).to_string(), f"\nratio quantiles {qlo:.3f} {qhi:.3f}")


if __name__ == "__main__":
    main()
