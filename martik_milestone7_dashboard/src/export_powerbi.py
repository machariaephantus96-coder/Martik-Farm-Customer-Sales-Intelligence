#!/usr/bin/env python3
"""Milestone 7: export a star schema for Power BI Desktop to powerbi/data/*.csv.  Run after the earlier milestones.
Accounts are labelled 'C101 Restaurant' (id + segment); customer names are left out on purpose (synthetic figures must not be attributed to real businesses)."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
C, OUT = ROOT / "data_clean", ROOT / "powerbi" / "data"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cust = pd.read_csv(C / "customers.csv"); cust["customer_label"] = cust.customer_id + " " + cust.segment
    dim_cust = cust[["customer_id", "customer_label", "segment", "delivery_area", "county", "first_order_date", "contract_payment_terms_days", "credit_limit_kes", "is_account"]]
    dim_cust.to_csv(OUT / "DimCustomer.csv", index=False)
    pd.read_csv(C / "products.csv")[["product_id", "product_name", "category", "unit", "base_price_jan2026_kes", "source_store_id", "is_imported", "is_peak_season_premium"]].to_csv(OUT / "DimProduct.csv", index=False)
    st = pd.read_csv(C / "stores.csv")[["store_id", "store_name", "town", "county", "role"]]; st.to_csv(OUT / "DimStore.csv", index=False)
    cal = pd.read_csv(C / "calendar.csv", parse_dates=["date"])
    cal["week_start"] = cal.date - pd.to_timedelta(cal.date.dt.weekday, unit="D")
    cal["month_start"] = cal.date.values.astype("datetime64[M]")
    cal["month_label"] = cal.month.map(lambda m: MONTHS[m - 1]) + " " + (cal.year % 100).astype(str)
    cal["month_sort"] = cal.year * 100 + cal.month
    cal[["date", "year", "month", "month_name", "month_start", "month_label", "month_sort", "week_start", "day_of_week", "is_weekend", "is_public_holiday", "holiday_name", "business_season", "is_school_term_assumed"]].to_csv(OUT / "DimDate.csv", index=False)
    f = pd.read_csv(C / "sales_fact.csv")
    f[["line_id", "order_id", "order_date", "customer_id", "product_id", "store_id", "billed_qty", "unit_price_kes", "discount_kes", "line_total_kes", "cost_kes", "gross_margin_kes", "promo_id", "is_promo"]].to_csv(OUT / "FactSales.csv", index=False)
    o = pd.read_csv(C / "orders.csv")
    o[["order_id", "order_date", "customer_id", "order_channel", "payment_status", "subtotal_kes", "delivery_fee_kes", "order_total_kes", "payment_terms_days", "invoice_due_date", "payment_date", "days_to_pay", "days_past_due", "is_paid_late", "is_account"]].to_csv(OUT / "FactOrders.csv", index=False)
    # credit exposure per account (unpaid invoices as at 30 Sep 2026)
    acc = o[(o.is_account == 1) & (o.payment_status != "Paid")]
    cr = acc.groupby("customer_id").apply(lambda g: pd.Series({"open_kes": g.loc[g.payment_status == "Open", "order_total_kes"].sum(), "overdue_kes": g.loc[g.payment_status == "Overdue", "order_total_kes"].sum(),
                                                                "written_off_kes": g.loc[g.payment_status == "Written Off", "order_total_kes"].sum(), "unpaid_invoices": int((g.payment_status != "Written Off").sum())})).reset_index()
    cr = cr.merge(cust[["customer_id", "customer_label", "segment", "credit_limit_kes"]], on="customer_id")
    cr["outstanding_kes"] = cr.open_kes + cr.overdue_kes
    cr["pct_of_credit_limit"] = (100 * cr.outstanding_kes / cr.credit_limit_kes.replace(0, np.nan)).round(1)
    cr.to_csv(OUT / "CreditExposure.csv", index=False)
    rfm = pd.read_csv(C / "customer_rfm.csv").drop(columns=["customer_name"]); rfm["customer_label"] = rfm.customer_id + " " + rfm.segment
    rfm.to_csv(OUT / "CustomerRFM.csv", index=False)
    gaps = pd.read_csv(ROOT / "sql/results/11_ordering_gaps.csv"); gaps["customer_label"] = gaps.customer_id + " " + gaps.segment
    gaps.drop(columns=["customer_name"]).to_csv(OUT / "CustomerQuiet.csv", index=False)
    # forecast table: last 14 weeks of actuals + next 4 weeks of forecast, per category, plus same week last year
    w = pd.read_csv(C / "weekly_sales.csv", parse_dates=["week_start"]); full = w[w.category == "ALL"].sort_values("week_start").iloc[1:-1].week_start
    cats = [c for c in w.category.unique() if c not in ("ALL", "Grains & Legumes")]
    q = w[w.category.isin(cats)].pivot(index="week_start", columns="category", values="billed_qty").reindex(full)
    nf = pd.read_csv(ROOT / "forecast/next_4_weeks.csv", parse_dates=["target_week"]); rows = []
    for c in cats:
        for d in q.index[-14:]:
            rows.append(dict(week_start=d.date(), category=c, kind="Actual", actual_units=q.loc[d, c], forecast_units=np.nan, low80=np.nan, high80=np.nan, same_week_last_year=q.loc[d - pd.Timedelta(weeks=52), c] if d - pd.Timedelta(weeks=52) in q.index else np.nan))
        for r in nf[nf.category == c].itertuples():
            ly = q.loc[r.target_week - pd.Timedelta(weeks=52), c] if r.target_week - pd.Timedelta(weeks=52) in q.index else np.nan
            rows.append(dict(week_start=r.target_week.date(), category=c, kind="Forecast", actual_units=np.nan, forecast_units=round(r.forecast), low80=round(r.low80), high80=round(r.high80), same_week_last_year=ly))
    pd.DataFrame(rows).to_csv(OUT / "ForecastChart.csv", index=False)
    pd.read_csv(ROOT / "forecast/scores_overall.csv").to_csv(OUT / "ForecastAccuracy.csv", index=False)
    for p in sorted(OUT.glob("*.csv")):
        print(f"{p.name:22s}{len(pd.read_csv(p)):>8,} rows  {p.stat().st_size/1024:>8,.0f} KB")


if __name__ == "__main__":
    main()
