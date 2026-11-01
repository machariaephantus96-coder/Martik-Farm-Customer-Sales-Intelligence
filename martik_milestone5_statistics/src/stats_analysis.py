#!/usr/bin/env python3
"""Milestone 5: hypothesis tests and confidence intervals on the cleaned Martik Farm data.

Four questions, each with its assumptions checked before a test is chosen:
  T1  Did a promotion raise sales of the promoted categories?         (5 promotions, paired by account, Holm-corrected)
  T2  Do customers who pay by M-Pesa spend more per order?            (naive vs adjusted for customer segment and customer)
  T3  How much higher is the Oct-Dec peak than the low season?        (weekly revenue, trend-adjusted, autocorrelation-robust)
  T4  Do customer segments differ in paying late?                     (chi-square + customer-level check)

Run after src/clean_data.py:   python src/stats_analysis.py
Outputs: stats/*.csv (all numbers), figures/s5_*.png. Everything is seeded (seed 42) and re-runnable.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint
from statsmodels.stats.stattools import durbin_watson

ROOT = Path(__file__).resolve().parents[1]
CLEAN, OUT = ROOT / "data_clean", ROOT / "stats"
RNG_SEED, N_BOOT, ALPHA = 42, 10_000, 0.05
CONTROL_CATS = ["Alliums", "Peppers & Chillies"]          # never promoted: used as the comparison group in T1
BASELINE_WEEKS = 8                                         # T1: compare with 8 weeks before and 8 weeks after


# ------------------------------------------------------------------ load
def load():
    d = {n: pd.read_csv(CLEAN / f"{n}.csv") for n in ["orders", "payments", "products", "promotions", "weekly_sales", "customers"]}
    fact = pd.read_csv(CLEAN / "sales_fact.csv", parse_dates=["order_date"])
    # volume at constant prices (Jan-2026 list price) so that price surges do not look like demand changes
    fact = fact.merge(d["products"][["product_id", "base_price_jan2026_kes"]], on="product_id")
    fact["volume_kes"] = fact["billed_qty"] * fact["base_price_jan2026_kes"]
    d["orders"]["order_date"] = pd.to_datetime(d["orders"]["order_date"])
    d["promotions"][["start_date", "end_date"]] = d["promotions"][["start_date", "end_date"]].apply(pd.to_datetime)
    d["weekly_sales"]["week_start"] = pd.to_datetime(d["weekly_sales"]["week_start"])
    d["fact"] = fact
    return d


def boot_ci(x, stat, n=N_BOOT, seed=RNG_SEED):
    """Percentile bootstrap CI of stat(x), resampling rows of x."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    vals = np.array([stat(x[rng.integers(0, len(x), len(x))]) for _ in range(n)])
    return np.percentile(vals, [2.5, 97.5])


def normality(x):
    x = np.asarray(x)
    sh = stats.shapiro(x if len(x) <= 5000 else np.random.default_rng(RNG_SEED).choice(x, 5000, replace=False))
    return dict(n=len(x), skew=round(float(stats.skew(x)), 2), shapiro_p=float(sh.pvalue))


# ------------------------------------------------------------------ T1 promotions
def _ratio_by_account(f, cats_num, cats_den, mask):
    g = f[mask]
    num = g[g["category"].isin(cats_num)].groupby("customer_id")["volume_kes"].sum()
    den = g[g["category"].isin(cats_den)].groupby("customer_id")["volume_kes"].sum()
    return (num / den).dropna().replace([np.inf, 0], np.nan).dropna()


def promo_effect(f, promos, row, cats_num, cats_den):
    """Per-account change in log[volume of promoted categories / volume of control categories], promo window vs baseline."""
    s, e = row.start_date, row.end_date
    other = [(r.start_date, r.end_date) for r in promos.itertuples() if r.promo_id != row.promo_id]
    in_promo = (f["order_date"] >= s) & (f["order_date"] <= e)
    lo, hi = s - pd.Timedelta(weeks=BASELINE_WEEKS), e + pd.Timedelta(weeks=BASELINE_WEEKS)
    base = ((f["order_date"] >= lo) & (f["order_date"] < s)) | ((f["order_date"] > e) & (f["order_date"] <= hi))
    base &= f["order_date"].between("2024-10-01", "2026-09-30")
    for a, b in other:                                    # keep other promotions' weeks out of the baseline
        base &= ~f["order_date"].between(a, b)
    r_p = _ratio_by_account(f, cats_num, cats_den, in_promo)
    r_b = _ratio_by_account(f, cats_num, cats_den, base)
    d = (np.log(r_p) - np.log(r_b)).dropna()
    return d, int(base.sum())


