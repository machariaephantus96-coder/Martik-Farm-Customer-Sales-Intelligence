#!/usr/bin/env bash
# Runs the full pipeline in order. Executed notebooks go to notebooks/executed/.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source .env; set +a
mkdir -p notebooks/executed

python src/generate_data.py
psql "postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}" -f sql/01_schema.sql

for nb in notebooks/0*.ipynb; do
  echo ">> Running $nb"
  papermill "$nb" "notebooks/executed/$(basename "$nb")" -k python3
done
echo "Done."
