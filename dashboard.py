#!/usr/bin/env python3
"""
TianDao-Info v2.7 — dashboard.py
Streamlit 6-page dashboard for quote management via Supabase REST API.
"""
import streamlit as st
import re
import json
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).parent.resolve()
DISCORD_ENV = Path.home() / ".config" / "openclaw" / "discord.env"

RELIGION_COLORS = {
    "buddhism": "#6B5B95",
    "daoism": "#4A7C59",
    "yiguandao": "#C0932F",
    "general": "#5B7FA6",
}
RELIGION_LABELS = {
    "buddhism": "佛教 / 禅宗",
    "daoism": "道教",
    "yiguandao": "一贯道",
    "general": "通用",
}
SUB_CATEGORY_LABELS = {
    "mind": "🧠 心性",
    "nature": "🌿 自然",
    "practice": "🍵 修行",
    "emptiness": "🌀 空性",
    "liberation": "✨ 解脱",
}

st.set_page_config(
    page_title="天道 TianDao-Info Dashboard v2.7",
    page_icon="🪷",
    layout="wide",
)

@st.cache_resource
def get_sb():
    load_dotenv(BASE_DIR / ".env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def classify_sub_category(text, religion):
    triggers = {
        "mind": ["心","念","性","觉","迷","悟","佛性","般若","自性","菩提"],
        "nature": ["花","竹","山","水","云","翠","溪","月","雪","风","柳","春","黄花"],
        "practice": ["坐","禅","吃","饮","睡","砍","担","行","戒","道场","饥","困"],
        "emptiness": ["空","无","虚","幻","泡","露","电","非","无相","无念","无住"],
        "liberation": ["放下","自在","涅槃","归","自度","安乐","清凉","回头","随缘"],
    }
    scores = {cat: sum(1 for w in words if w in text) for cat, words in triggers.items()}
    if not scores or max(scores.values()) == 0:
        return "mind"
    best = max(scores.values())
    candidates = [k for k, v in scores.items() if v == best]
    tiebreak = ["mind", "emptiness", "liberation", "practice", "nature"]
    for t in tiebreak:
        if t in candidates:
            return t
    return candidates[0]

def get_discord_status():
    if not DISCORD_ENV.exists():
        return "file_missing"
    with open(DISCORD_ENV) as f:
        content = f.read()
    channel = "unknown"
    valid = False
    for line in content.split("\n"):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            if k == "DISCORD_CHANNEL_NAME":
                channel = v.strip()
            elif k == "DISCORD_WEBHOOK_URL":
                if re.match(r"^https://discord\.com/api/webhooks/\d+/.+$", v.strip()):
                    valid = True
    if valid:
        return f"valid:{channel}"
    return f"invalid:{channel}"

def page_dashboard(sb):
    st.header("📊 Dashboard")
    try:
        r = sb.table("quotes").select("id", count="exact").execute()
        total = r.count if hasattr(r, "count") else len(r.data)
    except:
        total = 0
    try:
        r = sb.table("quotes").select("religion").execute()
        by_rel = {}
        for row in r.data:
            rel = row.get("religion", "unknown")
            by_rel[rel] = by_rel.get(rel, 0) + 1
    except:
        by_rel = {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Quotes", total)
    c2.metric("Active Religions", len(by_rel))
    c3.metric("Top Religion", max(by_rel, key=by_rel.get) if by_rel else "—")
    st.divider()
    st.subheader("Religion Distribution")
    if by_rel:
        cols = st.columns(min(len(by_rel), 3))
        for i, (rel, cnt) in enumerate(sorted(by_rel.items(), key=lambda x: -x[1])):
            color = RELIGION_COLORS.get(rel, "#5B7FA6")
            label = RELIGION_LABELS.get(rel, rel)
            with cols[i % 3]:
                st.markdown(
                    f"<div style='background:{color}22;border-left:4px solid {color};"
                    f"padding:12px;border-radius:4px;margin:4px 0'>"
                    f"<b>{label}</b><br><span style='font-size:24px'>{cnt}</span> quotes</div>",
                    unsafe_allow_html=True,
                )
    st.divider()
    st.subheader("Discord Status")
    status = get_discord_status()
    if status.startswith("valid"):
        channel = status.split(":", 1)[1]
        st.success(f"✅ Connected — {channel}")
    else:
        channel = status.split(":", 1)[1] if ":" in status else "unknown"
        st.error(f"❌ Invalid webhook — {channel}")
    st.divider()
    st.subheader("Pipeline State")
    sf = BASE_DIR / "data" / "state" / "rotation_state.json"
    if sf.exists():
        with open(sf) as f:
            state = json.load(f)
        for rel, info in state.items():
            idx = info.get("rotation_index", 0)
            posted = len(info.get("posted_ids", []))
            st.text(f"{RELIGION_LABELS.get(rel, rel)}: index={idx}, posted={posted}")
    else:
        st.info("No state file")
    st.divider()
    st.subheader("Recent Quotes")
    try:
        r = sb.table("quotes").select("*").order("created_at", desc=True).limit(6).execute()
        for q in r.data:
            rel = q.get("religion", "general")
            color = RELIGION_COLORS.get(rel, "#5B7FA6")
            tags = q.get("tags", []) or []
            tags_str = " · ".join([f"`{t}`" for t in tags[:4]])
            st.markdown(
                f"<div style='border-left:4px solid {color};padding:8px 12px;margin:8px 0;"
                f"background:#f8f9fa;border-radius:0 4px 4px 0'>"
                f"<p style='margin:0;font-family:serif'>{q.get('content','')[:100]}</p>"
                f"<small>{q.get('author','')} · {q.get('source','')} {tags_str}</small></div>",
                unsafe_allow_html=True,
            )
    except Exception as exc:
        st.error(f"Error: {exc}")

def page_browse(sb):
    st.header("📖 Browse Quotes")
    col_f, col_r = st.columns([1, 3])
    with col_f:
        st.subheader("Filters")
        religions = ["all"] + list(RELIGION_LABELS.keys())
        sel_rel = st.selectbox("Religion", religions)
        subcats = ["all"] + list(SUB_CATEGORY_LABELS.keys())
        sel_sub = st.selectbox("Sub-category", subcats)
        search = st.text_input("Keyword search", placeholder="Search...")
    with col_r:
        query = sb.table("quotes").select("*")
        if sel_rel != "all":
            query = query.eq("religion", sel_rel)
        if sel_sub != "all":
            query = query.eq("subcategory", sel_sub)
        if search:
            query = query.ilike("content", f"%{search}%")
        try:
            r = query.order("created_at", desc=True).limit(200).execute()
            data = r.data
        except:
            data = []
        st.text(f"Showing {len(data)} quotes")
        for q in data:
            rel = q.get("religion", "general")
            color = RELIGION_COLORS.get(rel, "#5B7FA6")
            tags = q.get("tags", []) or []
            tags_str = " · ".join([f"<code>{t}</code>" for t in tags[:4]])
            subcat = q.get("subcategory", "")
            subcat_label = SUB_CATEGORY_LABELS.get(subcat, subcat)
            st.markdown(
                f"<div style='border-left:4px solid {color};padding:12px;margin:12px 0;"
                f"background:#fafafa;border-radius:0 4px 4px 0'>"
                f"<p style='font-family:serif;font-size:16px;margin:0 0 8px'>{q.get('content','')}</p>"
                f"<small><b>{q.get('author','')}</b> · {q.get('source','')} · "
                f"<span style='color:{color}'>{subcat_label}</span><br>"
                f"ID: {q.get('id','')} {tags_str}</small></div>",
                unsafe_allow_html=True,
            )

def page_add(sb):
    st.header("➕ Add Quote")
    with st.form("add_form", clear_on_submit=True):
        content = st.text_area("Quote content", key="add_content")
        c1, c2 = st.columns(2)
        with c1:
            religion = st.selectbox("Religion", list(RELIGION_LABELS.keys()), key="add_rel")
            author = st.text_input("Author", key="add_author")
        with c2:
            subcat = st.selectbox("Sub-category", list(SUB_CATEGORY_LABELS.keys()), key="add_sub")
            source = st.text_input("Source", key="add_source")
        tags = st.text_input("Tags (comma-separated)", key="add_tags")
        auto_sug = st.checkbox("🤖 Auto-suggest sub-category", value=True)
        if auto_sug and content:
            sug = classify_sub_category(content, religion)
            st.info(f"Suggested: {SUB_CATEGORY_LABELS.get(sug, sug)}")
        sub = st.form_submit_button("Add Quote", use_container_width=True)
    if sub and content:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()][:4]
        try:
            id_r = sb.rpc("next_quote_id", {"prefix": religion[:3]}).execute()
            new_id = id_r.data
        except:
            new_id = f"{religion[:3]}_999"
        payload = {
            "id": new_id,
            "content": content,
            "author": author or "佚名",
            "source": source or "—",
            "religion": religion,
            "religionlabel": RELIGION_LABELS.get(religion, religion),
            "category": religion,
            "subcategory": subcat,
            "subcategorylabel": SUB_CATEGORY_LABELS.get(subcat, subcat),
            "tags": tag_list,
        }
        try:
            sb.table("quotes").insert(payload).execute()
            st.balloons()
            st.success(f"✅ Added: {new_id}")
        except Exception as exc:
            st.error(f"Insert failed: {exc}")

def page_edit_delete(sb):
    st.header("✏️ Edit / Delete")
    try:
        r = sb.table("quotes").select("id,content,author,source,religion,tags").limit(500).execute()
        quotes = r.data
    except:
        quotes = []
    options = {q["id"]: f"{q['content'][:40]} — {q['author']}" for q in quotes}
    sel_id = st.selectbox("Select quote", options=[""] + list(options.keys()),
                        format_func=lambda x: options.get(x, "— Select —") if x else "— Select —")
    if not sel_id:
        return
    sel_q = next((q for q in quotes if q["id"] == sel_id), None)
    if not sel_q:
        return
    tab_e, tab_d = st.tabs(["✏️ Edit", "🗑️ Delete"])
    with tab_e:
        with st.form("edit_form", clear_on_submit=False):
            content = st.text_area("Content", value=sel_q.get("content", ""), key="edit_content")
            c1, c2 = st.columns(2)
            with c1:
                author = st.text_input("Author", value=sel_q.get("author", ""), key="edit_author")
                religion = st.selectbox("Religion", list(RELIGION_LABELS.keys()), key="edit_rel")
            with c2:
                source = st.text_input("Source", value=sel_q.get("source", ""), key="edit_source")
                subcat = st.selectbox("Sub-category", list(SUB_CATEGORY_LABELS.keys()), key="edit_sub")
            tags_str = ", ".join(sel_q.get("tags", []) or [])
            tags = st.text_input("Tags", value=tags_str, key="edit_tags")
            sub2 = st.form_submit_button("Save Changes", use_container_width=True)
        if sub2:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()][:4]
            payload = {
                "content": content,
                "author": author,
                "source": source,
                "religion": religion,
                "religionlabel": RELIGION_LABELS.get(religion, religion),
                "subcategory": subcat,
                "subcategorylabel": SUB_CATEGORY_LABELS.get(subcat, subcat),
                "tags": tag_list,
            }
            try:
                sb.table("quotes").update(payload).eq("id", sel_id).execute()
                st.success("✅ Updated!")
                st.rerun()
            except Exception as exc:
                st.error(f"Update failed: {exc}")
    with tab_d:
        st.warning(f"Delete:\n\n**{sel_q.get('content','')[:100]}**")
        confirm = st.checkbox("I understand this is permanent", key="del_conf")
        if st.button("Delete permanently", disabled=not confirm, type="primary"):
            try:
                sb.table("quotes").delete().eq("id", sel_id).execute()
                st.success("🗑️ Deleted!")
                st.rerun()
            except Exception as exc:
                st.error(f"Delete failed: {exc}")