def t1_promotions(data):
    f = data["fact"]
    f = f[(f["is_account"] == 1) & (f["customer_id"] != "C001")]      # eligible accounts: B2B, excluding Java House (fixed contract prices)
    rows, details = [], {}
    for r in data["promotions"].itertuples():
        cats = [c.strip() for c in r.categories.split(";")]
        d, _ = promo_effect(f, data["promotions"], r, cats, CONTROL_CATS)
        t = stats.ttest_1samp(d, 0)
        w = stats.wilcoxon(d)
        lo, hi = boot_ci(d.values, np.mean)
        # placebo: two never-promoted categories against each other, same windows. Should show ~0 if the method is not biased.
        dp, _ = promo_effect(f, data["promotions"], r, [CONTROL_CATS[0]], [CONTROL_CATS[1]])
        tp = stats.ttest_1samp(dp, 0)
        nm = normality(d)
        rows.append(dict(promo_id=r.promo_id, promo_name=r.promo_name, categories=r.categories, discount_pct=r.discount_pct, accounts=len(d),
                         uplift_pct=100 * (np.exp(d.mean()) - 1), ci_low_pct=100 * (np.exp(lo) - 1), ci_high_pct=100 * (np.exp(hi) - 1),
                         t_p=t.pvalue, wilcoxon_p=w.pvalue, skew=nm["skew"], shapiro_p=nm["shapiro_p"],
                         share_of_accounts_up=float((d > 0).mean()),
                         placebo_uplift_pct=100 * (np.exp(dp.mean()) - 1), placebo_p=tp.pvalue))
        details[r.promo_id] = d
    res = pd.DataFrame(rows)
    res["t_p_holm"] = multipletests(res["t_p"], method="holm")[1]
    res["significant_5pct_holm"] = res["t_p_holm"] < ALPHA
    res["ci_halfwidth_pts"] = (res["ci_high_pct"] - res["ci_low_pct"]) / 2
    return res, details


def t1_pooled_fruit(details):
    """EXPLORATORY (decided after seeing the five results): the two January fruit promotions P01 and P04 used the same design,
    so pool them. Each account counts once (mean of its two changes) because the same accounts appear in both."""
    both = pd.concat([details["P01"].rename("P01"), details["P04"].rename("P04")], axis=1)
    d = both.mean(axis=1).dropna()
    lo, hi = boot_ci(d.values, np.mean)
    return dict(accounts=len(d), uplift_pct=100 * (np.exp(d.mean()) - 1), ci_low_pct=100 * (np.exp(lo) - 1), ci_high_pct=100 * (np.exp(hi) - 1),
                t_p=float(stats.ttest_1samp(d, 0).pvalue), wilcoxon_p=float(stats.wilcoxon(d).pvalue))


