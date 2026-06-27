import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import gspread
import re
import random
import urllib.request
import xml.etree.ElementTree as ET
from google.oauth2.service_account import Credentials

# --- NEW IMPORT FOR GOOGLE AI STUDIO ---
from google import genai

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
    else:
        facts["home_best_stage"] = facts["away_best_stage"] = None
        facts["home_best_stage_pct"] = facts["away_best_stage_pct"] = None
        facts["overall_favourite_team"] = facts["overall_favourite_stage"] = facts["overall_favourite_pct"] = None

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
# GOOGLE AI STUDIO NARRATIVE GENERATOR
# ==========================================
@st.cache_data(ttl=1800) # Caches the story for 30 mins so it doesn't spam the API
def generate_kid_friendly_narrative(facts: dict):
    home, away = facts["home"], facts["away"]

    scorer_tier = facts.get("scorer_tier", 1)

    facts_block = f"""
    - Chance to qualify: {home} {facts['qualify_home_pct']}% vs {away} {facts['qualify_away_pct']}%
    - {home}'s best path to winning this match: {facts['home_best_stage']} ({facts['home_best_stage_pct']}% chance)
    - {away}'s best path to winning this match: {facts['away_best_stage']} ({facts['away_best_stage_pct']}% chance)
    - Overall single most likely result: {facts['overall_favourite_team']} winning in {facts['overall_favourite_stage']} ({facts['overall_favourite_pct']}% chance)
    - {home}'s most likely first scorer: {facts['home_top_scorer']} ({facts['home_top_scorer_pct']}% chance)
    - {away}'s most likely first scorer: {facts['away_top_scorer']} ({facts['away_top_scorer_pct']}% chance)
    """
    if scorer_tier == 2 and facts.get("home_second_scorer") and facts.get("away_second_scorer"):
        facts_block += f"""
    - {home}'s second most likely first scorer: {facts['home_second_scorer']} ({facts['home_second_scorer_pct']}% chance)
    - {away}'s second most likely first scorer: {facts['away_second_scorer']} ({facts['away_second_scorer_pct']}% chance)
    """

    scorer_instruction = (
        f"""Both teams' most likely first scorer, with their percentage - e.g. "{facts.get('home_top_scorer')} is
           favoured to score first at {facts.get('home_top_scorer_pct')}%, just ahead of {facts.get('away_top_scorer')}
           at {facts.get('away_top_scorer_pct')}%" (or similar, in your own words)."""
        if scorer_tier == 1 or not facts.get("home_second_scorer")
        else
        f"""Each team's TOP TWO most likely first scorers, with percentages - mention {facts.get('home_top_scorer')}
           and {facts.get('home_second_scorer')} for {home}, and {facts.get('away_top_scorer')} and
           {facts.get('away_second_scorer')} for {away}, each with their percentage chance."""
    )

    prompt = f"""
    You are a fun, casual, kid-friendly Aussie sports commentator. Write a short, exciting pre-match scoop for kids
    about this World Cup knockout match. This is for a kids' prediction game where players guess: (1) who scores
    first, (2) whether it goes to a penalty shootout, (3) who qualifies.

    MATCH: {home} vs {away}

    Here are the FINAL, ALREADY-CALCULATED percentage facts you must use (do not do any maths yourself, do not
    change these numbers or invent new ones, just narrate them in a fun way):
    {facts_block}

    RULES:
    - You MUST mention BOTH sides for every category, never just the favourite alone:
        1. Both teams' chance to qualify (use both percentages).
        2. Both teams' best path to winning (their stage + percentage) - e.g. compare {home}'s best path against
           {away}'s best path. Only call out a penalty shootout as a real chance if "Penalties" is actually one of
           the best-path stages mentioned above for either team - otherwise don't bring penalties up.
        3. {scorer_instruction}
    - EVERY time you mention a player's name, their country must appear with it in the same breath - either as
      "PlayerName (Country)", or "PlayerName for Country", or "Country's PlayerName" - pick whichever reads most
      naturally in the sentence, but never write a player's name on its own without their country attached
      somewhere nearby in that sentence.
    - Use the percentages given, e.g. "32%", as the way of expressing chance - never the words "odds", "bet",
      "stake", "wager", "favourite to win money", or anything gambling-related. Frame it purely as "chance to
      qualify" / "favoured to score first" / "most likely outcome" etc, kid-friendly.
    - Use **bold** (markdown) around player names, team names, and key percentages to make it pop visually.
    - Use 3-5 relevant emojis scattered through the text (⚽🏆🔥🎯👀 etc) - make it feel hyped and fun, not flat.
    - Write 3-4 short, punchy sentences in casual Aussie kid-commentator style.
    - DO NOT always open with the same greeting or the same slang. Randomly pick a different way to open and a
      different way to refer to "the experts"/percentages each time - mix it up across calls, never default to
      the same pair of phrases. Invent your own wording each time rather than rotating a fixed list.
    - Never say "data", "stats", "JSON", or anything technical - it should read like a real commentator hyping
      up a match, just backed by real numbers presented in a fun way.

    Write the match story now:
    """
    try:
        client = genai.Client(api_key=st.secrets["GOOGLE_API_KEY"])
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                "temperature": 1.1,   # higher = more variety, less "scripted" feel
                "max_output_tokens": 500,
                "thinking_config": {"thinking_budget": 0},  # turn off internal thinking so tokens go to the actual reply
            }
        )
        return response.text.strip()
    except Exception as e:
        # TEMP DEBUG: surfacing the real error so we can see exactly what's failing.
        # Remove this st.error line once confirmed working, and revert to a quiet fallback.
        st.error(f"DEBUG - Gemini call failed: {repr(e)}")
        return f"Hold onto your hats! The stats van is running late, but {home} vs {away} is going to be an absolute ripper of a match! ⚽"

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

