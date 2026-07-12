import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import pytz
import gspread
import re
import random
import urllib.request
import xml.etree.ElementTree as ET
from google.oauth2.service_account import Credentials

# --- GROQ API FOR MATCH NARRATIVE ---
from groq import Groq

st.set_page_config(page_title="World Cup Challenge", page_icon="🏆", layout="wide")

# --- CUSTOM CSS (Clean White Theme & Ticker) ---
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
            color: #111111 !important;
        }
        h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown {
            color: #111111 !important;
        }
        .ticker-wrap {
            width: 100%;
            background-color: #198754 !important;
            overflow: hidden;
            height: 38px;
            padding-left: 100%;
            box-sizing: content-box;
            border-radius: 6px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            display: flex;
            align-items: center;
        }
        @keyframes marquee {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-100%, 0, 0); }
        }
        .ticker-content {
            display: inline-block;
            white-space: nowrap;
            padding-right: 100%;
            animation-iteration-count: infinite;
            animation-timing-function: linear;
            animation-name: marquee;
            animation-duration: 35s;
        }
        .ticker-content span {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            letter-spacing: 0.5px;
        }
        div.stButton > button {
            background-color: #198754 !important;
            border: 1px solid #146c43 !important;
            border-radius: 8px !important;
            padding: 0.7rem 1.5rem !important;
            width: 100% !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08) !important;
            transition: all 0.2s ease-in-out !important;
        }
        div.stButton > button:hover {
            background-color: #146c43 !important;
            border-color: #0f5132 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 8px rgba(0, 0, 0, 0.12) !important;
        }
        div.stButton > button * {
            color: #FFFFFF !important;
            font-weight: bold !important;
            font-size: 1.05rem !important;
        }
        input, select, div[data-baseweb="select"], div[data-testid="stNumberInput"] input {
            background-color: #F8F9FA !important;
            color: #111111 !important;
            border: 1px solid #DEE2E6 !important;
            border-radius: 4px !important;
        }
        div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E9ECEF !important;
            border-radius: 8px !important;
            padding: 10px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #FFFFFF !important;
            border-bottom: 2px solid #F1F3F5;
        }
        .stTabs [data-baseweb="tab"] {
            color: #495057 !important;
            font-weight: 500 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #198754 !important;
            font-weight: bold !important;
            border-bottom-color: #198754 !important;
        }
        .prediction-card {
            background-color: #F8F9FA;
            border: 1px dashed #198754;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }
        .story-card {
            background-color: #e8f5e9;
            border-left: 5px solid #198754;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# --- NEWS TICKER ---
@st.cache_data(ttl=900)
def fetch_ticker_string():
    rss_url = "http://newsrss.bbc.co.uk/rss/sportonline_uk_edition/football/rss.xml"
    fallback_string = (
        "🏆 FIFA WORLD CUP 2026: Tournament shifts into high gear "
        "⚽ FUTURES MARKET UPDATE: Analytical goalscoring models updated "
        "🏆 TACTICAL REPORT: Technical staff implement strict player rotation patterns "
        "⚽ READY TO WATCH: Broadcast metrics indicate record-breaking views expected live across Australia on SBS Networks."
    )
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        ticker_items = []
        for item in root.findall('.//item')[:15]:
            title = item.find('title').text if item.find('title') is not None else ""
            if any(k in title.lower() for k in ['world cup', 'fifa', 'international', 'national team', 'qualifier', '2026']):
                ticker_items.append(f"⚽ {title.upper().strip()}")
        if ticker_items:
            return "   ||   ".join(ticker_items) + "   ||   "
        return fallback_string
    except Exception:
        return fallback_string

ticker_text = fetch_ticker_string()
st.markdown(f"""
    <div class="ticker-wrap"><div class="ticker-content"><span>{ticker_text}</span></div></div>
""", unsafe_allow_html=True)

st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# --- HELPER FUNCTIONS ---
def get_flag_url(text):
    if not isinstance(text, str): return ""
    text_clean = text.strip().lower()
    codes = [chr(ord(char) - 0x1F1E6 + ord('a')) for char in text if 0x1F1E6 <= ord(char) <= 0x1F1FF]
    if len(codes) >= 2: return f"https://flagcdn.com/w80/{''.join(codes[:2])}.png"
    
    flag_map = {
        'argentina': 'ar', 'australia': 'au', 'belgium': 'be', 'brazil': 'br',
        'canada': 'ca', 'croatia': 'hr', 'denmark': 'dk', 'france': 'fr',
        'germany': 'de', 'italy': 'it', 'japan': 'jp', 'mexico': 'mx',
        'morocco': 'ma', 'netherlands': 'nl', 'portugal': 'pt', 'spain': 'es',
        'usa': 'us', 'united states': 'us', 'england': 'gb-eng', 'wales': 'gb-wls',
        'scotland': 'gb-sct', 'saudi arabia': 'sa', 'south korea': 'kr', 'uruguay': 'uy',
        'south africa': 'za', 'paraguay': 'py', 'bosnia & herz.': 'ba', 'czech republic': 'cz',
        'haiti': 'ht', 'curacao': 'cw', 'uzbekistan': 'uz', 'jordan': 'jo', 'cape verde': 'cv',
        'ivory coast': 'ci', "cote d'ivoire": 'ci', 'sweden': 'se', 'turkey': 'tr',
        'turkiye': 'tr', 'norway': 'no', 'iraq': 'iq', 'ecuador': 'ec', 'serbia': 'rs',
        'cameroon': 'cm', 'ghana': 'gh', 'senegal': 'sn', 'tunisia': 'tn', 'algeria': 'dz',
        'egypt': 'eg', 'nigeria': 'ng', 'colombia': 'co', 'austria': 'at', 'switzerland': 'ch',
        'poland': 'pl', 'ukraine': 'ua', 'dr congo': 'cd'
    }
    pure_name = re.sub(r'[\U0001f1e6-\U0001f1ff\U00010000-\U0010ffff\u2600-\u27bf]', '', text_clean).strip()
    return f"https://flagcdn.com/w80/{flag_map[pure_name]}.png" if pure_name in flag_map else ""

def clean_country_name(text):
    if not isinstance(text, str): return text
    return re.sub(r'[\U0001f1e6-\U0001f1ff\U00010000-\U0010ffff\u2600-\u27bf]', '', text).strip()

def build_champion_options(matches_df, team_status_df):
    """Returns (sorted clean team names, dict clean_name -> raw team text w/ flag emoji).
    Keeping the raw text (with its flag emoji) around means get_flag_url() can use the
    reliable emoji-codepoint path instead of falling back to the hand-maintained flag_map dict.
    If team_status_df has a usable Still_Alive column, the list is filtered to survivors only."""
    clean_to_raw = {}
    for col in ['Home_Team', 'Away_Team']:
        if col in matches_df.columns:
            for raw in matches_df[col].tolist():
                if isinstance(raw, str):
                    clean = clean_country_name(raw)
                    if clean and clean not in clean_to_raw:
                        clean_to_raw[clean] = raw

    still_alive_set = None
    if team_status_df is not None and not team_status_df.empty and 'Team' in team_status_df.columns:
        still_alive_set = set(
            str(r['Team']).strip() for _, r in team_status_df.iterrows()
            if str(r.get('Still_Alive', '')).strip().upper() in ('TRUE', '1', 'YES')
        )

    if still_alive_set:
        clean_names = sorted(c for c in clean_to_raw if c in still_alive_set)
    else:
        clean_names = sorted(clean_to_raw.keys())

    return clean_names, clean_to_raw

def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

def clean_and_parse_date(date_val):
    if not date_val or pd.isna(date_val): return datetime(2026, 6, 12, 5, 0)
    date_str = str(date_val).strip()
    try: return pd.to_datetime(date_str, dayfirst=False)
    except:
        try: return pd.to_datetime(date_str, dayfirst=True)
        except: return datetime(2026, 6, 12, 5, 0)

def get_match_stage(match_id):
    try:
        return "Knockout" if int(match_id) >= 73 else "Group"
    except:
        return "Group"

# ==========================================
# ODDS -> FAIR PROBABILITY ENGINE
# (No gambling odds shown to kids - we convert everything to clean percentages
#  and always surface BOTH sides, not just the single favourite.)
# ==========================================
def _implied_normalised(raw_odds_list):
    """Takes a list of decimal odds, returns normalised fair probabilities (removes bookmaker margin)."""
    implied = [1.0 / o for o in raw_odds_list]
    total = sum(implied)
    return [round((i / total) * 100, 1) for i in implied]

def compute_match_probabilities(home, away, qualify_home_odds, qualify_away_odds, progression_str, first_scorer_str):
    facts = {"home": home, "away": away}

    # --- 1. Qualify probabilities (2-way) ---
    try:
        q_home_odds = float(qualify_home_odds)
        q_away_odds = float(qualify_away_odds)
        q_probs = _implied_normalised([q_home_odds, q_away_odds])
        facts["qualify_home_pct"] = q_probs[0]
        facts["qualify_away_pct"] = q_probs[1]
    except Exception:
        facts["qualify_home_pct"] = None
        facts["qualify_away_pct"] = None

    # --- 2. Progression data: "Team Stage Odds, Team Stage Odds, ..." (6 entries) ---
    progression_entries = []  # list of dicts: team, stage, odds
    for chunk in str(progression_str).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(.*?)\s+(Normal Time|Extra Time|Penalties)\s+([\d.]+)$", chunk)
        if m:
            team_raw, stage, odds = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
            progression_entries.append({"team": team_raw, "stage": stage, "odds": odds})

    if progression_entries:
        probs = _implied_normalised([e["odds"] for e in progression_entries])
        for e, p in zip(progression_entries, probs):
            e["pct"] = p

        def best_for_team(team_clean):
            team_rows = [e for e in progression_entries if clean_country_name(e["team"]) == team_clean]
            return max(team_rows, key=lambda x: x["pct"]) if team_rows else None

        home_best = best_for_team(home)
        away_best = best_for_team(away)
        overall_best = max(progression_entries, key=lambda x: x["pct"])

        facts["home_best_stage"] = home_best["stage"] if home_best else None
        facts["home_best_stage_pct"] = home_best["pct"] if home_best else None
        facts["away_best_stage"] = away_best["stage"] if away_best else None
        facts["away_best_stage_pct"] = away_best["pct"] if away_best else None
        facts["overall_favourite_team"] = overall_best["team"]
        facts["overall_favourite_stage"] = overall_best["stage"]
        facts["overall_favourite_pct"] = overall_best["pct"]

        # Full per-team, per-stage grid - handed to the AI as-is so IT makes the
        # NT/ET/PK call itself from the raw numbers, rather than us pre-deciding it.
        def pct_for(team_clean, stage_name):
            for e in progression_entries:
                if clean_country_name(e["team"]) == team_clean and e["stage"] == stage_name:
                    return e["pct"]
            return 0
        facts["home_nt_pct"] = pct_for(home, "Normal Time")
        facts["home_et_pct"] = pct_for(home, "Extra Time")
        facts["home_pk_pct"] = pct_for(home, "Penalties")
        facts["away_nt_pct"] = pct_for(away, "Normal Time")
        facts["away_et_pct"] = pct_for(away, "Extra Time")
        facts["away_pk_pct"] = pct_for(away, "Penalties")

        # --- Separate "how far into the match might this go" analysis ---
        # NT/ET/PK base rates are structurally similar across most matches (bookmakers apply a fairly fixed
        # split for how knockout matches generally resolve), so comparing a team's own 3 rows against each
        # other will almost always crown Normal Time, even when ET/PK are genuinely live possibilities.
        # Instead, sum BOTH teams' percentage together per stage, so we get one clean view of how likely the
        # match overall is to need Extra Time or Penalties, independent of who wins.
        nt_total = sum(e["pct"] for e in progression_entries if e["stage"] == "Normal Time")
        et_total = sum(e["pct"] for e in progression_entries if e["stage"] == "Extra Time")
        pk_total = sum(e["pct"] for e in progression_entries if e["stage"] == "Penalties")
        facts["nt_total_pct"] = round(nt_total, 1)
        facts["et_total_pct"] = round(et_total, 1)
        facts["pk_total_pct"] = round(pk_total, 1)
    else:
        facts["home_best_stage"] = facts["away_best_stage"] = None
        facts["home_best_stage_pct"] = facts["away_best_stage_pct"] = None
        facts["overall_favourite_team"] = facts["overall_favourite_stage"] = facts["overall_favourite_pct"] = None
        facts["nt_total_pct"] = facts["et_total_pct"] = facts["pk_total_pct"] = None
        facts["home_nt_pct"] = facts["home_et_pct"] = facts["home_pk_pct"] = 0
        facts["away_nt_pct"] = facts["away_et_pct"] = facts["away_pk_pct"] = 0

    # --- 3. First scorer data: "Name (Country) Odds, Name (Country) Odds, ..." ---
    scorer_entries = []
    for chunk in str(first_scorer_str).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(.*?)\s+\(([^)]+)\)\s+([\d.]+)$", chunk)
        if m:
            name, country, odds = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
            scorer_entries.append({"name": name, "country": country, "odds": odds})

    if scorer_entries:
        probs = _implied_normalised([e["odds"] for e in scorer_entries])
        for e, p in zip(scorer_entries, probs):
            e["pct"] = p

        def top_scorer_for_team(team_clean):
            team_rows = [e for e in scorer_entries if clean_country_name(e["country"]) == team_clean]
            team_rows.sort(key=lambda x: x["pct"], reverse=True)
            return team_rows

        home_ranked = top_scorer_for_team(home)
        away_ranked = top_scorer_for_team(away)
        overall_top = max(scorer_entries, key=lambda x: x["pct"])

        facts["home_top_scorer"] = home_ranked[0]["name"] if home_ranked else None
        facts["home_top_scorer_pct"] = home_ranked[0]["pct"] if home_ranked else None
        facts["home_second_scorer"] = home_ranked[1]["name"] if len(home_ranked) > 1 else None
        facts["home_second_scorer_pct"] = home_ranked[1]["pct"] if len(home_ranked) > 1 else None

        facts["away_top_scorer"] = away_ranked[0]["name"] if away_ranked else None
        facts["away_top_scorer_pct"] = away_ranked[0]["pct"] if away_ranked else None
        facts["away_second_scorer"] = away_ranked[1]["name"] if len(away_ranked) > 1 else None
        facts["away_second_scorer_pct"] = away_ranked[1]["pct"] if len(away_ranked) > 1 else None

        facts["overall_top_scorer_name"] = overall_top["name"]
        facts["overall_top_scorer_country"] = overall_top["country"]
        facts["overall_top_scorer_pct"] = overall_top["pct"]
    else:
        facts["home_top_scorer"] = facts["away_top_scorer"] = None
        facts["home_top_scorer_pct"] = facts["away_top_scorer_pct"] = None
        facts["home_second_scorer"] = facts["away_second_scorer"] = None
        facts["home_second_scorer_pct"] = facts["away_second_scorer_pct"] = None
        facts["overall_top_scorer_name"] = facts["overall_top_scorer_country"] = facts["overall_top_scorer_pct"] = None

    return facts

# ==========================================
# GROQ NARRATIVE GENERATOR
# ==========================================
@st.cache_data(ttl=86400)
def generate_kid_friendly_narrative(facts: dict):
    home, away = facts["home"], facts["away"]

    stage_grid = (
        f"{home} - NT {facts.get('home_nt_pct', 0)}% / ET {facts.get('home_et_pct', 0)}% / PK {facts.get('home_pk_pct', 0)}%; "
        f"{away} - NT {facts.get('away_nt_pct', 0)}% / ET {facts.get('away_et_pct', 0)}% / PK {facts.get('away_pk_pct', 0)}%"
    )

    prompt = f"""
    You're a fun, kid-friendly Aussie sports commentator. Write an EXTREMELY SHORT pre-match hype line for a kids'
    prediction game. Players are guessing: (1) who scores first, (2) if it goes to penalties, (3) who wins.

    MATCH: {home} vs {away}

    FACTS (already calculated - just narrate them, don't do any maths):
    - Win chance: {home} {facts.get('qualify_home_pct')}% vs {away} {facts.get('qualify_away_pct')}%
    - Most likely to score first: {facts.get('home_top_scorer')} ({home}) {facts.get('home_top_scorer_pct')}%
      vs {facts.get('away_top_scorer')} ({away}) {facts.get('away_top_scorer_pct')}%
    - Chance the match is decided in each stage: {stage_grid}

    YOUR JOB: look at that stage grid and make your OWN call - Normal Time, Extra Time, or Penalties, and who
    wins it that way. A wrong call is completely fine, this is just for fun - just make it an informed guess
    based on those numbers, not a random pick.

    STRICT RULES:
    - MAXIMUM 2 short sentences. Total. That's the entire brief - be brutally concise, this is a compressed
      hype line, not a story.
    - Squeeze in all 3: the win favourite, the first-scorer pick, and your NT/ET/PK call.
    - **Bold** the key names, teams and percentages.
    - 1-2 emoji max.
    - Say "chance" / "favoured" - never "odds", "bet", "stake", or anything gambling-related.
    - Every player name needs their country right next to it (e.g. "PlayerName (Country)").
    - No jokes based on nationality, culture, accent, or flag.
    - Vary your opening words each time - don't reuse the same opener call after call.

    Write it now (2 sentences max, no preamble):
    """
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=120,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"DEBUG - Groq call failed: {repr(e)}")
        return f"**{home}** vs **{away}** — buckle up, this one's a cracker! ⚽"