# ------------------------------------------------------------------ T2 M-Pesa
def t2_mpesa(data):
    o = data["orders"].merge(data["payments"][["order_id", "method"]], on="order_id")       # one payment per paid order
    o["log_total"] = np.log(o["order_total_kes"])
    o["mpesa"] = (o["method"] == "M-Pesa").astype(int)
    acc = o[o["is_account"] == 1].copy()
    out = {}

    # assumption checks
    out["mix"] = pd.crosstab(acc["segment"], acc["method"], normalize="index").mul(100).round(1)
    out["chi2_mix_p"] = float(stats.chi2_contingency(pd.crosstab(acc["segment"], acc["mpesa"]))[1])
    out["normality_raw"] = normality(acc["order_total_kes"]); out["normality_log"] = normality(acc["log_total"])
    out["levene_p"] = float(stats.levene(acc.loc[acc.mpesa == 1, "log_total"], acc.loc[acc.mpesa == 0, "log_total"]).pvalue)
    between = acc.groupby("customer_id")["log_total"].transform("mean").var() / acc["log_total"].var()
    out["share_variance_between_customers"] = float(between)

    rows = []
    def add(label, est, lo, hi, p, n, note=""):
        rows.append(dict(analysis=label, ratio=np.exp(est), pct_diff=100 * (np.exp(est) - 1), ci_low_pct=100 * (np.exp(lo) - 1),
                         ci_high_pct=100 * (np.exp(hi) - 1), p_value=p, n=n, note=note))

    # 1 naive: ignore who the customer is (all account orders)
    m = smf.ols("log_total ~ mpesa", acc).fit(cov_type="cluster", cov_kwds={"groups": acc["customer_id"]})
    ci = m.conf_int().loc["mpesa"]
    add("1 Naive: M-Pesa vs other methods, all account orders", m.params["mpesa"], ci[0], ci[1], m.pvalues["mpesa"], len(acc),
        "ignores that different customer types prefer different methods")
    mw = stats.mannwhitneyu(acc.loc[acc.mpesa == 1, "order_total_kes"], acc.loc[acc.mpesa == 0, "order_total_kes"])
    out["naive_mannwhitney_p"] = float(mw.pvalue)
    # 2 adjusted for segment
    m2 = smf.ols("log_total ~ mpesa + C(segment)", acc).fit(cov_type="cluster", cov_kwds={"groups": acc["customer_id"]})
    ci = m2.conf_int().loc["mpesa"]
    add("2 Adjusted for customer segment", m2.params["mpesa"], ci[0], ci[1], m2.pvalues["mpesa"], len(acc), "compares like with like by segment")
    # 3 adjusted for the individual customer (customer fixed effects)
    m3 = smf.ols("log_total ~ mpesa + C(customer_id)", acc).fit(cov_type="cluster", cov_kwds={"groups": acc["customer_id"]})
    ci = m3.conf_int().loc["mpesa"]
    add("3 Same customer, M-Pesa vs other methods (customer fixed effects)", m3.params["mpesa"], ci[0], ci[1], m3.pvalues["mpesa"], len(acc),
        "each customer is compared with itself")
    # 4 customer-level paired test as a check that does not rely on the regression
    g = acc.groupby(["customer_id", "mpesa"])["log_total"].agg(["mean", "size"]).unstack()
    ok = g[(g["size"][0] >= 10) & (g["size"][1] >= 10)]
    dd = (ok["mean"][1] - ok["mean"][0]).dropna()
    lo, hi = boot_ci(dd.values, np.mean)
    add("4 Customer-level paired check (accounts with 10+ orders of each kind)", dd.mean(), lo, hi, stats.ttest_1samp(dd, 0).pvalue, len(dd),
        f"Wilcoxon p = {stats.wilcoxon(dd).pvalue:.3g}")
    # 5 walk-in shop customers: M-Pesa vs cash (the only segment where both are common)
    w = o[o["is_account"] == 0]
    a, b = w.loc[w.method == "M-Pesa", "log_total"], w.loc[w.method == "Cash", "log_total"]
    diff = a.mean() - b.mean(); se = np.sqrt(a.var() / len(a) + b.var() / len(b))
    add("5 Walk-in sales: M-Pesa vs cash", diff, diff - 1.96 * se, diff + 1.96 * se, stats.ttest_ind(a, b, equal_var=False).pvalue, len(w),
        f"Mann-Whitney p = {stats.mannwhitneyu(a, b).pvalue:.3g}; walk-in rows are shop-level aggregates")
    # 6 within each segment where both kinds are common
    seg_rows = []
    for sname, gseg in acc.groupby("segment"):
        n1, n0 = int((gseg.mpesa == 1).sum()), int((gseg.mpesa == 0).sum())
        if min(n1, n0) < 50:
            continue
        ms = smf.ols("log_total ~ mpesa", gseg).fit(cov_type="cluster", cov_kwds={"groups": gseg["customer_id"]})
        ci = ms.conf_int().loc["mpesa"]
        seg_rows.append(dict(segment=sname, mpesa_orders=n1, other_orders=n0, pct_diff=100 * (np.exp(ms.params["mpesa"]) - 1),
                             ci_low_pct=100 * (np.exp(ci[0]) - 1), ci_high_pct=100 * (np.exp(ci[1]) - 1), p_value=ms.pvalues["mpesa"]))
    seg = pd.DataFrame(seg_rows)
    seg["p_holm"] = multipletests(seg["p_value"], method="holm")[1]
    out["table"], out["by_segment"] = pd.DataFrame(rows), seg
    out["medians"] = o.groupby("method")["order_total_kes"].agg(orders="size", mean="mean", median="median").round(0)
    return out