try:
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # Force a fresh pull of all worksheets
    all_worksheets = {ws.title.strip().lower(): ws for ws in sh.worksheets()}
    
    if "knockout_predictions" not in all_worksheets:
        st.error(f"🔍 I still can't see the tab! Here are the tabs I DO see: {list(all_worksheets.keys())}")
        st.stop()
        
    matches_worksheet = all_worksheets["matches"]
    knockout_worksheet = all_worksheets["knockout_predictions"]
    leaderboard_worksheet = all_worksheets["leaderboard"]
    
    # NEW: Safely pull the Match_Odds_Feed if it exists
    odds_worksheet = all_worksheets.get("match_odds_feed")
    
    matches_df = pd.DataFrame(matches_worksheet.get_all_records())
    knockout_df = pd.DataFrame(knockout_worksheet.get_all_records())
    leaderboard_df = pd.DataFrame(leaderboard_worksheet.get_all_records())
    odds_df = pd.DataFrame(odds_worksheet.get_all_records()) if odds_worksheet else pd.DataFrame()

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
participants = ['ND', 'CD', 'SB', 'GB', 'LS', 'HD']

tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "⚽ Submit Predictions", "🔒 Admin Engine"])

# ==========================================
# TAB 1: LEADERBOARD
# ==========================================
with tab1:
    st.subheader("Current Standings")
    leaderboard_sorted = leaderboard_df.sort_values(by="Points", ascending=False).reset_index(drop=True)
    st.dataframe(
        leaderboard_sorted,
        use_container_width=True, hide_index=True,
        column_config={"Participant": "Player", "Points": st.column_config.NumberColumn("Total Points", format="%d pts")}
    )
    st.divider()
    st.markdown("🎁 **Prize:** $20 Kmart Gift Card up for grabs.")

