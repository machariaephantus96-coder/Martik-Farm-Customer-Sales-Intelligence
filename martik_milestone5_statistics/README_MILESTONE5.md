# Milestone 5: Statistical Analysis

Hypothesis tests and confidence intervals on four real business questions, with the assumptions checked before each test is trusted,
and a plain-language conclusion for each.

> The data is **synthetic** (calibrated on Martik Farm's real price list; see `DATA_README.md`). Conclusions describe the simulated business; the methods are what is being demonstrated.

## What is in this milestone
```
notebooks/05_statistical_analysis.ipynb   executed notebook: hypotheses, assumption checks, results, conclusions (start here)
src/stats_analysis.py                     all the tests (re-runnable, seed 42):  python src/stats_analysis.py
src/stats_figures.py                      the five figures:                      python src/stats_figures.py
stats/*.csv                               every number behind the notebook
figures/s5_01..05_*.png                   promotions, M-Pesa, season, late payment, assumption checks
```
Needs: `pip install -r requirements.txt` (adds scipy and statsmodels). Uses `data_clean/` from Milestone 2.

## The four tests and what they found
| | Question | Method | Result |
|---|---|---|---|
| **T1** | Did a promotion change sales? | Per-account change in promoted-category volume against never-discounted control categories, 8 weeks either side; constant-price volume; bootstrap CI; Holm correction for 5 tests; placebo test | **P01 fruit +23% (CI +5% to +44%), P04 fruit +17% (0% to +39%)**; P02, P03, P05 inconclusive (intervals include zero). **None is significant after correcting for 5 tests** (P01 adjusted p = 0.075). Exploratory pooled fruit result +16% (2% to 33%). |
| **T2** | Do M-Pesa customers spend more? | Regression on log order value with customer-clustered errors, four ways from naive to same-customer | Raw gap **-38%**, but **-6% within segments (not significant)** and **-0.2% (CI -2.0% to +1.7%) for the same customer**. **No evidence M-Pesa customers spend more.** |
| **T3** | How strong is the Oct-Dec peak? | Weekly log revenue ~ season + trend, Newey-West errors | **Peak weeks earn 1.76x low weeks (CI 1.67 to 1.86)** |
| **T4** | Do segments differ in paying late? | Chi-square, Cramer's V, Wilson CIs, customer-level Kruskal-Wallis | **Yes: chi2 = 908, p far below 0.001, V = 0.28.** Hotels and schools 99% late; caterers and fast food 72%. Hotels vs restaurants +9.6 points; with only 7 hotel accounts that is moderate evidence |

### Plain-language conclusions
- **Promotions:** the two January fruit promotions are the only ones that look like they raised sales, by roughly 15-20%, but even those do not pass the stricter test needed when five promotions are checked at once. The other three cannot be called either successes or failures: the data is too thin to detect a 10% lift. To get a clear answer, run the next promotion on a random half of eligible accounts.
- **M-Pesa:** M-Pesa orders are smaller on average only because small businesses and walk-ins use M-Pesa while hotels and schools use bank transfer. The same customer orders about the same amount whichever way they pay.
- **Season:** budget for revenue about 1.7-1.8 times the low-season level from October to December (part of that is higher produce prices).
- **Late payment:** follow up hotels and schools first; they are the latest payers and also have the longest credit terms.

## Assumptions checked (details and figures in the notebook)
- **Independence:** T2 and T4 observations cluster by customer (about two thirds of the variance in order value is between customers), so T2 uses customer-clustered errors and T4 adds a customer-level test. T3 weekly revenue is autocorrelated (Durbin-Watson 1.32), so it uses Newey-West errors.
- **Normality:** T1 changes are checked per promotion (three of five fail Shapiro, so Wilcoxon, bootstrap and a permutation test are reported alongside the t-test); T2 uses logs because raw order values are heavily skewed (2.3 to 0.09 after the log).
- **Equal variances:** Levene test fails for T2, so robust standard errors are used.
- **Confounding and bias:** T2's naive result is deliberately shown next to the adjusted ones. T1 uses a placebo test on never-promoted categories: it shows the method's noise is about +/-10%.
- **Multiple testing:** Holm correction across the five promotions and across the segment comparisons.
- **Expected counts:** the smallest chi-square expected count in T4 is 64 (minimum needed is 5).

## How it was tested
- **Two independent methods per key result:** T1 with t-test, Wilcoxon, bootstrap and sign-flip permutation test (p-values agree); T2 with regression, customer fixed effects and a customer-level paired test.
- **SQL cross-check:** late-payment rates for all 8 segments and the naive M-Pesa gap (-38.3%) recomputed in PostgreSQL match to the digit shown; the SQL weekly peak/low ratio is 1.65 against 1.62 for the simple Python version (they assign weeks to seasons slightly differently).
- **Known-answer test:** because the data is synthetic, the true promotion lifts built into the generator were 18%, 12%, 0%, 15% and 10%. All five confidence intervals contain the truth, and P03 (built with no effect) shows none. This tests the method; real data has no answer key.
- Every number in the notebook text is computed from the results in the same run; no figures are typed in by hand apart from the layout notes.
- Assertions: `late` flag equals `days_past_due > 0` for every invoice.

## Known limits
- Synthetic data: the effects are properties of the simulation.
- T1 is a before/after comparison with a control group of categories, not a randomised experiment. Power is low: only lifts above about 15% can be detected. The pooled fruit test was chosen after seeing the results and is labelled exploratory.
- T2 is an association in paid orders only; walk-in rows are daily shop aggregates.
- T3 has just two peak seasons, and revenue includes price rises as well as volume.
- T4: few accounts per segment (one coffee chain); lateness and credit terms move together, so cause cannot be separated.
- The tests were designed and written by me for this project and have not been reviewed by an independent statistician.