# --- DATABASE CONNECTION ---
@st.cache_resource(ttl=600)
def get_gspread_client():
    try:
        secret_info = st.secrets["connections"]["gsheets"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(secret_info, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Google Authentication Failed: {e}")
        st.stop()

gc = get_gspread_client()
SPREADSHEET_ID = "1BIeawdAb7CuL4UWwjrW7OE7vjW__eZ6SbXVDG__rX-M"

# --- QUOTA-FRIENDLY CACHING LAYER ---
# Opening the spreadsheet + listing worksheets is itself a read call, so we only
# want to do it once every few minutes rather than on every single rerun/click.
@st.cache_resource(ttl=300)
def get_workbook(_gc, spreadsheet_id):
    return _gc.open_by_key(spreadsheet_id)

@st.cache_resource(ttl=300)
def get_worksheets_dict(_sh):
    return {ws.title.strip().lower(): ws for ws in _sh.worksheets()}

# Actual row DATA changes far more often (predictions/results), so this gets a
# short TTL - long enough to absorb rapid-fire reruns from clicks/dropdowns
# within the same minute, short enough that saves are visible almost immediately.
# Any successful write elsewhere in the app calls st.cache_data.clear() to force
# an instant refresh rather than waiting out the TTL.
SHEET_DATA_TTL = 20

@st.cache_data(ttl=SHEET_DATA_TTL, show_spinner=False)
def load_all_sheet_records(_worksheets_dict):
    def _records(key):
        ws = _worksheets_dict.get(key)
        return ws.get_all_records() if ws else []
    return {
        "matches": _records("matches"),
        "knockout": _records("knockout_predictions"),
        "leaderboard": _records("leaderboard"),
        "odds": _records("match_odds_feed"),
        "golden_boot": _records("golden_boot_candidates"),
        "once_off": _records("once_off_predictions"),
        "team_status": _records("team_status"),
    }

# Headers rarely change (only when you edit the sheet structure), so these get
# a much longer TTL - saves a read-call on every single prediction/admin save.
# NOTE: sheet_title is passed in separately (not underscore-prefixed) purely so
# Streamlit's cache key can tell different worksheets apart - _ws itself is
# excluded from hashing since gspread Worksheet objects aren't hashable, and
# without a distinguishing hashable arg every worksheet would collide on one
# shared cache entry.
@st.cache_data(ttl=600, show_spinner=False)
def get_headers(_ws, sheet_title):
    return [h.strip() for h in _ws.row_values(1)]

try:
    sh = get_workbook(gc, SPREADSHEET_ID)
    all_worksheets = get_worksheets_dict(sh)
    
    if "knockout_predictions" not in all_worksheets:
        st.error(f"🔍 I still can't see the tab! Here are the tabs I DO see: {list(all_worksheets.keys())}")
        st.stop()
        
    matches_worksheet = all_worksheets["matches"]
    knockout_worksheet = all_worksheets["knockout_predictions"]
    leaderboard_worksheet = all_worksheets["leaderboard"]
    
    # NEW: Safely pull the Match_Odds_Feed if it exists
    odds_worksheet = all_worksheets.get("match_odds_feed")

    # NEW: Golden Boot candidates + Once-Off predictions (Golden Boot / Champion)
    golden_boot_worksheet = all_worksheets.get("golden_boot_candidates")
    once_off_worksheet = all_worksheets.get("once_off_predictions")

    # NEW: Team elimination tracker (used to filter Champion picker to survivors only)
    team_status_worksheet = all_worksheets.get("team_status")

    sheet_records = load_all_sheet_records(all_worksheets)
    matches_df = pd.DataFrame(sheet_records["matches"])
    knockout_df = pd.DataFrame(sheet_records["knockout"])
    leaderboard_df = pd.DataFrame(sheet_records["leaderboard"])
    odds_df = pd.DataFrame(sheet_records["odds"])
    golden_boot_df = pd.DataFrame(sheet_records["golden_boot"])
    once_off_df = pd.DataFrame(sheet_records["once_off"])
    team_status_df = pd.DataFrame(sheet_records["team_status"])

except Exception as e:
    st.error(f"❌ Connection Blocked: {e}")
    st.stop()

# Standardize dataframes
for df in [matches_df, knockout_df]:
    if not df.empty:
        df.columns = df.columns.str.strip()
        df['Match_ID'] = df['Match_ID'].astype(str)
        df['Kickoff_AEST'] = df['Kickoff_AEST'].apply(clean_and_parse_date)
        df['Kickoff_Date'] = df['Kickoff_AEST'].dt.date

leaderboard_df.columns = leaderboard_df.columns.str.strip()
if not golden_boot_df.empty:
    golden_boot_df.columns = golden_boot_df.columns.str.strip()
if not once_off_df.empty:
    once_off_df.columns = once_off_df.columns.str.strip()
if not team_status_df.empty:
    team_status_df.columns = team_status_df.columns.str.strip()
participants = ['ND', 'CD', 'SB', 'GB', 'LS', 'HD']

# ==========================================
# ROUND OF 16+ CONSTANTS (5-question format)
# ==========================================
ROUND16_MATCH_ID_THRESHOLD = 89
ONCE_OFF_LOCK_DATETIME = datetime(2026, 7, 5, 3, 0, 0)  # naive AEST, compared against get_current_aest()

TIME_BRACKET_OPTIONS = [
    "0:00 – 9:59", "10:00 – 19:59", "20:00 – 29:59", "30:00 – 39:59",
    "40:00 – End of 1st Half", "45:00 – 54:59", "55:00 – 64:59",
    "65:00 – 74:59", "75:00 – 84:59", "85:00 – End of 2nd Half",
    "1st Half ET", "2nd Half ET",
]
METHOD_OPTIONS = ["Normal Shot (Foot)", "Header", "Penalty", "Free Kick", "Own Goal"]

def map_minute_to_bracket(minute):
    m = int(minute)
    if m <= 9:   return "0:00 – 9:59"
    if m <= 19:  return "10:00 – 19:59"
    if m <= 29:  return "20:00 – 29:59"
    if m <= 39:  return "30:00 – 39:59"
    if m <= 44 or m == 45: return "40:00 – End of 1st Half"
    if m <= 54:  return "45:00 – 54:59"
    if m <= 64:  return "55:00 – 64:59"
    if m <= 74:  return "65:00 – 74:59"
    if m <= 84:  return "75:00 – 84:59"
    if m <= 89 or m == 90: return "85:00 – End of 2nd Half"
    if m <= 105: return "1st Half ET"
    return "2nd Half ET"

def is_round16_plus(match_id):
    try:
        return int(match_id) >= ROUND16_MATCH_ID_THRESHOLD
    except Exception:
        return False

def is_once_off_locked():
    return get_current_aest() >= ONCE_OFF_LOCK_DATETIME

# ==========================================
# QUARTER FINAL+ CONSTANTS (Match_ID >= 97)
# Exact score replaces Goal Gap, simplified 4-bracket time (10pts, was 20),
# "Team Advances" is removed (exact score already determines the winner), and
# Q5 is an "Anytime Scorer" player ladder question (scores in Normal Time or
# Extra Time only - penalty shootout goals don't count). Still reads from
# Match_Odds_Feed.First_Scorer_Data even though it's no longer strictly a
# "first scorer" market.
# ==========================================
QF_MATCH_ID_THRESHOLD = 97
QF_TIME_BRACKET_OPTIONS = ["1st Half NT", "2nd Half NT", "1st Half ET", "2nd Half ET"]
Q6_NOGOAL_LABEL = "No Goal"
Q6_CATCHALL_POINTS = 10  # points for "none of these named players score anytime" (goal happens, just not from the list)
Q6_NO_GOAL_POINTS = 30   # points for correctly calling a true 0-0 (no goals at all, from anyone) - a genuinely
                         # rarer outcome than even the longest-shot named player scoring, so it earns more
                         # than the general catchall above rather than being tied to it

# --- DEV OVERRIDE: force specific matches into the prediction window early ---
# Temporary way to open a match for predictions before its normal rolling
# window kicks in, without touching kickoff times. Remove/empty this list
# once the normal window naturally reaches these matches.
FORCE_OPEN_MATCHES = ["97", "98", "99", "100"]

def is_qf_plus(match_id):
    try:
        return int(match_id) >= QF_MATCH_ID_THRESHOLD
    except Exception:
        return False

# ==========================================
# SEMI FINAL+ CONSTANTS (Match_ID >= 101)
# Adds a new "Method of Progression" question (which team wins in which stage -
# NT/ET/PK), ranked on its own steeper points ladder since there are only ever
# up to 6 team+stage combos (vs. up to 24 for Anytime Scorer). Everything else
# from the QF+ format carries over unchanged (Time bracket, Method, Anytime
# Scorer just gets a wider player cap here). QF matches (97-100) are already
# done and dusted, so this only ever applies from 101 onward.
# ==========================================
SF_MATCH_ID_THRESHOLD = 101

def is_sf_plus(match_id):
    try:
        return int(match_id) >= SF_MATCH_ID_THRESHOLD
    except Exception:
        return False

PROGRESSION_STAGE_CODE = {"Normal Time": "NT", "Extra Time": "ET", "Penalties": "PK"}

def parse_progression_ladder(progression_str):
    """Parse 'Team Stage Odds, Team Stage Odds, ...' from Match_Odds_Feed's
    Progression_Data, e.g. 'France Normal Time 2.30, Spain Normal Time 3.10,
    France Extra Time 9.00, Spain Extra Time 11.00, France Penalties 10.00,
    Spain Penalties 11.00'. Returns entries ranked ascending by odds (favourite
    first), each tagged with its points on a steeper ladder than Anytime Scorer's
    (there are only ever up to 6 combos here, so bigger steps feel right): 10,
    14, 18, 22... (+4 per UNIQUE odds value, mirroring the tie-handling already
    used for Anytime Scorer - entries sharing identical odds share identical
    points and emoji)."""
    entries = []
    for chunk in str(progression_str).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(.*?)\s+(Normal Time|Extra Time|Penalties)\s+([\d.]+)$", chunk)
        if m:
            team, stage_label, odds = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
            entries.append({
                "team": clean_country_name(team),
                "stage_label": stage_label,
                "stage_code": PROGRESSION_STAGE_CODE.get(stage_label, stage_label),
                "odds": odds,
            })
    entries.sort(key=lambda e: e["odds"])

    unique_odds = sorted(set(e["odds"] for e in entries))
    n_unique = len(unique_odds)
    odds_to_points = {o: 10 + 4 * i for i, o in enumerate(unique_odds)}
    odds_to_fraction = {o: (i / (n_unique - 1) if n_unique > 1 else 0) for i, o in enumerate(unique_odds)}
    for e in entries:
        e["points"] = odds_to_points[e["odds"]]
        e["rank_fraction"] = odds_to_fraction[e["odds"]]
    return entries

def parse_scorer_ladder(first_scorer_str):
    """Parse 'Name (Country) Odds, Name (Country) Odds, ...' from Match_Odds_Feed's
    First_Scorer_Data. Returns entries ranked ascending by odds (favourite first),
    each tagged with its points on the risk/reward ladder: 5, 8, 11, 14... (+3 per
    UNIQUE odds value) - this naturally scales to however many named players are
    actually given, rather than assuming exactly 6.

    Players sharing identical odds get identical points (and identical emoji/risk
    level) - the ladder only steps up when the odds themselves increase, so two
    equally-priced players are equally risky/rewarding picks."""
    entries = []
    for chunk in str(first_scorer_str).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(.*?)\s+\(([^)]+)\)\s+([\d.]+)$", chunk)
        if m:
            name, country, odds = m.group(1).strip(), m.group(2).strip(), float(m.group(3))
            entries.append({"name": name, "country": clean_country_name(country), "odds": odds})
    entries.sort(key=lambda e: e["odds"])  # ascending odds = shortest price = favourite first

    unique_odds = sorted(set(e["odds"] for e in entries))
    n_unique = len(unique_odds)
    odds_to_points = {o: 5 + 3 * i for i, o in enumerate(unique_odds)}
    odds_to_fraction = {o: (i / (n_unique - 1) if n_unique > 1 else 0) for i, o in enumerate(unique_odds)}

    for e in entries:
        e["points"] = odds_to_points[e["odds"]]
        e["rank_fraction"] = odds_to_fraction[e["odds"]]
    return entries

# 24 distinct emoji, cold (safest pick, fewest points) -> hot (riskiest pick,
# most points). Capped at 24 since that's the max total named players across
# both sides (up to 12 each) for Anytime Scorer from SF+ onward. Also reused
# for the Method of Progression ladder (up to 6 combos), which just uses a
# smaller slice of the same gradient proportionally.
TEMP_EMOJI_GRADIENT = [
    "🧊", "❄️", "🥶", "🌨️", "⛄", "🌬️", "⛅", "🌥️", "🌤️", "🌦️", "🌈", "☀️",
    "🌞", "🏖️", "🌡️", "♨️", "🥵", "🌶️", "🔥", "🌋", "⚡", "☄️", "🧨", "💥",
]

def temp_emoji(fraction):
    """Cold (favourite, low points) -> hot (longshot, high points) emoji scale.
    Maps the 0-1 rank_fraction proportionally onto the 24-slot gradient above.
    With <=24 distinct odds tiers this is guaranteed to give every tier its own
    unique emoji - scaling onto evenly-spaced slots and rounding can't collide
    as long as there are 24 tiers or fewer."""
    idx = round(fraction * (len(TEMP_EMOJI_GRADIENT) - 1))
    idx = max(0, min(idx, len(TEMP_EMOJI_GRADIENT) - 1))
    return TEMP_EMOJI_GRADIENT[idx]


def get_player_photo(player_name):
    """Looks up a player's photo from golden_boot_candidates by exact name match.
    Returns None (no photo, not an error) if the sheet is empty, the player isn't
    listed there yet, or the image file doesn't exist - Q6 still works fine without
    a photo, it's a nice-to-have."""
    if golden_boot_df.empty or 'Player_Name' not in golden_boot_df.columns:
        return None
    match = golden_boot_df[golden_boot_df['Player_Name'].str.strip() == str(player_name).strip()]
    if match.empty:
        return None
    img_path = match.iloc[0].get('Image_File', '')
    return img_path if img_path and os.path.exists(img_path) else None

def saved_index(options, saved_value):
    """Returns the index of saved_value within options, or None if it's empty or
    doesn't match anything. Used so switching between users re-populates each
    question with THAT user's already-saved pick, instead of leaving whatever
    the previously-viewed user last had on screen (widget state in Streamlit is
    otherwise shared across reruns by key, regardless of which user is showing)."""
    if not saved_value:
        return None
    try:
        return options.index(saved_value)
    except ValueError:
        return None

def get_player_note(player_name):
    """Looks up a short set-piece duty note (e.g. 'Penalty taker') for a player from
    golden_boot_candidates' Scoring_Note column. This is deliberately NOT AI-generated -
    penalty/free-kick duty is precise factual info that's easy to get subtly wrong if
    paraphrased, so it's just plain maintained data, shown as-is. Returns None (not an
    error) if the sheet/column doesn't exist yet or nothing's been entered for this
    player - Q6 works fine either way, this is a nice-to-have consideration for kids."""
    if golden_boot_df.empty or 'Player_Name' not in golden_boot_df.columns or 'Scoring_Note' not in golden_boot_df.columns:
        return None
    match = golden_boot_df[golden_boot_df['Player_Name'].str.strip() == str(player_name).strip()]
    if match.empty:
        return None
    note = str(match.iloc[0].get('Scoring_Note', '')).strip()
    return note if note else None

tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "⚽ Submit Predictions", "🔒 Admin Engine"])

