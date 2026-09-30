"""Load a DGCA monthly average-fare series into ``dgca_benchmarks``.

CSV columns (header required)::

    period_month,avg_fare,route_code,source_label,source_url
    2026-07,5480.00,ALL,"DGCA domestic average fare, Jul 2026",https://www.dgca.gov.in/...

* ``period_month`` — ``YYYY-MM`` (or any date in the month, ``YYYY-MM-DD``);
* ``avg_fare`` — INR;
* ``route_code`` — ``ALL`` for the all-India figure (used by the back-test) or a
  basket route such as ``DEL-BOM``; optional, defaults to ``ALL``;
* ``source_label`` / ``source_url`` — provenance, shown in the API and dashboard.

Rows are upserted on (period_month, route_code) and stored with
``is_synthetic = false``. Usage::

    python -m scripts.db.load_dgca_benchmark path/to/dgca.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from packages.domain.db import session_scope
from packages.domain.exceptions import ConfigurationError, SafarError
from packages.domain.repositories.benchmarks import BenchmarkRecord, BenchmarkRepository


def parse_rows(path: Path) -> list[BenchmarkRecord]:
    records: list[BenchmarkRecord] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"period_month", "avg_fare", "source_label"} - set(reader.fieldnames or [])
        if missing:
            raise ConfigurationError("benchmark CSV is missing columns", columns=sorted(missing))
        for line, row in enumerate(reader, start=2):
            try:
                period = row["period_month"].strip()
                month = date.fromisoformat(period if len(period) > 7 else f"{period}-01")
                fare = Decimal(row["avg_fare"].replace(",", "").strip())
            except (ValueError, InvalidOperation) as exc:
                raise ConfigurationError("invalid benchmark row", line=line) from exc
            if fare <= 0:
                raise ConfigurationError("benchmark fare must be positive", line=line)
            records.append(
                BenchmarkRecord(
                    period_month=month.replace(day=1),
                    route_code=(row.get("route_code") or "ALL").strip() or "ALL",
                    avg_fare=fare,
                    source_label=row["source_label"].strip(),
                    source_url=(row.get("source_url") or "").strip() or None,
                    is_synthetic=False,
                )
            )
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("csv", type=Path)
    args = parser.parse_args(argv)
    try:
        records = parse_rows(args.csv)
        with session_scope() as session:
            count = BenchmarkRepository(session).upsert(records)
    except SafarError as exc:
        print(f"error [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    print(f"loaded {count} benchmark rows from {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