def page_bulk_import(sb):
    st.header("📥 Bulk Import JSON")
    uploaded = st.file_uploader("Upload JSON array", type="json")
    if not uploaded:
        return
    try:
        data = json.load(uploaded)
        if not isinstance(data, list):
            st.error("JSON must be an array")
            return
        st.info(f"Loaded {len(data)} quotes")
        st.subheader("Preview (first 10)")
        st.dataframe(data[:10], use_container_width=True)
        mode = st.radio("ID handling", ["Overwrite existing (upsert)", "Auto-assign missing"])
        if st.button("Import all", use_container_width=True):
            prog = st.progress(0)
            imported = errors = 0
            for i in range(0, len(data), 50):
                batch = data[i:i+50]
                clean_batch = []
                for item in batch:
                    clean = {k: v for k, v in item.items() if k not in ("charcount", "created_at", "updated_at")}
                    clean["content"] = clean.pop("quote_text", clean.get("content", ""))
                    clean["author"] = clean.pop("attribution_author", clean.get("author", ""))
                    clean["source"] = clean.pop("attribution_source", clean.get("source", ""))
                    rel = clean.get("religion", "buddhism")
                    clean["religionlabel"] = RELIGION_LABELS.get(rel, rel)
                    clean["category"] = rel
                    if "id" not in clean or mode == "Auto-assign missing":
                        try:
                            id_r = sb.rpc("next_quote_id", {"prefix": rel[:3]}).execute()
                            clean["id"] = id_r.data
                        except:
                            pass
                    clean_batch.append(clean)
                try:
                    sb.table("quotes").upsert(clean_batch, on_conflict="id").execute()
                    imported += len(clean_batch)
                except:
                    errors += len(clean_batch)
                prog.progress(min(1.0, (i + 50) / len(data)))
            st.success(f"✅ Imported {imported} ({errors} errors)")
    except Exception as exc:
        st.error(f"Failed: {exc}")