# ------------------------------------------------------------------ T3 peak vs low
def t3_season(data):
    w = data["weekly_sales"]
    w = w[w["category"] == "ALL"].sort_values("week_start").iloc[1:-1].copy()           # drop the two partial end weeks
    w["log_rev"] = np.log(w["revenue_kes"]); w["t"] = np.arange(len(w)) / 52.0           # t in years
    w["season"] = pd.Categorical(w["season"], ["Normal", "Low", "Peak"])
    m = smf.ols("log_rev ~ C(season) + t", w).fit()
    ols_se = m
    hac = smf.ols("log_rev ~ C(season) + t", w).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    dw = float(durbin_watson(m.resid))
    lb = float(acorr_ljungbox(m.resid, lags=[4]).iloc[0]["lb_pvalue"])
    pk, lo_ = hac.params["C(season)[T.Peak]"], hac.params["C(season)[T.Low]"]
    # peak vs low contrast with its own CI
    cn = hac.t_test("C(season)[T.Peak] - C(season)[T.Low] = 0")
    est = float(cn.effect[0]); ci = cn.conf_int()[0]
    res = dict(peak_vs_low_ratio=np.exp(est), ci_low=np.exp(ci[0]), ci_high=np.exp(ci[1]), p_value=float(cn.pvalue),
               peak_vs_normal_ratio=np.exp(pk), low_vs_normal_ratio=np.exp(lo_),
               naive_ci_low=np.exp(float(ols_se.t_test("C(season)[T.Peak] - C(season)[T.Low] = 0").conf_int()[0][0])),
               naive_ci_high=np.exp(float(ols_se.t_test("C(season)[T.Peak] - C(season)[T.Low] = 0").conf_int()[0][1])),
               trend_pct_per_year=100 * (np.exp(hac.params["t"]) - 1), durbin_watson=dw, ljungbox_p_lag4=lb,
               shapiro_p_resid=float(stats.shapiro(m.resid).pvalue), weeks=len(w),
               peak_weeks=int((w.season == "Peak").sum()), low_weeks=int((w.season == "Low").sum()))
    # simple check without a model: Welch t-test on log weekly revenue, peak vs low
    a, b = w.loc[w.season == "Peak", "log_rev"], w.loc[w.season == "Low", "log_rev"]
    res["welch_p_simple"] = float(stats.ttest_ind(a, b, equal_var=False).pvalue)
    res["simple_ratio"] = float(np.exp(a.mean() - b.mean()))
    # each peak season separately against the low weeks that follow/precede it in the same financial year
    yr = {}
    for label, lo_d, hi_d in [("Oct-Dec 2024 vs Jan 2025 + mid-2025", "2024-10-01", "2025-08-31"), ("Oct-Dec 2025 vs Jan 2026 + mid-2026", "2025-10-01", "2026-08-31")]:
        s = w[(w.week_start >= lo_d) & (w.week_start <= hi_d)]
        yr[label] = float(np.exp(s.loc[s.season == "Peak", "log_rev"].mean() - s.loc[s.season == "Low", "log_rev"].mean()))
    res["by_year"] = yr
    return res, w, hac


