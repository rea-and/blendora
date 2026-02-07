from __future__ import annotations

import argparse
import json
from pathlib import Path

import app


def load_seed_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reload the Blendora SQLite database from a seed JSON file."
    )
    parser.add_argument(
        "--json",
        default=str(app.SEED_JSON_PATH),
        help="Path to the JSON seed file.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=True,
        help="Clear existing data before loading new data (default).",
    )
    parser.add_argument(
        "--no-reset",
        dest="reset",
        action="store_false",
        help="Insert data without clearing existing rows.",
    )
    args = parser.parse_args()

    seed_path = Path(args.json)
    data = load_seed_json(seed_path)

    conn = app.get_db()
    app.ensure_schema(conn)
    app.seed_from_json(conn, data, reset=args.reset)
    conn.close()

    print(f"Database updated from {seed_path}")


if __name__ == "__main__":
    main()
