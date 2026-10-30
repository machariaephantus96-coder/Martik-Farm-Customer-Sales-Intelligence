# Milestone 2: Data Cleaning and Preparation

A re-runnable pandas pipeline that turns the raw Martik Farm data into clean tables and analysis-ready features,
with before/after counts for every fix. The raw files in `data/` are never modified.

> The sales data is **synthetic**, calibrated on Martik Farm's real price list (see `DATA_README.md` and `docs/data_inventory.md`).
> The errors in the raw files were put there deliberately, so this milestone has real cleaning work to do.

## What is in this milestone
```
src/clean_data.py                   the pipeline (run this)
notebooks/02_data_cleaning.ipynb    executed notebook: runs the pipeline and shows the evidence
reports/cleaning_report.md/.csv     before/after counts for every step
data_clean/                         cleaned tables + features (output)
requirements.txt                    pandas, numpy, matplotlib
```

## How to run
```bash
pip install -r requirements.txt
python src/clean_data.py            # raw data/ -> data_clean/ + reports/
```
Running it twice gives byte-identical output. The notebook calls the same code and displays the results.

## What the pipeline does
| Step | Problem found | Fix | Before | After |
|---|---|---|---|---|
| 1 Types | Dates stored as text | Parsed to datetime; IDs trimmed; numbers checked | 0 parse failures | 0 |
| 2 Duplicates | Double-entered order lines | Dropped exact duplicates (127,736 to 127,354 rows) | 382 | 0 |
| 3 Consistency | Payment method spelled 17 ways ("Mpesa", "M-PESA", "Bank Trf"...) | Mapped to M-Pesa / Bank Transfer / Cheque / Cash | 17 values | 4 |
| 4 Missing values | Blank delivery area | Walk-ins labelled "In-shop (walk-in)"; account orders filled from the customer record | 8,460 | 0 |
| 4 Missing values | Blank order channel | Walk-ins set to "Walk-in"; the rest "Unknown" (not guessed) | 447 | 0 |
| 5 Outliers | Prices about 10x too high (decimal slips) | Detected against the monthly price list, divided by 10, flagged `price_corrected` | 82 | 0 |
| 5 Outliers | Unusually large quantities | Flagged `is_qty_outlier`, **kept** (big clients place genuine bulk orders) | 388 flagged | 388 kept |
| 6 Reconciliation | Orders whose lines do not add up to the subtotal | Resolved by the fixes above | 450 | 0 |

After cleaning, revenue in the fact table equals the sum of order subtotals exactly (KES 75,884,399.51). Before the fixes the
order lines overstated revenue by KES 671,703. Foreign keys, payment amounts, payment dates and due dates were also checked and
had no problems. The full log, including checks that found nothing, is in `reports/cleaning_report.md`.

## Features built (`data_clean/`)
| File | Rows | What it is |
|---|---|---|
| `sales_fact.csv` | 127,354 | One row per order line joined to order, customer, product, store and calendar; adds billed quantity, discount, cost, gross margin, margin %, rejected value. For EDA and Power BI. |
| `orders.csv` | 20,852 | Cleaned orders plus line count, margin, payment date, days to pay, days past due, late-payment flag, week, holiday and season. |
| `customer_rfm.csv` | 70 | Recency, frequency, monetary value, 1-5 scores and a segment (Champions, Loyal, At risk...) per account at 30 Sep 2026. |
| `churn_panel.csv` | 995 | One row per active account per month-end snapshot (19 snapshots), with order trends, spend, payment behaviour and the label `churned_next_60d`. 54 positives (5.4%). |
| `weekly_sales.csv` | 1,043 | Weekly revenue and quantity, in total and by product category, for the demand forecast. |
| other tables | | Cleaned copies of `payments`, `order_lines`, `customers`, `products`, `stores`, `promotions`, `price_list_monthly`, `calendar`. |

**No leakage in the churn panel:** features use only data up to each snapshot date, payments count only if made on or before it,
and the label looks 60 days ahead.

## How it was tested
- Before/after counts for every step (`reports/cleaning_report.md`).
- Reconciliation: line totals vs order subtotals (450 mismatches to 0), payments vs orders, orphan keys, dates.
- 11 built-in post-condition checks at the end of the run; the pipeline stops with an error if any fail.
- Re-run test: two runs produce files with identical checksums.
- Churn labels compared with the generator's answer key: 48 of the 54 positives are genuine churners.

## Known limits
- The price-typo check works because every price can be compared with a known monthly list price.
- 6 of the 54 churn positives are schools quiet in the December holidays, not churn. Use the `is_school` column or exclude that window when modelling.
- The checks are rules written for this project, not independent testing, and the data errors are deliberate.
