#!/usr/bin/env python3
"""
TianDao-Info v2.7 — daily_select.py
Step 2 of 3-agent daily pipeline.
Read rotation state, select next quote for each religion.
Supports --dry-run and --commit-state flags.
Writes data/quotes/{religion}/selected_quote.json and data/state/rotation_state.json.
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
STATE_FILE = BASE_DIR / "data" / "state" / "rotation_state.json"
OUTPUT_FILE = BASE_DIR / "data" / "quotes" / "selected_quote.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / f"daily_select_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("daily_select")

RELIGIONS = ["buddhism"]  # extend here as registry grows


def load_rotation_state() -> dict:
    if not STATE_FILE.exists():
        return {rel: {"rotation_index": 0} for rel in RELIGIONS}
    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_rotation_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_sb_client() -> Client:
    load_dotenv(BASE_DIR / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
    return create_client(url, key)


def load_all_quotes(religion: str) -> list[dict]:
    try:
        sb = get_sb_client()
        result = sb.table("quotes").select("*").eq("religion", religion).execute()
        quotes = result.data
        if not quotes:
            log.warning("No quotes found in Supabase for religion '%s'.", religion)
        return quotes
    except Exception as exc:
        log.error("Failed to load quotes from Supabase: %s", exc)
        # Fallback to local JSON
        all_file = BASE_DIR / "data" / "quotes" / religion / "all.json"
        if all_file.exists():
            with open(all_file, encoding="utf-8") as f:
                return json.load(f)
        return []


def select_next_quote(religion: str, state: dict) -> dict | None:
    quotes = load_all_quotes(religion)
    if not quotes:
        return None

    idx = state.get(religion, {}).get("rotation_index", 0)
    # Wrap around
    selected = quotes[idx % len(quotes)]
    return selected


def write_selected_quote(selected: dict):
    # Strip charcount if present (it's a generated column)
    clean = {k: v for k, v in selected.items() if k != "charcount"}
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    log.info("Wrote selected_quote.json — %s", clean.get("content", clean.get("quote_text", ""))[:30])


def advance_rotation(state: dict, religion: str, total: int):
    if religion not in state:
        state[religion] = {}
    state[religion]["rotation_index"] = (state[religion].get("rotation_index", 0) + 1) % total


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Daily quote selector")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be selected without writing state or files")
    parser.add_argument("--commit-state", action="store_true",
                        help="Actually write state and selected_quote.json (default: dry-run)")
    parser.add_argument("--religion", default="buddhism",
                        help="Religion to select from (default: buddhism)")
    args = parser.parse_args()

    dry_run = args.dry_run
    commit_state = args.commit_state
    # Write selected_quote.json if NOT dry-run
    write_selected = not dry_run
    # Write state.json only if --commit-state
    write_state = commit_state

    log.info("=== daily_select.py v2.7 starting (%s) ===", "dry-run" if dry_run else ("commit" if commit_state else "normal"))

    state = load_rotation_state()
    religion = args.religion
    quotes = load_all_quotes(religion)
    total = len(quotes)

    if total == 0:
        log.error("No quotes available for '%s'. Aborting.", religion)
        sys.exit(1)

    selected = select_next_quote(religion, state)
    if not selected:
        log.error("Selection returned None. Aborting.")
        sys.exit(1)

    # Show preview
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Selected quote ({religion}):")
    print(f"  Text: {selected.get('content', selected.get('quote_text', ''))}")
    print(f"  Author: {selected.get('author', selected.get('attribution_author', ''))}")
    print(f"  Source: {selected.get('source', selected.get('attribution_source', ''))}")
    print(f"  Sub-category: {selected.get('subcategory', selected.get('sub_category', ''))}")
    print(f"  Rotation index: {state.get(religion, {}).get('rotation_index', 0)} / {total - 1}")

    if dry_run:
        print("\n  → Pass --commit-state to write state and selected_quote.json")
    else:
        if write_selected:
            write_selected_quote(selected)
            print("\n  → Wrote selected_quote.json")
        if write_state:
            advance_rotation(state, religion, total)
            save_rotation_state(state)
            print(f"\n  → State committed: next index = {state[religion]['rotation_index']} (was {(state[religion]['rotation_index'] - 1) % total})")
        if write_selected and not write_state:
            print("\n  → (state not updated - pass --commit-state to persist)")

    log.info("=== daily_select.py complete ===")


if __name__ == "__main__":
    main()