# ==========================================
# TAB 1: LEADERBOARD
# ==========================================
with tab1:
    st.subheader("Current Standings")
    leaderboard_sorted = leaderboard_df.sort_values(by="Points", ascending=False).reset_index(drop=True)

    top_points = leaderboard_sorted["Points"].max() if not leaderboard_sorted.empty else None

    def _highlight_leader(row):
        if top_points is not None and row["Points"] == top_points:
            return ["background-color: #FFD700; color: #1a1a1a; font-weight: bold;"] * len(row)
        return [""] * len(row)

    styled_leaderboard = leaderboard_sorted.style.apply(_highlight_leader, axis=1)
    st.dataframe(
        styled_leaderboard,
        use_container_width=True, hide_index=True,
        column_config={"Participant": "Player", "Points": st.column_config.NumberColumn("Total Points", format="%d pts")}
    )
    if top_points is not None and top_points > 0:
        leaders = leaderboard_sorted.loc[leaderboard_sorted["Points"] == top_points, "Participant"].tolist()
        st.markdown(f"👑 **Current leader{'s' if len(leaders) > 1 else ''}:** {', '.join(leaders)} 🎉🔥")
    st.divider()
    st.markdown("🎁 **Prize:** $20 Kmart Gift Card up for grabs.")

    # ==========================================
    # ACTIVE PREDICTIONS — ALL PARTICIPANTS
    # Shows today's not-yet-scored matches. From 5:00 PM AEDT onward, also
    # previews tomorrow's matches (so people can see/compare picks ahead of
    # kickoff even before anyone's submitted). A match disappears from here
    # the moment Admin marks it Completed — nothing to maintain manually.
    # ==========================================
    st.divider()
    st.markdown("### 📢 Active Predictions — All Participants")

    lb_now = get_current_aest()
    lb_today = lb_now.date()
    lb_tomorrow = lb_today + timedelta(days=1)
    lb_cutover = lb_now.replace(hour=17, minute=0, second=0, microsecond=0)

    lb_combined = pd.concat(
        [df for df in [matches_df, knockout_df] if not df.empty], ignore_index=True
    ) if (not matches_df.empty or not knockout_df.empty) else pd.DataFrame()

    if lb_combined.empty:
        st.info("No match schedule loaded yet.")
    else:
        cond_today = (lb_combined['Kickoff_Date'] == lb_today) & (lb_combined['Status'] != 'Completed')
        cond_tomorrow_preview = (lb_now >= lb_cutover) & (lb_combined['Kickoff_Date'] == lb_tomorrow) & (lb_combined['Status'] != 'Completed')
        lb_active_window = lb_combined[cond_today | cond_tomorrow_preview].sort_values('Kickoff_AEST')

        if lb_active_window.empty:
            st.info("No active matches to show right now — check back closer to kickoff! 🎉")
        else:
            if lb_now >= lb_cutover:
                st.caption(f"Showing today's remaining matches plus a preview of tomorrow's ({lb_tomorrow.strftime('%a, %d %b')}) matches.")
            for _, arow in lb_active_window.iterrows():
                a_mid = arow['Match_ID']
                a_stage = 'Group' if a_mid in matches_df['Match_ID'].values else 'Knockout'
                a_home = clean_country_name(arow['Home_Team'])
                a_away = clean_country_name(arow['Away_Team'])
                a_locked = lb_now >= arow['Kickoff_AEST']
                lock_badge = "🔒 **LOCKED**" if a_locked else "🟢 **OPEN**"

                st.markdown(
                    f"**Match {a_mid}: {a_home} vs {a_away}**  "
                    f"⏰ {arow['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p')} AEST  —  {lock_badge}"
                )

                p_rows = []
                for p in participants:
                    if a_stage == 'Group':
                        p_first = str(arow.get(f'{p}_FirstScorer', "")).strip()
                        p_score = str(arow.get(f'{p}_Score', "")).strip()
                        p_rows.append({
                            "Player": p,
                            "⚽ First Scorer": clean_country_name(p_first) or "—",
                            "📊 Score": p_score or "—",
                        })
                    else:
                        p_first = str(arow.get(f'{p}_FirstScorer', "")).strip()
                        p_row = {
                            "Player": p,
                            "⚽ First Scorer": clean_country_name(p_first) or "—",
                        }
                        if is_qf_plus(a_mid):
                            p_home_sc = str(arow.get(f'{p}_HomeScore', "")).strip()
                            p_away_sc = str(arow.get(f'{p}_AwayScore', "")).strip()
                            p_row["🔢 Score"] = f"{p_home_sc}-{p_away_sc}" if p_home_sc != "" and p_away_sc != "" else "—"
                            if is_sf_plus(a_mid):
                                p_progression = str(arow.get(f'{p}_ProgressionPick', "")).strip()
                                p_row["🏁 Progression"] = p_progression or "—"
                            p_nominated = str(arow.get(f'{p}_NominatedScorer', "")).strip()
                            p_row["🏃 Anytime Scorer"] = p_nominated or "—"
                        else:
                            p_qual = str(arow.get(f'{p}_Qualifier', "")).strip()
                            p_gap = str(arow.get(f'{p}_GoalGap', "")).strip()
                            p_row["🏆 Advances"] = clean_country_name(p_qual) or "—"
                            p_row["📏 Goal Gap"] = p_gap or "—"
                        if is_round16_plus(a_mid):
                            p_time = str(arow.get(f'{p}_TimeOfFirstGoal', "")).strip()
                            p_method = str(arow.get(f'{p}_MethodOfFirstGoal', "")).strip()
                            p_row["⏱️ Time"] = p_time or "—"
                            p_row["🎯 Method"] = p_method or "—"
                        p_rows.append(p_row)

                p_df = pd.DataFrame(p_rows).set_index("Player")
                st.dataframe(p_df, use_container_width=True)

    # ==========================================
    # GOLDEN BOOT & CHAMPION PICKS — moved to the bottom + collapsible.
    # These are FYI-only once locked (5 July 3AM AEDT), so they don't need
    # prime real estate above the live active-predictions table.
    # ==========================================
    if not once_off_df.empty:
        st.divider()
        with st.expander("🏅 Golden Boot & 🏆 Champion Picks"):
            oo_display_rows = []
            for _, r in once_off_df.iterrows():
                oo_display_rows.append({
                    "Player": r.get("Participant", ""),
                    "🏅 Golden Boot Pick": r.get("GoldenBoot_Pick", "") or "—",
                    "🏆 Champion Pick": clean_country_name(str(r.get("Champion_Pick", ""))) or "—",
                })
            st.dataframe(pd.DataFrame(oo_display_rows), use_container_width=True, hide_index=True)
            if not is_once_off_locked():
                st.caption("Picks are still editable until 5 July 2026, 3:00 AM AEDT.")
            else:
                st.caption("🔒 Locked in — FYI only now.")

