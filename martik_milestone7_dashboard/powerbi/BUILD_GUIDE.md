# Build the Power BI report (about 90 minutes)

Everything the report needs is in this folder. Power BI Desktop is a Windows application, so the `.pbix` itself has to be saved on your own computer.
A finished, working version of the same dashboard (same numbers, same pages) is the hosted page linked in `README_MILESTONE7.md`; use it as the picture of what to build.

## 1. Load the data
Home > Get data > Text/CSV, and load every file in `powerbi/data/`:
`FactSales`, `FactOrders`, `DimDate`, `DimCustomer`, `DimProduct`, `DimStore`, `CreditExposure`, `CustomerRFM`, `CustomerQuiet`, `ForecastChart`, `ForecastAccuracy`.
- In Power Query set types: dates (`order_date`, `date`, `month_start`, `week_start`, `invoice_due_date`, `payment_date`, `week_start` in ForecastChart) to **Date**; the KES columns to **Fixed decimal number**; `is_account`, `month` to **Whole number**.
- Theme: View > Themes > Browse for themes > `powerbi/martik_theme.json`.

## 2. Model (Model view)
Draw these many-to-one relationships (single direction, from the dimension to the fact):

| From (many) | To (one) |
|---|---|
| FactSales[order_date] | DimDate[date] |
| FactSales[customer_id] | DimCustomer[customer_id] |
| FactSales[product_id] | DimProduct[product_id] |
| FactSales[store_id] | DimStore[store_id] |
| FactOrders[order_date] | DimDate[date] |
| FactOrders[customer_id] | DimCustomer[customer_id] |
| CreditExposure[customer_id], CustomerRFM[customer_id], CustomerQuiet[customer_id] | DimCustomer[customer_id] |

`ForecastChart` and `ForecastAccuracy` stay unconnected (they have their own category column). Mark `DimDate` as the date table (Table tools > Mark as date table > `date`).
Sort `DimDate[month_label]` by `DimDate[month_sort]`, and `DimDate[month_name]` by `DimDate[month]`.
Hide the key columns in the report view.

## 3. Measures
Home > Enter data > one empty column, name the table `_Measures`. Add every measure from `measures.dax` to it. Format: Revenue, Gross Margin, Average Order, credit measures as `KES #,0`; the `%` measures as percentage with 1 decimal.

## 4. Pages
**Page 1: Overview** (the manager's first look)
- Slicers across the top: `DimDate[date]` (Between), `DimStore[store_name]`, `DimCustomer[segment]`.
- Five cards: Revenue (with Revenue YoY % as the callout), Margin %, Orders, Average Order, Avg Monthly Active Accounts.
- Clustered column chart: axis `DimDate[month_label]`, values `[Revenue]`; Format > Columns > Color > fx > Field value > `[Bar Colour]` so peak months are orange. Title: the finding, for example "Revenue peaks in December".
- Line chart: axis `DimDate[month_label]`, values `[Margin %]`.

**Page 2: Customers and products**
- Bar chart: axis `DimCustomer[segment]`, values `[Revenue]`, data labels on; add `[Segment Share %]` and `[Margin %]` to the tooltip. Turn off the segment slicer's effect on this visual (Format > Edit interactions) so segments stay comparable.
- Bar chart: axis `DimProduct[category]`, values `[Revenue]`; tooltip `[Category Share %]`, `[Margin %]`.
- Table: `DimProduct[product_name]`, `[Revenue]`, `[Margin %]`, sorted by Revenue; conditional-format Margin % (red under 22%).

**Page 3: Forecast**
- Slicer: `ForecastChart[category]`.
- Line chart: axis `ForecastChart[week_start]`, values `[Actual Units]`, `[Forecast Units]`, `[Same Week LY Units]`; add `[Forecast Low 80]` and `[Forecast High 80]` as thin dashed lines (a shaded band needs the Analytics pane or a custom visual; thin lines are fine).
- Table: week, `[Forecast Units]`, `[Forecast Low 80]`, `[Forecast High 80]`, `[Same Week LY Units]` filtered to `kind = Forecast`.
- Cards: `[Forecast Weekly Avg]`, `[Forecast Test WAPE]`, `[Avg4 Test WAPE]`.
- Text box: "Peak weeks are the model's weak spot. Plan for the forecast and be ready for the top of the 80% range."

**Page 4: Credit and customers**
- Cards: `[Unpaid Invoices KES]`, `[Overdue KES]`, `[Overdue Invoices]`, `[Over Credit Limit Accounts]`, `[Quiet Accounts]`.
- Table from `CreditExposure`: `customer_label`, `outstanding_kes`, `overdue_kes`, `pct_of_credit_limit` sorted by `overdue_kes`; conditional-format `pct_of_credit_limit` red above 100.
- Bar chart: axis `DimCustomer[segment]`, values `[Late Payment %]` and tooltip `[Avg Days Past Due]`.
- Table from `CustomerRFM` grouped by `rfm_segment`: `[RFM Accounts]`, `[RFM Revenue Share]`.
- Table from `CustomerQuiet` filtered to `status = recently quiet: call now`: `customer_label`, `days_silent`, `median_gap_days`.

**Page 5: What this means** (text boxes, copy from `README_MILESTONE7.md`, section "Insights in words").

## 5. Check the numbers before you screenshot
These must match, or a relationship or filter is wrong:

| Check | Expected |
|---|---|
| Revenue, all dates, no filters | KES 75,884,399.51 (75.88M) |
| Orders, all dates | 20,852 |
| Margin % | 27.4% |
| Unpaid Invoices KES | 3,947,085 |
| Overdue KES / Overdue Invoices | 852,164 / 147 |
| Late Payment %, Hotel/Lodge | 99.2% |
| Peak vs Low Ratio | about 1.6 to 1.7 (weekly averages, partial end weeks included) |
| Forecast Weekly Avg (All categories) | 8,383 |

## 6. Save and screenshot
File > Save as `martik_dashboard.pbix`. Use Windows+Shift+S (or File > Export > PDF) for each page, and put the screenshots in the `screenshots/` folder of your repository.
To share without the file: Publish to Power BI service (needs a work or school account) and paste the link in the README.
