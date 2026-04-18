#!/usr/bin/env python3
"""
TianDao-Info v2.7 — process_quotes.py
Step 1 of 3-agent daily pipeline.
Bootstrap Supabase schema, load QUOTE_REGISTRY, process (merge/dedupe/classify/attribute/tag),
write JSON files, upsert to Supabase.
"""

import json
import re
import os
from dotenv import load_dotenv
import sys
import logging
from datetime import datetime
from pathlib import Path

from supabase import create_client, Client

# ── Paths ────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
STATE_DIR = DATA_DIR / "state"
DATA_QUOTES_DIR = DATA_DIR / "quotes"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"process_quotes_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("process_quotes")

# ── Registry ────────────────────────────────────────────────────────────────────
QUOTE_REGISTRY = {
    "buddhism": {
        "label": "佛教 / 禅宗",
        "id_prefix": "bud",
        "merge_rules": [
            ["春有百花秋有月。", "夏有凉风冬有雪。", "若无闲事挂心头。", "便是人间好时节。"],
            ["行亦禅，坐亦禅。", "语默动静体安然。"],
            ["一切有为法，如梦幻泡影。", "如露亦如电，应作如是观。"],
            ["心无挂碍。", "无挂碍故，无有恐怖。"],
            ["空手把锄头，步行骑水牛。", "人从桥上过，桥流水不流。"],
            ["心平何劳持戒。", "行直何用修禅。"],
            ["一灯能除千年暗。", "一智能灭万年愚。"],
        ],
        "raw_quotes": [
            "本来无一物，何处惹尘埃。", "菩提本无树，明镜亦非台。", "应无所住，而生其心。",
            "直指人心，见性成佛。", "不立文字，教外别传。", "平常心是道。", "吃茶去。",
            "即心即佛。", "非心非佛。", "明心见性。", "见性成佛。", "佛法在世间，不离世间觉。",
            "离世觅菩提，恰如求兔角。", "无念为宗。", "无相为体。", "无住为本。",
            "前念迷即凡夫，后念悟即佛。", "念念不离自性。", "迷时师度，悟时自度。",
            "自性若悟，众生是佛。", "一念愚即般若绝，一念智即般若生。",
            "不是风动，不是幡动，仁者心动。", "逢佛杀佛，逢祖杀祖。", "随处作主，立处皆真。",
            "无事是贵人。", "赤肉团上，有一无位真人。", "平常无事，便是安乐。", "日日是好日。",
            "春有百花秋有月。", "夏有凉风冬有雪。", "若无闲事挂心头。", "便是人间好时节。",
            "行亦禅，坐亦禅。", "语默动静体安然。", "饥来吃饭，困来即眠。", "担水砍柴，无非妙道。",
            "柳绿花红，无非妙道。", "郁郁黄花，无非般若。", "青青翠竹，尽是法身。",
            "溪声尽是广长舌，山色无非清净身。", "山河大地，皆是法身。", "一花一世界。",
            "一叶如来。", "万法唯心。", "心外无法。", "触目皆道。", "当下即是。", "回头是岸。",
            "放下即自在。", "一念放下，万般自在。", "烦恼即菩提。", "生死即涅槃。",
            "色即是空，空即是色。", "凡所有相，皆是虚妄。", "若见诸相非相，即见如来。",
            "一切有为法，如梦幻泡影。", "如露亦如电，应作如是观。", "心无挂碍。",
            "无挂碍故，无有恐怖。", "远离颠倒梦想。", "心净则国土净。", "欲得净土，当净其心。",
            "心生种种法生，心灭种种法灭。", "一切现成。", "本地风光。", "莫向外求。", "向内观心。",
            "但尽凡心，别无圣解。", "但用此心，直了成佛。", "但自无心，于万物何妨。",
            "不怕念起，只怕觉迟。", "念起即觉，觉之即无。",
            "见山是山，见山不是山，见山还是山。", "看山还是山，看水还是水。",
            "睡时便睡，坐时便坐。", "来时无所从来，去时亦无所去。", "随缘不变，不变随缘。",
            "随缘消旧业，更莫造新殃。", "一切众生，皆有佛性。", "当处出生，随处灭尽。",
            "云在青天水在瓶。", "空手把锄头，步行骑水牛。", "人从桥上过，桥流水不流。",
            "大死一番，方得大活。", "庭前柏树子。", "麻三斤。", "本来面目。",
            "父母未生前本来面目。", "万古长空，一朝风月。", "不取于相，如如不动。",
            "心平何劳持戒。", "行直何用修禅。", "见色明心，闻声悟道。", "脚下即是道场。",
            "处处皆是道场。", "一灯能除千年暗。", "一智能灭万年愚。", "心安即是归处。",
            "当下这一念，便是归家路。", "放下分别，便见清凉。",
        ],
        "attribution": [
            {"starts_with": ["本来无一物", "菩提本无树", "不是风动", "心平何劳持戒",
             "无念为宗", "无相为体", "无住为本", "前念迷即凡夫",
             "念念不离自性", "佛法在世间"],
             "author": "惠能 (六祖)", "source": "六祖坛经"},
            {"starts_with": ["应无所住", "凡所有相", "一切有为法", "若见诸相", "不取于相"],
             "author": "—", "source": "金刚经"},
            {"starts_with": ["色即是空", "心无挂碍", "远离颠倒"],
             "author": "—", "source": "心经"},
            {"starts_with": ["平常心是道"], "author": "南泉普愿", "source": "景德传灯录"},
            {"starts_with": ["吃茶去", "庭前柏树子"], "author": "赵州从谂", "source": "赵州录"},
            {"starts_with": ["逢佛杀佛", "随处作主", "赤肉团上"],
             "author": "临济义玄", "source": "临济录"},
            {"starts_with": ["日日是好日", "麻三斤"], "author": "云门文偃", "source": "云门录"},
            {"starts_with": ["春有百花秋有月"], "author": "无门慧开", "source": "无门关"},
            {"starts_with": ["溪声尽是广长舌"], "author": "苏轼", "source": "赠东林总长老偈"},
            {"starts_with": ["直指人心", "不立文字"], "author": "达摩", "source": "禅宗传灯录"},
            {"starts_with": ["见山是山"], "author": "青原惟信", "source": "五灯会元"},
            {"starts_with": ["一花一世界", "一叶如来"], "author": "—", "source": "华严经"},
            {"starts_with": ["随缘消旧业"], "author": "—", "source": "禅宗偈语"},
        ],
        "default_attribution": {"author": "禅宗古德", "source": "禅宗语录"},
    }
}