# ==========================================
# TAB 2: SUBMIT PREDICTIONS
# ==========================================
with tab2:
    st.subheader("Log or Edit Your Predictions")
    user = st.selectbox("Who are you?", ["Select your name..."] + participants)

    if user != "Select your name...":
        current_time = get_current_aest()
        today = current_time.date()

        st.markdown(f"### Your Active Predictions Overview ({user})")
        overview_rows = []
        
        # Pull active Group matches
        active_group = matches_df[matches_df['Status'] != 'Completed'] if not matches_df.empty else pd.DataFrame()
        for _, row in active_group.iterrows():
            m_id = row['Match_ID']
            first_scorer = str(row.get(f'{user}_FirstScorer', "")).strip()
            score = str(row.get(f'{user}_Score', "")).strip()
            
            summary = "Not Submitted"
            if first_scorer or score:
                summary = f"First: {first_scorer or '?'} | Score: {score or '?'}"
                
            overview_rows.append({
                "Match ID": m_id,
                "🏳️ Home": get_flag_url(row['Home_Team']),
                "Home Team": clean_country_name(row['Home_Team']),
                "Away Team": clean_country_name(row['Away_Team']),
                "🏳️ Away": get_flag_url(row['Away_Team']),
                "Kickoff (AEST)": row['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p'),
                "Your Prediction": summary
            })
            
        # Pull active Knockout matches
        active_ko = knockout_df[knockout_df['Status'] != 'Completed'] if not knockout_df.empty else pd.DataFrame()
        for _, row in active_ko.iterrows():
            m_id = row['Match_ID']
            first_scorer = str(row.get(f'{user}_FirstScorer', "")).strip()
            penalty = str(row.get(f'{user}_Penalty', "")).strip()
            qualifier = str(row.get(f'{user}_Qualifier', "")).strip()
            
            summary = "Not Submitted"
            if first_scorer or penalty or qualifier:
                summary = f"First: {first_scorer or '?'} | Pens: {penalty or '?'} | Adv: {qualifier or '?'}"
                
            overview_rows.append({
                "Match ID": m_id,
                "🏳️ Home": get_flag_url(row['Home_Team']),
                "Home Team": clean_country_name(row['Home_Team']),
                "Away Team": clean_country_name(row['Away_Team']),
                "🏳️ Away": get_flag_url(row['Away_Team']),
                "Kickoff (AEST)": row['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p'),
                "Your Prediction": summary
            })

        if overview_rows:
            st.dataframe(
                pd.DataFrame(overview_rows), use_container_width=True, hide_index=True,
                column_config={"🏳️ Home": st.column_config.ImageColumn(""), "🏳️ Away": st.column_config.ImageColumn("")}
            )
        else:
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

            f_col1, f_col2, f_col3 = st.columns([2, 1, 2])
            with f_col1:
                if get_flag_url(m_row['Home_Team']): st.image(get_flag_url(m_row['Home_Team']), width=90)
                st.markdown(f"### {home_clean}")
            with f_col2:
                st.markdown("<h2 style='text-align: center; margin-top: 20px;'>VS</h2>", unsafe_allow_html=True)
            with f_col3:
                if get_flag_url(m_row['Away_Team']): st.image(get_flag_url(m_row['Away_Team']), width=90)
                st.markdown(f"### {away_clean}")

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
                            headers = [h.strip() for h in target_ws.row_values(1)]
                            first_col_idx = headers.index(f"{user}_FirstScorer") + 1
                            score_col_idx = headers.index(f"{user}_Score") + 1
                            sheet_row_num = int(m_idx) + 2
                            
                            sheet_first_val = m_row['Home_Team'] if p_first == home_clean else (m_row['Away_Team'] if p_first == away_clean else "No Goal")
                            target_ws.update_cell(sheet_row_num, first_col_idx, sheet_first_val)
                            target_ws.update_cell(sheet_row_num, score_col_idx, predicted_score_str)
                            st.success("Prediction cleanly saved to Google Sheets!")
                            st.rerun()
                        except Exception as write_err:
                            st.error(f"Failed to update spreadsheet: {write_err}")

            else:
                # KNOCKOUT STAGE 3-QUESTION FORMAT
                st.info("🏆 Knockout Stage: 30 Points Total (10 pts per correct answer)")
                
                # --- GOOGLE AI STUDIO NARRATIVE INJECTION ---
                if not odds_df.empty:
                    # Find the odds row for this match ID
                    match_odds_row = odds_df[odds_df['Match_ID'].astype(str) == str(m_id)]
                    if not match_odds_row.empty:
                        odds_data = match_odds_row.iloc[0]
                        
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
                                # Randomly decide whether this story mentions just the top scorer per team, or
                                # also the 2nd-best - keeps the 2nd/3rd odds you enter actually useful sometimes,
                                # without making every single story longer.
                                match_facts["scorer_tier"] = random.choice([1, 2])
                                narrative = generate_kid_friendly_narrative(match_facts)
                            # Convert markdown **bold** to real <strong> tags - markdown syntax does NOT get
                            # re-parsed once it's inside a raw HTML block, so we have to do this conversion
                            # ourselves before injecting it into the story-card div.
                            narrative_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", narrative)
                            # Display it in a styled custom box
                            st.markdown(f"<div class='story-card'>🎙️ <strong>The Pre-Match Scoop:</strong><br><br>{narrative_html}</div>", unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Commentary offline. Missing GOOGLE_API_KEY in Streamlit secrets.")
                # --------------------------------------

                st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                st.markdown("#### ⚽ Who scores first?")
                q1_first = st.radio("Select Team:", [home_clean, away_clean, "No Goal (0-0)"], index=None, key=f"q1_{m_id}")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                st.markdown("#### 🎯 Will there be a penalty shootout?")
                st.caption("Does this match require a shootout to decide the winner?")
                q2_pen = st.radio("Select:", ["Yes", "No"], index=None, key=f"q2_{m_id}")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='prediction-card'>", unsafe_allow_html=True)
                st.markdown("#### 🏆 Which team advances to the next round?")
                q3_adv = st.radio("Select Winner:", [home_clean, away_clean], index=None, key=f"q3_{m_id}")
                st.markdown("</div>", unsafe_allow_html=True)

                if st.button("Lock Prediction In"):
                    if is_locked:
                        st.error("This match has already kicked off! Changing predictions is locked.")
                    elif not (q1_first and q2_pen and q3_adv):
                        st.warning("⚠️ Please answer all 3 questions before submitting!")
                    else:
                        try:
                            headers = [h.strip() for h in target_ws.row_values(1)]
                            first_col_idx = headers.index(f"{user}_FirstScorer") + 1
                            pen_col_idx = headers.index(f"{user}_Penalty") + 1
                            qual_col_idx = headers.index(f"{user}_Qualifier") + 1
                            sheet_row_num = int(m_idx) + 2
                            
                            sheet_first_val = m_row['Home_Team'] if q1_first == home_clean else (m_row['Away_Team'] if q1_first == away_clean else "No Goal")
                            sheet_adv_val = m_row['Home_Team'] if q3_adv == home_clean else m_row['Away_Team']

                            target_ws.update_cell(sheet_row_num, first_col_idx, sheet_first_val)
                            target_ws.update_cell(sheet_row_num, pen_col_idx, q2_pen)
                            target_ws.update_cell(sheet_row_num, qual_col_idx, sheet_adv_val)
                            
                            st.success("Knockout predictions cleanly saved to Google Sheets!")
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
            actual_pen_val = ""
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
                    
                    hype = "🔥 MAXED OUT!" if earned == 20 else ""
                    st.write(f"**{p}:** {earned} pts {hype} (Predicted {p_score} & {clean_country_name(p_first)})")

            # --- KNOCKOUT STAGE ADMIN ---
            else:
                st.markdown("### 1. Enter Actual Match Result (Knockout Stage)")
                
                act_first_selection = st.radio("1. Who scored first?", [home_clean, away_clean, "No Goal (0-0)"])
                act_pen_selection = st.radio("2. Did it go to a Penalty Shootout?", ["Yes", "No"])
                act_adv_selection = st.radio("3. Who Advanced?", [home_clean, away_clean])

                actual_first_val = match_row['Home_Team'] if act_first_selection == home_clean else (match_row['Away_Team'] if act_first_selection == away_clean else "No Goal")
                actual_pen_val = act_pen_selection
                actual_qual_val = match_row['Home_Team'] if act_adv_selection == home_clean else match_row['Away_Team']

                st.markdown("### Points Preview:")
                for p in participants:
                    p_first = str(match_row.get(f'{p}_FirstScorer', "")).strip()
                    p_pen = str(match_row.get(f'{p}_Penalty', "")).strip()
                    p_qual = str(match_row.get(f'{p}_Qualifier', "")).strip()
                    
                    earned = 0
                    if p_first.lower() == str(actual_first_val).lower() and p_first != "": earned += 10
                    if p_pen.lower() == str(actual_pen_val).lower() and p_pen != "": earned += 10
                    if p_qual.lower() == str(actual_qual_val).lower() and p_qual != "": earned += 10
                    calculated_points_delta[p] = earned
                    
                    hype = "🚀 PERFECT SCORE!" if earned == 30 else ""
                    st.write(f"**{p}:** {earned} pts {hype} (Preds: {clean_country_name(p_first)} | Pens: {p_pen} | Adv: {clean_country_name(p_qual)})")

            st.divider()

            if st.button("💾 Save & Finalize Match Results"):
                try:
                    with st.spinner("Updating Google Sheets & calculating points live..."):
                        sheet_row_num = int(m_idx) + 2
                        headers = [h.strip() for h in target_ws.row_values(1)]

                        # 1. Update Match Status
                        if "Status" in headers:
                            target_ws.update_cell(sheet_row_num, headers.index("Status") + 1, "Completed")
                        
                        # 2. Update Actual Results based on Stage
                        if "Actual_FirstScorer" in headers:
                            target_ws.update_cell(sheet_row_num, headers.index("Actual_FirstScorer") + 1, str(actual_first_val))
                            
                        if stage == "Group" and "Actual_Score" in headers:
                            target_ws.update_cell(sheet_row_num, headers.index("Actual_Score") + 1, actual_score_str)
                        elif stage == "Knockout":
                            if "Penalty_Shootout" in headers:
                                target_ws.update_cell(sheet_row_num, headers.index("Penalty_Shootout") + 1, actual_pen_val)
                            if "Qualifying_Team" in headers:
                                target_ws.update_cell(sheet_row_num, headers.index("Qualifying_Team") + 1, actual_qual_val)

                        # 3. Update Leaderboard
                        lead_headers = [h.strip() for h in leaderboard_worksheet.row_values(1)]
                        pts_col_idx = lead_headers.index("Points") + 1
                        current_leaderboard_rows = leaderboard_worksheet.get_all_records()

                        for p, points_to_add in calculated_points_delta.items():
                            if points_to_add > 0:
                                for idx, l_row in enumerate(current_leaderboard_rows):
                                    if str(l_row.get("Participant")).strip() == p:
                                        l_sheet_row = idx + 2
                                        current_pts = int(l_row.get("Points", 0))
                                        leaderboard_worksheet.update_cell(l_sheet_row, pts_col_idx, current_pts + points_to_add)
                                        break

                        st.success("🏆 Match finalized! Scores stored and Leaderboard updated successfully.")
                        st.cache_data.clear()
                        st.rerun()

                except Exception as write_err:
                    st.error(f"Database sync failed: {write_err}")

    elif admin_password:
        st.error("Incorrect password.")
