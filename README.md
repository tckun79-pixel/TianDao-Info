# TianDao-Info v2.7

Chinese religious/philosophical quote management system. Manages a curated quote
registry and runs a daily Discord broadcasting pipeline backed by Supabase.

---

## Prerequisites

- Python 3.10+
- A Supabase PostgreSQL project
- A Discord server with at least one channel and a webhook
- (Optional) GitHub personal access token for `push_to_github.py`

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Credentials Setup

Credentials are loaded from `~/.bashrc` automatically when scripts are run
inside a login shell. Source them before running any script:

```bash
source ~/.bashrc
```

Or copy `.env.example` to `.env` and fill in the values. When using `.env`,
load it before running scripts:

```bash
set -a && source .env && set +a
```

Required variables in `~/.bashrc` (or `.env`):

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `SUPABASE_DB_URL` | Full PostgreSQL connection string |
| `DISCORD_WEBHOOK_URL` | Discord channel webhook URL |
| `GITHUB_USER` | GitHub username |
| `GITHUB_TOKEN` | GitHub personal access token |

---

## Running the Pipeline

### Step 1 — Bootstrap and process quotes

```bash
source ~/.bashrc
python3 process_quotes.py
```

- Creates the DB schema if it doesn't exist
- Loads the quote registry, expands merge groups, classifies into
  sub-categories, resolves attribution, assigns tags
- Writes JSON files to `data/quotes/{religion}/`
- Upserts everything into Supabase (skipped if DB unreachable)

### Step 2 — Select daily quote (dry-run)

```bash
source ~/.bashrc
python3 daily_select.py --dry-run
```

Reads the rotation state, picks the next quote in sequence, and prints
a preview without writing anything.

To commit the selection:

```bash
python3 daily_select.py --commit-state
```

### Step 3 — Post to Discord

```bash
source ~/.bashrc
python3 discord_post.py
```

Reads `data/quotes/selected_quote.json`, builds a rich embed, and posts it
to the Discord webhook. Falls back to logging the quote text on failure.

### Full pipeline (cron)

```bash
./run_pipeline.sh
```

Dry-run mode:

```bash
./run_pipeline.sh dry-run
```

---

## Dashboard

Start the Streamlit dashboard:

```bash
streamlit run dashboard.py --server.port 8501
```

Six pages:

| Page | Description |
|---|---|
| Dashboard | Stats, sub-category breakdown, today's pick preview |
| Browse | Searchable/filterable quote list |
| Add | Manual quote entry form |
| Edit/Delete | Search and modify existing quotes |
| Bulk Import | Paste JSON or CSV for bulk insert |
| Export | Download quotes as JSON or CSV |

---

## Cron Setup

Example crontab entries:

```cron
# Morning: refresh quotes DB
0 8 * * *  cd /home/ck_kun/TianDao-Info && ./run_pipeline.sh >> logs/cron.log 2>&1

# Check rotation state
0 9 * * *  cd /home/ck_kun/TianDao-Info && python3 daily_select.py --dry-run >> logs/cron.log 2>&1
```

---

## Adding a New Religion

1. Add the religion key to `QUOTE_REGISTRY` in `process_quotes.py`
2. Add a matching entry to `RELIGION_CONFIG` (sub-categories, tiebreak order, Discord color)
3. Add attribution rules for the new religion's texts
4. Re-run `process_quotes.py` — the new religion's JSON files will be generated automatically

---

## Directory Layout

```
TianDao-Info/
├── SPEC.md
├── README.md
├── requirements.txt
├── .env.example
├── process_quotes.py     ← Step 1: bootstrap, process, upsert
├── daily_select.py       ← Step 2: rotation select
├── discord_post.py       ← Step 3: Discord embed post
├── dashboard.py          ← Streamlit 6-page dashboard
├── push_to_github.py     ← GitPython commit + push
├── run_pipeline.sh       ← Cron orchestrator
├── data/
│   ├── quotes/
│   │   └── buddhist/
│   │       ├── mind.json
│   │       ├── nature.json
│   │       ├── practice.json
│   │       ├── emptiness.json
│   │       ├── liberation.json
│   │       ├── all.json
│   │       └── selected_quote.json
│   └── state/
│       └── rotation_state.json
└── logs/
```

---

## Notes

- All file reads/writes: `encoding="utf-8"`
- All JSON output: `ensure_ascii=False, indent=2`
- `process_quotes.py` skips DB upsert if `SUPABASE_DB_URL` is unreachable
  (e.g. WSL network restrictions) — JSON files are always written
- Rotation advances modulo total quotes, so every quote is served before any repeats
