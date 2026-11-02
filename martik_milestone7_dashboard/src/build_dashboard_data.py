#!/usr/bin/env python3
"""Milestone 7: build the compact dataset behind the dashboard (dashboard/dashboard_data.json).
Run after clean_data.py, stats_analysis.py and forecast_model.py.  Accounts are shown as 'C001 Coffee Chain' (id + segment), never by name."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
C, OUT = ROOT / "data_clean", ROOT / "dashboard"
AS_OF = "2026-09-30"


def main():
    OUT.mkdir(exist_ok=True)
    f = pd.read_csv(C / "sales_fact.csv", parse_dates=["order_date"])
    o = pd.read_csv(C / "orders.csv", parse_dates=["order_date"])
    cust = pd.read_csv(C / "customers.csv"); rfm = pd.read_csv(C / "customer_rfm.csv")
    f["month"] = f.order_date.dt.strftime("%Y-%m"); o["month"] = o.order_date.dt.strftime("%Y-%m")
    store_of = f.groupby("order_id").store_id.agg(lambda s: sorted(set(s)))
    # F: revenue and margin by month x segment x store x category
    F = f.groupby(["month", "segment", "store_id", "category"]).agg(rev=("line_total_kes", "sum"), gm=("gross_margin_kes", "sum")).round(0).reset_index()
    # O: distinct orders by month x segment x store, and by month x segment (an order can touch both stores)
    Os = f.groupby(["month", "segment", "store_id"]).order_id.nunique().reset_index(name="orders")
    Oa = o.groupby(["month", "segment"]).agg(orders=("order_id", "size"), accounts=("customer_id", lambda s: s.nunique())).reset_index()
    # credit as at 30 Sep: unpaid account invoices
    acc = o[o.is_account == 1]
    unpaid = acc[acc.payment_status.isin(["Open", "Overdue"])]
    lab = cust.set_index("customer_id").apply(lambda r: f"{r.name} {r.segment}", axis=1)
    cr = unpaid.groupby("customer_id").apply(lambda g: pd.Series({"outstanding": g.order_total_kes.sum(), "overdue": g.loc[g.payment_status == "Overdue", "order_total_kes"].sum(),
                                                                   "invoices": len(g)})).reset_index()
    cr = cr.merge(cust[["customer_id", "segment", "credit_limit_kes"]], on="customer_id")
    cr["label"] = cr.customer_id + " " + cr.segment
    cr["pct_limit"] = (100 * cr.outstanding / cr.credit_limit_kes.replace(0, np.nan)).round(0)
    cr = cr.sort_values(["overdue", "outstanding"], ascending=False).head(10)
    credit = dict(top=cr[["label", "outstanding", "overdue", "invoices", "credit_limit_kes", "pct_limit"]].round(0).replace({np.nan: None}).to_dict("records"),
                  outstanding=float(unpaid.order_total_kes.sum()), overdue=float(acc.loc[acc.payment_status == "Overdue", "order_total_kes"].sum()),
                  open=float(acc.loc[acc.payment_status == "Open", "order_total_kes"].sum()), written_off=float(acc.loc[acc.payment_status == "Written Off", "order_total_kes"].sum()),
                  overdue_invoices=int((acc.payment_status == "Overdue").sum()))
    late = pd.read_csv(ROOT / "stats/t4_late_by_segment.csv")[["segment", "late_pct", "avg_days_past_due", "avg_terms_days", "customers"]].round(1).to_dict("records")
    # RFM
    rseg = rfm.groupby("rfm_segment").agg(accounts=("customer_id", "size"), revenue=("monetary_kes", "sum"), recency=("recency_days", "mean"), orders=("frequency", "mean")).reset_index()
    rseg["share"] = 100 * rseg.revenue / rseg.revenue.sum()
    rseg = rseg.round(1).sort_values("revenue", ascending=False).to_dict("records")
    risk = rfm[rfm.rfm_segment == "At risk"].sort_values("monetary_kes", ascending=False).head(8)
    risk = [dict(label=f"{r.customer_id} {r.segment}", recency=int(r.recency_days), orders=int(r.frequency), revenue=float(r.monetary_kes)) for r in risk.itertuples()]
    # accounts gone quiet relative to their own ordering rhythm (SQL query 11, Milestone 4): the call list
    gaps = pd.read_csv(ROOT / "sql/results/11_ordering_gaps.csv"); gaps = gaps[gaps.status.str.startswith("recently quiet")]
    life = acc.groupby("customer_id").order_total_kes.sum()
    quiet = [dict(label=f"{r.customer_id} {r.segment}", days=int(r.days_silent), usual_gap=float(r.median_gap_days), orders=int(r.orders), revenue=float(life[r.customer_id]))
             for r in gaps.sort_values("days_silent", ascending=False).itertuples()]
    # forecast
    w = pd.read_csv(C / "weekly_sales.csv", parse_dates=["week_start"]); full = w[w.category == "ALL"].sort_values("week_start").iloc[1:-1].week_start
    cats = sorted(w.category.unique().tolist()); cats.remove("ALL"); cats.remove("Grains & Legumes")
    q = w[w.category.isin(cats)].pivot(index="week_start", columns="category", values="billed_qty").reindex(full)
    nf = pd.read_csv(ROOT / "forecast/next_4_weeks.csv", parse_dates=["target_week"])
    weeks_f = sorted(nf.target_week.unique())
    ly = {str(pd.Timestamp(d).date()): {c: float(q.loc[pd.Timestamp(d) - pd.Timedelta(weeks=52), c]) for c in cats} for d in weeks_f}
    fc = dict(actual_weeks=[str(d.date()) for d in q.index[-14:]], actual={c: q[c].iloc[-14:].round(0).tolist() for c in cats},
              future_weeks=[str(pd.Timestamp(d).date()) for d in weeks_f],
              forecast={c: nf[nf.category == c].sort_values("target_week")[["forecast", "low80", "high80"]].round(0).values.tolist() for c in cats},
              last_year={c: [ly[str(pd.Timestamp(d).date())][c] for d in weeks_f] for c in cats}, cats=cats)
    sc = pd.read_csv(ROOT / "forecast/scores_overall.csv"); t = sc[sc.split == "test"].set_index("method").wape
    fc["test_wape"] = {k: round(100 * float(t[k]), 1) for k in ["b2_avg4", "b4_ly_growth", "model", "blend"]}
    data = dict(as_of=AS_OF, F=F.values.tolist(), Fcols=list(F.columns), Os=Os.values.tolist(), Oa=Oa.values.tolist(),
                segments=sorted(f.segment.unique().tolist()), months=sorted(f.month.unique().tolist()), credit=credit, late=late, rfm=rseg, risk=risk, quiet=quiet, forecast=fc)
    (OUT / "dashboard_data.json").write_text(json.dumps(data, separators=(",", ":")))
    print("wrote", OUT / "dashboard_data.json", round((OUT / "dashboard_data.json").stat().st_size / 1024), "KB")
    print("rev total", F.rev.sum(), "orders", Oa.orders.sum(), "credit", {k: v for k, v in credit.items() if k != "top"})


if __name__ == "__main__":
    main()
