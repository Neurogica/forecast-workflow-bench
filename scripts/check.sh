#!/usr/bin/env bash
set -euo pipefail
python -m ruff check src tests leaderboard scripts
python scripts/audit_release.py
python -m pytest -q
python -m forecast_workflow.cli results --input results/leaderboard.json