# ==========================================
# TAB 2: SUBMIT PREDICTIONS
# ==========================================
with tab2:
    st.subheader("Log or Edit Your Predictions")
    user = st.selectbox("Who are you?", ["Select your name..."] + participants)

    if user != "Select your name...":
        current_time = get_current_aest()
        today = current_time.date()

        # ==========================================
        # PINNED: ONCE-OFF PREDICTIONS (Golden Boot + Champion)
        # Only shown here while still editable. Once locked, it's FYI-only and
        # already visible in the collapsible section at the bottom of the
        # Leaderboard tab - no need to repeat it here too.
        # ==========================================
        once_off_locked = is_once_off_locked()

        if once_off_locked:
            pass  # locked - nothing to edit here, see Leaderboard tab for the FYI view
        elif golden_boot_df.empty or once_off_df.empty:
            st.markdown("### 🏅 Golden Boot & 🏆 Champion Picks")
            st.warning("⚠️ Once-off predictions aren't set up yet in the sheet (golden_boot_candidates / once_off_predictions tabs).")
        else:
            st.markdown("### 🏅 Golden Boot & 🏆 Champion Picks")
            existing_row = once_off_df[once_off_df['Participant'] == user]
            current_gb_pick = str(existing_row.iloc[0].get('GoldenBoot_Pick', '')).strip() if not existing_row.empty else ""
            current_champ_pick = str(existing_row.iloc[0].get('Champion_Pick', '')).strip() if not existing_row.empty else ""

            st.caption(f"⏰ Locks 5 July 2026, 3:00 AM AEDT. Worth **50 pts each**, scored at the Final.")
            oo_col1, oo_col2 = st.columns(2)

            with oo_col1:
                st.markdown("**🏅 Golden Boot Winner**")
                gb_names = golden_boot_df['Player_Name'].tolist()
                gb_default_idx = (gb_names.index(current_gb_pick) + 1) if current_gb_pick in gb_names else 0
                gb_pick = st.selectbox("Pick your Golden Boot winner:", ["Select player..."] + gb_names, index=gb_default_idx, key="gb_pick_select")
                if gb_pick != "Select player...":
                    gb_row = golden_boot_df[golden_boot_df['Player_Name'] == gb_pick].iloc[0]
                    img_path = gb_row.get('Image_File', '')
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, width=120, caption=f"{gb_pick} ({gb_row.get('Team','')})")
                    else:
                        st.caption(f"{gb_pick} ({gb_row.get('Team','')})")

            with oo_col2:
                st.markdown("**🏆 Tournament Champion**")
                champ_options, champ_raw_lookup = build_champion_options(matches_df, team_status_df)
                current_champ_clean = clean_country_name(current_champ_pick)
                champ_default_idx = (champ_options.index(current_champ_clean) + 1) if current_champ_clean in champ_options else 0
                champ_pick = st.selectbox("Pick the World Cup Champion:", ["Select country..."] + champ_options, index=champ_default_idx, key="champ_pick_select")
                if champ_pick != "Select country...":
                    flag_src = get_flag_url(champ_raw_lookup.get(champ_pick, champ_pick))
                    if flag_src:
                        st.image(flag_src, width=90, caption=champ_pick)
                    else:
                        st.caption(champ_pick)

            if st.button("💾 Save Once-Off Picks"):
                if gb_pick == "Select player..." or champ_pick == "Select country...":
                    st.error("Please pick both a Golden Boot winner and a Champion before saving.")
                else:
                    try:
                        oo_headers = get_headers(once_off_worksheet, "once_off_predictions")
                        row_num = None
                        for idx, r in once_off_df.reset_index(drop=True).iterrows():
                            if str(r.get("Participant", "")).strip() == user:
                                row_num = idx + 2
                                break
                        if row_num is None:
                            st.error(f"Couldn't find a row for {user} in once_off_predictions — check the sheet has all 6 participants listed.")
                        else:
                            once_off_worksheet.update_cell(row_num, oo_headers.index("GoldenBoot_Pick") + 1, gb_pick)
                            once_off_worksheet.update_cell(row_num, oo_headers.index("Champion_Pick") + 1, champ_pick)
                            st.cache_data.clear()
                            st.toast("✅ Once-off picks saved!", icon="✅")
                            st.rerun()
                    except Exception as write_err:
                        st.error(f"Failed to save once-off picks: {write_err}")

        st.divider()
        st.markdown(f"### Your Active Predictions Overview ({user})")
        group_overview_rows = []
        ko_overview_rows = []
        
        # Pull active Group matches
        active_group = matches_df[matches_df['Status'] != 'Completed'] if not matches_df.empty else pd.DataFrame()
        for _, row in active_group.iterrows():
            m_id = row['Match_ID']
            first_scorer = str(row.get(f'{user}_FirstScorer', "")).strip()
            score = str(row.get(f'{user}_Score', "")).strip()
            
            group_overview_rows.append({
                "Match ID": m_id,
                "🏳️ Home": get_flag_url(row['Home_Team']),
                "Home Team": clean_country_name(row['Home_Team']),
                "Away Team": clean_country_name(row['Away_Team']),
                "🏳️ Away": get_flag_url(row['Away_Team']),
                "Kickoff (AEST)": row['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p'),
                "⚽ First Scorer": first_scorer or "—",
                "📊 Score": score or "—",
            })
            
        # Pull active Knockout matches
        active_ko = knockout_df[knockout_df['Status'] != 'Completed'] if not knockout_df.empty else pd.DataFrame()
        # "Advances" and "Goal Gap" only apply to pre-QF matches (R32 / R16-QF-1). Once
        # nothing pre-QF is left active, drop those columns entirely instead of showing
        # them full of "N/A" - cleaner table once the tournament moves past R16.
        any_pre_qf_active = any(not is_qf_plus(mid) for mid in active_ko['Match_ID']) if not active_ko.empty else False
        for _, row in active_ko.iterrows():
            m_id = row['Match_ID']
            first_scorer = str(row.get(f'{user}_FirstScorer', "")).strip()

            ko_row = {
                "Match ID": m_id,
                "🏳️ Home": get_flag_url(row['Home_Team']),
                "Home Team": clean_country_name(row['Home_Team']),
                "Away Team": clean_country_name(row['Away_Team']),
                "🏳️ Away": get_flag_url(row['Away_Team']),
                "Kickoff (AEST)": row['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p'),
                "⚽ First Scorer": clean_country_name(first_scorer) if first_scorer else "—",
            }
            if is_qf_plus(m_id):
                home_sc = str(row.get(f'{user}_HomeScore', "")).strip()
                away_sc = str(row.get(f'{user}_AwayScore', "")).strip()
                if any_pre_qf_active:
                    ko_row["🏆 Advances"] = "N/A"
                    ko_row["📏 Goal Gap"] = "N/A"
                ko_row["🔢 Score"] = f"{home_sc}-{away_sc}" if home_sc != "" and away_sc != "" else "—"
                if is_sf_plus(m_id):
                    progression_pick = str(row.get(f'{user}_ProgressionPick', "")).strip()
                    ko_row["🏁 Progression"] = progression_pick or "—"
                else:
                    ko_row["🏁 Progression"] = "N/A"
                nominated = str(row.get(f'{user}_NominatedScorer', "")).strip()
                ko_row["🏃 Anytime Scorer"] = nominated or "—"
            else:
                qualifier = str(row.get(f'{user}_Qualifier', "")).strip()
                goal_gap = str(row.get(f'{user}_GoalGap', "")).strip()
                ko_row["🏆 Advances"] = clean_country_name(qualifier) if qualifier else "—"
                ko_row["📏 Goal Gap"] = goal_gap or "—"
                ko_row["🔢 Score"] = "N/A"
                ko_row["🏁 Progression"] = "N/A"
                ko_row["🏃 Anytime Scorer"] = "N/A"

            if is_round16_plus(m_id):
                time_pick = str(row.get(f'{user}_TimeOfFirstGoal', "")).strip()
                method_pick = str(row.get(f'{user}_MethodOfFirstGoal', "")).strip()
                ko_row["⏱️ Time"] = time_pick or "—"
                ko_row["🎯 Method"] = method_pick or "—"
            else:
                ko_row["⏱️ Time"] = "N/A"
                ko_row["🎯 Method"] = "N/A"
            ko_overview_rows.append(ko_row)

        if group_overview_rows:
            st.markdown("**Group Stage**")
            st.dataframe(
                pd.DataFrame(group_overview_rows), use_container_width=True, hide_index=True,
                column_config={"🏳️ Home": st.column_config.ImageColumn(""), "🏳️ Away": st.column_config.ImageColumn("")}
            )

        if ko_overview_rows:
            st.markdown("**Knockout Stage**")
            st.dataframe(
                pd.DataFrame(ko_overview_rows), use_container_width=True, hide_index=True,
                column_config={"🏳️ Home": st.column_config.ImageColumn(""), "🏳️ Away": st.column_config.ImageColumn("")}
            )

        if not group_overview_rows and not ko_overview_rows:
            st.info("No active matches scheduled right now.")

        st.divider()
        st.markdown("### ✍️ Submit or Edit a Prediction")

        # Combine schedules to find open matches in the rolling window
        combined_schedule = pd.concat([active_group, active_ko], ignore_index=True) if not active_group.empty or not active_ko.empty else pd.DataFrame()
        
        open_matches = pd.DataFrame()
        if not combined_schedule.empty:
            tournament_start_date = datetime.strptime("2026-06-12", "%Y-%m-%d").date()
            if today < tournament_start_date:
                allowed_days = [tournament_start_date, tournament_start_date + timedelta(days=1), tournament_start_date + timedelta(days=2)]
                open_matches = combined_schedule[combined_schedule['Kickoff_Date'].isin(allowed_days)].copy()
            else:
                day_d = today
                day_d1 = today + timedelta(days=1)
                day_d2 = today + timedelta(days=2)
                cond_today = (combined_schedule['Kickoff_Date'] == day_d) & (combined_schedule['Kickoff_AEST'] > current_time)
                cond_future = combined_schedule['Kickoff_Date'].isin([day_d1, day_d2])
                open_matches = combined_schedule[cond_today | cond_future].copy()

            # DEV OVERRIDE: force specific matches into the list even if their normal
            # rolling window hasn't opened yet (kickoff times themselves are untouched).
            if FORCE_OPEN_MATCHES:
                forced_rows = combined_schedule[combined_schedule['Match_ID'].isin(FORCE_OPEN_MATCHES)]
                if not forced_rows.empty:
                    open_matches = pd.concat([open_matches, forced_rows], ignore_index=True).drop_duplicates(subset='Match_ID')

        if open_matches.empty:
            st.info("No matches scheduled for this specific rolling window are open right now.")
        else:
            match_options = open_matches.apply(lambda r: f"Match {r['Match_ID']}: {clean_country_name(r['Home_Team'])} vs {clean_country_name(r['Away_Team'])} ({r['Kickoff_AEST'].strftime('%a, %d %b %I:%M %p')})", axis=1).tolist()
            selected_pred_match = st.selectbox("Choose a match to log/modify:", match_options)

            m_id = selected_pred_match.split(":")[0].replace("Match ", "").strip()
            stage = get_match_stage(m_id)
            
            # Determine which dataframe and worksheet we are interacting with
            target_df = knockout_df if stage == "Knockout" else matches_df
            target_ws = knockout_worksheet if stage == "Knockout" else matches_worksheet
            
            m_idx = target_df[target_df['Match_ID'] == m_id].index[0]
            m_row = target_df.loc[m_idx]

            is_locked = current_time >= m_row['Kickoff_AEST']
            st.write(f"⏰ **Kickoff:** {m_row['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p')} AEST ({'LOCKED' if is_locked else 'Open for Changes'})")

            home_clean = clean_country_name(m_row['Home_Team'])
            away_clean = clean_country_name(m_row['Away_Team'])

            home_flag = get_flag_url(m_row['Home_Team'])
            away_flag = get_flag_url(m_row['Away_Team'])
            home_flag_html = f'<img src="{home_flag}" style="width:28px; vertical-align:middle; margin-right:6px; border-radius:3px;">' if home_flag else ''
            away_flag_html = f'<img src="{away_flag}" style="width:28px; vertical-align:middle; margin-right:6px; border-radius:3px;">' if away_flag else ''

            # A single flex row (not st.columns, which stacks vertically on mobile) so
            # "Country1 vs Country2" always stays on one horizontal line, phones included.
            st.markdown(
                f"""
                <div style='display:flex; align-items:center; justify-content:center; flex-wrap:nowrap;
                            gap:8px; margin:8px 0; white-space:nowrap; overflow-x:auto;'>
                    <span style='font-size:clamp(0.85em, 3.8vw, 1.25em); font-weight:700;'>{home_flag_html}{home_clean}</span>
                    <span style='font-size:0.8em; opacity:0.55; font-weight:600;'>vs</span>
                    <span style='font-size:clamp(0.85em, 3.8vw, 1.25em); font-weight:700;'>{away_flag_html}{away_clean}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.write("---")

            # ==========================================
            # INPUT FORMS (GROUP VS KNOCKOUT)
            # ==========================================
            if stage == "Group":
                st.info("⚽ Group Stage: 20 Points Total")
                col1, col2 = st.columns(2)
                with col1:
                    p_home_score = st.number_input(f"{home_clean} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
                with col2:
                    p_away_score = st.number_input(f"{away_clean} Predicted Goals", min_value=0, max_value=20, step=1, value=0)

                predicted_score_str = f"{p_home_score}-{p_away_score}"
                p_first = st.selectbox("Who will score first?", ["Select option...", home_clean, away_clean, "No Goal"])

                if st.button("Lock Prediction In"):
                    if is_locked:
                        st.error("This match has already kicked off! Changing predictions is locked.")
                    elif p_first == "Select option...":
                        st.error("Please explicitly declare who scores first!")
                    elif p_first.strip().lower() == home_clean.strip().lower() and p_home_score == 0:
                        st.error(f"❌ You cannot pick {home_clean} to score first if they have 0 goals!")
                    elif p_first.strip().lower() == away_clean.strip().lower() and p_away_score == 0:
                        st.error(f"❌ You cannot pick {away_clean} to score first if they have 0 goals!")
                    elif p_home_score == 0 and p_away_score == 0 and p_first != "No Goal":
                        st.error("❌ If your exact score is 0-0, your first scorer must be 'No Goal'!")
                    elif (p_home_score > 0 or p_away_score > 0) and p_first == "No Goal":
                        st.error(f"❌ You predicted goals ({predicted_score_str}), so 'No Goal' is impossible!")
                    else:
                        try:
                            headers = get_headers(target_ws, target_ws.title)
                            first_col_idx = headers.index(f"{user}_FirstScorer") + 1
                            score_col_idx = headers.index(f"{user}_Score") + 1
                            sheet_row_num = int(m_idx) + 2
                            
                            sheet_first_val = m_row['Home_Team'] if p_first == home_clean else (m_row['Away_Team'] if p_first == away_clean else "No Goal")
                            target_ws.update_cell(sheet_row_num, first_col_idx, sheet_first_val)
                            target_ws.update_cell(sheet_row_num, score_col_idx, predicted_score_str)
                            st.cache_data.clear()
                            st.toast("✅ Prediction saved!", icon="✅")
                            st.rerun()
                        except Exception as write_err:
                            st.error(f"Failed to update spreadsheet: {write_err}")

            else:
                # KNOCKOUT STAGE — 3-Q (R32) / 5-Q (R16-QF-1) / 6-Q (QF+) / 7-Q (SF+, Match_ID >= 101) FORMAT
                round16_plus = is_round16_plus(m_id)
                qf_plus = is_qf_plus(m_id)
                sf_plus = is_sf_plus(m_id)

                # --- GOOGLE AI STUDIO NARRATIVE INJECTION ---
                odds_data = None
                if not odds_df.empty:
                    match_odds_row = odds_df[odds_df['Match_ID'].astype(str) == str(m_id)]
                    if not match_odds_row.empty:
                        odds_data = match_odds_row.iloc[0]

                # For QF+, the Q6 player ladder comes straight from First_Scorer_Data -
                # parsed once here so we can both show the max-points banner accurately
                # and build the Q6 picker further down. For SF+, the Progression ladder
                # (which team wins in which stage) comes from Progression_Data the same way.
                scorer_ladder = []
                if qf_plus and odds_data is not None:
                    scorer_ladder = parse_scorer_ladder(str(odds_data.get('First_Scorer_Data', '')))
                progression_ladder = []
                if sf_plus and odds_data is not None:
                    progression_ladder = parse_progression_ladder(str(odds_data.get('Progression_Data', '')))

                if qf_plus:
                    ladder_max = max([e['points'] for e in scorer_ladder], default=Q6_CATCHALL_POINTS)
                    q6_max_pts = max(ladder_max, Q6_NO_GOAL_POINTS)
                    progression_max_pts = max([e['points'] for e in progression_ladder], default=0) if sf_plus else 0
                    max_pts = 10 + 20 + 10 + 10 + q6_max_pts + progression_max_pts  # Q1(first scorer)+Q2(score)+Q3(time)+Q4(method)+Q5(anytime scorer)+Q(progression, SF+ only)
                    st.info(f"🏆 Knockout Stage: up to {max_pts} Points Total (Anytime Scorer{'/Progression' if sf_plus else ''}'s max varies by match)")
                elif round16_plus:
                    max_pts = 60
                    st.info(f"🏆 Knockout Stage: {max_pts} Points Total")
                else:
                    max_pts = 30
                    st.info(f"🏆 Knockout Stage: {max_pts} Points Total")

                if odds_data is not None:
                    # Only run the AI if the GOOGLE_API_KEY is present in secrets
                    if "GOOGLE_API_KEY" in st.secrets:
                        with st.spinner("🎤 Crossing to the commentary box for the pre-match scoop..."):
                            match_facts = compute_match_probabilities(
                                home_clean,
                                away_clean,
                                odds_data.get('Qualify_Home', '?'),
                                odds_data.get('Qualify_Away', '?'),
                                str(odds_data.get('Progression_Data', 'No data')),
                                str(odds_data.get('First_Scorer_Data', 'No data'))
                            )
                            narrative = generate_kid_friendly_narrative(match_facts)
                        # Convert markdown **bold** to real <strong> tags - markdown syntax does NOT get
                        # re-parsed once it's inside a raw HTML block, so we have to do this conversion
                        # ourselves before injecting it into the story-card div.
                        narrative_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", narrative)
                        # Display it in a styled custom box
                        st.markdown(f"<div class='story-card'>🎙️ <strong>The Pre-Match Scoop:</strong><br><br>{narrative_html}<br><br><span style='font-size:0.7em; opacity:0.5;'>⚡ Powered by Groq</span></div>", unsafe_allow_html=True)
                    else:
                        st.warning("⚠️ Commentary offline. Missing GOOGLE_API_KEY in Streamlit secrets.")
                # --------------------------------------

                st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                st.markdown("#### ⚽ Who scores first?")
                saved_first_raw = str(m_row.get(f'{user}_FirstScorer', "")).strip()
                if saved_first_raw == "No Goal":
                    saved_first_display = "No Goal (0-0)"
                elif saved_first_raw:
                    saved_first_display = clean_country_name(saved_first_raw)
                else:
                    saved_first_display = None
                q1_options = [home_clean, away_clean, "No Goal (0-0)"]
                q1_first = st.radio("Select Team:", q1_options, index=saved_index(q1_options, saved_first_display), key=f"q1_{m_id}_{user}")
                st.markdown("</div>", unsafe_allow_html=True)

                q2_gap = None
                q2_home_score = None
                q2_away_score = None
                st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                if qf_plus:
                    st.markdown("#### 🔢 What's the exact score? (20 pts)")
                    st.caption("Final score after 90 mins + extra time — before any penalty shootout.")
                    if q1_first == "No Goal (0-0)":
                        q2_home_score, q2_away_score = 0, 0
                        st.info("🔒 You picked No Goal — score is automatically locked to **0-0**! Already locked in for you — worth **20 pts** if that's the actual result. 🎯")
                    else:
                        # Prefer this user's already-saved exact score, if they've submitted
                        # one before - otherwise fall back to the simple "scoring team can't
                        # be 0" default. This only matters the FIRST time this exact widget
                        # key is rendered (i.e. right when you switch to this user); if they
                        # then actively change their Q1 pick during this session, resetting to
                        # the simple 1/0 default (handled below via score_key_suffix) is still
                        # correct, since an old saved score wouldn't match a newly-changed pick.
                        saved_home_score_raw = str(m_row.get(f'{user}_HomeScore', "")).strip()
                        saved_away_score_raw = str(m_row.get(f'{user}_AwayScore', "")).strip()
                        if saved_home_score_raw != "" and saved_away_score_raw != "" and saved_first_display == q1_first:
                            try:
                                default_home_score = int(float(saved_home_score_raw))
                                default_away_score = int(float(saved_away_score_raw))
                            except ValueError:
                                default_home_score = 1 if q1_first == home_clean else 0
                                default_away_score = 1 if q1_first == away_clean else 0
                        else:
                            # Default the scoring team's box to 1 (their goal tally can't be 0
                            # since they were picked to score first) - still fully editable.
                            default_home_score = 1 if q1_first == home_clean else 0
                            default_away_score = 1 if q1_first == away_clean else 0
                        # IMPORTANT: the key includes q1_first AND user. Streamlit only honours
                        # the `value=` argument the FIRST time a given key is rendered - on every
                        # rerun after that, it silently keeps whatever's already in session
                        # state for that key and ignores `value=` entirely. Without user in the
                        # key, switching between people would leave the score boxes showing
                        # whichever user was last edited instead of resetting per-user; without
                        # q1_first in the key, switching your "who scores first" pick would leave
                        # the score boxes stuck showing the OLD default instead of updating.
                        score_key_suffix = q1_first if q1_first else "none"
                        sc_col1, sc_col2 = st.columns(2)
                        with sc_col1:
                            q2_home_score = st.number_input(f"{home_clean} Score", min_value=0, max_value=20, step=1, value=default_home_score, key=f"q2home_{m_id}_{user}_{score_key_suffix}")
                        with sc_col2:
                            q2_away_score = st.number_input(f"{away_clean} Score", min_value=0, max_value=20, step=1, value=default_away_score, key=f"q2away_{m_id}_{user}_{score_key_suffix}")
                        if q2_home_score == 0 and q2_away_score == 0:
                            st.info("🔫 So you think it's going all the way to a penalty shootout? Bold call!")

                        # Live cross-check, shown immediately rather than only at submit time -
                        # you were picked to score first, so your own score can't be 0.
                        if q1_first == home_clean and q2_home_score == 0:
                            st.error(f"❌ You picked {home_clean} to score first, so their score can't be 0 — bump it up to at least 1.")
                        elif q1_first == away_clean and q2_away_score == 0:
                            st.error(f"❌ You picked {away_clean} to score first, so their score can't be 0 — bump it up to at least 1.")
                else:
                    st.markdown("#### 📏 What's the goal gap when the final whistle blows?")
                    st.caption("Count the difference in goals after 90 mins + extra time — but NOT penalty shootouts. So if it's 2-1 after extra time, the gap is 1.")
                    if q1_first == "No Goal (0-0)":
                        q2_gap = "0"
                        st.info("🔒 You picked No Goal — so your goal gap is automatically locked to **0**! No goals = no difference. If the match ends 0-0 and goes to a penalty shootout, you'll still earn your **10 pts** for the goal gap — it's already locked in for you, no need to pick anything! 🎯")
                    else:
                        saved_gap = str(m_row.get(f'{user}_GoalGap', "")).strip()
                        gap_options = ["0", "1", "2", "3+"]
                        q2_gap = st.radio("Select Goal Gap:", gap_options, index=saved_index(gap_options, saved_gap), key=f"q2_{m_id}_{user}")
                        if q2_gap == "0":
                            st.info("🔫 So you think it's going all the way to a penalty shootout? Bold call!")
                st.markdown("</div>", unsafe_allow_html=True)

                q4_progression_pick = None
                if sf_plus:
                    st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                    progression_max = max([e['points'] for e in progression_ladder], default=0)
                    st.markdown(f"#### 🏁 Method of progression — who wins it, and in which stage? (up to {progression_max} pts)")
                    if not progression_ladder:
                        st.warning("⚠️ No progression odds found for this match — check Progression_Data in Match_Odds_Feed.")
                    elif q2_home_score is None or q2_away_score is None:
                        st.caption("👆 Enter your exact score above first — this narrows down to the options that actually still make sense.")
                    else:
                        # This is entirely dictated by the exact score just entered, not by
                        # who scored first: a draw at this point (AET, before pens) can ONLY
                        # mean it's going to penalties - nobody could have won yet. A non-draw
                        # means someone already won outright, so PK is impossible and only that
                        # winning team's NT/ET options make sense.
                        if q2_home_score == q2_away_score:
                            eligible_progression = [e for e in progression_ladder if e["stage_code"] == "PK"]
                            st.caption(f"Your score is a draw after ET — that can only mean penalties. Showing PK options only.")
                        elif q2_home_score > q2_away_score:
                            eligible_progression = [e for e in progression_ladder if e["team"] == home_clean and e["stage_code"] in ("NT", "ET")]
                            st.caption(f"You predicted {home_clean} winning outright — showing {home_clean}'s NT/ET options only (no shootout needed if someone's already ahead).")
                        else:
                            eligible_progression = [e for e in progression_ladder if e["team"] == away_clean and e["stage_code"] in ("NT", "ET")]
                            st.caption(f"You predicted {away_clean} winning outright — showing {away_clean}'s NT/ET options only (no shootout needed if someone's already ahead).")

                        prog_label_to_entry = {}
                        prog_option_labels = ["Select..."]
                        for e in eligible_progression:
                            label = f"{temp_emoji(e['rank_fraction'])} {e['team']} wins in {e['stage_label']} — {e['points']} pts"
                            prog_option_labels.append(label)
                            prog_label_to_entry[label] = e

                        saved_progression = str(m_row.get(f'{user}_ProgressionPick', "")).strip()
                        prog_default_index = 0
                        for idx, lbl in enumerate(prog_option_labels):
                            entry_check = prog_label_to_entry.get(lbl)
                            if entry_check and f"{entry_check['team']} {entry_check['stage_label']}" == saved_progression:
                                prog_default_index = idx
                                break
                        # Key includes the eligibility bucket (draw/home/away) AND user, so the
                        # picker resets cleanly both when the exact score changes and when
                        # switching between users.
                        prog_bucket = "draw" if q2_home_score == q2_away_score else ("home" if q2_home_score > q2_away_score else "away")
                        prog_key = f"q4prog_{m_id}_{user}_{prog_bucket}"
                        picked_prog_label = st.selectbox("Pick who wins it and how:", prog_option_labels, index=prog_default_index, key=prog_key)
                        if picked_prog_label != "Select...":
                            entry = prog_label_to_entry[picked_prog_label]
                            q4_progression_pick = f"{entry['team']} {entry['stage_label']}"
                    st.markdown("</div>", unsafe_allow_html=True)

                q3_adv = None
                if not qf_plus:
                    st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                    st.markdown("#### 🏆 Which team advances to the next round?")
                    saved_qual_raw = str(m_row.get(f'{user}_Qualifier', "")).strip()
                    saved_qual_display = clean_country_name(saved_qual_raw) if saved_qual_raw else None
                    q3_options = [home_clean, away_clean]
                    q3_adv = st.radio("Select Winner:", q3_options, index=saved_index(q3_options, saved_qual_display), key=f"q3_{m_id}_{user}")
                    st.markdown("</div>", unsafe_allow_html=True)

                # For QF+, "no goal" is driven by the exact score prediction itself (Q2), not
                # the Who-scores-first radio, since those two answers could otherwise drift out
                # of sync. For Round of 16-only matches, Q1 is still the source of truth.
                qf_zero_zero = qf_plus and (q2_home_score == 0 and q2_away_score == 0)

                q4_time = None
                q5_method = None
                if round16_plus:
                    st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                    q4_points_label = "10 pts" if qf_plus else "20 pts"
                    st.markdown(f"#### ⏱️ What time does the 1st goal go in? ({q4_points_label})")
                    time_locked = qf_zero_zero if qf_plus else (q1_first == "No Goal (0-0)")
                    if time_locked:
                        q4_time = "No Goal"
                        st.info(f"🔒 No goals predicted — Time of 1st Goal is automatically locked to **No Goal** (still worth **{q4_points_label}** if that's the actual result).")
                    else:
                        bracket_options = QF_TIME_BRACKET_OPTIONS if qf_plus else TIME_BRACKET_OPTIONS
                        saved_time = str(m_row.get(f'{user}_TimeOfFirstGoal', "")).strip()
                        q4_full_options = ["Select bracket..."] + bracket_options
                        q4_default_index = q4_full_options.index(saved_time) if saved_time in bracket_options else 0
                        q4_time = st.selectbox("Select time bracket:", q4_full_options, index=q4_default_index, key=f"q4_{m_id}_{user}")
                        if q4_time == "Select bracket...":
                            q4_time = None
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                    st.markdown("#### 🎯 How does the 1st goal happen?")
                    if time_locked or q4_time == "No Goal":
                        q5_method = "No Goal"
                        st.info("🔒 Locked to **No Goal** (still worth **10 pts** if that's the actual result).")
                    else:
                        saved_method = str(m_row.get(f'{user}_MethodOfFirstGoal', "")).strip()
                        q5_method = st.radio("Select method:", METHOD_OPTIONS, index=saved_index(METHOD_OPTIONS, saved_method), key=f"q5_{m_id}_{user}")
                    st.markdown("</div>", unsafe_allow_html=True)

                q6_pick = None
                if qf_plus:
                    st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                    st.markdown("#### 🏃🔥 Who scores anytime? (higher risk = higher reward!)")
                    st.caption("Any goal in Normal Time or Extra Time counts — penalty shootout goals don't count.")
                    if not scorer_ladder:
                        st.warning("⚠️ No scorer odds found for this match — check First_Scorer_Data in Match_Odds_Feed.")
                    elif qf_zero_zero:
                        q6_pick = "No Goal"
                        st.info(f"🔒 You predicted 0-0 — automatically locked to **No Goal** (worth **{Q6_NO_GOAL_POINTS} pts** if the actual result is also 0-0 — a true scoreless draw is rarer than even the biggest longshot player scoring, so it pays more than the usual catch-all).")
                    else:
                        home_scored = q2_home_score > 0
                        away_scored = q2_away_score > 0
                        if home_scored and not away_scored:
                            eligible_players = [e for e in scorer_ladder if e["country"] == home_clean]
                            st.caption(f"Only showing {home_clean} players — you predicted {away_clean} to score 0.")
                        elif away_scored and not home_scored:
                            eligible_players = [e for e in scorer_ladder if e["country"] == away_clean]
                            st.caption(f"Only showing {away_clean} players — you predicted {home_clean} to score 0.")
                        else:
                            eligible_players = scorer_ladder

                        # Set-piece cheat sheet - penalty/free-kick takers get extra chances to
                        # score, so it's a genuinely useful thing to weigh before picking. Only
                        # shows players that actually have a note entered against them.
                        players_with_notes = [(e, get_player_note(e["name"])) for e in eligible_players]
                        players_with_notes = [(e, note) for e, note in players_with_notes if note]
                        if players_with_notes:
                            with st.expander("📋 Set-piece cheat sheet (who takes penalties/free-kicks?)"):
                                for e, note in players_with_notes:
                                    st.markdown(f"**{e['name']}** ({e['country']}): {note}")

                        label_to_entry = {}
                        option_labels = ["Select player..."]
                        for e in eligible_players:
                            label = f"{temp_emoji(e['rank_fraction'])} {e['name']} ({e['country']}) — {e['points']} pts"
                            option_labels.append(label)
                            label_to_entry[label] = e

                        # Key includes which side(s) are eligible AND the user, so the picker
                        # resets cleanly both when the exact-score prediction changes and when
                        # switching between different users.
                        q6_key = f"q6_{m_id}_{user}_{int(home_scored)}_{int(away_scored)}"
                        saved_scorer = str(m_row.get(f'{user}_NominatedScorer', "")).strip()
                        q6_default_index = 0
                        for idx, lbl in enumerate(option_labels):
                            entry_check = label_to_entry.get(lbl)
                            if entry_check and entry_check["name"] == saved_scorer:
                                q6_default_index = idx
                                break
                        picked_label = st.selectbox("Pick a player:", option_labels, index=q6_default_index, key=q6_key)
                        if picked_label == "Select player...":
                            q6_pick = None
                        else:
                            entry = label_to_entry[picked_label]
                            q6_pick = entry["name"]
                            photo = get_player_photo(entry["name"])
                            if photo:
                                st.image(photo, width=100, caption=f"{entry['name']} ({entry['country']})")
                            note = get_player_note(entry["name"])
                            if note:
                                st.caption(f"📋 {note}")
                    st.markdown("</div>", unsafe_allow_html=True)

                if qf_plus:
                    num_questions_label = 7 if sf_plus else 5
                    required_answered = bool(
                        q1_first and (q2_home_score is not None and q2_away_score is not None)
                        and q4_time and q5_method and q6_pick
                        and (q4_progression_pick if sf_plus else True)
                    )

                    # Cross-question validation: the "who scores first" pick and the exact
                    # score prediction must agree with each other.
                    qf_consistency_error = None
                    if q1_first == home_clean and q2_home_score == 0:
                        qf_consistency_error = f"❌ You picked {home_clean} to score first, so their score can't be 0!"
                    elif q1_first == away_clean and q2_away_score == 0:
                        qf_consistency_error = f"❌ You picked {away_clean} to score first, so their score can't be 0!"
                else:
                    qf_consistency_error = None

                if round16_plus and not qf_plus:
                    num_questions_label = 5
                    required_answered = bool(q1_first and q2_gap and q3_adv and q4_time and q5_method)
                elif not qf_plus and not round16_plus:
                    num_questions_label = 3
                    required_answered = bool(q1_first and q2_gap and q3_adv)

                if st.button("Lock Prediction In"):
                    if is_locked:
                        st.error("This match has already kicked off! Changing predictions is locked.")
                    elif not required_answered:
                        st.warning(f"⚠️ Please answer all {num_questions_label} questions before submitting!")
                    elif qf_consistency_error:
                        st.error(qf_consistency_error)
                    else:
                        try:
                            headers = get_headers(target_ws, target_ws.title)
                            first_col_idx = headers.index(f"{user}_FirstScorer") + 1
                            sheet_row_num = int(m_idx) + 2
                            
                            sheet_first_val = m_row['Home_Team'] if q1_first == home_clean else (m_row['Away_Team'] if q1_first == away_clean else "No Goal")
                            target_ws.update_cell(sheet_row_num, first_col_idx, sheet_first_val)

                            if not qf_plus:
                                qual_col_idx = headers.index(f"{user}_Qualifier") + 1
                                sheet_adv_val = m_row['Home_Team'] if q3_adv == home_clean else m_row['Away_Team']
                                target_ws.update_cell(sheet_row_num, qual_col_idx, sheet_adv_val)

                            if qf_plus:
                                home_score_idx = headers.index(f"{user}_HomeScore") + 1
                                away_score_idx = headers.index(f"{user}_AwayScore") + 1
                                target_ws.update_cell(sheet_row_num, home_score_idx, q2_home_score)
                                target_ws.update_cell(sheet_row_num, away_score_idx, q2_away_score)
                            else:
                                gap_col_idx = headers.index(f"{user}_GoalGap") + 1
                                target_ws.update_cell(sheet_row_num, gap_col_idx, q2_gap)

                            if round16_plus:
                                time_col_idx = headers.index(f"{user}_TimeOfFirstGoal") + 1
                                method_col_idx = headers.index(f"{user}_MethodOfFirstGoal") + 1
                                target_ws.update_cell(sheet_row_num, time_col_idx, q4_time)
                                target_ws.update_cell(sheet_row_num, method_col_idx, q5_method)

                            if qf_plus:
                                scorer_col_idx = headers.index(f"{user}_NominatedScorer") + 1
                                target_ws.update_cell(sheet_row_num, scorer_col_idx, q6_pick)

                            if sf_plus:
                                progression_col_idx = headers.index(f"{user}_ProgressionPick") + 1
                                target_ws.update_cell(sheet_row_num, progression_col_idx, q4_progression_pick)
                            
                            st.cache_data.clear()
                            st.toast("✅ Prediction saved!", icon="✅")
                            st.rerun()
                        except Exception as write_err:
                            st.error(f"Failed to update spreadsheet: {write_err}")

# ==========================================
# TAB 3: ADMIN ENGINE
# ==========================================
with tab3:
    st.subheader("Admin Scoring Panel")
    admin_password = st.text_input("Enter Password", type="password")

    if admin_password == "kmart20":
        st.success("Welcome back.")
        
        # Combine schedules to find matches to finalize
        active_group = matches_df[matches_df['Status'] != 'Completed'] if not matches_df.empty else pd.DataFrame()
        active_ko = knockout_df[knockout_df['Status'] != 'Completed'] if not knockout_df.empty else pd.DataFrame()
        active_combined = pd.concat([active_group, active_ko], ignore_index=True)

        if active_combined.empty:
            st.info("All matches finalized!")
        else:
            match_options = active_combined.apply(lambda r: f"Match {r['Match_ID']}: {clean_country_name(r['Home_Team'])} vs {clean_country_name(r['Away_Team'])}", axis=1).tolist()
            selected_match_str = st.selectbox("Select match to calculate points:", match_options)

            selected_id = selected_match_str.split(":")[0].replace("Match ", "").strip()
            stage = get_match_stage(selected_id)
            
            target_df = knockout_df if stage == "Knockout" else matches_df
            target_ws = knockout_worksheet if stage == "Knockout" else matches_worksheet
            
            m_idx = target_df[target_df['Match_ID'] == selected_id].index[0]
            match_row = target_df.loc[m_idx]

            home_clean = clean_country_name(match_row['Home_Team'])
            away_clean = clean_country_name(match_row['Away_Team'])
            
            st.divider()
            
            calculated_points_delta = {}
            actual_score_str = ""
            actual_first_val = ""
            actual_gap_val = ""
            actual_qual_val = ""

            # --- GROUP STAGE ADMIN ---
            if stage == "Group":
                st.markdown("### 1. Enter Actual Match Result (Group Stage)")
                col1, col2 = st.columns(2)
                with col1: act_home = st.number_input(f"Actual {home_clean} Score", min_value=0, step=1, value=0, key="ah")
                with col2: act_away = st.number_input(f"Actual {away_clean} Score", min_value=0, step=1, value=0, key="aa")

                if act_home == 0 and act_away == 0: act_first_options = ["No Goal"]
                elif act_home > 0 and act_away == 0: act_first_options = [home_clean]
                elif act_home == 0 and act_away > 0: act_first_options = [away_clean]
                else: act_first_options = [home_clean, away_clean]

                act_first_selection = st.selectbox("Who scored first in reality?", act_first_options)
                actual_score_str = f"{act_home}-{act_away}"
                actual_first_val = match_row['Home_Team'] if act_first_selection == home_clean else (match_row['Away_Team'] if act_first_selection == away_clean else "No Goal")

                st.markdown("### Points Preview:")
                for p in participants:
                    p_first = str(match_row.get(f'{p}_FirstScorer', "")).strip()
                    p_score = str(match_row.get(f'{p}_Score', "")).strip()
                    
                    earned = 0
                    if p_score == actual_score_str: earned += 10
                    if p_first.lower() == str(actual_first_val).lower() and p_first != "": earned += 10
                    calculated_points_delta[p] = earned
                    
                    if earned == 20:
                        st.markdown(
                            f"<div style='background:linear-gradient(90deg,#FFD700,#FF6B00); padding:10px 16px; "
                            f"border-radius:10px; margin:4px 0; font-weight:bold; color:#1a1a1a; "
                            f"box-shadow:0 2px 6px rgba(0,0,0,0.25);'>"
                            f"🔥🎉 <strong>{p}</strong> MAXED OUT! 20/20 pts 🎉🔥 "
                            f"<span style='font-weight:normal;'>(Predicted {p_score} & {clean_country_name(p_first)})</span>"
                            f"</div>", unsafe_allow_html=True
                        )
                    else:
                        st.write(f"**{p}:** {earned} pts (Predicted {p_score} & {clean_country_name(p_first)})")

            # --- KNOCKOUT STAGE ADMIN ---
            else:
                st.markdown("### 1. Enter Actual Match Result (Knockout Stage)")
                round16_plus_admin = is_round16_plus(selected_id)
                qf_plus_admin = is_qf_plus(selected_id)
                sf_plus_admin = is_sf_plus(selected_id)

                act_first_selection = st.radio("1. Who scored first?", [home_clean, away_clean, "No Goal (0-0)"])

                actual_first_val = match_row['Home_Team'] if act_first_selection == home_clean else (match_row['Away_Team'] if act_first_selection == away_clean else "No Goal")
                actual_qual_val = None

                if qf_plus_admin:
                    st.markdown("##### 2. Exact final score (before penalties)")
                    ac_col1, ac_col2 = st.columns(2)
                    with ac_col1:
                        actual_home_score = st.number_input(f"{home_clean} Score", min_value=0, max_value=20, step=1, value=0, key="admin_home_score")
                    with ac_col2:
                        actual_away_score = st.number_input(f"{away_clean} Score", min_value=0, max_value=20, step=1, value=0, key="admin_away_score")
                    actual_gap_val = None
                    # No "Team Advances" question for QF+ — exact score already determines the winner.
                    actual_qual_val = None
                else:
                    actual_gap_val = st.radio("2. What was the goal gap at full time (90 min + ET, before pens)?", ["0", "1", "2", "3+"])
                    actual_home_score = actual_away_score = None

                    act_adv_selection = st.radio("3. Who Advanced?", [home_clean, away_clean])
                    actual_qual_val = match_row['Home_Team'] if act_adv_selection == home_clean else match_row['Away_Team']

                actual_time_val = "No Goal"
                actual_method_val = "No Goal"
                if round16_plus_admin:
                    time_method_prefix = "3" if qf_plus_admin else "4"
                    if act_first_selection == "No Goal (0-0)":
                        st.info("🔒 No Goal selected — Time & Method of 1st goal auto-locked to 'No Goal'.")
                    elif qf_plus_admin:
                        actual_time_val = st.radio(f"{time_method_prefix}. What time did the 1st goal go in?", QF_TIME_BRACKET_OPTIONS)
                        actual_method_val = st.radio(f"{int(time_method_prefix) + 1}. How did the 1st goal happen?", METHOD_OPTIONS)
                    else:
                        act_minute = st.number_input(f"{time_method_prefix}. Actual minute of the 1st goal (enter 45 for 1st-half injury time, 90 for 2nd-half injury time):", min_value=0, max_value=120, step=1, value=0)
                        actual_time_val = map_minute_to_bracket(act_minute)
                        st.caption(f"→ Maps to bracket: **{actual_time_val}**")
                        actual_method_val = st.radio(f"{int(time_method_prefix) + 1}. How did the 1st goal happen?", METHOD_OPTIONS)

                # Anytime Scorer (QF+ only): admin selects EVERY player who scored during
                # Normal Time or Extra Time (penalty shootout goals don't count). Multiselect
                # since more than one player can score across the match.
                actual_q6_selected = []
                scorer_ladder_admin = []
                if qf_plus_admin:
                    st.markdown("##### 5. Who scored anytime? (Normal Time + Extra Time only — select every scorer)")
                    odds_row_admin = odds_df[odds_df['Match_ID'].astype(str) == str(selected_id)] if not odds_df.empty else pd.DataFrame()
                    if not odds_row_admin.empty:
                        scorer_ladder_admin = parse_scorer_ladder(str(odds_row_admin.iloc[0].get('First_Scorer_Data', '')))

                    if actual_home_score == 0 and actual_away_score == 0:
                        st.info("🔒 0-0 result — no anytime scorers possible.")
                    elif not scorer_ladder_admin:
                        st.warning("⚠️ No scorer odds found for this match — check First_Scorer_Data in Match_Odds_Feed.")
                    else:
                        label_to_entry_admin = {}
                        admin_option_labels = []
                        for e in scorer_ladder_admin:
                            label = f"{e['name']} ({e['country']}) — {e['points']} pts"
                            admin_option_labels.append(label)
                            label_to_entry_admin[label] = e
                        picked_admin_labels = st.multiselect("Select every player who scored (NT + ET):", admin_option_labels, key="admin_q6_multi")
                        actual_q6_selected = [label_to_entry_admin[lbl]["name"] for lbl in picked_admin_labels]

                # Method of Progression (SF+ only): single actual outcome - only one
                # team+stage combo can be true, so this is a straightforward radio, not
                # a multiselect like Anytime Scorer. Options narrowed by the actual exact
                # score, same draw/home/away logic as the user-facing picker.
                actual_progression_val = None
                progression_ladder_admin = []
                if sf_plus_admin:
                    st.markdown("##### 6. Method of progression — who actually won it, and in which stage?")
                    prog_row_admin = odds_df[odds_df['Match_ID'].astype(str) == str(selected_id)] if not odds_df.empty else pd.DataFrame()
                    if not prog_row_admin.empty:
                        progression_ladder_admin = parse_progression_ladder(str(prog_row_admin.iloc[0].get('Progression_Data', '')))

                    if not progression_ladder_admin:
                        st.warning("⚠️ No progression odds found for this match — check Progression_Data in Match_Odds_Feed.")
                    else:
                        if actual_home_score == actual_away_score:
                            eligible_progression_admin = [e for e in progression_ladder_admin if e["stage_code"] == "PK"]
                        elif actual_home_score > actual_away_score:
                            eligible_progression_admin = [e for e in progression_ladder_admin if e["team"] == home_clean and e["stage_code"] in ("NT", "ET")]
                        else:
                            eligible_progression_admin = [e for e in progression_ladder_admin if e["team"] == away_clean and e["stage_code"] in ("NT", "ET")]

                        prog_label_to_entry_admin = {}
                        prog_admin_labels = []
                        for e in eligible_progression_admin:
                            label = f"{e['team']} wins in {e['stage_label']} — {e['points']} pts"
                            prog_admin_labels.append(label)
                            prog_label_to_entry_admin[label] = e
                        picked_prog_admin_label = st.radio("Actual outcome:", prog_admin_labels, key="admin_progression")
                        actual_progression_val = f"{prog_label_to_entry_admin[picked_prog_admin_label]['team']} {prog_label_to_entry_admin[picked_prog_admin_label]['stage_label']}"

                st.markdown("### Points Preview:")
                if qf_plus_admin:
                    ladder_max_admin = max([e['points'] for e in scorer_ladder_admin], default=Q6_CATCHALL_POINTS)
                    q6_max_pts_admin = max(ladder_max_admin, Q6_NO_GOAL_POINTS)
                    progression_max_pts_admin = max([e['points'] for e in progression_ladder_admin], default=0) if sf_plus_admin else 0
                    max_pts_admin = 10 + 20 + 10 + 10 + q6_max_pts_admin + progression_max_pts_admin
                else:
                    max_pts_admin = 60 if round16_plus_admin else 30

                # Build a name -> points lookup for this match's Anytime Scorer ladder, used
                # to award each participant the points THEIR picked player was actually worth.
                q6_points_lookup = {e["name"]: e["points"] for e in scorer_ladder_admin} if qf_plus_admin else {}
                # Same idea for Progression: "Team Stage" string -> points.
                progression_points_lookup = {f"{e['team']} {e['stage_label']}": e["points"] for e in progression_ladder_admin} if sf_plus_admin else {}

                for p in participants:
                    p_first = str(match_row.get(f'{p}_FirstScorer', "")).strip()

                    earned = 0
                    if p_first.lower() == str(actual_first_val).lower() and p_first != "": earned += 10

                    if qf_plus_admin:
                        p_home_score = str(match_row.get(f'{p}_HomeScore', "")).strip()
                        p_away_score = str(match_row.get(f'{p}_AwayScore', "")).strip()
                        if (p_home_score != "" and p_away_score != ""
                                and str(actual_home_score) == p_home_score and str(actual_away_score) == p_away_score):
                            earned += 20
                        preview_line = f"First: {clean_country_name(p_first)} | Score: {p_home_score or '—'}-{p_away_score or '—'}"
                    else:
                        p_qual = str(match_row.get(f'{p}_Qualifier', "")).strip()
                        if p_qual.lower() == str(actual_qual_val).lower() and p_qual != "": earned += 10
                        p_gap = str(match_row.get(f'{p}_GoalGap', "")).strip()
                        if p_gap == str(actual_gap_val) and p_gap != "": earned += 10
                        preview_line = f"First: {clean_country_name(p_first)} | Gap: {p_gap} | Adv: {clean_country_name(p_qual)}"

                    if round16_plus_admin:
                        p_time = str(match_row.get(f'{p}_TimeOfFirstGoal', "")).strip()
                        p_method = str(match_row.get(f'{p}_MethodOfFirstGoal', "")).strip()
                        time_pts = 10 if qf_plus_admin else 20
                        if p_time == actual_time_val and p_time != "": earned += time_pts
                        if p_method == actual_method_val and p_method != "": earned += 10
                        preview_line += f" | Time: {p_time or '—'} | Method: {p_method or '—'}"

                    if qf_plus_admin:
                        p_q6 = str(match_row.get(f'{p}_NominatedScorer', "")).strip()
                        if p_q6 == Q6_NOGOAL_LABEL:
                            if not actual_q6_selected: earned += Q6_NO_GOAL_POINTS
                        elif p_q6 != "" and p_q6 in actual_q6_selected:
                            earned += q6_points_lookup.get(p_q6, 0)
                        preview_line += f" | Anytime Scorer: {p_q6 or '—'}"

                    if sf_plus_admin:
                        p_progression = str(match_row.get(f'{p}_ProgressionPick', "")).strip()
                        if p_progression != "" and actual_progression_val and p_progression == actual_progression_val:
                            earned += progression_points_lookup.get(p_progression, 0)
                        preview_line += f" | Progression: {p_progression or '—'}"

                    calculated_points_delta[p] = earned
                    
                    if earned == max_pts_admin:
                        st.markdown(
                            f"<div style='background:linear-gradient(90deg,#FF1E1E,#FFD700); padding:10px 16px; "
                            f"border-radius:10px; margin:4px 0; font-weight:bold; color:#1a1a1a; "
                            f"box-shadow:0 2px 6px rgba(0,0,0,0.25);'>"
                            f"🚀🏆 <strong>{p}</strong> PERFECT SCORE! {max_pts_admin}/{max_pts_admin} pts 🏆🚀 "
                            f"<span style='font-weight:normal;'>({preview_line})</span>"
                            f"</div>", unsafe_allow_html=True
                        )
                    else:
                        st.write(f"**{p}:** {earned} pts ({preview_line})")

            st.divider()

            if st.button("💾 Save & Finalize Match Results"):
                try:
                    with st.spinner("Updating Google Sheets & calculating points live..."):
                        sheet_row_num = int(m_idx) + 2
                        headers = get_headers(target_ws, target_ws.title)

                        # 1. Update Match Status
                        if "Status" in headers:
                            target_ws.update_cell(sheet_row_num, headers.index("Status") + 1, "Completed")
                        
                        # 2. Update Actual Results based on Stage
                        if "Actual_FirstScorer" in headers:
                            target_ws.update_cell(sheet_row_num, headers.index("Actual_FirstScorer") + 1, str(actual_first_val))
                            
                        if stage == "Group" and "Actual_Score" in headers:
                            target_ws.update_cell(sheet_row_num, headers.index("Actual_Score") + 1, actual_score_str)
                        elif stage == "Knockout":
                            qf_plus_save = is_qf_plus(selected_id)

                            # "Team Advances" (Qualifying_Team) is no longer a QF+ question —
                            # exact score already determines the winner, so skip this write.
                            if not qf_plus_save and "Qualifying_Team" in headers:
                                target_ws.update_cell(sheet_row_num, headers.index("Qualifying_Team") + 1, actual_qual_val)

                            if qf_plus_save:
                                if "Actual_HomeScore" in headers:
                                    target_ws.update_cell(sheet_row_num, headers.index("Actual_HomeScore") + 1, actual_home_score)
                                if "Actual_AwayScore" in headers:
                                    target_ws.update_cell(sheet_row_num, headers.index("Actual_AwayScore") + 1, actual_away_score)
                                if "Actual_NominatedScorer" in headers:
                                    # Multiple anytime scorers are possible - store as a
                                    # comma-joined string in the existing column so the sheet
                                    # structure doesn't need to change.
                                    actual_q6_str = ", ".join(actual_q6_selected) if actual_q6_selected else Q6_NOGOAL_LABEL
                                    target_ws.update_cell(sheet_row_num, headers.index("Actual_NominatedScorer") + 1, actual_q6_str)
                                if is_sf_plus(selected_id) and "Actual_ProgressionPick" in headers and actual_progression_val:
                                    target_ws.update_cell(sheet_row_num, headers.index("Actual_ProgressionPick") + 1, actual_progression_val)
                            elif "Actual_GoalGap" in headers:
                                target_ws.update_cell(sheet_row_num, headers.index("Actual_GoalGap") + 1, actual_gap_val)

                            if is_round16_plus(selected_id):
                                if "Actual_TimeOfFirstGoal" in headers:
                                    target_ws.update_cell(sheet_row_num, headers.index("Actual_TimeOfFirstGoal") + 1, actual_time_val)
                                if "Actual_MethodOfFirstGoal" in headers:
                                    target_ws.update_cell(sheet_row_num, headers.index("Actual_MethodOfFirstGoal") + 1, actual_method_val)

                            # 2b. Auto-update team_status: mark the losing team as eliminated.
                            # Not tracked for QF+ matches, since "Team Advances" no longer exists there.
                            if not qf_plus_save and team_status_worksheet is not None:
                                try:
                                    loser_raw = match_row['Away_Team'] if str(actual_qual_val).strip() == str(match_row['Home_Team']).strip() else match_row['Home_Team']
                                    loser_clean = clean_country_name(loser_raw)
                                    ts_headers = get_headers(team_status_worksheet, "team_status")
                                    for ts_idx, ts_row in team_status_df.reset_index(drop=True).iterrows():
                                        if str(ts_row.get('Team', '')).strip() == loser_clean:
                                            team_status_worksheet.update_cell(ts_idx + 2, ts_headers.index('Still_Alive') + 1, "FALSE")
                                            break
                                except Exception:
                                    pass  # non-critical — don't block the match save if this fails

                        # 3. Update Leaderboard
                        lead_headers = get_headers(leaderboard_worksheet, "leaderboard")
                        pts_col_idx = lead_headers.index("Points") + 1

                        for p, points_to_add in calculated_points_delta.items():
                            if points_to_add > 0:
                                for idx, l_row in leaderboard_df.reset_index(drop=True).iterrows():
                                    if str(l_row.get("Participant")).strip() == p:
                                        l_sheet_row = idx + 2
                                        current_pts = int(l_row.get("Points", 0))
                                        leaderboard_worksheet.update_cell(l_sheet_row, pts_col_idx, current_pts + points_to_add)
                                        break

                        st.cache_data.clear()
                        st.toast("🏆 Match finalized! Leaderboard updated.", icon="🏆")
                        st.rerun()

                except Exception as write_err:
                    st.error(f"Database sync failed: {write_err}")

        # ==========================================
        # ONCE-OFF FINALIZATION (Golden Boot + Champion) — run once, at the Final
        # ==========================================
        st.divider()
        with st.expander("🏅 Finalize Once-Off Predictions (Golden Boot + Champion) — run this at the Final"):
            if once_off_df.empty or golden_boot_df.empty:
                st.warning("once_off_predictions or golden_boot_candidates tab not found/empty.")
            else:
                st.caption("Enter the actual tournament outcomes below. This awards 50 pts each and only needs to be run once, after the Final.")
                actual_gb_winner = st.selectbox("Actual Golden Boot Winner:", ["Select player..."] + golden_boot_df['Player_Name'].tolist())
                champ_country_options, _champ_raw_lookup_admin = build_champion_options(matches_df, team_status_df)
                actual_champion = st.selectbox("Actual World Cup Champion:", ["Select country..."] + champ_country_options)

                if actual_gb_winner != "Select player..." and actual_champion != "Select country...":
                    st.markdown("### Once-Off Points Preview:")
                    once_off_points_delta = {}
                    for _, r in once_off_df.iterrows():
                        p = str(r.get("Participant", "")).strip()
                        p_gb = str(r.get("GoldenBoot_Pick", "")).strip()
                        p_champ = clean_country_name(str(r.get("Champion_Pick", ""))).strip()
                        earned = 0
                        if p_gb == actual_gb_winner and p_gb != "": earned += 50
                        if p_champ.lower() == actual_champion.lower() and p_champ != "": earned += 50
                        once_off_points_delta[p] = earned
                        st.write(f"**{p}:** {earned} pts (Golden Boot: {p_gb or '—'} | Champion: {p_champ or '—'})")

                    if st.button("💾 Save & Award Once-Off Points"):
                        try:
                            oo_headers = get_headers(once_off_worksheet, "once_off_predictions")
                            lead_headers = get_headers(leaderboard_worksheet, "leaderboard")
                            pts_col_idx = lead_headers.index("Points") + 1

                            for idx, r in once_off_df.reset_index(drop=True).iterrows():
                                p = str(r.get("Participant", "")).strip()
                                row_num = idx + 2
                                p_gb = str(r.get("GoldenBoot_Pick", "")).strip()
                                p_champ = clean_country_name(str(r.get("Champion_Pick", ""))).strip()
                                gb_pts = 50 if (p_gb == actual_gb_winner and p_gb != "") else 0
                                champ_pts = 50 if (p_champ.lower() == actual_champion.lower() and p_champ != "") else 0

                                if "GoldenBoot_Locked" in oo_headers:
                                    once_off_worksheet.update_cell(row_num, oo_headers.index("GoldenBoot_Locked") + 1, "TRUE")
                                if "Champion_Locked" in oo_headers:
                                    once_off_worksheet.update_cell(row_num, oo_headers.index("Champion_Locked") + 1, "TRUE")
                                if "GoldenBoot_Points" in oo_headers:
                                    once_off_worksheet.update_cell(row_num, oo_headers.index("GoldenBoot_Points") + 1, gb_pts)
                                if "Champion_Points" in oo_headers:
                                    once_off_worksheet.update_cell(row_num, oo_headers.index("Champion_Points") + 1, champ_pts)

                                total_add = gb_pts + champ_pts
                                if total_add > 0:
                                    for l_idx, l_row in leaderboard_df.reset_index(drop=True).iterrows():
                                        if str(l_row.get("Participant")).strip() == p:
                                            l_sheet_row = l_idx + 2
                                            current_pts = int(l_row.get("Points", 0))
                                            leaderboard_worksheet.update_cell(l_sheet_row, pts_col_idx, current_pts + total_add)
                                            break

                            st.cache_data.clear()
                            st.toast("🏅 Once-off points awarded!", icon="🏅")
                            st.rerun()
                        except Exception as write_err:
                            st.error(f"Failed to save once-off results: {write_err}")

    elif admin_password:
        st.error("Incorrect password.")
