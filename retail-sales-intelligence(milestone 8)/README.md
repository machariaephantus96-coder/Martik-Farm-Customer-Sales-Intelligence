# Customer and Sales Intelligence for a Kenyan Retailer

> TODO: 2-3 sentence problem statement.

## Headline findings
- TODO finding 1 (with number)
- TODO finding 2 (with number)
- TODO finding 3 (with number)

## Repo map
| Path | Contents |
|------|----------|
| `notebooks/` | Numbered notebooks 01-06, run in order |
| `sql/` | Schema and analytics queries (PostgreSQL) |
| `src/` | Config and seeded data generator |
| `data/` | `raw/`, `processed/`, and `DATA_SOURCES.md` |
| `dashboard/` | Power BI file and screenshots |
| `deck/` | Final presentation (PDF + source) |
| `run_all.sh` | Runs the whole pipeline end to end |

## Setup
Requirements: Conda (or Miniconda), PostgreSQL 14+, Power BI Desktop (dashboard only).

```bash
conda env create -f environment.yml
conda activate retail-capstone
cp .env.example .env          # then edit .env with your Postgres credentials
createdb retail_capstone      # or create the DB in pgAdmin
```

## Run everything
```bash
./run_all.sh
```
Or step by step:
1. `python src/generate_data.py` creates the data in `data/raw/`
2. `psql -f sql/01_schema.sql` creates the tables
3. Notebooks `01` to `06` in `notebooks/`, in numeric order
4. Open `dashboard/` in Power BI Desktop and refresh

Expected runtime: TODO minutes. Random seed: `RANDOM_SEED` in `.env` (default 42).

## Data
See `data/DATA_SOURCES.md`. TODO: summarise what is real vs generated.

## Dashboard
TODO: how to open it, plus screenshots from `docs/`.

## Authorship
This is my individual capstone work for Lux Dev Academy. Tools and libraries used: TODO (e.g. pandas, scikit-learn, PostgreSQL, Power BI). AI assistance, if any, was limited to TODO.

## Limitations and next steps
TODO