RELIGION_CONFIG = {
    "buddhism": {
        "rotation_index": 0,
        "discord_color": 6736998,
        "label": "佛教 / 禅宗",
        "color": "#6B5B95",
        "sub_categories": {
            "mind":       {"label": "🧠 心性", "triggers": ["心","念","性","觉","迷","悟","佛性","般若","自性","菩提"]},
            "nature":     {"label": "🌿 自然", "triggers": ["花","竹","山","水","云","翠","溪","月","雪","风","柳","春","黄花"]},
            "practice":   {"label": "🍵 修行", "triggers": ["坐","禅","吃","饮","睡","砍","担","行","戒","道场","饥","困"]},
            "emptiness":  {"label": "🌀 空性", "triggers": ["空","无","虚","幻","泡","露","电","非","无相","无念","无住"]},
            "liberation": {"label": "✨ 解脱", "triggers": ["放下","自在","涅槃","归","自度","安乐","清凉","回头","随缘"]},
        },
        "tiebreak_order": ["mind", "emptiness", "liberation", "practice", "nature"],
        "default_sub_category": "mind",
    }
}

# ── DB helpers ────────────────────────────────────────────────────────────────
# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv("/home/ck_kun/TianDao-Info/.env")
except ImportError:
    pass

def process_all_quotes() -> list[dict]:
    """Process quotes for all religions: merge → dedup → classify → tag."""
    all_entries = []
    for religion_key in QUOTE_REGISTRY:
        entries = expand_merge_groups(religion_key)
        entries = deduplicate_entries(entries)
        entries = classify_sub_categories(entries, religion_key)
        entries = assign_attributions(entries, religion_key)
        entries = extract_tags(entries)
        all_entries.extend(entries)
        log.info("Processed %d entries for %s.", len(entries), religion_key)
    return all_entries


