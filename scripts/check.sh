#!/usr/bin/env bash
set -euo pipefail
python -m ruff check src tests leaderboard scripts
python -m pytest -q
python -m forecast_workflow.cli results --input leaderboard/results.json
