#!/usr/bin/env python3
"""
TianDao-Info v2.7 — discord_post.py
Step 3 of 3-agent daily pipeline.
Read data/selected_quote.json, post rich embed to Discord webhook.
"""

import json
import logging
import os
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

import os as _os
from dotenv import load_dotenv as _load_dotenv
_load_dotenv(_os.path.expanduser('~/.config/openclaw/discord.env'), override=True)

BASE_DIR = Path(__file__).parent.resolve()
SELECTED_FILE = BASE_DIR / "data" / "quotes" / "selected_quote.json"
DISCORD_ENV = Path.home() / ".config" / "openclaw" / "discord.env"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "logs" / f"discord_post_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("discord_post")

RELIGION_COLORS = {
    "buddhism": 0x6B5B95,
}

RELIGION_LABELS = {
    "buddhism": "佛教 / 禅宗",
}

SUB_CATEGORY_LABELS = {
    "mind":       "🧠 心性",
    "nature":     "🌿 自然",
    "practice":   "🍵 修行",
    "emptiness":  "🌀 空性",
    "liberation": "✨ 解脱",
}


def load_discord_webhook() -> str:
    """Load webhook URL from discord.env or environment."""
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        return os.environ["DISCORD_WEBHOOK_URL"]

    env_file = DISCORD_ENV
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                if line.startswith("DISCORD_WEBHOOK_URL") and "=" in line:
                    return line.split("=", 1)[1].strip()

    raise RuntimeError("DISCORD_WEBHOOK_URL not found in environment or ~/.config/openclaw/discord.env")


def load_selected_quote() -> dict:
    if not SELECTED_FILE.exists():
        raise FileNotFoundError(f"selected_quote.json not found at {SELECTED_FILE}")
    with open(SELECTED_FILE, encoding="utf-8") as f:
        return json.load(f)


def build_embed(quote: dict) -> dict:
    religion = quote.get("religion", "buddhism")
    sub_cat = quote.get("sub_category", "mind")
    today = date.today().isoformat()

    # Remove trailing punctuation for a cleaner display quote
    text = quote["content"].rstrip("。")
    display_text = f"「{text}」"

    embed = {
        "title": f"{SUB_CATEGORY_LABELS.get(sub_cat, sub_cat)} · {RELIGION_LABELS.get(religion, religion)}",
        "description": display_text,
        "color": RELIGION_COLORS.get(religion, 0x6B5B95),
        "fields": [
            {
                "name": "📖 出处",
                "value": f"**{quote['author']}** — {quote['source']}",
                "inline": False,
            },
        ],
        "footer": {
            "text": f"TianDao-Info · {today}",
        },
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    tags = quote.get("tags", [])
    if tags:
        tag_str = " · ".join(tags[:8])  # cap at 8 tags
        embed["fields"].append({
            "name": "🏷 关键词",
            "value": tag_str,
            "inline": False,
        })

    return embed


def post_to_discord(embed: dict, webhook_url: str) -> bool:
    import requests as _requests
    payload = {"embeds": [embed]}
    try:
        resp = _requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code in (200, 204):
            return True
        body = resp.json()
        log.error(f"HTTP error posting to Discord: {resp.status_code} — error code: {body.get('code', '?')}")
        return False
    except Exception as exc:
        log.error(f"Exception posting to Discord: {exc}")
        return False


def main():
    log.info("=== discord_post.py v2.7 starting ===")

    try:
        webhook_url = load_discord_webhook()
        quote = load_selected_quote()
    except Exception as exc:
        log.error("Failed to load data: %s", exc)
        sys.exit(1)

    embed = build_embed(quote)
    success = post_to_discord(embed, webhook_url)

    if not success:
        # Fallback: log the quote text so it can be posted manually
        log.warning("Discord post failed. Quote for manual posting:")
        log.warning("「%s」 — %s (%s)", quote["content"],
                   quote["author"], quote["source"])
        sys.exit(1)

    log.info("=== discord_post.py complete ===")


if __name__ == "__main__":
    main()
