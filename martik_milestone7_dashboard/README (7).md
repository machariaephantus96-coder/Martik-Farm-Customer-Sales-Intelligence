# Kenya Mobile Money Transactions Analysis

Exploratory analysis of **6,000 mobile money transactions** (M-Pesa, Airtel Money and others) across 20 Kenyan counties from **1 Jan to 31 Dec 2024**, built with Python, pandas, matplotlib and seaborn.

## Key Findings

All figures use **completed** transactions only.

| Question | Finding |
|---|---|
| Fastest-growing month (fee revenue) | **May 2024**, +11.18% month over month |
| Steepest monthly decline | **June 2024**, -14.81% |
| Busiest hour of the week | **Wednesday, 9 AM** (69 transactions) |
| Highest-value customer | **Anyango Onyango**, Mombasa (KES 555,051); the top 3 customers in every county are in the notebook |

## What's Inside

1. **Monthly fee revenue** and month-over-month % change
2. **Weekday × hour** pivot table of transaction counts
3. **Top 3 customers per county** by total amount transacted
4. **Daily volume vs. 7-day rolling average**, flagging days above 1.5× the average

## Project Structure

```
├── Data/
│   └── kenya_mobile_money_transactions.csv
├── analysis.ipynb
└── README.md
```

## Run It

```bash
pip install pandas matplotlib seaborn jupyter
git clone https://github.com/machariaephantus96-coder/Kenya-Mobile-Money-Analysis.git
cd Kenya-Mobile-Money-Analysis
jupyter notebook analysis.ipynb
```

## Summary

Monthly fee revenue stayed in a fairly narrow band, from KES 31,452 (February) to KES 37,474 (May), with May the standout month and June giving most of it back. Wednesday at 9 AM is the busiest hour of the week for transactions. The highest-spending customers are in Mombasa, Nairobi and Kajiado, each with over KES 550,000 transacted in 2024.

## Tools

Python 3.13 · pandas · matplotlib · seaborn · Jupyter Notebook

## Author

**Ephantus Macharia**, aspiring data analyst · [GitHub](https://github.com/machariaephantus96-coder)
