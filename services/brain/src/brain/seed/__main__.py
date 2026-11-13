"""`python -m brain.seed` seeds an empty database. `scripts/gen_org.py` is the same with options."""

import argparse
import logging
from datetime import date
from pathlib import Path

from brain.db.engine import make_engine
from brain.seed.load import run_seed


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the synthetic Data DNA company.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--anchor", type=date.fromisoformat, help="Day after the last of 14 days (YYYY-MM-DD)"
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--log-dir", type=Path, default=Path("/var/dna/logs"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    engine = make_engine()
    if engine is None:
        print("DATABASE_URL is empty: nothing to seed.")
        return 1
    seeded = run_seed(engine, args.data_dir, args.log_dir, args.seed, args.anchor)
    print(
        "Seeded."
        if seeded
        else "Database already has users: nothing to do (use `make reset` first)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
