"""Group existing reports into events once (see app/grouping.py).

    python -m app.group_reports --dry-run   # counts only, saves nothing
    python -m app.group_reports             # save
"""

import argparse

from .db import SessionLocal, init_db
from .grouping import group_all


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="count only, save nothing")
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        group_all(db, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
