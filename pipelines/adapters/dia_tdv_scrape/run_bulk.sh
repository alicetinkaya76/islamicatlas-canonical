#!/usr/bin/env bash
# H9 Stage 2d — overnight bulk-run launcher for dia-tdv-scrape (AO).
#
# Self-resuming: safe to re-run; completed slugs are skipped (checkpoint sidecar
# data/_state/h9_scrape_progress.json). Prevents sleep (caffeinate -i), detaches
# (nohup), appends to logs/h9_scrape.log (gitignored).
#
# Compliance: ADR-014 — runs ONLY under İSAM written permission; 1 request / 2 s,
# single-threaded, identifying User-Agent. Scope: ~8,093 distinct slugs ≈ 4.5 h
# (minus any already-done pilot slugs). Raw HTML archived gzipped + gitignored.
#
# Usage:   bash pipelines/adapters/dia_tdv_scrape/run_bulk.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."                     # → repo root
mkdir -p logs
LOG="logs/h9_scrape.log"

echo "[run_bulk] $(date -u +%FT%TZ) launching dia-tdv-scrape --all (self-resuming)."
caffeinate -i nohup python3 pipelines/adapters/dia_tdv_scrape/scrape.py --all \
    >> "$LOG" 2>&1 &
echo "[run_bulk] detached (wrapper PID $!). Log: $LOG"
echo "[run_bulk] monitor : tail -f $LOG"
echo "[run_bulk]           python3 pipelines/adapters/dia_tdv_scrape/scrape.py --status"
echo "[run_bulk] stop     : pkill -INT -f dia_tdv_scrape/scrape.py   (graceful checkpoint; re-run this script to resume)"
echo "[run_bulk] after done: python3 pipelines/adapters/dia_tdv_scrape/scrape.py --assemble"