def write_json_files(quotes: list[dict]):
    """Group quotes by religion and sub_category, write to JSON files."""
    data_dir = Path("data/quotes")
    data_dir.mkdir(parents=True, exist_ok=True)

    by_religion = {}
    for q in quotes:
        rel = q["religion"]
        sub = q["sub_category"]
        by_religion.setdefault(rel, {}).setdefault(sub, []).append(q)

    for rel, subcats in by_religion.items():
        rel_dir = data_dir / rel
        rel_dir.mkdir(parents=True, exist_ok=True)
        for sub, qs in subcats.items():
            out_file = rel_dir / f"{sub}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(qs, f, ensure_ascii=False, indent=2)
            log.info("Wrote %s (%d quotes)", out_file, len(qs))

    # Also write all-in-one per religion
    for rel, subcats in by_religion.items():
        all_qs = []
        for qs in subcats.values():
            all_qs.extend(qs)
        out_file = data_dir / rel / "all.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(all_qs, f, ensure_ascii=False, indent=2)
        log.info("Wrote %s (%d total)", out_file, len(all_qs))

    # Write master index
    master = {
        "religions": list(by_religion.keys()),
        "total_quotes": len(quotes),
        "by_religion": {
            rel: {sub: len(qs) for sub, qs in subcats.items()}
            for rel, subcats in by_religion.items()
        },
        "last_updated": datetime.now().isoformat(),
    }
    with open(data_dir / "master_index.json", "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)
    log.info("Wrote master index.")


def deduplicate_entries(entries: list[dict]) -> list[dict]:
    """Deduplicate by quote_text, preserve first occurrence."""
    seen = set()
    result = []
    for e in entries:
        txt = e["quote_text"]
        if txt not in seen:
            seen.add(txt)
            result.append(e)
        else:
            log.warning("Duplicate removed: %s", txt[:50])
    return result


def classify_sub_categories(entries: list[dict], religion_key: str) -> list[dict]:
    """Classify each entry into sub_category based on trigger words."""
    cfg = RELIGION_CONFIG[religion_key]
    sub_cats = cfg["sub_categories"]
    tiebreak = cfg.get("tiebreak_order", list(sub_cats.keys()))

    for entry in entries:
        text = entry["quote_text"]
        scores = {}
        for sub_key, sub_cfg in sub_cats.items():
            score = sum(1 for w in sub_cfg.get("triggers", []) if w in text)
            scores[sub_key] = score

        best_score = max(scores.values()) if scores else 0
        if best_score == 0:
            entry["sub_category"] = cfg["default_sub_category"]
            entry["sub_category_label"] = sub_cats[cfg["default_sub_category"]]["label"]
            continue

        best_subs = [s for s, sc in scores.items() if sc == best_score]
        if len(best_subs) == 1:
            chosen = best_subs[0]
        else:
            idx = min(tiebreak.index(s) for s in best_subs if s in tiebreak)
            chosen = tiebreak[idx]

        entry["sub_category"] = chosen
        entry["sub_category_label"] = sub_cats[chosen]["label"]
    return entries


def assign_attributions(entries: list[dict], religion_key: str) -> list[dict]:
    """Assign author/source based on starts_with rules."""
    registry = QUOTE_REGISTRY[religion_key]
    attrib_rules = registry.get("attribution", [])
    default = registry.get("default_attribution", {"author": "佚名", "source": "—"})

    for entry in entries:
        txt = entry["quote_text"]
        author, source = default["author"], default["source"]
        for rule in attrib_rules:
            if any(txt.startswith(sw) for sw in rule.get("starts_with", [])):
                author = rule.get("author", author)
                source = rule.get("source", source)
                break
        entry["author"] = author
        entry["source"] = source
    return entries


TAG_RE = re.compile(r"[一-鿿]{2,4}")
STOP_TAGS = {"的", "是", "有", "无", "在", "为", "不", "也", "都", "了", "曰", "云"}

def extract_tags(entries: list[dict]) -> list[dict]:
    """Extract 2-4 unique Chinese keyword tags per entry."""
    for entry in entries:
        text = entry["quote_text"]
        raw_tags = TAG_RE.findall(text)
        entry["tags"] = list(dict.fromkeys(t for t in raw_tags if t not in STOP_TAGS))[:4]
    return entries


def validate_config():
    """Verify all religions in QUOTE_REGISTRY exist in RELIGION_CONFIG with required keys."""
    required_keys = ["label", "sub_categories", "tiebreak_order", "default_sub_category"]
    for rkey in QUOTE_REGISTRY:
        if rkey not in RELIGION_CONFIG:
            raise KeyError(f"Religion '{rkey}' in QUOTE_REGISTRY but missing from RELIGION_CONFIG")
        for k in required_keys:
            if k not in RELIGION_CONFIG[rkey]:
                raise KeyError(f"RELIGION_CONFIG['{rkey}'] missing required key: {k}")


def expand_merge_groups(religion_key: str) -> list[dict]:
    """Expand merge groups: emit merged full text, skip fragments.
    
    CRITICAL ORDER:
    1. If line is first component of merge group → emit FULL merged text
    2. Else if line in component_set → skip (it's a fragment)
    3. Else → emit as-is
    """
    registry = QUOTE_REGISTRY[religion_key]
    rcfg = RELIGION_CONFIG[religion_key]
    
    # Build component_set: all lines in merge groups (for skip detection)
    component_set = set()
    for group in registry["merge_rules"]:
        for line in group:
            component_set.add(line)
    
    entries = []
    order = 0

    # First: emit FULL merged quote for each group (not individual lines)
    for group_idx, group in enumerate(registry["merge_rules"]):
        if not group:
            continue
        merged_text = "".join(group)  # Full merged text
        group_id = f"{registry['id_prefix']}_grp{group_idx:03d}"
        entries.append({
            "quote_text": merged_text,
            "religion": religion_key,
            "sub_category": rcfg["default_sub_category"],
            "author": registry["default_attribution"]["author"],
            "source": registry["default_attribution"]["source"],
            "tags": [],
            "merge_group": group_id,
            "display_order": order,
            "is_merged": True,
        })
        order += 1

    # Second: raw_quotes - skip if in component_set, emit otherwise
    for raw in registry["raw_quotes"]:
        if raw in component_set:
            continue  # Skip fragments already in merge groups
        entries.append({
            "quote_text": raw,
            "religion": religion_key,
            "sub_category": rcfg["default_sub_category"],
            "author": registry["default_attribution"]["author"],
            "source": registry["default_attribution"]["source"],
            "tags": [],
            "merge_group": None,
            "display_order": order,
            "is_merged": False,
        })
        order += 1

    return entries


def get_sb_client() -> Client:
    """Create Supabase client using SUPABASE_URL and SUPABASE_KEY from environment."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(url, key)


# Schema bootstrap not needed via REST API - table must exist in Supabase
def bootstrap_schema(sb):
    """Table schema must exist in Supabase. Run DB bootstrap manually if needed."""
    log.info("Schema assumed to exist in Supabase.")

def upsert_to_supabase(sb: Client, quotes: list[dict]):
    """Upsert quotes to Supabase via REST API. Batch size 50."""
    BATCH_SIZE = 50
    total = len(quotes)
    total_upserted = 0
    errors = 0
    
    # Only use columns that exist in Supabase table: id, content, author, source, religion, tags
    for i in range(0, total, BATCH_SIZE):
        batch = quotes[i:i+BATCH_SIZE]
        clean_batch = []
        for j, q in enumerate(batch):
            idx = i + j
            clean_q = {
                'id': f"bud_{idx+1:03d}",
                'content': q.get('quote_text', ''),
                'author': q.get('author') or q.get('attribution_author', '佚名'),
                'source': q.get('source') or q.get('attribution_source', '—'),
                'religion': q.get('religion', 'buddhism'),
                'religionlabel': q.get('religion_label', '佛教 / 禅宗'),
                'category': q.get('category', 'buddhism'),
                'subcategory': q.get('sub_category', ''),
                'subcategorylabel': q.get('sub_category_label', ''),
                'tags': q.get('tags', []),
            }
            clean_batch.append(clean_q)
        
        try:
            result = sb.table("quotes").upsert(clean_batch, on_conflict="id").execute()
            total_upserted += len(clean_batch)
            log.info("Upserted batch %d-%d (%d total)", i+1, min(i+BATCH_SIZE, total), total_upserted)
        except Exception as exc:
            log.warning("Batch %d-%d failed: %s — continuing with remaining batches", i+1, min(i+BATCH_SIZE, total), exc)
            errors += 1
    
    log.info("Upsert complete: %d/%d quotes (%d batches, %d errors)", total_upserted, total, (total+BATCH_SIZE-1)//BATCH_SIZE, errors)
    return total_upserted

def get_row_count(sb: Client) -> int:
    """Get total count of quotes in Supabase."""
    try:
        result = sb.table("quotes").select("id", count="exact").execute()
        return result.count if hasattr(result, 'count') else len(result.data)
    except Exception:
        return 0


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("=== process_quotes.py v2.7 starting ===")
    
    # Validate config before processing
    validate_config()

    try:
        sb = get_sb_client()
    except Exception as exc:
        log.warning("Supabase not available (%s) — skipping DB write, writing JSON only.", exc)
        conn = None

    if sb:
        try:
            bootstrap_schema(sb)
        except Exception as exc:
            log.warning("Schema check skipped: %s", exc)

    quotes = process_all_quotes()
    write_json_files(quotes)

    if sb:
        try:
            before = get_row_count(sb)
            upsert_to_supabase(sb, quotes)
            after = get_row_count(sb)
            log.info("DB: %d → %d rows after upsert.", before, after)
        except Exception as exc:
            log.error("DB upsert failed: %s", exc)
    else:
        log.info("DB skipped — JSON files written only.")

    log.info("=== process_quotes.py complete — %d quotes processed ===", len(quotes))


if __name__ == "__main__":
    main()
