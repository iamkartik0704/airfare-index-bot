from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from packages.domain.exceptions import ConfigurationError
from packages.domain.repositories.benchmarks import BenchmarkRepository
from scripts.db.load_dgca_benchmark import main, parse_rows

CSV = """period_month,avg_fare,route_code,source_label,source_url
2026-07,"5,480.00",ALL,DGCA test,https://example.test/dgca
2026-08-15,5710,,DGCA test,
2026-09,5901.5,DEL-BOM,DGCA test,
"""


def test_parse_rows(tmp_path: Path) -> None:
    path = tmp_path / "dgca.csv"
    path.write_text(CSV)
    rows = parse_rows(path)
    assert [r.period_month for r in rows] == [date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1)]
    assert rows[0].avg_fare == Decimal("5480.00") and rows[1].route_code == "ALL"
    assert not any(r.is_synthetic for r in rows)


@pytest.mark.parametrize(
    "content",
    ["period_month,avg_fare\n2026-07,5000\n", "period_month,avg_fare,source_label\nJuly,5000,x\n",
     "period_month,avg_fare,source_label\n2026-07,-1,x\n"],
)
def test_invalid_csv_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(content)
    with pytest.raises(ConfigurationError):
        parse_rows(path)


def test_cli_loads_and_upserts(tmp_path: Path, session: Session) -> None:
    path = tmp_path / "dgca.csv"
    path.write_text(CSV)
    assert main([str(path)]) == 0
    assert main([str(path)]) == 0  # idempotent upsert
    all_india = BenchmarkRepository(session).monthly("ALL")
    assert [b.avg_fare for b in all_india] == [Decimal("5480.00"), Decimal("5710.00")]
