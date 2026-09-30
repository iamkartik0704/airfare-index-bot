"""Back-test APIx against the loaded DGCA benchmark.

Thin wrapper over ``safar backtest`` (``packages.index_engine.backtest_service``),
kept for discoverability. Usage::

    python -m scripts.backtest [--date-from 2026-08-01] [--date-to 2026-09-30]
"""

from __future__ import annotations

import sys

from packages.job_orchestration.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["backtest", *sys.argv[1:]]))
