# Data Inventory: sources, how obtained, terms

All dates are 2026. "Raw" means exactly as obtained, before any cleaning (cleaning is Milestone 2).

## Summary
| # | Dataset | Type | Files (in repo) | Obtained | Terms / licence | Status |
|---|---|---|---|---|---|---|
| 1 | Martik sales & customer data | **Generated** (calibrated on real inputs) | `data/orders.csv`, `order_lines.csv`, `payments.csv`, `customers.csv`, `products.csv`, `stores.csv`, `promotions.csv`, `price_list_monthly.csv` | 22 Oct | Own work, no external licence | Raw, in repo |
| 2 | County population, 2019 census | **Public** | `data/public/kenya_county_population_2019.csv` | 30 Oct | See below | Raw, in repo |
| 3 | Public holidays and school terms | Compiled reference | `data/calendar.csv` | 22 Oct | Compiled by the author, **not yet verified** | Verify against Kenya Gazette |
| 4 | Simulated price index | Generated stand-in | `data/synthetic_price_index.csv` | 22 Oct | Own work | To be compared with real CPI |
| 5 | KNBS consumer price index (CPI) | Public | not yet obtained | - | KNBS terms to be read and cited | **Planned** |
| 6 | Market produce prices (KAMIS) | Public | not yet obtained | - | KAMIS terms to be read and cited | **Planned** |

## 1. Martik sales and customer data (generated)
- **What:** 24 months (1 Oct 2024 to 30 Sep 2026): about 20,900 orders, 127,700 order lines, 20,200 payments, 70 customer accounts plus 2 walk-in aggregates, 71 products, 2 stores.
- **How it was made:** by `data_generation/generate_dataset.py` (Python, fixed random seed 42, reproducible). The script was written with the help of an AI assistant (Claude); the business inputs and the design decisions are the author's.
- **Real inputs it is calibrated on:**
  - the Java House Africa price list for January 2026 (71 products and prices, supplied by the business owner);
  - the client roster (Java House, Norfolk Hotel, The Chef Restaurant, Riara School);
  - the two shops (Ruiru fries production, Nairobi CBD grocery outlet);
  - seasonality (Oct-Dec peak, January and mid-year low), credit-based payment, and the products whose prices surge in the peak season.
- **Simulated:** every order, quantity, delivery, payment and its delay, all prices other than January 2026, promotions and their effects, and customer churn. The 66 other accounts have generic names (e.g. "Restaurant 007").
- **Deliberate data-entry errors** (duplicates, price typos, inconsistent spellings, blanks) are included in the raw files so the cleaning milestone has real work to do.
- **Terms:** own work, no third-party licence. Contains no personal data. The four named businesses appear only on simulated figures; consider using generic labels if the repository is public.
- **Assumptions to confirm:** price units (KES per kg, per bunch for herbs); the school calendar used for Riara is assumed.

## 2. County population, 2019 census (public)
- **What:** population of all 47 counties from the 2019 Kenya Population and Housing Census.
- **Original publisher:** Kenya National Bureau of Statistics (KNBS), *2019 Kenya Population and Housing Census, Volume I: Population by County and Sub-County*.
  [KNBS census results page](https://www.knbs.or.ke/2019-kenya-population-and-housing-census-results/)
- **How obtained:** the county figures were read from the Wikipedia table
  [List of counties of Kenya by population](https://en.wikipedia.org/wiki/List_of_counties_of_Kenya_by_population) (accessed 30 Oct 2026), which cites KNBS Volume I,
  and saved unchanged as a CSV (`county`, `population_2019`).
- **Check performed:** the 47 county values sum to 47,564,296, which equals the national total published by KNBS. Both Martik counties (Nairobi, Kiambu) match.
- **Terms:**
  - The same table is published by the World Bank as [Kenya Population 2019 - Table Extract](https://datacatalog.worldbank.org/search/dataset/0063327/kenya-population-2019-table-extract) under **Creative Commons Attribution 4.0** (attribute KNBS).
  - The Wikipedia text is licensed CC BY-SA 4.0.
  - The KNBS page itself states no licence, so credit KNBS as the source and check KNBS terms before any commercial reuse.
- **Use in this project:** per-county demand context (e.g. revenue per 1,000 residents) and for the dashboard.
- **To strengthen:** download the official World Bank / KNBS file and confirm it matches.

## 3. Public holidays and school terms (compiled)
`data/calendar.csv` holds Kenyan public holidays (2024-2026) and an *assumed* school-term calendar. These were compiled from general knowledge and are **not yet checked** against the Kenya Gazette or the school's own calendar (Eid and "observed" dates are best estimates). Treat as provisional until verified.

## 4. Simulated price index
`data/synthetic_price_index.csv` is a simulated produce-price index (Jan 2026 = 100) that drives price movement in the generated data. It is a **stand-in for real inflation data** and must not be presented as CPI.

## 5-6. Planned public sources
- **KNBS Consumer Price Index:** monthly CPI and inflation, to compare with the simulated price movement and use as a model feature.
- **KAMIS produce prices** (Ministry of Agriculture): market prices to benchmark the price list.
For each, the URL, date accessed and terms of use will be recorded here when downloaded.

## Folder layout in the repository
```
data/                      raw generated data (as produced, errors included)
data/public/               raw public data (as downloaded)
data_clean/                cleaned tables and features (Milestone 2)
data_generation/           generator script and PostgreSQL schema
docs/                      this inventory and the problem statement
```
