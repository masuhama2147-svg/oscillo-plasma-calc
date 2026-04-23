#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/shiny run --reload --port 8000 src/oscillo_plasma_calc/ui/app.py
