# Martik-Farm-Customer-Sales-Intelligence
Data Science & Analytics capstone (Lux Dev Academy) by **Ephantus Macharia**.

## Overview
An analysis of customer behaviour and sales for Martik Farm Enterprises, a Nairobi fresh-produce
supplier with a potato/fries production shop in Ruiru and a grocery outlet in the CBD. It serves hotels,
restaurants, a coffee chain and a school, mostly on credit. The goal is to understand who buys what and
when, which products drive revenue, which customers are drifting away, and what demand to expect next month.

## Data
**Synthetic data calibrated on real business inputs.** The 71-product price list (January 2026 prices),
the client types, the two shops and the seasonality (Oct-Dec peak, January and mid-year low) come from the
real business. All orders, payments and later price movements are simulated, with the generator script
included. The generator was built with Claude's assistance.

- 24 months (Oct 2024 - Sep 2026), about 20,900 orders, 127,000 order lines
- 70 customer accounts, 71 products, 2 stores, credit and M-Pesa payments
- Raw data in `data/`, cleaned data in `data_clean/`, readable tables in `docs/data_tables.md`

## Progress
-  Problem framing and data acquisition
-  Data cleaning and preparation: removed 382 duplicate order lines, corrected 82 price typos and
      standardised payment-method spellings, so line totals now reconcile with order totals
      ([report](reports/cleaning_report.md))
- [ ] Exploratory data analysis
- [ ] SQL analytics (PostgreSQL)
- [ ] Statistical analysis
- [ ] Predictive model (churn / demand forecast)
- [ ] Dashboard and storytelling (Power BI)
- [ ] Documentation and presentation

## Tools
Python, pandas, matplotlib, Jupyter, PostgreSQL, Power BI
