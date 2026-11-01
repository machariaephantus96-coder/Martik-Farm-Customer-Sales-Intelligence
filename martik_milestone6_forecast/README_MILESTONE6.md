# Milestone 6: Predictive Model, weekly demand forecast

A forecast of weekly demand for each of 8 product categories, 1 to 4 weeks ahead, with simple baselines, time-ordered
train/validation/test splits, metrics, and an analysis of what the model gets wrong.

> The data is **synthetic** (calibrated on Martik Farm's real price list; see `DATA_README.md`). The method is what is being demonstrated.

**Why a forecast and not churn?** The churn table has only 54 positive cases, too few to train and validate a reliable model. The weekly series gives 2,832 forecast rows.

## What is in this milestone
```
notebooks/06_forecast_model.ipynb   executed notebook: design, splits, baselines, model, results, errors, next-4-week forecast (start here)
src/forecast_model.py               features, baselines, model, evaluation (re-runnable, seed 42):  python src/forecast_model.py
src/forecast_figures.py             the six figures:                                                python src/forecast_figures.py
forecast/*.csv                      backtest forecasts, scores, model selection, next 4 weeks
figures/m6_01..06_*.png             splits, actual vs forecast, error by horizon / category / week type, next 4 weeks
```
Needs `pip install -r requirements.txt` (adds scikit-learn). Uses `data_clean/weekly_sales.csv` from Milestone 2.

## Design
| | |
|---|---|
| Target | units sold per week for 8 categories (Grains & Legumes left out: 0.3% of revenue, missing weeks) |
| Horizon | 1, 2, 3, 4 weeks ahead from the last completed week |
| Metric | **WAPE** (total absolute error / total actual; lower is better) and bias |
| Splits (by target week, in time order) | **Train** 7 Oct 2024 - 29 Sep 2025 / **Validation** 6 Oct 2025 - 30 Mar 2026 / **Test** 6 Apr - 21 Sep 2026 |
| Baselines | B1 last week; **B2 4-week average**; B3 same week last year; **B4 last year x recent growth** |
| Model | Gradient boosting (scikit-learn) predicting the ratio of future demand to the last-8-week level; calendar facts known in advance (season label, holidays, planned promotions); no last-year values |
| Selection | model settings and best baseline chosen on **validation only**; test scored once, with the model refitted on train + validation |

## Results on the test weeks (800 forecast rows, WAPE %)
| Method | WAPE | Bias |
|---|---|---|
| B1 Naive (last week) | 17.7 | -0.6% |
| **B2 4-week average (the baseline named in the problem statement)** | **17.3** | -0.4% |
| B3 Same week last year | 12.7 | -5.1% |
| **B4 Last year x growth (best baseline, chosen on validation)** | **13.1** | +5.3% |
| **Model** | **12.2** | +6.0% |
| Blend (50/50 model and B4) | 12.0 | +5.6% |

**Comparison with the baseline**
- The model has about **30% less error than the 4-week average** (12.2% vs 17.3%; 95% interval for the difference -9.2 to -0.8 points). The Milestone 1 success measure is met.
- Against the strongest rule (B4) the model is **not distinguishable** (difference -0.9 points, interval -2.3 to +0.5). At the weekly total level B4 is slightly better (8.6% vs 9.8%).
- The 50/50 blend is best on test (12.0%; 1.1 points better than B4, interval -1.9 to -0.4). It was added after I saw the model's peak weakness on validation, so treat it as a safeguard.
- Accuracy holds out to 4 weeks: model 11.4% at 1 week, 12.6% at 4 weeks; the 4-week average goes from 15.1% to 18.6%.

## What the model gets wrong
1. **It misses the peak.** On all 13 peak weeks of validation (Oct-Dec 2025) it is *worse than the 4-week average* (16.5% vs 12.6%) and under-forecasts by 14% (11% one week ahead, 17% four weeks ahead). It had seen only one earlier peak and had no last-year values. **The test period has no peak, so the blend's peak performance is unverified.**
2. **It over-forecasts low-season weeks** (+11% on validation low weeks) and the test period overall (+6%).
3. **Holiday aftermath.** The worst test weeks are 6 and 13 April, right after Easter: actual about 5,000 units, forecast about 6,600-6,700. The model knows the number of holiday days in a week, not that a slow week follows Easter.
4. **Small, noisy categories.** Leafy Greens (3% of demand) has 25% error; Roots & Tubers (18% error) and Potato Products (14% error) are over-forecast by 9-11%. Vegetables, Herbs, Fruit and Peppers have 9-10% error.
5. **It mostly reads the calendar.** Week-of-year and season matter most (permutation importance); last week's level matters little.

## Forecast for the next 4 weeks (start of the Oct 2026 peak)
Recommended = the blend, because the model alone is weakest in the peak. Totals across the 8 categories (units per week, 80% range):

| Week starting | Forecast | 80% range |
|---|---|---|
| 28 Sep | 8,098 | 6,406 - 9,598 |
| 5 Oct | 8,482 | 6,709 - 10,053 |
| 12 Oct | 8,647 | 6,840 - 10,249 |
| 19 Oct | 8,307 | 6,571 - 9,846 |

By-category numbers are in `forecast/next_4_weeks.csv`. Assumption: the season label and holidays for these weeks are copied from the same weeks a year earlier; check Oct 2026 public holidays against the official calendar.

## How it was tested
- **Time-ordered splits only**, split by target week; every feature uses data up to the forecast origin plus calendar facts known in advance; the churn answer key is not used.
- **Model and best baseline picked on validation; test scored once.** Six model settings were compared.
- **Like-for-like comparison:** all methods are scored on the same rows; the peak was additionally checked on all validation weeks after noticing that the last-year baselines drop the first part of the peak.
- **Uncertainty:** block bootstrap (4-week blocks) intervals for WAPE differences.
- **Re-run test:** running the pipeline twice gives identical output files (checksums).
- Not independently reviewed; the checks are mine.

## Known limits
- Two years of synthetic data, two peaks. A model trained on one peak cannot learn seasonality well; with a third year, last-year features could be used in training.
- No peak in the test period.
- Demand is units, mixed across kg and bunches inside categories; category totals are fine for purchasing planning but not for revenue.
- Not done: forecasts by individual product, a price/revenue forecast, and the churn model.
