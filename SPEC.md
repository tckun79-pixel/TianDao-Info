# TianDao-Info v2.7 — Specification

## Project Overview

TianDao-Info is a Chinese religious/philosophical quote management system with:
1. Streamlit dashboard (browse, add, edit, delete, bulk import, export)
2. 3-step daily Discord broadcasting pipeline (process → select → post)
3. Supabase as the database backend
4. GitHub push script for version control

Working directory: `/home/ck_kun/TianDao-Info/`

---

## Section A — Quote Registry

```python
QUOTE_REGISTRY = {
  # Buddhism only for v2.7
}
```

See the full registry definition in the source spec file.

---

## Section B — Religion Config

```python
RELIGION_CONFIG = {
  # Rotation index, Discord color, label, color, sub-categories, tiebreak order
}
```

Sub-categories with triggers:
- 🧠 **mind** — 心性类
- 🌿 **nature** — 自然类
- 🍵 **practice** — 修行类
- 🌀 **emptiness** — 空性类
- ✨ **liberation** — 解脱类

---

## Database Schema (Supabase / PostgreSQL)

```sql
-- Quotes table
CREATE TABLE IF NOT EXISTS quotes (
  id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  quote_text      TEXT        NOT NULL,
  religion        VARCHAR(50) NOT NULL DEFAULT 'buddhism',
  sub_category    VARCHAR(50) NOT NULL,
  attribution_author VARCHAR(255),
  attribution_source VARCHAR(255),
  tags            TEXT[]      DEFAULT '{}',
  merge_group     VARCHAR(100),
  display_order   INTEGER,
  is_merged       BOOLEAN     DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_quotes_text ON quotes(quote_text);
CREATE INDEX IF NOT EXISTS idx_quotes_religion ON quotes(religion);
CREATE INDEX IF NOT EXISTS idx_quotes_sub_category ON quotes(sub_category);

-- Daily selections log
CREATE TABLE IF NOT EXISTS daily_selections (
  id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  quote_id        UUID        REFERENCES quotes(id),
  selected_date   DATE        NOT NULL,
  religion        VARCHAR(50) NOT NULL,
  posted          BOOLEAN     DEFAULT FALSE,
  posted_at       TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(selected_date, religion)
);

CREATE INDEX IF NOT EXISTS idx_selections_date ON daily_selections(selected_date);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_versions (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Process Pipeline (process_quotes.py)

1. Bootstrap schema (create tables/indexes if not exist)
2. Load QUOTE_REGISTRY
3. Expand merge groups into individual quote entries
4. Deduplicate against existing DB content
5. Classify into sub_categories using keyword triggers
6. Resolve attribution using starts_with rules
7. Tag with keywords
8. Write JSON files: `data/quotes/{religion}/{sub_category}.json`
9. Upsert to Supabase (ON CONFLICT quote_text DO UPDATE)
10. Log results

---

## Daily Selection (daily_select.py)

- Read `data/state/rotation_state.json` (tracks rotation_index per religion)
- Select next quote in rotation order for each religion
- `--dry-run`: show what would be selected without writing
- `--commit-state`: actually write selected_quote.json and update state
- Write `data/quotes/selected_quote.json`

---

## Discord Posting (discord_post.py)

- Read `data/quotes/selected_quote.json`
- Build rich embed with:
  - Color from religion config
  - Quote text, author, source
  - Sub-category label
  - Footer with date
- POST to Discord webhook URL
- Handle errors with fallback message

---

## Dashboard (dashboard.py — Streamlit, 6 pages)

1. **Dashboard** — summary stats, recent activity, daily pick preview
2. **Browse** — filterable/searchable quote list
3. **Add** — form to add new quote manually
4. **Edit/Delete** — search and modify/delete existing quotes
5. **Bulk Import** — paste JSON or CSV for bulk insert
6. **Export** — download quotes as JSON or CSV

---

## GitHub Push (push_to_github.py)

- Use GitPython
- Initialize repo if not present
- Auto-create GitHub repo via GitHub API if missing
- Commit all project files
- Push to remote

---

## Cron Orchestrator (run_pipeline.sh)

```sh
# Daily pipeline
python3 scripts/process_quotes.py  # morning — refresh DB
python3 scripts/daily_select.py    # midday — select quote
python3 scripts/discord_post.py    # afternoon — post to Discord
```

---

## UTF-8 Rules

- All file reads/writes: `encoding='utf-8'`
- All JSON: `ensure_ascii=False, indent=2`

---

## Credentials

| Variable | Value |
|---|---|
| SUPABASE_URL | `https://xqatmutydxsxvrgnuwgm.supabase.co` |
| SUPABASE_KEY | `sb_secret_...` |
| SUPABASE_DB_URL | `postgresql://postgres:...@db.xqatmutydxsxvrgnuwgm.supabase.co:5432/postgres` |
| DISCORD_WEBHOOK_URL | Already in `~/.config/openclaw/discord.env` |

---

## Directory Structure

```
TianDao-Info/
├── SPEC.md
├── README.md
├── requirements.txt
├── .env.example
├── dashboard.py
├── process_quotes.py
├── daily_select.py
├── discord_post.py
├── push_to_github.py
├── run_pipeline.sh
├── data/
│   ├── quotes/
│   │   ├── buddhist/
│   │   │   ├── mind.json, nature.json, practice.json, emptiness.json, liberation.json
│   │   │   └── selected_quote.json
│   │   └── {religion}/
│   └── state/
│       └── rotation_state.json
├── logs/
└── scripts/  (helper modules)
```