def page_export(sb):
    st.header("📤 Export")
    fmt = st.radio("Format", ["All-in-one JSON", "Split by religion", "Split by sub-category"])
    rel_filter = st.multiselect("Filter by religion", list(RELIGION_LABELS.keys()))
    if st.button("Generate Export", use_container_width=True):
        try:
            query = sb.table("quotes").select("*")
            if rel_filter:
                filters = "".join([f"religion.eq.{r}." for r in rel_filter])
                query = query.or_(filters.rstrip("."))
            r = query.order("religion").execute()
            data = r.data
            if fmt == "All-in-one JSON":
                st.download_button("Download", json.dumps(data, ensure_ascii=False, indent=2),
                                 file_name="tiandao_quotes.json", mime="application/json")
            elif fmt == "Split by religion":
                by_rel = {}
                for q in data:
                    by_rel.setdefault(q.get("religion", "general"), []).append(q)
                for rel, quotes in by_rel.items():
                    label = RELIGION_LABELS.get(rel, rel)
                    st.download_button(f"Download {label}",
                                     json.dumps(quotes, ensure_ascii=False, indent=2),
                                     file_name=f"quotes_{rel}.json", mime="application/json")
            else:
                by_sub = {}
                for q in data:
                    by_sub.setdefault(q.get("subcategory", "other"), []).append(q)
                for sub, quotes in by_sub.items():
                    label = SUB_CATEGORY_LABELS.get(sub, sub)
                    st.download_button(f"Download {label}",
                                     json.dumps(quotes, ensure_ascii=False, indent=2),
                                     file_name=f"quotes_{sub}.json", mime="application/json")
        except Exception as exc:
            st.error(f"Export failed: {exc}")

def main():
    sb = get_sb()
    if not sb:
        st.error("Cannot connect to Supabase. Check .env configuration.")
        return
    page = st.sidebar.radio("Navigation", [
        "📊 Dashboard", "📖 Browse Quotes", "➕ Add Quote",
        "✏️ Edit / Delete", "📥 Bulk Import", "📤 Export",
    ])
    if page == "📊 Dashboard":
        page_dashboard(sb)
    elif page == "📖 Browse Quotes":
        page_browse(sb)
    elif page == "➕ Add Quote":
        page_add(sb)
    elif page == "✏️ Edit / Delete":
        page_edit_delete(sb)
    elif page == "📥 Bulk Import":
        page_bulk_import(sb)
    elif page == "📤 Export":
        page_export(sb)

if __name__ == "__main__":
    main()
