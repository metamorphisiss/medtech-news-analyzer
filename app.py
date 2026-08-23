# app.py
# Streamlit entry point — UI, password gate, pipeline orchestration.
# This is the single file that runs on Streamlit Community Cloud.
#
# Secrets expected in .streamlit/secrets.toml (local) or Community Cloud dashboard:
#   GEMINI_API_KEY      = "..."
#   SUPABASE_CONN_STR   = "postgresql://postgres:[password]@[host]:5432/postgres"
#   APP_PASSWORD        = "..."

import os
import json
import datetime
import feedparser
import streamlit as st
from db import save_briefing_row
from db import fetch_briefing_dates, fetch_briefings_for_date

# Page config — must be first Streamlit call
st.set_page_config(
    page_title="Healthcare GDPI Co-Pilot",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Design tokens — exact values from build spec Section 6.
# No gradients. Flat fills only. Sans-serif typography.
# Using Inter from Google Fonts (clean grotesque, non-generic when paired well).
STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; color: #0A0A0A; }
.stApp { background-color: #FFFFFF; }
#MainMenu, footer, header { visibility: hidden; }

h1, [data-testid="stMarkdownContainer"] h1 { font-size: 3.8rem !important; font-weight: 800 !important; letter-spacing: -1.5px !important; color: #0A0A0A !important; line-height: 1.15 !important; }
h2, [data-testid="stMarkdownContainer"] h2 { font-size: 2.2rem !important; font-weight: 700 !important; color: #0A0A0A !important; }
h3, [data-testid="stMarkdownContainer"] h3 { font-size: 1.8rem !important; font-weight: 600 !important; color: #0A0A0A !important; }
p, li { font-size: 1.35rem; line-height: 1.7; color: #0A0A0A; }

.hero-title { font-size: 4.5rem !important; font-weight: 900 !important; letter-spacing: -2px !important; line-height: 1.05 !important; color: #0A0A0A !important; margin-bottom: 0.5rem !important; display: block !important; }
.hero-sub { font-family: 'Space Mono', monospace !important; font-size: 1.3rem !important; color: #444444 !important; margin-bottom: 1.5rem !important; display: block !important; line-height: 1.6 !important; }

/* Soft bordered containers for executive highlights */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #EAEAEA !important;
    background-color: #FAFAFA !important;
    border-radius: 8px !important;
    padding: 0.5rem !important;
}

/* Brutalist card */
.b-card { background: #FFFFFF; border: 2px solid #0A0A0A; padding: 1.8rem 2rem; margin-bottom: 1.5rem; }

/* Tags */
.tag-red { display: inline-block; background: #CC0000; color: #FFF; font-family: 'Space Mono', monospace; font-size: 0.95rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; padding: 5px 12px; margin-bottom: 0.8rem; }
.tag-black { display: inline-block; background: #0A0A0A; color: #FFF; font-family: 'Space Mono', monospace; font-size: 0.95rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; padding: 5px 12px; margin-bottom: 0.8rem; }

/* Terminal block */
.terminal { background: #0A0A0A; color: #00FF41; font-family: 'Space Mono', monospace; font-size: 1.05rem; padding: 1.4rem 1.6rem; border: 2px solid #0A0A0A; line-height: 1.9; white-space: pre-wrap; margin-bottom: 1rem; height: 320px; overflow-y: auto; }

/* Quick-jump index */
.story-index { border: 2px solid #0A0A0A; padding: 1.4rem 1.8rem; margin-bottom: 2rem; }
.story-index-title { font-family: 'Space Mono', monospace; font-size: 1.0rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #888; margin-bottom: 0.8rem; }
.idx-item { display: block; font-family: 'Space Mono', monospace; font-size: 1.25rem; font-weight: 700; color: #0A0A0A; text-decoration: none; padding: 0.5rem 0; border-bottom: 1px solid #E0E0E0; }
.idx-item:last-child { border-bottom: none; }
.idx-item:hover { color: #CC0000; padding-left: 0.5rem; }
.idx-num { color: #CC0000; margin-right: 0.5rem; }

/* Metric boxes */
.metric-box { border: 2px solid #0A0A0A; padding: 1.5rem 1rem; text-align: center; }
.metric-num { font-family: 'Space Mono', monospace; font-size: 4.2rem; font-weight: 700; color: #CC0000; line-height: 1; }
.metric-label { font-family: 'Space Mono', monospace; font-size: 1.1rem; letter-spacing: 0.1em; text-transform: uppercase; color: #0A0A0A; margin-top: 0.6rem; }

/* Story headline inside card */
.story-hed { font-size: 2.2rem; font-weight: 700; color: #0A0A0A; line-height: 1.45; margin-bottom: 0.2rem; }
.story-src { font-family: 'Space Mono', monospace; font-size: 1.1rem; letter-spacing: 0.07em; text-transform: uppercase; color: #888; }
.story-num-badge { font-family: 'Space Mono', monospace; font-size: 1.1rem; font-weight: 700; color: #CC0000; }

/* Dividers */
hr.bd { border: none; border-top: 3px solid #0A0A0A; margin: 2rem 0; }
hr.bd-light { border: none; border-top: 1px solid #DDD; margin: 1.2rem 0; }

/* Button */
.stButton > button { background-color: #0A0A0A !important; color: #FFFFFF !important; border: 2px solid #0A0A0A !important; border-radius: 0 !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; font-size: 1.1rem !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; padding: 0.85rem 2rem !important; transition: background-color 0.1s, color 0.1s; }
.stButton > button * { color: #FFFFFF !important; }
.stButton > button:hover { background-color: #CC0000 !important; border-color: #CC0000 !important; }
.stButton > button:hover * { color: #FFFFFF !important; }

/* Input */
.stTextInput input { border-radius: 0 !important; border: 2px solid #0A0A0A !important; background-color: #FFFFFF !important; color: #0A0A0A !important; font-family: 'Space Mono', monospace !important; font-size: 1.2rem !important; padding: 0.75rem 1rem !important; }

/* Select box */
div[data-baseweb="select"] > div { background-color: #FFFFFF !important; color: #0A0A0A !important; border: 2px solid #0A0A0A !important; border-radius: 0 !important; }
div[data-baseweb="select"] * { color: #0A0A0A !important; font-size: 1.1rem !important; }

/* Password gate */
.pw-center { max-width: 750px; margin: 5rem auto 0 auto; text-align: center; }

/* Meta text */
.meta { font-family: 'Space Mono', monospace; font-size: 1.25rem !important; color: #555 !important; letter-spacing: 0.03em; line-height: 1.6 !important; }

/* Tabs */
[data-testid="stTabs"] button { border-radius: 0 !important; font-family: 'Space Mono', monospace !important; font-size: 1.1rem !important; text-transform: uppercase !important; letter-spacing: 0.07em !important; font-weight: 700 !important; padding: 0.6rem 1.2rem !important; }
[data-testid="stTabs"] button[aria-selected="true"] { border-bottom: 3px solid #CC0000 !important; color: #CC0000 !important; }

/* Expanders */
[data-testid="stExpander"] { border: 2px solid #0A0A0A !important; border-radius: 0 !important; background-color: #FFFFFF !important; margin-bottom: 1.2rem !important; }
[data-testid="stExpander"] details summary { padding: 1.5rem 2rem !important; background-color: #FFFFFF !important; border-radius: 0 !important; border-bottom: 2px solid #0A0A0A !important; }
[data-testid="stExpander"] details summary:hover { background-color: #F8F8F8 !important; }
[data-testid="stExpander"] details summary p, [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p { font-size: 1.4rem !important; font-weight: 700 !important; font-family: 'Inter', sans-serif !important; color: #0A0A0A !important; margin: 0 !important; line-height: 1.45 !important; }
[data-testid="stExpander"] details div[data-testid="stExpanderDetails"] { background-color: #FFFFFF !important; padding: 2rem !important; color: #0A0A0A !important; }

/* Section label */
.section-tag { display: inline-block; background: #0A0A0A; color: #FFF; font-family: 'Space Mono', monospace; font-size: 0.95rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; padding: 5px 12px; margin-bottom: 0.8rem; }
.accent-tag { display: inline-block; background: #CC0000; color: #FFF; font-family: 'Space Mono', monospace; font-size: 0.95rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; padding: 5px 12px; margin-bottom: 0.8rem; }

/* Mobile responsive */
@media (max-width: 768px) {
    .metric-num { font-size: 2.2rem; }
    h1, [data-testid="stMarkdownContainer"] h1, .pw-center h1 { font-size: 2.2rem !important; }
    .b-card { padding: 1rem; }
    .terminal { font-size: 0.85rem; padding: 0.9rem; }
}
</style>
"""

st.markdown(STYLE, unsafe_allow_html=True)


# Helper: inject API keys into os.environ from st.secrets
def _inject_secrets():
    os.environ["GROQ_API_KEY"]         = st.secrets.get("GROQ_API_KEY", "")
    os.environ["OPENROUTER_API_KEY"]   = st.secrets.get("OPENROUTER_API_KEY", "")

# Password Gate
def _password_gate() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        """
        <div class="pw-center">
            <h1 class="hero-title">Healthcare GDPI Co-Pilot</h1>
            <p class="hero-sub">
                Daily intelligence and interview prep — healthcare, pharma, medtech, policy.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pw = st.text_input("Password", type="password", key="pw_input", label_visibility="collapsed")
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        submit = st.button("Enter", use_container_width=True)

    if submit:
        if pw == st.secrets["APP_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False

# Feed Fetching (Pure Python)
def _pull_feed_entries(urls: list[str]) -> list[dict]:
    """Pulls recent entries from feeds, tagged by region (India vs Global)."""
    from sources import INDIA_FEEDS
    india_feed_set = set(INDIA_FEEDS)
    entries = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            source_title = feed.feed.get("title", "News Source")
            # Tag by explicit source list — not URL guessing
            is_india = url in india_feed_set
            prefix = "[INDIA] " if is_india else ""
            # Equal pool size for both regions — guarantees 50/50 scout selection
            for entry in feed.entries[:10]:
                entries.append({
                    "title":     entry.get("title", ""),
                    "link":      entry.get("link", ""),
                    "source":    f"{prefix}{source_title}",
                    "published": entry.get("published", ""),
                })
        except Exception:
            pass
    return entries

# Pipeline Orchestration
def _run_pipeline(terminal_box=None, anim_box=None) -> list[dict]:
    """
    Orchestrates the full pipeline using direct LLM calls (no CrewAI).
    Returns a list of assembled row dicts.
    """
    from pipeline import run_scout, run_analyst_and_coach
    from tools import fetch_full_article_text
    from sources import CANDIDATE_FEEDS

    today          = datetime.date.today()
    current_run_id = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
    conn_str       = st.secrets["SUPABASE_CONN_STR"]

    # --- Terminal Visualizer ---
    log_lines = []
    if terminal_box is None:
        terminal_box = st.empty()

    def _log(msg: str, done: bool = False):
        log_lines.append(msg)
        bar_fill = min(len(log_lines), 10)
        bar      = "█" * bar_fill + "░" * (10 - bar_fill)
        status   = "COMPLETE" if done else "RUNNING"
        header   = f"[ HEALTHCARE GDPI CO-PILOT — PIPELINE {status} ]\n[{bar}] {len(log_lines)} ops\n\n"
        terminal_box.markdown(
            f"<div class='terminal'>{header}" + "\n".join(f"> {l}" for l in log_lines[-12:]) + "</div>",
            unsafe_allow_html=True,
        )

    def _update_anim(active_node: str, msg: str):
        if not anim_box: return
        s_cls = "node active" if active_node == "SCOUT"   else "node"
        a_cls = "node active" if active_node == "ANALYST" else "node"
        c_cls = "node active" if active_node == "COACH"   else "node"
        html = f"""
        <style>
        .n-wrap {{ display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem 0;width:100%; }}
        .n-row  {{ display:flex;align-items:center;justify-content:center;gap:2rem;width:100%; }}
        .node   {{ padding:1rem 2rem;border:2px solid #333;color:#555;font-family:'Space Mono',monospace;font-weight:bold;font-size:1.1rem;transition:all 0.3s;background:transparent; }}
        .node.active {{ border-color:#CC0000;color:#CC0000;box-shadow:0 0 20px rgba(204,0,0,0.15);transform:scale(1.05); }}
        .arr    {{ color:#333;font-size:1.5rem; }}
        .n-msg  {{ margin-top:2.5rem;font-family:'Space Mono',monospace;font-size:0.85rem;color:#888;background:#0A0A0A;padding:0.5rem 1.5rem;border:1px solid #222;text-transform:uppercase;letter-spacing:1px; }}
        </style>
        <div class="n-wrap">
            <div class="n-row">
                <div class="{s_cls}">[ 01: SCOUT ]</div>
                <div class="arr">&#10132;</div>
                <div class="{a_cls}">[ 02: ANALYST ]</div>
                <div class="arr">&#10132;</div>
                <div class="{c_cls}">[ 03: COACH ]</div>
            </div>
            <div class="n-msg">>> {msg}</div>
        </div>"""
        anim_box.markdown(html, unsafe_allow_html=True)

    # Step 1: Pull entries from all feeds in one pass (no double-parse)
    _update_anim("SCOUT", "Pulling entries from RSS feeds...")
    _log("INIT — fetching RSS feeds")
    from sources import INDIA_FEEDS, GLOBAL_FEEDS, CANDIDATE_FEEDS
    india_feed_set = set(INDIA_FEEDS)
    india_entries, global_entries = [], []

    for url in CANDIDATE_FEEDS:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            source_title = feed.feed.get("title", "News Source")
            
            # Clean up messy Google News search titles
            if "GOOGLE NEWS" in source_title.upper() or "OR" in source_title:
                source_title = "Google News"
            elif "|" in source_title:
                source_title = source_title.split("|")[0].strip()
                
            is_india = url in india_feed_set
            region = "India" if is_india else "Global"
            
            for entry in feed.entries[:10]:
                raw_title = entry.get("title", "")
                # Strip any HTML tags some feeds inject into titles
                import re as _re
                clean_title = _re.sub(r"<[^>]+>", "", raw_title).strip()
                if not clean_title:
                    continue
                item = {
                    "title":     clean_title,
                    "link":      entry.get("link", ""),
                    "source":    source_title,
                    "region":    region,
                    "published": entry.get("published", ""),
                }
                if is_india:
                    india_entries.append(item)
                else:
                    global_entries.append(item)
        except Exception as e:
            _log(f"FEED ERROR — {url[:50]}: {str(e)[:40]}")

    _log(f"FETCH — {len(india_entries)} India / {len(global_entries)} Global entries pulled")

    if not india_entries and not global_entries:
        st.error("No entries found in any RSS feeds. Check your network connection.")
        return []

    if not india_entries:
        _log("WARNING — No India feed entries found, will show Global-only briefing")
    if not global_entries:
        _log("WARNING — No Global feed entries found, will show India-only briefing")

    # Step 2: Regional scouts
    _update_anim("SCOUT", "Running India relevance filter...")
    india_stories = run_scout(india_entries, "India", log_fn=_log)
    if not india_stories:
        _log("WARNING — India scout returned 0 stories")

    _update_anim("SCOUT", "Running Global relevance filter...")
    global_stories = run_scout(global_entries, "Global", log_fn=_log)
    if not global_stories:
        _log("WARNING — Global scout returned 0 stories")

    stories = india_stories + global_stories
    if not stories:
        st.error("Scout agents returned no stories — check terminal logs for details.")
        return []
    _log(f"SCOUT COMPLETE — {len(stories)} stories ({len(india_stories)} India + {len(global_stories)} Global)")


    # Step 4: Analyst + Coach per story (single combined call)
    results = []
    for idx, story in enumerate(stories, start=1):
        title_short = story.get("title", "")[:50] + ("..." if len(story.get("title","")) > 50 else "")
        _update_anim("ANALYST", f"Story {idx}/{len(stories)}: {title_short}")
        _log(f"ANALYSIS — story {idx}: fetching article text")

        full_text = fetch_full_article_text(story.get("link", ""))
        _log(f"ANALYSIS — story {idx}: running analyst + coach (single call)")
        analyst_json, coach_json = run_analyst_and_coach(story, full_text, log_fn=_log)

        # Save to DB
        try:
            save_briefing_row(conn_str, today, story, analyst_json, coach_json, run_id=current_run_id)
            _log(f"DB::WRITE — story {idx} saved")
        except Exception as db_exc:
            st.warning(f"Database save failed for story {idx}: {db_exc}")

        results.append({"story": story, "analyst": analyst_json, "coach": coach_json})

    _log(f"PIPELINE COMPLETE — {len(results)} briefings assembled", done=True)
    _update_anim("COACH", f"Done! {len(results)} stories analysed and saved.")
    return results


# ---------------------------------------------------------------------------
# Dashboard Rendering (Full Layout)
# ---------------------------------------------------------------------------

def _safe_parse_json(data):
    import json
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        cleaned = data.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, str):
                return json.loads(parsed)
            return parsed
        except Exception:
            pass
    return {}

def _render_dashboard(rows: list[dict]):
    if not rows:
        st.info("No briefing data to display.")
        return

    today_str = datetime.date.today().strftime("%A, %d %B %Y")

    # --- Aggregate data (logic unchanged) ---
    all_facts, all_numbers, all_companies, all_policies, all_concepts, all_opinions = [], [], [], [], [], []
    for row in rows:
        an = _safe_parse_json(row.get("analyst", {}))
        if an.get("key_facts"): all_facts.extend(an["key_facts"])
        if an.get("key_numbers"): all_numbers.extend(an["key_numbers"])
        if an.get("companies_mentioned"): all_companies.extend(an["companies_mentioned"])
        if an.get("policies_mentioned"): all_policies.extend(an["policies_mentioned"])
        if an.get("key_concepts"): all_concepts.extend(an["key_concepts"])
        if an.get("one_opinion"): all_opinions.append(an["one_opinion"])
    all_companies = list(dict.fromkeys(all_companies))
    all_policies  = list(dict.fromkeys(all_policies))
    all_concepts  = list(dict.fromkeys(all_concepts))

    radar_entries = [_safe_parse_json(r.get("coach", {})).get("policy_radar_entry") for r in rows if _safe_parse_json(r.get("coach", {})).get("policy_radar_entry")]
    companies_w   = [_safe_parse_json(r.get("coach", {})).get("company_to_watch")   for r in rows if _safe_parse_json(r.get("coach", {})).get("company_to_watch")]
    concepts_e    = [_safe_parse_json(r.get("coach", {})).get("concept_explained")  for r in rows if _safe_parse_json(r.get("coach", {})).get("concept_explained")]

    # --- DATE HEADER ---
    st.markdown(f"<p class='meta'>{today_str.upper()}</p>", unsafe_allow_html=True)
    st.markdown("<hr class='bd'>", unsafe_allow_html=True)

    # --- METRIC WIDGETS ROW ---
    m_cols = st.columns(5)
    metrics = [
        (len(rows),              "Stories"),
        (len(all_companies),     "Companies"),
        (len(all_policies),      "Policies"),
        (len(all_facts[:10]),    "Key Facts"),
        (len(radar_entries),     "Policy Alerts"),
    ]
    for col, (num, label) in zip(m_cols, metrics):
        with col:
            st.markdown(
                f"<div class='metric-box'><div class='metric-num'>{num}</div>"
                f"<div class='metric-label'>{label}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<hr class='bd'>", unsafe_allow_html=True)

    # --- QUICK-JUMP INDEX ---
    idx_html = "<div class='story-index'>\n<div class='story-index-title'>TOP HEADLINES</div>\n"
    for idx, r in enumerate(rows, start=1):
        st_title = r["story"].get("title", "")
        idx_html += f"<a class='idx-item' href='#story-{idx}'><span class='idx-num'>STORY {idx:02d}</span> {st_title}</a>\n"
    idx_html += "</div>"
    st.markdown(idx_html, unsafe_allow_html=True)

    # --- EXECUTIVE HIGHLIGHTS ---
    if True:
        rd_col, right_col = st.columns([6, 4])
        with rd_col:
            if radar_entries:
                st.markdown("<div style='margin-bottom: 1rem;'><span class='tag-black' style='font-size: 1.1rem !important; padding: 8px 16px !important;'>RADAR ENTRIES</span></div>", unsafe_allow_html=True)
                with st.container(height=480, border=True):
                    html_list = "<ul style='margin: 0; padding-left: 1.5rem;'>"
                    for e in radar_entries:
                        html_list += f"<li style='font-size: 1.35rem; color: #111; margin-bottom: 0.8rem; line-height: 1.5; text-align: justify;'>{e}</li>"
                    html_list += "</ul>"
                    st.markdown(html_list, unsafe_allow_html=True)
        
        with right_col:
            st.markdown("<div style='margin-bottom: 1rem;'><span class='tag-black' style='font-size: 1.1rem !important; padding: 8px 16px !important;'>COMPANIES & CONCEPTS</span></div>", unsafe_allow_html=True)
            with st.container(height=480, border=True):
                if companies_w:
                    c = companies_w[0]
                    name = c.get('name','') if isinstance(c, dict) else str(c)
                    why = c.get('why','') if isinstance(c, dict) else ""
                    st.markdown(f"<div style='font-size: 1.1rem; color: #CC0000; font-weight: 700; margin-bottom: 0.5rem;'>COMPANY TO WATCH</div><div style='font-size: 1.5rem; font-weight: 900; color: #000; margin-bottom: 0.8rem;'>{name}</div><div style='font-size: 1.35rem; color: #111; line-height: 1.65; text-align: justify;'>{why}</div>", unsafe_allow_html=True)
                
                st.markdown("<hr style='border-top: 2px solid BLACK; margin: 1.5rem 0;'>", unsafe_allow_html=True)
                
                if concepts_e:
                    c = concepts_e[0]
                    concept = c.get('concept','') if isinstance(c, dict) else str(c)
                    english = c.get('plain_english','') if isinstance(c, dict) else ""
                    st.markdown(f"<div style='font-size: 1.1rem; color: #CC0000; font-weight: 700; margin-bottom: 0.5rem;'>CONCEPTS TO KNOW</div><div style='font-size: 1.5rem; font-weight: 900; color: #000; margin-bottom: 0.8rem;'>{concept}</div><div style='font-size: 1.35rem; color: #111; line-height: 1.65; text-align: justify;'>{english}</div>", unsafe_allow_html=True)
        st.markdown("<hr class='bd'>", unsafe_allow_html=True)

    # --- DEEP DIVE STORY CARDS ---
    for i, row in enumerate(rows, start=1):
        story   = row["story"]
        analyst = _safe_parse_json(row.get("analyst"))
        coach   = _safe_parse_json(row.get("coach"))

        # Anchor target for quick-jump
        st.markdown(f"<div id='story-{i}'></div>", unsafe_allow_html=True)

        # Clean title for expander
        story_source = story.get('source', '')
        # If the source string still has [INDIA], strip it for cleaner display
        is_legacy_india = story_source.startswith("[INDIA]")
        if is_legacy_india:
            story_source = story_source.replace("[INDIA]", "").strip()
            
        region = story.get('region')
        if not region:
            region = "India" if is_legacy_india else "Global"
            
        badge_color = "#CC0000" if region == "India" else "#333333"
        
        st.markdown(f"""
            <div style="margin-top: 2rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.8rem;">
                <span style="background-color: {badge_color}; color: white; padding: 0.4rem 0.9rem; font-family: 'Space Mono', monospace; font-size: 1.0rem; font-weight: bold; border-radius: 2px; text-transform: uppercase;">
                    {region}
                </span>
                <span style="font-family: 'Space Mono', monospace; font-size: 1.15rem; color: #555; text-transform: uppercase; font-weight: bold;">
                    {story_source}
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        expander_title = f"STORY {i:02d}: {story.get('title', '')}"
        
        with st.expander(expander_title, expanded=(i == 1)):
            st.markdown(
                f"<a href='{story.get('link','#')}' target='_blank' style='text-decoration:none;font-family:Space Mono,monospace;font-weight:700;color:#CC0000;font-size:1.1em;text-transform:uppercase;'>Read Source Article ↗</a>",
                unsafe_allow_html=True
            )
            # Tabbed content
            tab_mba, tab_gdpi, tab_data = st.tabs(["MBA Lens", "GD / PI Exam", "Raw Data"])

            with tab_mba:
                if isinstance(analyst, dict) and analyst:
                    found_any = False
                    for key, label in [
                        ("what_happened",           "What Happened"),
                        ("why_it_matters",          "Why It Matters"),
                        ("stakeholders",            "Stakeholders"),
                        ("business_implications",   "Business Implications"),
                        ("regulatory_implications", "Regulatory Implications"),
                        ("health_system_implications", "Health System Implications"),
                    ]:
                        val = analyst.get(key)
                        if val:
                            found_any = True
                            if isinstance(val, list):
                                val = ", ".join(str(v) for v in val)
                            st.markdown(f"<div style='font-size: 1.8rem; font-weight: 800; color: #000; margin-bottom: 0.6rem;'>{label}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #111; text-align: justify; margin-bottom: 1.2rem;'>{val}</div>", unsafe_allow_html=True)
                            st.markdown("<hr class='bd-light'>", unsafe_allow_html=True)
                    ca = analyst.get("counterargument")
                    if ca:
                        found_any = True
                        st.markdown("<div style='margin-bottom: 0.6rem;'><span class='tag-red'>Counterargument</span></div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #111; text-align: justify; margin-bottom: 1.2rem;'>{ca}</div>", unsafe_allow_html=True)
                    
                    if not found_any:
                        st.info("Structured MBA fields empty. Raw data:")
                        st.json(analyst)
                elif isinstance(analyst, str) and analyst:
                    st.markdown(analyst)
                else:
                    st.info("No MBA analysis available for this story.")

            with tab_gdpi:
                if isinstance(coach, dict) and coach:
                    gd_q = coach.get("gd_question")
                    pi_q = coach.get("pi_question")
                    ans  = coach.get("thirty_second_answer")
                    if gd_q:
                        st.markdown("<div style='margin-bottom: 0.6rem;'><span class='tag-black'>GD Debate</span></div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #333; font-style: italic; text-align: justify; border-left: 4px solid #CC0000; padding-left: 1rem; margin-bottom: 1.2rem;'>{gd_q}</div>", unsafe_allow_html=True)
                        st.markdown("<hr class='bd-light'>", unsafe_allow_html=True)
                    if pi_q:
                        st.markdown("<div style='margin-bottom: 0.6rem;'><span class='tag-black'>PI Probe</span></div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #333; font-style: italic; text-align: justify; border-left: 4px solid #CC0000; padding-left: 1rem; margin-bottom: 1.2rem;'>{pi_q}</div>", unsafe_allow_html=True)
                        st.markdown("<hr class='bd-light'>", unsafe_allow_html=True)
                    if ans:
                        st.markdown("<div style='font-size: 1.4rem; font-weight: 800; color: #000; margin-bottom: 0.6rem;'>30-Second Model Answer</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #111; text-align: justify; margin-bottom: 1.2rem;'>{ans}</div>", unsafe_allow_html=True)
                    if not (gd_q or pi_q or ans):
                        st.info("Structured GD/PI fields empty. Raw data:")
                        st.json(coach)
                elif isinstance(coach, str) and coach:
                    st.markdown(coach)
                else:
                    st.info("No GD/PI prep available for this story.")

            with tab_data:
                if isinstance(analyst, dict) and analyst:
                    kn = analyst.get("key_numbers", [])
                    kf = analyst.get("key_facts",   [])
                    cm = analyst.get("companies_mentioned", [])
                    pm = analyst.get("policies_mentioned",  [])
                    if kn:
                        st.markdown("<div style='font-size: 1.4rem; font-weight: 800; color: #000; margin-bottom: 0.6rem;'>Key Numbers</div>", unsafe_allow_html=True)
                        html = "<ul style='margin-bottom: 1.2rem;'>"
                        for n in kn:
                            if isinstance(n, dict):
                                html += f"<li style='font-size: 1.35rem; line-height: 1.65; color: #111;'><strong>{n.get('figure','')}</strong> — {n.get('context','')}</li>"
                            else:
                                html += f"<li style='font-size: 1.35rem; line-height: 1.65; color: #111;'>{n}</li>"
                        html += "</ul>"
                        st.markdown(html, unsafe_allow_html=True)
                    if kf:
                        st.markdown("<div style='font-size: 1.4rem; font-weight: 800; color: #000; margin-bottom: 0.6rem;'>Key Facts</div>", unsafe_allow_html=True)
                        html = "<ul style='margin-bottom: 1.2rem;'>"
                        for f in kf: html += f"<li style='font-size: 1.35rem; line-height: 1.65; color: #111; margin-bottom: 0.4rem;'>{f}</li>"
                        html += "</ul>"
                        st.markdown(html, unsafe_allow_html=True)
                    if cm:
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #111; margin-bottom: 0.8rem;'><strong>Companies</strong> — {', '.join(str(c) for c in cm)}</div>", unsafe_allow_html=True)
                    if pm:
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #111; margin-bottom: 0.8rem;'><strong>Policies</strong> — {', '.join(str(p) for p in pm)}</div>", unsafe_allow_html=True)
                    op = analyst.get("one_opinion")
                    if op:
                        st.markdown("<div style='font-size: 1.4rem; font-weight: 800; color: #000; margin-bottom: 0.6rem;'>One Opinion</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size: 1.35rem; line-height: 1.65; color: #111; font-style: italic; margin-bottom: 1.2rem; text-align: justify;'>\"{op}\"</div>", unsafe_allow_html=True)
                    if not (kn or kf or cm or pm or op):
                        st.info("No raw data entities extracted.")
                else:
                    st.info("No raw data available.")

        st.markdown("<hr class='bd'>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Past Briefings
# ---------------------------------------------------------------------------
def _render_past_briefings():
    from db import fetch_briefing_dates, fetch_briefings_for_date
    conn_str = st.secrets["SUPABASE_CONN_STR"]

    st.markdown("<span class='tag-black'>Past Briefings</span>", unsafe_allow_html=True)

    try:
        dates = fetch_briefing_dates(conn_str)
    except Exception:
        return st.warning("Could not load past dates.")

    if not dates: return st.info("No past briefings.")

    sel = st.selectbox("Select past run", [str(d) for d in dates], label_visibility="collapsed", key="past_date_selector")
    if not sel: return

    try:
        rows = fetch_briefings_for_date(conn_str, sel)
    except Exception as e:
        return st.error(f"Error loading: {e}")

    normalized = []
    for r in rows:
        a_json = r.get("analyst_json") or {}
        c_json = r.get("coach_json")   or {}
        if isinstance(a_json, str):
            try: a_json = json.loads(a_json)
            except: a_json = {}
        if isinstance(c_json, str):
            try: c_json = json.loads(c_json)
            except: c_json = {}
        normalized.append({
            "story":   {"title": r.get("title",""), "link": r.get("link",""), "source": r.get("source",""), "published_date": str(r.get("date",""))},
            "analyst": a_json,
            "coach":   c_json,
        })

    _render_dashboard(normalized)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not _password_gate(): return
    _inject_secrets()

    st.markdown(
        """
        <div style="margin-bottom:0.4rem;">
            <h1 class="hero-title">Healthcare GDPI Co-Pilot</h1>
            <p class="hero-sub">Daily intelligence and interview preparation — healthcare, pharma, medtech, policy.</p>
        </div>
        <hr class='bd'>
        """,
        unsafe_allow_html=True,
    )

    # --- Button row ---
    col1, col2 = st.columns([4, 1])
    with col2:
        run_clicked = st.button("Run Pipeline", use_container_width=True, key="run_btn")

    # --- Containers declared immediately after button, before any rendering ---
    animation_container = col1.empty()
    pipeline_container = st.empty()

    # --- Show hint text when idle ---
    if not run_clicked:
        animation_container.markdown(
            "<p style='font-family:Space Mono,monospace;font-size:1.15rem;color:#555;font-weight:bold;'>"
            "Run the pipeline to generate today's briefing from live RSS sources.</p>",
            unsafe_allow_html=True,
        )

    # --- Show existing results if available ---
    if "pipeline_results" in st.session_state and not run_clicked:
        _render_dashboard(st.session_state["pipeline_results"])

    # --- Past briefings expander ---
    with st.expander("View a past briefing"):
        _render_past_briefings()

    # --- Execute pipeline on click ---
    if run_clicked:
        animation_container.empty()
        res = _run_pipeline(terminal_box=pipeline_container, anim_box=animation_container)
        if res:
            st.session_state["pipeline_results"] = res
            st.rerun()

if __name__ == "__main__":
    main()
