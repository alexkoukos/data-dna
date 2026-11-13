"""Generate the synthetic company into the database: `uv run python ../../scripts/gen_org.py --seed 42`.

Run from services/brain (needs DATABASE_URL). Same options as `python -m brain.seed`.
"""

import sys

from brain.seed.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
