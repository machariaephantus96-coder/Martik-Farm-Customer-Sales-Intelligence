# Problem Statement

**Project:** Customer & Sales Intelligence for Martik Farm Enterprises
**Author:** Ephantus Macharia | Data Science & Analytics capstone, Lux Dev Academy

## The business
Martik Farm Enterprises is a Nairobi fresh-produce supplier. A shop in Ruiru produces potato products (fries) and a shop in
the Nairobi CBD sells branded, packed produce. It supplies hotels, restaurants, a coffee chain and a school, plus smaller
accounts around Nairobi and Kiambu, mostly **on credit**. Demand peaks from October to December and is weakest in January
and mid-year. Prices of peppers, grapes, onions, tomatoes and oranges rise sharply in the peak season.

## The problem
The business keeps its records by hand and has never analysed them. The owners cannot say with evidence which customers and
products bring the money, which accounts are drifting away, whether discounts worked, how much credit is overdue, or how much
stock to prepare for next month. Decisions are made on memory and instinct, which is risky for a business selling perishable goods.

## Business questions
1. **Who buys what, where and when?** Which customer segments, areas and products drive revenue and margin, and how strong is the Oct-Dec peak?
2. **Which stores and products make the most money?** Compare Ruiru and the CBD shop, and find high-revenue but low-margin products.
3. **Which customers are drifting away?** Can we flag accounts likely to stop ordering in the next 60 days, early enough to act?
4. **Did our promotions work?** Did discounts raise sales by more than chance would explain?
5. **Where is credit risk?** Which customers pay late, and how much money is overdue?
6. **What demand should we expect next month?** A weekly demand forecast by product group, so purchasing and production can be planned.

## Success measures (proposed)
| Question | How we will know it worked |
|---|---|
| 1-2 | Findings stated with figures (e.g. share of revenue by segment, peak vs low-season uplift) that a manager can check against the data |
| 3 Churn | The model beats a simple baseline ("no order in 30 days = will churn") on precision/recall for the churn class, tested on later months than it was trained on |
| 4 Promotions | A hypothesis test with a confidence interval for the sales uplift, stating clearly whether the effect is real |
| 5 Credit | Overdue amount and late-payment rate per segment, and a ranked list of accounts to follow up |
| 6 Forecast | Forecast error (WAPE/MAPE) lower than a naive baseline (same week last year or last 4-week average) on a hold-out period |
| Overall | A dashboard that answers each question in a few clicks and a short deck with recommended actions |

## Data needed
- **Sales and customers:** orders, order lines, customers, products, stores, payments (credit and M-Pesa), promotions: at least a year. *Generated for this project, calibrated on Martik's real price list.*
- **Context:** county population, public holidays and school terms, consumer price inflation, market produce prices.
  See [data_inventory.md](data_inventory.md) for what has been obtained and what is still to come.

## Scope and limits
This is an individual academic project. The transaction data is **synthetic**, so findings describe the simulated business
and the methods are what is being demonstrated, not claims about Martik's real performance.