# ------------------------------------------------------------------ T4 late payment
def t4_late(data):
    o = data["orders"]
    p = o[(o["payment_status"] == "Paid") & (o["is_account"] == 1)].copy()
    p["late"] = (p["days_past_due"] > 0).astype(int)
    assert (p["late"] == p["is_paid_late"]).all(), "late flag must match days_past_due"
    tab = pd.crosstab(p["segment"], p["late"])
    chi2, pval, dof, exp = stats.chi2_contingency(tab)
    n = tab.values.sum(); v = float(np.sqrt(chi2 / (n * (min(tab.shape) - 1))))
    rows = []
    for s_, r in tab.iterrows():
        k, nn = int(r[1]), int(r.sum())
        lo, hi = proportion_confint(k, nn, method="wilson")
        sub = p[p["segment"] == s_]
        rows.append(dict(segment=s_, paid_invoices=nn, late_pct=100 * k / nn, ci_low_pct=100 * lo, ci_high_pct=100 * hi,
                         avg_days_past_due=sub["days_past_due"].mean(), avg_terms_days=sub["payment_terms_days"].mean(), customers=sub["customer_id"].nunique()))
    t = pd.DataFrame(rows).sort_values("late_pct", ascending=False)
    # customer-level check: each account counts once, so one big account cannot dominate the result
    c = p.groupby(["segment", "customer_id"])["late"].mean().reset_index()
    groups = [g["late"].values for _, g in c.groupby("segment") if len(g) >= 3]
    kw = stats.kruskal(*groups)
    # hotels vs restaurants head to head
    h, r_ = p[p.segment == "Hotel/Lodge"]["late"], p[p.segment == "Restaurant"]["late"]
    z = proportion_confint  # noqa (kept for clarity)
    diff = h.mean() - r_.mean(); se = np.sqrt(h.var() / len(h) + r_.var() / len(r_))
    hc = c[c.segment == "Hotel/Lodge"]["late"]; rc = c[c.segment == "Restaurant"]["late"]
    mw = stats.mannwhitneyu(hc, rc)
    res = dict(chi2=float(chi2), dof=int(dof), p_value=float(pval), cramers_v=v, min_expected_count=float(exp.min()), n_invoices=int(n),
               customer_level_kruskal_p=float(kw.pvalue), customer_level_groups=len(groups),
               hotel_vs_restaurant_diff_pts=100 * diff, hotel_vs_restaurant_ci=(100 * (diff - 1.96 * se), 100 * (diff + 1.96 * se)),
               hotel_vs_restaurant_customer_level_p=float(mw.pvalue),
               hotel_customers=len(hc), restaurant_customers=len(rc))
    return t, res


# ------------------------------------------------------------------ main
def main():
    OUT.mkdir(exist_ok=True)
    data = load()
    t1, d1 = t1_promotions(data); t1.to_csv(OUT / "t1_promotions.csv", index=False)
    pooled = t1_pooled_fruit(d1); pd.Series(pooled).to_csv(OUT / "t1_pooled_fruit_exploratory.csv", header=["value"])
    print("pooled fruit (exploratory):", {k: round(v, 4) for k, v in pooled.items()})
    t2 = t2_mpesa(data); t2["table"].to_csv(OUT / "t2_mpesa.csv", index=False); t2["by_segment"].to_csv(OUT / "t2_mpesa_by_segment.csv", index=False)
    t3, wk, _ = t3_season(data); pd.Series({k: v for k, v in t3.items() if k != "by_year"}).to_csv(OUT / "t3_season.csv", header=["value"])
    t4, r4 = t4_late(data); t4.to_csv(OUT / "t4_late_by_segment.csv", index=False); pd.Series(r4).to_csv(OUT / "t4_tests.csv", header=["value"])
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print("\nT1\n", t1.round(3).to_string(index=False))
    print("\nT2\n", t2["table"].round(3).to_string(index=False)); print(t2["by_segment"].round(3).to_string(index=False))
    print({k: v for k, v in t2.items() if k not in ("table", "by_segment", "mix", "medians")})
    print("\nT3\n", t3)
    print("\nT4\n", t4.round(2).to_string(index=False)); print(r4)


if __name__ == "__main__":
    main()
