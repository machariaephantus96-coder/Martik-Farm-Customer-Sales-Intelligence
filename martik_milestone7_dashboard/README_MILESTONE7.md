# Milestone 7: Dashboard and Storytelling

A dashboard a store manager can use: KPIs, trends, customer segments, the demand forecast, credit risk, and the insights stated in words.

> The data is **synthetic** (calibrated on Martik Farm's real price list; see `DATA_README.md`). Accounts are shown as ID and segment (for example "C101 Restaurant"), not by client name.

## What was delivered
| | |
|---|---|
| **Working dashboard (hosted)** | https://claude.ai/artifact/BGz1E2tN9zjBAxx3ZMQjtd (private until you share it from the page's Share menu). Source: `dashboard/martik_dashboard.html`, a single self-contained page that also opens by double-clicking the file. |
| **Screenshots** | `dashboard/screenshots/` (9 images, listed below) |
| **Power BI kit** | `powerbi/`: 11 model-ready tables, 38 DAX measures, a colour theme and a step-by-step build guide, so the same dashboard can be built in Power BI Desktop |
| **Questions answered and insights** | below |

### Please read: the `.pbix` file
The course asks for a Power BI dashboard. Power BI Desktop is a Windows application and could not be run where this work was done, so **there is no `.pbix` file yet**. The hosted dashboard is a working web dashboard (not Power BI) with the same pages, filters and numbers, and `powerbi/BUILD_GUIDE.md` takes about 90 minutes to follow, with a table of numbers to check at the end. The DAX measures were written to match the tested numbers but **have not been run in Power BI**; the build guide's checks will show quickly if one needs a fix. After building it, save the `.pbix` and your own Power BI screenshots into this folder.

## Folder
```
dashboard/martik_dashboard.html      the hosted dashboard (self-contained)
dashboard/dashboard_template.html    page template; dashboard_data.json is the data behind it
dashboard/screenshots/               evidence
powerbi/data/*.csv                   star schema for Power BI (FactSales, FactOrders, DimDate, DimCustomer, DimProduct, DimStore, CreditExposure, CustomerRFM, CustomerQuiet, ForecastChart, ForecastAccuracy)
powerbi/measures.dax                 DAX measures
powerbi/martik_theme.json            theme (blue / orange / green / grey, same as the dashboard)
powerbi/BUILD_GUIDE.md               how to build the report
src/build_dashboard_data.py          builds dashboard_data.json from the earlier milestones
src/export_powerbi.py                exports the Power BI tables
```
Rebuild: `python src/build_dashboard_data.py` then `python src/export_powerbi.py` (run after Milestones 2, 4, 5 and 6).

## What the dashboard shows
- **Filters:** period (3, 6, 12, 24 months), store (Ruiru, Nairobi CBD), customer segment. Every sales chart and KPI responds.
- **KPI strip:** revenue and change on the previous period, gross margin, orders, average order, active accounts. A second strip (as at 30 Sep 2026): unpaid invoices, overdue, accounts gone quiet, next-4-week forecast.
- **Trends:** monthly revenue (peak months in orange) and gross margin.
- **Segments and products:** revenue share and margin by segment and by category.
- **Forecast:** actual weekly units, the next 4 weeks with an 80% range, and the same weeks last year, by category, with the model's test error.
- **Credit and customers:** largest unpaid balances against credit limit, late payment by segment, RFM groups, and the accounts that have gone quiet.
- **Insights in words:** eight findings, each with what to do.

## Questions it answers
| Question a store manager asks | Where |
|---|---|
| How much did we sell, at what margin, and is it up or down? | KPI strip, monthly trend |
| Is the Oct-Dec peak coming and how big is it? | Trend (orange months), forecast, insight 1 |
| Which customer types and products make the money? | Segment and category charts |
| How do Ruiru and the CBD shop compare? | Store filter on every chart |
| How many units should we prepare for the next four weeks? | Forecast chart and table |
| Who owes us money and who pays late? | Unpaid balances, late-payment chart |
| Which good customers are drifting away? | RFM groups, Gone quiet table |
| Did discounts and M-Pesa change sales? | Insights 6 and 7 |

## Insights in words
1. **Stock up for October to December.** Peak weeks earn about 1.76 times low-season weeks (interval 1.67 to 1.86). December 2025 was the best month at KES 5.16M; January falls about 50% from December each year. *Plan stock, cash and staff for the peak by the end of September.*
2. **A few accounts carry the business.** The largest account (C001) is 16.9% of account revenue; the top seven are 52.7%. Hotels (24%) and restaurants (23%) are the biggest segments. *Protect these relationships.*
3. **Fruit leads in town, fries lead in Ruiru.** CBD fruit is 20.4% of revenue; Ruiru potato products are 16.7% at a 30.2% margin. Cucumber, matoke, white onion, lemon and coriander are top sellers with below-average margin. *Review those five prices first.*
4. **Credit is the biggest risk.** KES 3.95M is unpaid, KES 852,000 of it overdue across 147 invoices; KES 56,000 is written off. Hotels and schools pay late 99% of the time, 14 to 16 days late on average. Seven accounts owe more than their credit limit (worst: C101 Restaurant 169%, C150 School 163%, C111 Restaurant 142%). *Chase hotels and schools first and stop new credit to accounts over their limit.*
5. **Four active accounts have gone quiet.** 16 Champions bring 55% of revenue. C133 Hotel (KES 6.0M to date), C105 Restaurant, C145 Caterer and C135 Hotel have not ordered for 83 to 145 days though they used to order every few days. *Call them this week.*
6. **M-Pesa does not change how much customers order.** Orders look 38% smaller only because small shops use M-Pesa; the same customer orders the same either way.
7. **Only January fruit promotions look useful** (+17% to +23%), and none passes a strict test. *Next time, promote to a random half of accounts.*
8. **Trust the forecast, but not blindly in the peak.** Test error is about 12% against 17% for a 4-week average; the model alone under-forecast the 2025 peak by 14%, so the dashboard shows a blend with last year's pattern. *Be ready for the top of the 80% range.*

## Screenshots (`dashboard/screenshots/`)
`01_overview_kpis_trend` | `02_segments_categories` | `03_forecast` | `04_credit_and_customers` | `05_insights_and_questions` | `06_filtered_ruiru_restaurants_3months` (shows the filters working) | `07_forecast_fruit` (category selector) | `08_mobile` | `09_dark_theme`

## How it was tested
- **Numbers reconcile with earlier milestones:** revenue KES 75,884,399.51, 20,852 orders and 27.4% margin in the exported tables match Milestones 2 and 4; credit (KES 3,947,085 unpaid, KES 852,164 overdue, 147 invoices) matches the SQL results; forecast average 8,383 units a week matches Milestone 6.
- **Claims checked against data before publishing:** this caught two errors that were then fixed. The over-limit accounts are seven, not four. And the RFM "At risk" group includes accounts only 2 to 5 days quiet (most accounts order almost daily), so the call list now uses each account's own ordering rhythm (Milestone 4, query 11) instead.
- **Rendering:** opened in a headless browser at desktop and phone width, light and dark; no horizontal scroll and no script errors; filters and the category selector tested.
- **Not tested:** the DAX measures in Power BI (see above), and viewing by anyone other than the author.

## Known limits
- Synthetic data; all findings describe the simulated business.
- The forecast calendar for October 2026 is copied from 2025: check the public holidays.
- "Active accounts" cannot be split by store (orders are not tied to a store), so it shows n/a when one store is selected.
- The category forecast ranges are added up for the total, so the total range is approximate.
- The RFM "At risk" group is a relative score and is not the call list; use "Gone quiet".
