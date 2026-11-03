"""Shared config: loads .env, builds the Postgres engine, fixes the random seed."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SEED = int(os.getenv("RANDOM_SEED", 42))
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def get_engine():
    url = (
        f"postgresql+psycopg2://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}"
        f"@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
    )
    return create_engine(url)
