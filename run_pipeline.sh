#!/usr/bin/env bash
# TianDao-Info v2.7 — run_pipeline.sh
# Cron orchestrator: process → select → post
# Usage: ./run_pipeline.sh [dry-run]
#   Set DRY_RUN=1 in environment to force dry-run mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

# Load credentials from bashrc (must be bash login shell)
load_env() {
    if [[ -f ~/.bashrc ]]; then
# SUPABASE_KEY loaded from .env — do not hardcode here
    fi
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

DRY_RUN="${DRY_RUN:-0}"
if [[ "${1:-}" == "dry-run" ]] || [[ "$DRY_RUN" == "1" ]]; then
    DRY_RUN=1
fi

main() {
    load_env

    log "=== TianDao-Info v2.7 pipeline starting (dry-run=$DRY_RUN) ==="

    # ── Step 1: Process quotes ────────────────────────────────────────────────
    log "[1/3] Running process_quotes.py ..."
    if ! python3 "$SCRIPT_DIR/process_quotes.py"; then
        log "[ERROR] process_quotes.py failed — aborting pipeline."
        exit 1
    fi
    log "[1/3] process_quotes.py complete."

    # ── Step 2: Daily select ─────────────────────────────────────────────────
    log "[2/4] Running daily_select.py (write selected_quote.json only)..."
    if [[ "$DRY_RUN" == "1" ]]; then
        python3 "$SCRIPT_DIR/daily_select.py" --dry-run
    else
        if ! python3 "$SCRIPT_DIR/daily_select.py"; then
            log "[ERROR] daily_select.py failed — aborting pipeline."
            exit 1
        fi
    fi
    log "[2/4] daily_select.py complete."

    # ── Step 3: Discord post ─────────────────────────────────────────────────
    log "[3/4] Running discord_post.py ..."
    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] Skipping discord_post.py (add --dry-run flag to that script to preview embed)"
    else
        if ! python3 "$SCRIPT_DIR/discord_post.py"; then
            log "[ERROR] discord_post.py failed — state NOT committed."
            exit 1
        fi
    fi
    log "[3/4] discord_post.py complete."

    # ── Step 4: Commit state (only after successful Discord post) ─────────────
    log "[4/4] Committing state (--commit-state)..."
    if [[ "$DRY_RUN" == "1" ]]; then
        log "[DRY-RUN] Skipping state commit."
    else
        if ! python3 "$SCRIPT_DIR/daily_select.py" --commit-state; then
            log "[ERROR] --commit-state failed — state NOT committed."
            exit 1
        fi
    fi
    log "[4/4] State committed."

    log "=== TianDao-Info v2.7 pipeline complete ==="
}

main "$@"
