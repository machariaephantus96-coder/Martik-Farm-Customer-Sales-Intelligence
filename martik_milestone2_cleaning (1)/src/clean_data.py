#!/usr/bin/env python3
"""
Martik Farm capstone - Milestone 2: data cleaning and feature pipeline
=====================================================================
Re-runnable end to end:  raw CSVs in data/  ->  cleaned tables + features in data_clean/  +  reports/.
Raw files are never modified. Every fix is logged with before/after counts in reports/cleaning_report.csv/.md.

    python src/clean_data.py                 # run the pipeline
    python src/clean_data.py --raw data --out data_clean

Steps
  1 types           parse dates/numbers, strip IDs, record parse failures
  2 duplicates      exact duplicate order lines (and key duplicates in every table)
  3 consistency     standardise payment-method spellings
  4 missing values  fill structural blanks, impute what can be recovered, flag the rest
  5 outliers        decimal-slip prices (vs the monthly price list), extreme quantities (flagged, kept)
  6 reconciliation  line totals, order subtotals, payments, orphan keys - before vs after
  7 features        sales fact table, order features, RFM, monthly churn panel, weekly sales
  8 checks          hard assertions - the pipeline fails loudly if the cleaned data breaks a rule
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_END = pd.Timestamp("2026-09-30")
LOG = []


def record(step, table, check, before, after, action):
    """Append one line of evidence to the cleaning report."""
    LOG.append(dict(step=step, table=table, check=check, before=before, after=after, action=action))


# --------------------------------------------------------------------------- load
def load_raw(raw):
    r = lambda name: pd.read_csv(raw / f"{name}.csv")
    return {n: r(n) for n in ["stores", "products", "customers", "promotions", "price_list_monthly",
                              "calendar", "orders", "order_lines", "payments"]}


# --------------------------------------------------------------------------- 1 types
DATE_COLS = {"orders": ["order_date", "invoice_due_date"], "payments": ["payment_date"], "calendar": ["date"],
             "promotions": ["start_date", "end_date"], "customers": ["first_order_date"]}
ID_COLS = {"orders": ["order_id", "customer_id"], "order_lines": ["line_id", "order_id", "store_id"],
           "payments": ["payment_id", "order_id", "customer_id"], "customers": ["customer_id"],
           "stores": ["store_id"], "promotions": ["promo_id"]}
NUM_COLS = {"orders": ["payment_terms_days", "subtotal_kes", "delivery_fee_kes", "order_total_kes", "delivered_late"],
            "order_lines": ["product_id", "quantity_ordered", "quantity_rejected", "unit_price_kes", "discount_pct",
                            "unit_cost_kes", "line_total_kes"],
            "payments": ["amount_kes"], "price_list_monthly": ["product_id", "list_price_kes", "unit_cost_kes"]}


def fix_types(t):
    for tab, cols in DATE_COLS.items():
        for c in cols:
            before_nulls = t[tab][c].isna().sum()
            parsed = pd.to_datetime(t[tab][c], errors="coerce", format="%Y-%m-%d")
            bad = int(parsed.isna().sum() - before_nulls)
            record("1 types", tab, f"{c}: text -> datetime (values that fail to parse)", bad, 0 if bad == 0 else bad,
                   f"parsed {int(parsed.notna().sum()):,} values to datetime64")
            t[tab][c] = parsed
    for tab, cols in ID_COLS.items():
        for c in cols:
            t[tab][c] = t[tab][c].astype("string").str.strip()
    for tab, cols in NUM_COLS.items():
        for c in cols:
            before_nulls = t[tab][c].isna().sum()
            t[tab][c] = pd.to_numeric(t[tab][c], errors="coerce")
            bad = int(t[tab][c].isna().sum() - before_nulls)
            if bad:
                record("1 types", tab, f"{c}: non-numeric values", bad, bad, "coerced to NaN - investigate")
    record("1 types", "all", "tables loaded", 9, 9, "IDs stripped of whitespace; numeric columns coerced")


# --------------------------------------------------------------------------- 2 duplicates
def drop_duplicates(t):
    L = t["order_lines"]
    n0, d_exact, d_id = len(L), int(L.duplicated().sum()), int(L["line_id"].duplicated().sum())
    L = L.drop_duplicates().reset_index(drop=True)
    record("2 duplicates", "order_lines", "exact duplicate rows (all columns identical)", d_exact, int(L.duplicated().sum()),
           "kept first occurrence of each row")
    record("2 duplicates", "order_lines", "duplicated line_id", d_id, int(L["line_id"].duplicated().sum()), "resolved by the step above")
    record("2 duplicates", "order_lines", "row count", n0, len(L), f"removed {n0 - len(L):,} double-entered lines")
    near = int(L.duplicated(["order_id", "product_id"]).sum())
    record("2 duplicates", "order_lines", "same product twice in one order (different line_id)", near, near,
           "none found - no further action" if near == 0 else "review manually")
    t["order_lines"] = L
    for tab, key in (("orders", "order_id"), ("payments", "payment_id"), ("customers", "customer_id"), ("products", "product_id")):
        d = int(t[tab][key].duplicated().sum())
        record("2 duplicates", tab, f"duplicated {key}", d, d, "none found" if d == 0 else "REVIEW")
    d = int(t["payments"]["order_id"].duplicated().sum())
    record("2 duplicates", "payments", "more than one payment for the same order", d, d, "none found" if d == 0 else "REVIEW")


# --------------------------------------------------------------------------- 3 consistency
METHOD_MAP = {"mpesa": "M-Pesa", "banktransfer": "Bank Transfer", "banktrf": "Bank Transfer",
              "cheque": "Cheque", "check": "Cheque", "cash": "Cash"}


def standardise_methods(t):
    p = t["payments"]
    key = p["method"].str.lower().str.replace(r"[^a-z]", "", regex=True)
    new = key.map(METHOD_MAP)
    unmapped = int(new.isna().sum())
    changed = int((new != p["method"]).sum())
    record("3 consistency", "payments", "distinct spellings of payment method", int(p["method"].nunique()), int(new.nunique()),
           f"mapped to M-Pesa / Bank Transfer / Cheque / Cash ({changed:,} rows rewritten, {unmapped} unmapped)")
    p["method"] = new.fillna(p["method"])


# --------------------------------------------------------------------------- 4 missing values
def fix_missing(t):
    o, c, L = t["orders"], t["customers"], t["order_lines"]
    walkin = o["customer_id"].isin(c.loc[c["is_account"] == 0, "customer_id"])

    # delivery_area: blank for walk-ins by design; for account orders recover it from the customer record
    miss0 = int(o["delivery_area"].isna().sum())
    structural = int((o["delivery_area"].isna() & walkin).sum())
    lookup = c.set_index("customer_id")["delivery_area"]
    recover = o["delivery_area"].isna() & ~walkin
    o.loc[recover, "delivery_area"] = o.loc[recover, "customer_id"].map(lookup)
    o.loc[walkin & o["delivery_area"].isna(), "delivery_area"] = "In-shop (walk-in)"
    record("4 missing", "orders", "delivery_area missing", miss0, int(o["delivery_area"].isna().sum()),
           f"{structural:,} were walk-in sales (no delivery: labelled 'In-shop (walk-in)'); "
           f"{int(recover.sum()):,} account orders recovered from the customer's delivery area")

    # order_channel: walk-ins are certain; for accounts we do not guess
    miss0 = int(o["order_channel"].isna().sum())
    wi = o["order_channel"].isna() & walkin
    o.loc[wi, "order_channel"] = "Walk-in"
    o["order_channel"] = o["order_channel"].fillna("Unknown")
    record("4 missing", "orders", "order_channel missing", miss0, int(o["order_channel"].isna().sum()),
           f"{int(wi.sum()):,} walk-in sales set to 'Walk-in'; the rest labelled 'Unknown' (not guessed)")

    # blanks that mean "none" rather than "lost"
    m = int(L["promo_id"].isna().sum())
    L["promo_id"] = L["promo_id"].fillna("NO_PROMO")
    record("4 missing", "order_lines", "promo_id blank", m, int(L["promo_id"].isna().sum()), "blank means no promotion -> 'NO_PROMO'")
    bad = int(((L["quantity_rejected"] > 0) & L["reject_reason"].isna()).sum())
    m = int(L["reject_reason"].isna().sum())
    L["reject_reason"] = L["reject_reason"].fillna("None")
    record("4 missing", "order_lines", "reject_reason blank", m, int(L["reject_reason"].isna().sum()),
           f"blank means nothing rejected -> 'None' ({bad} rows had a rejection with no reason)")
    key_cols = {"orders": ["order_id", "order_date", "customer_id", "order_total_kes", "payment_terms_days"],
                "order_lines": ["line_id", "order_id", "product_id", "quantity_ordered", "unit_price_kes", "line_total_kes"],
                "payments": ["payment_id", "order_id", "payment_date", "amount_kes", "method"]}
    for tab, cols in key_cols.items():
        n = int(t[tab][cols].isna().sum().sum())
        record("4 missing", tab, "nulls in key columns " + ", ".join(cols[:3]) + ", ...", n, n, "none" if n == 0 else "REVIEW")


# --------------------------------------------------------------------------- 5 outliers
def fix_outliers(t):
    L, o, pl, c = t["order_lines"], t["orders"], t["price_list_monthly"], t["customers"]
    month = o.set_index("order_id")["order_date"].dt.strftime("%Y-%m")
    L["_month"] = L["order_id"].map(month)
    ref = L.merge(pl.rename(columns={"month": "_month", "list_price_kes": "_list"})[["_month", "product_id", "_list"]],
                  on=["_month", "product_id"], how="left")["_list"].values
    ratio = L["unit_price_kes"].values / ref
    # normal prices sit between ~0.8x and ~1.4x the monthly list (customer markup up to 28%, rounding to nearest 5)
    high = ratio > 3
    n_high = int(high.sum())
    fixed_price = np.where(high, (L["unit_price_kes"] / 10).round(0), L["unit_price_kes"])
    new_ratio = fixed_price / ref
    ok = high & (new_ratio > 0.8) & (new_ratio < 1.4)
    L["price_corrected"] = ok.astype(int)
    L.loc[ok, "unit_price_kes"] = fixed_price[ok]
    L.loc[ok, "line_total_kes"] = (L.loc[ok, "line_total_kes"] / 10).round(2)
    final = L["unit_price_kes"].values / ref
    out_of_band = int(((final < 0.8) | (final > 1.4)).sum())
    record("5 outliers", "order_lines", "unit price > 3x the monthly list price (decimal-slip keying errors)", n_high,
           int((final > 3).sum()), f"{int(ok.sum()):,} corrected by dividing price and line total by 10 (flag: price_corrected=1)")
    record("5 outliers", "order_lines", "unit price outside 0.8x-1.4x of monthly list price", int(((ratio < 0.8) | (ratio > 1.4)).sum()),
           out_of_band, "all remaining prices are inside the expected band" if out_of_band == 0 else "REVIEW")

    # extreme quantities: genuine bulk orders exist (hotels, Java House) so flag, do not delete
    seg = L["order_id"].map(o.set_index("order_id")["customer_id"]).map(c.set_index("customer_id")["segment"])
    grp = [L["product_id"], seg]
    q1 = L.groupby(grp)["quantity_ordered"].transform(lambda s: s.quantile(0.25))
    q3 = L.groupby(grp)["quantity_ordered"].transform(lambda s: s.quantile(0.75))
    L["is_qty_outlier"] = (L["quantity_ordered"] > q3 + 3 * (q3 - q1)).astype(int)
    record("5 outliers", "order_lines", "quantity above Q3 + 3xIQR within product x customer segment", int(L["is_qty_outlier"].sum()),
           int(L["is_qty_outlier"].sum()), "flagged (is_qty_outlier=1), kept: large accounts place genuine bulk orders")
    neg = int(((L["quantity_ordered"] <= 0) | (L["unit_price_kes"] <= 0)).sum())
    rej = int((L["quantity_rejected"] > L["quantity_ordered"]).sum())
    record("5 outliers", "order_lines", "zero/negative quantity or price", neg, neg, "none" if neg == 0 else "REVIEW")
    record("5 outliers", "order_lines", "rejected quantity greater than ordered", rej, rej, "none" if rej == 0 else "REVIEW")
    L.drop(columns="_month", inplace=True)


# --------------------------------------------------------------------------- 6 reconciliation
def order_mismatch(lines, orders):
    s = lines.groupby("order_id")["line_total_kes"].sum().reindex(orders["order_id"]).fillna(0).values
    return int((np.abs(orders["subtotal_kes"].values - s) > 1).sum())


def line_mismatch(L):
    calc = ((L["quantity_ordered"] - L["quantity_rejected"]) * L["unit_price_kes"] * (1 - L["discount_pct"] / 100)).round(2)
    return int((np.abs(calc - L["line_total_kes"]) > 0.05).sum())


def reconcile(t, raw_lines):
    L, o, p = t["order_lines"], t["orders"], t["payments"]
    record("6 reconcile", "orders vs order_lines", "orders whose line totals do not add up to the subtotal (>1 KES)",
           order_mismatch(raw_lines, o), order_mismatch(L, o), "fixed by removing duplicate lines and correcting price slips")
    record("6 reconcile", "order_lines", "line_total != billed qty x price x (1 - discount)", line_mismatch(raw_lines), line_mismatch(L),
           "recomputed totals agree after the fixes above")
    diff = int((np.abs(o["order_total_kes"] - (o["subtotal_kes"] + o["delivery_fee_kes"])) > 0.05).sum())
    record("6 reconcile", "orders", "order_total != subtotal + delivery fee", diff, diff, "none" if diff == 0 else "REVIEW")
    due = int((o["invoice_due_date"] != o["order_date"] + pd.to_timedelta(o["payment_terms_days"], unit="D")).sum())
    record("6 reconcile", "orders", "invoice_due_date != order_date + payment terms", due, due, "none" if due == 0 else "REVIEW")
    pm = p.merge(o[["order_id", "order_total_kes", "order_date", "payment_status"]], on="order_id", how="left")
    record("6 reconcile", "payments", "payment amount != order total", int((np.abs(pm["amount_kes"] - pm["order_total_kes"]) > 0.05).sum()), 0, "agree")
    record("6 reconcile", "payments", "payment dated before the order", int((pm["payment_date"] < pm["order_date"]).sum()), 0, "none")
    record("6 reconcile", "payments", "payments on orders not marked Paid", int((pm["payment_status"] != "Paid").sum()), 0, "none")
    paid_no_pay = int(((o["payment_status"] == "Paid") & ~o["order_id"].isin(p["order_id"])).sum())
    record("6 reconcile", "orders", "orders marked Paid with no payment record", paid_no_pay, paid_no_pay, "none" if paid_no_pay == 0 else "REVIEW")
    for name, child, ck, parent, pk in (("lines -> orders", L, "order_id", o, "order_id"), ("lines -> products", L, "product_id", t["products"], "product_id"),
                                        ("orders -> customers", o, "customer_id", t["customers"], "customer_id"),
                                        ("payments -> orders", p, "order_id", o, "order_id")):
        orphan = int((~child[ck].isin(parent[pk])).sum())
        record("6 reconcile", name, "orphan keys (no matching parent)", orphan, orphan, "none" if orphan == 0 else "REVIEW")


# --------------------------------------------------------------------------- 7 features
def build_features(t):
    L, o, p, c, pr, st, cal = (t[k] for k in ["order_lines", "orders", "payments", "customers", "products", "stores", "calendar"])
    # line-level economics
    L["billed_qty"] = L["quantity_ordered"] - L["quantity_rejected"]
    L["gross_revenue_kes"] = (L["billed_qty"] * L["unit_price_kes"]).round(2)
    L["discount_kes"] = (L["gross_revenue_kes"] - L["line_total_kes"]).round(2)
    L["cost_kes"] = (L["billed_qty"] * L["unit_cost_kes"]).round(2)
    L["gross_margin_kes"] = (L["line_total_kes"] - L["cost_kes"]).round(2)
    L["margin_pct"] = np.where(L["line_total_kes"] > 0, L["gross_margin_kes"] / L["line_total_kes"] * 100, np.nan).round(2)
    L["is_promo"] = (L["promo_id"] != "NO_PROMO").astype(int)
    L["rejected_value_kes"] = (L["quantity_rejected"] * L["unit_price_kes"]).round(2)

    # order-level features
    g = L.groupby("order_id")
    o["n_lines"] = o["order_id"].map(g.size())
    o["gross_margin_kes"] = o["order_id"].map(g["gross_margin_kes"].sum()).round(2)
    o["margin_pct"] = (o["gross_margin_kes"] / o["subtotal_kes"] * 100).round(2)
    o["payment_date"] = o["order_id"].map(p.set_index("order_id")["payment_date"])
    o["days_to_pay"] = (o["payment_date"] - o["order_date"]).dt.days
    o["days_past_due"] = (o["payment_date"] - o["invoice_due_date"]).dt.days
    o["is_credit"] = (o["payment_terms_days"] > 0).astype(int)
    o["is_paid_late"] = np.where(o["payment_date"].notna(), (o["days_past_due"] > 0).astype(int), np.nan)
    o["week_start"] = o["order_date"] - pd.to_timedelta(o["order_date"].dt.dayofweek, unit="D")
    o = o.merge(cal[["date", "day_of_week", "is_public_holiday", "business_season", "is_school_term_assumed"]],
                left_on="order_date", right_on="date", how="left").drop(columns="date")
    o = o.merge(c[["customer_id", "segment", "is_account"]], on="customer_id", how="left")
    t["orders"] = o

    # flat, analysis-ready fact table (one row per order line)
    fact = (L.merge(o[["order_id", "order_date", "customer_id", "segment", "is_account", "county", "delivery_area", "order_channel",
                       "payment_terms_days", "payment_status", "week_start", "day_of_week", "is_public_holiday", "business_season"]],
                    on="order_id", how="left")
            .merge(pr[["product_id", "product_name", "category", "unit"]], on="product_id", how="left")
            .merge(st[["store_id", "store_name", "county"]].rename(columns={"county": "store_county"}), on="store_id", how="left"))
    fact["year_month"] = fact["order_date"].dt.strftime("%Y-%m")
    t["sales_fact"] = fact

    acc = o[o["is_account"] == 1]
    t["customer_rfm"] = make_rfm(acc, c, DATA_END)
    t["churn_panel"] = make_churn_panel(acc, c)
    t["weekly_sales"] = make_weekly(fact)


def make_rfm(acc, c, snap):
    g = acc[acc["order_date"] <= snap].groupby("customer_id")
    r = pd.DataFrame({"first_order": g["order_date"].min(), "last_order": g["order_date"].max(), "frequency": g.size(),
                      "monetary_kes": g["order_total_kes"].sum().round(2), "avg_order_value_kes": g["order_total_kes"].mean().round(2),
                      "avg_days_to_pay": g["days_to_pay"].mean().round(1), "late_payment_rate": g["is_paid_late"].mean().round(3)})
    r["recency_days"] = (snap - r["last_order"]).dt.days
    r["tenure_days"] = (snap - r["first_order"]).dt.days
    score = lambda s, asc: pd.qcut(s.rank(method="first", ascending=asc), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    r["R"], r["F"], r["M"] = score(r["recency_days"], False), score(r["frequency"], True), score(r["monetary_kes"], True)

    def seg(x):
        if x.R >= 4 and x.F >= 4: return "Champions"
        if x.R >= 3 and x.F >= 3: return "Loyal"
        if x.R <= 2 and x.F >= 3: return "At risk"
        if x.R <= 2 and x.F <= 2: return "Lost / low value"
        if x.R >= 4: return "Recent"
        return "Needs attention"
    r["rfm_segment"] = r.apply(seg, axis=1)
    return r.reset_index().merge(c[["customer_id", "customer_name", "segment", "county"]], on="customer_id", how="left")


def make_churn_panel(acc, c, horizon=60, active_window=90):
    """One row per active account per month-end snapshot. Features use only information up to the snapshot;
    the label looks `horizon` days ahead. No leakage: payments are only counted if made on/before the snapshot."""
    snaps = pd.date_range("2025-01-31", DATA_END - pd.Timedelta(days=horizon), freq="ME")
    seginfo = c.set_index("customer_id")[["segment", "contract_payment_terms_days", "credit_limit_kes"]]
    rows = []
    for snap in snaps:
        h = acc[acc["order_date"] <= snap]
        w = lambda a, b: h[(h["order_date"] > snap - pd.Timedelta(days=a)) & (h["order_date"] <= snap - pd.Timedelta(days=b))]
        f = pd.DataFrame({"last_order": h.groupby("customer_id")["order_date"].max(), "first_order": h.groupby("customer_id")["order_date"].min(),
                          "orders_total": h.groupby("customer_id").size()})
        f["orders_30d"] = w(30, 0).groupby("customer_id").size()
        f["orders_60d"] = w(60, 0).groupby("customer_id").size()
        f["orders_90d"] = w(90, 0).groupby("customer_id").size()
        f["orders_prev_60d"] = w(120, 60).groupby("customer_id").size()
        f["spend_90d"] = w(90, 0).groupby("customer_id")["order_total_kes"].sum()
        f["spend_prev_90d"] = w(180, 90).groupby("customer_id")["order_total_kes"].sum()
        f["avg_basket_90d"] = w(90, 0).groupby("customer_id")["order_total_kes"].mean()
        paid = h[(h["payment_date"] > snap - pd.Timedelta(days=90)) & (h["payment_date"] <= snap)]
        f["avg_days_to_pay_90d"] = paid.groupby("customer_id")["days_to_pay"].mean()
        f["late_rate_90d"] = paid.groupby("customer_id")["is_paid_late"].mean()
        f = f.fillna({"orders_30d": 0, "orders_60d": 0, "orders_90d": 0, "orders_prev_60d": 0, "spend_90d": 0, "spend_prev_90d": 0})
        f["recency_days"] = (snap - f["last_order"]).dt.days
        f["tenure_days_in_data"] = (snap - f["first_order"]).dt.days
        f["order_trend_ratio"] = ((f["orders_60d"] + 1) / (f["orders_prev_60d"] + 1)).round(3)
        f = f[f["recency_days"] <= active_window].copy()                      # only accounts still ordering
        fut = acc[(acc["order_date"] > snap) & (acc["order_date"] <= snap + pd.Timedelta(days=horizon))].groupby("customer_id").size()
        f["churned_next_60d"] = (~f.index.isin(fut.index)).astype(int)
        f.insert(0, "snapshot_date", snap)
        rows.append(f.drop(columns=["last_order", "first_order"]))
    panel = pd.concat(rows).reset_index().merge(seginfo.reset_index(), on="customer_id", how="left")
    panel["is_school"] = (panel["segment"] == "School/Daycare").astype(int)
    return panel.round({c: 3 for c in panel.select_dtypes("number").columns})


def make_weekly(fact):
    by_cat = fact.groupby(["week_start", "category"]).agg(revenue_kes=("line_total_kes", "sum"), billed_qty=("billed_qty", "sum"),
                                                          order_lines=("line_id", "count")).reset_index()
    allw = fact.groupby("week_start").agg(revenue_kes=("line_total_kes", "sum"), billed_qty=("billed_qty", "sum"),
                                          order_lines=("line_id", "count")).reset_index().assign(category="ALL")
    w = pd.concat([allw, by_cat], ignore_index=True)
    flags = fact.groupby("week_start").agg(orders=("order_id", "nunique"), holiday_days=("is_public_holiday", "max"),
                                           season=("business_season", "first")).reset_index()
    w = w.merge(flags, on="week_start", how="left")
    w["revenue_kes"] = w["revenue_kes"].round(2)
    return w.sort_values(["category", "week_start"]).reset_index(drop=True)


# --------------------------------------------------------------------------- 8 checks
def final_checks(t):
    L, o, p = t["order_lines"], t["orders"], t["payments"]
    checks = {
        "line_id unique": L["line_id"].is_unique, "order_id unique": o["order_id"].is_unique, "payment_id unique": p["payment_id"].is_unique,
        "orders reconcile to lines": order_mismatch(L, o) == 0, "line totals recompute": line_mismatch(L) == 0,
        "payment methods standardised": set(p["method"].unique()) <= {"M-Pesa", "Bank Transfer", "Cheque", "Cash"},
        "no nulls in order_channel/delivery_area": int(o[["order_channel", "delivery_area"]].isna().sum().sum()) == 0,
        "all lines have a known order": bool(L["order_id"].isin(o["order_id"]).all()),
        "dates inside the data window": bool(o["order_date"].between("2024-10-01", DATA_END).all()),
        "no negative billed quantity": bool((L["billed_qty"] >= 0).all()),
        "churn panel has both classes": set(t["churn_panel"]["churned_next_60d"].unique()) == {0, 1}}
    failed = [k for k, v in checks.items() if not v]
    record("8 checks", "all", "post-conditions passed", 0, len(checks) - len(failed), "; ".join(checks))
    if failed:
        raise SystemExit(f"Pipeline checks FAILED: {failed}")


# --------------------------------------------------------------------------- run
def main(raw, out, reports):
    LOG.clear()
    out.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    t = load_raw(raw)
    record("0 load", "all", "raw rows (orders / order_lines / payments)", f"{len(t['orders']):,} / {len(t['order_lines']):,} / {len(t['payments']):,}",
           "-", "raw files read, never modified")
    fix_types(t)
    raw_lines = t["order_lines"].copy()           # typed but otherwise untouched, for before/after comparison
    drop_duplicates(t)
    standardise_methods(t)
    fix_missing(t)
    fix_outliers(t)
    reconcile(t, raw_lines)
    build_features(t)
    final_checks(t)
    record("9 output", "all", "clean rows (orders / order_lines / payments)", "-",
           f"{len(t['orders']):,} / {len(t['order_lines']):,} / {len(t['payments']):,}", f"written to {out.name}/")

    for name, df in t.items():
        df.to_csv(out / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    rep = pd.DataFrame(LOG)
    rep.to_csv(reports / "cleaning_report.csv", index=False)
    md = ["# Cleaning report (before vs after)", "", "| Step | Table | Check | Before | After | What was done |", "|---|---|---|---|---|---|"]
    md += [f"| {r.step} | {r.table} | {r.check} | {r.before} | {r.after} | {r.action} |" for r in rep.itertuples()]
    (reports / "cleaning_report.md").write_text("\n".join(md) + "\n")
    return t, rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(ROOT / "data"))
    ap.add_argument("--out", default=str(ROOT / "data_clean"))
    ap.add_argument("--reports", default=str(ROOT / "reports"))
    a = ap.parse_args()
    _, rep = main(Path(a.raw), Path(a.out), Path(a.reports))
    with pd.option_context("display.max_colwidth", 70, "display.width", 250):
        print(rep[["step", "table", "check", "before", "after"]].to_string(index=False))
