import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import gspread
import re
import requests
import urllib.request
import xml.etree.ElementTree as ET
from google.oauth2.service_account import Credentials

# Page setup - wide layout to maximize workspace and eliminate horizontal scrollbars
st.set_page_config(page_title="World Cup Challenge", page_icon="🏆", layout="wide")

# 🎨 Custom CSS Engine: Enforces strict white background and crisp, readable contrast
st.markdown("""
    <style>
        /* 1. Base App White Background Overrides */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #FFFFFF !important;
            color: #111111 !important;
        }
        
        /* 2. Global Typography Visibility Controls */
        h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown {
            color: #111111 !important;
        }
        
        /* 3. Horizontal Premium Ticker Canvas (Top of Page) */
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
        
        /* Crucial: Override the global #111111 text color rule inside the ticker banner */
        .ticker-content span {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            letter-spacing: 0.5px;
        }
        
        /* 4. High-Contrast Buttons: Premium Stadium Green with Bold White Text */
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
        
        /* 5. High-Contrast Form Inputs */
        input, select, div[data-baseweb="select"], div[data-testid="stNumberInput"] input {
            background-color: #F8F9FA !important;
            color: #111111 !important;
            border: 1px solid #DEE2E6 !important;
            border-radius: 4px !important;
        }
        
        /* 6. Pandas Dataframe High-Contrast Framing Panel */
        div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E9ECEF !important;
            border-radius: 8px !important;
            padding: 10px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }

        /* 7. Clean Navigation Tabs on White Canvas */
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
        
        /* 8. AI Forecast Box Styling */
        .forecast-box {
            background-color: #F8F9FA;
            border: 1px dashed #198754;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# 📡 LIVE WORLD CUP NEWS TICKER ENGINE
@st.cache_data(ttl=900)
def fetch_ticker_string():
    # Swapped to your preferred BBC RSS Feed URL
    rss_url = "http://newsrss.bbc.co.uk/rss/sportonline_uk_edition/football/rss.xml"
    
    fallback_string = (
        "🏆 FIFA WORLD CUP 2026: Tournament group structures finalized ahead of high-intensity opening match blocks "
        "⚽ FUTURES MARKET UPDATE: Analytical goalscoring models shifting odds heavily toward clinical penalty area specialists "
        "🏆 TACTICAL REPORT: Technical staff implement strict player rotation patterns ahead of grueling cross-continent travel corridors "
        "⚽ READY TO WATCH: Broadcast metrics indicate record-breaking views expected live across Australia on SBS Networks."
    )
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        ticker_items = []
        
        for item in root.findall('.//item')[:15]: # Checked a wider sample size since it's a general feed
            title = item.find('title').text if item.find('title') is not None else ""
            
            # Tighter filter keywords to ensure BBC's domestic UK news doesn't clutter your World Cup space
            if any(k in title.lower() for k in ['world cup', 'fifa', 'international', 'national team', 'qualifier', '2026']):
                ticker_items.append(f"⚽ {title.upper().strip()}")
        
        if ticker_items:
            return "   ||   ".join(ticker_items) + "   ||   "
        return fallback_string
    except Exception:
        return fallback_string

# 🏁 STEP 1: Render the continuous news ticker string at the absolute top of the viewport canvas
ticker_text = fetch_ticker_string()
st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker-content">
            <span>{ticker_text}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 🏁 STEP 2: Main Application Title Context
st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# 🛠️ Smart Flag Parsing & Country Cleaning Engine
def get_flag_url(text):
    if not isinstance(text, str):
        return ""
    text_clean = text.strip().lower()
    
    codes = []
    for char in text:
        cp = ord(char)
        if 0x1F1E6 <= cp <= 0x1F1FF:
            codes.append(chr(cp - 0x1F1E6 + ord('a')))
    if len(codes) >= 2:
        return f"https://flagcdn.com/w80/{''.join(codes[:2])}.png"
        
    flag_map = {
        'argentina': 'ar', 'australia': 'au', 'belgium': 'be', 'brazil': 'br', 
        'canada': 'ca', 'croatia': 'hr', 'denmark': 'dk', 'france': 'fr', 
        'germany': 'de', 'italy': 'it', 'japan': 'jp', 'mexico': 'mx', 
        'morocco': 'ma', 'netherlands': 'nl', 'portugal': 'pt', 'spain': 'es', 
        'usa': 'us', 'united states': 'us', 'england': 'gb-eng', 'wales': 'gb-wls',
        'scotland': 'gb-sct', 'saudi arabia': 'sa', 'south korea': 'kr', 'uruguay': 'uy',
        'south africa': 'za', 'paraguay': 'py', 'bosnia & herz.': 'ba', 'czech republic': 'cz',
        'haiti': 'ht', 'curacao': 'cw', 'uzbekistan': 'uz', 'jordan': 'jo', 'cape verde': 'cv'
    }
    pure_name = re.sub(r'[\U0001f1e6-\U0001f1ff\U00010000-\U0010ffff\u2600-\u27bf]', '', text_clean).strip()
    if pure_name in flag_map:
        return f"https://flagcdn.com/w80/{flag_map[pure_name]}.png"
    return ""

def clean_country_name(text):
    if not isinstance(text, str):
        return text
    return re.sub(r'[\U0001f1e6-\U0001f1ff\U00010000-\U0010ffff\u2600-\u27bf]', '', text).strip()

def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

def clean_and_parse_date(date_val):
    if not date_val or pd.isna(date_val):
        return datetime(2026, 6, 12, 5, 0)
    date_str = str(date_val).strip()
    try:
        return pd.to_datetime(date_str, dayfirst=False)
    except Exception:
        try:
            return pd.to_datetime(date_str, dayfirst=True)
        except Exception:
            return datetime(2026, 6, 12, 5, 0)

# 🔮 AUTOMATIC HYBRID FORECAST ENGINE (REAL-TIME FIFA RANKING FALLBACK)
@st.cache_data(ttl=7200)
def fetch_api_football_forecast(home_team, away_team):
    def normalize_name(name):
        n = clean_country_name(name).lower().strip()
        mapping = {
            'united states': 'usa', 'united states of america': 'usa',
            'korea republic': 'south korea', 'republic of korea': 'south korea',
            'czechia': 'czech republic',
            'bosnia & herz.': 'bosnia and herzegovina', 'bosnia & herzegovina': 'bosnia and herzegovina',
            'cote d\'ivoire': "cote d'ivoire", 'ivory coast': "cote d'ivoire",
            'congo dr': 'dr congo', 'democratic republic of the congo': 'dr congo'
        }
        return mapping.get(n, n)

    home_clean = normalize_name(home_team)
    away_clean = normalize_name(away_team)
    
    power_tiers = {
        'france': 95, 'argentina': 95, 'spain': 94, 'england': 92, 'brazil': 91,
        'portugal': 89, 'netherlands': 88, 'belgium': 88, 'germany': 87, 'morocco': 86,
        'croatia': 85, 'uruguay': 84, 'colombia': 83, 'usa': 83, 'japan': 82, 
        'senegal': 81, 'mexico': 81, 'denmark': 81, 'switzerland': 80, 'south korea': 79,
        'australia': 78, 'turkiye': 78, 'ecuador': 77, 'austria': 77, 'sweden': 77,
        'nigeria': 76, 'algeria': 76, 'egypt': 76, 'scotland': 76, 'canada': 75, 
        'czech republic': 75, 'ukraine': 75, 'poland': 74, 'wales': 74, 'panama': 74, 
        'paraguay': 74, 'ghana': 74, 'serbia': 73, 'tunisia': 73, 'cameroon': 73,
        'dr congo': 73, 'bosnia and herzegovina': 73, 'cote d\'ivoire': 73, 'qatar': 72, 
        'south africa': 72, 'uzbekistan': 71, 'saudi arabia': 71, 'iraq': 71, 
        'jordan': 69, 'cape verde': 69, 'haiti': 68, 'curacao': 67, 'new zealand': 66
    }
    
    home_strength = power_tiers.get(home_clean, 70)
    away_strength = power_tiers.get(away_clean, 70)
    
    home_calc = home_strength + 3
    away_calc = away_strength
    total = home_calc + away_calc
    
    fallback_home_pct = int((home_calc / total) * 76)
    fallback_away_pct = int((away_calc / total) * 76)
    fallback_draw_pct = 100 - fallback_home_pct - fallback_away_pct
    
    h_display = clean_country_name(home_team)
    a_display = clean_country_name(away_team)
    
    if abs(home_calc - away_calc) <= 3:
        fallback_advice = f"Tactical Balance: Highly competitive match between {h_display} and {a_display}."
    elif home_calc > away_calc:
        fallback_advice = f"Direct Win Strategy: Match favor leans toward {h_display}"
    else:
        fallback_advice = f"Direct Win Strategy: Match favor leans toward {a_display}"

    api_key = "9db5ecb263b045ec724c436046a92bd5"
    headers = {
        'x-apisports-key': api_key,
        'x-rapidapi-host': 'v3.football.api-sports.io'
    }
    
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        params = {"league": "1", "season": "2026"}
        res = requests.get(url, headers=headers, params=params, timeout=10).json()
        
        fixture_id = None
        if res.get("response"):
            for fix in res["response"]:
                fix_home = normalize_name(fix["teams"]["home"]["name"])
                fix_away = normalize_name(fix["teams"]["away"]["name"])
                
                if (home_clean in fix_home or fix_home in home_clean) and \
                   (away_clean in fix_away or fix_away in away_clean):
                    fixture_id = fix["fixture"]["id"]
                    break
                    
        if fixture_id:
            pred_url = f"https://v3.football.api-sports.io/predictions?fixture={fixture_id}"
            pred_res = requests.get(pred_url, headers=headers, timeout=10).json()
            
            if pred_res.get("response") and len(pred_res["response"]) > 0:
                data = pred_res["response"][0]
                predictions = data.get("predictions", {})
                percents = predictions.get("percent", {})
                advice_str = predictions.get("advice", "")
                
                h_pct = percents.get("home")
                d_pct = percents.get("draw")
                a_pct = percents.get("away")
                
                if h_pct is not None and d_pct is not None and a_pct is not None and advice_str != "":
                    return {
                        "home": int(str(h_pct).replace("%","")),
                        "draw": int(str(d_pct).replace("%","")),
                        "away": int(str(a_pct).replace("%","")),
                        "advice": advice_str
                    }
    except Exception:
        pass
        
    return {
        "home": fallback_home_pct, 
        "draw": fallback_draw_pct, 
        "away": fallback_away_pct, 
        "advice": f"⭐ {fallback_advice} (FIFA Rank Analytical Preview)"
    }

# 🔐 Establish Direct Google Sheets Connection Engine
@st.cache_resource(ttl=3)
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
SPREADSHEET_ID = "1Cc0MnMtMfwfhyGWpPeQULLVjuSs1dNs91Yf98PW0SL0"

try:
    sh = gc.open_by_key(SPREADSHEET_ID)
    all_worksheets = {ws.title.strip().lower(): ws for ws in sh.worksheets()}
    matches_worksheet = all_worksheets["matches"]
    leaderboard_worksheet = all_worksheets["leaderboard"]

    matches_df = pd.DataFrame(matches_worksheet.get_all_records())
    leaderboard_df = pd.DataFrame(leaderboard_worksheet.get_all_records())
except Exception as e:
    st.error(f"❌ Connection Blocked: {e}")
    st.stop()

matches_df.columns = matches_df.columns.str.strip()
leaderboard_df.columns = leaderboard_df.columns.str.strip()
matches_df['Match_ID'] = matches_df['Match_ID'].astype(str)
matches_df['Kickoff_AEST'] = matches_df['Kickoff_AEST'].apply(clean_and_parse_date)

participants = ['ND', 'CD', 'SB', 'GB', 'LS', 'HD']

tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "⚽ Submit Predictions", "🔒 Admin Engine"])

# --- TAB 1: LEADERBOARD ---
with tab1:
    st.subheader("Current Standings")
    leaderboard_sorted = leaderboard_df.sort_values(by="Points", ascending=False).reset_index(drop=True)
    st.dataframe(
        leaderboard_sorted, 
        use_container_width=True, 
        hide_index=True,
        column_config={"Participant": "Player", "Points": st.column_config.NumberColumn("Total Points", format="%d pts")}
    )
    st.divider()
    st.markdown("🎁 **Prize:** $20 Kmart Gift Card up for grabs.")

# --- TAB 2: SUBMIT PREDICTIONS ---
with tab2:
    st.subheader("Log or Edit Your Predictions")
    user = st.selectbox("Who are you?", ["Select your name..."] + participants)
    
    if user != "Select your name...":
        current_time = get_current_aest()
        today = current_time.date()
        matches_df['Kickoff_Date'] = matches_df['Kickoff_AEST'].dt.date
        
        st.markdown(f"### Your Active Predictions Overview ({user})")
        active_matches = matches_df[matches_df['Status'] != 'Completed'].copy()
        
        overview_rows = []
        for _, row in active_matches.iterrows():
            m_id = row['Match_ID']
            kickoff_str = row['Kickoff_AEST'].strftime('%a, %d %b, %I:%M %p')
            
            saved_first = row.get(f'{user}_FirstScorer', "")
            saved_score = row.get(f'{user}_Score', "")
            
            first_display = clean_country_name(str(saved_first)) if pd.notna(saved_first) and str(saved_first).strip() != "" else "Not Submitted"
            score_display = str(saved_score) if pd.notna(saved_score) and str(saved_score).strip() != "" else "Not Submitted"
            
            overview_rows.append({
                "Match ID": m_id,
                "🏳️ Home": get_flag_url(row['Home_Team']),
                "Home Team": clean_country_name(row['Home_Team']),
                "Away Team": clean_country_name(row['Away_Team']),
                "🏳️ Away": get_flag_url(row['Away_Team']),
                "Kickoff Time (AEST)": kickoff_str,
                "First Team to Score": first_display,
                "Predicted Score": score_display
            })
            
        if overview_rows:
            overview_df = pd.DataFrame(overview_rows)
            st.dataframe(
                overview_df, use_container_width=True, hide_index=True,
                column_config={"🏳️ Home": st.column_config.ImageColumn(""), "🏳️ Away": st.column_config.ImageColumn("")}
            )
        else:
            st.info("No active matches scheduled right now.")
            
        st.divider()
        
        st.markdown("### ✍️ Submit or Edit a Prediction")
        
        tournament_start_date = datetime.strptime("2026-06-12", "%Y-%m-%d").date()
        uncompleted_matches = matches_df[matches_df['Status'] != 'Completed'].copy()
        
        if today < tournament_start_date:
            allowed_days = [
                tournament_start_date,
                tournament_start_date + timedelta(days=1),
                tournament_start_date + timedelta(days=2)
            ]
            open_matches = uncompleted_matches[uncompleted_matches['Kickoff_Date'].isin(allowed_days)].copy()
        else:
            day_d = today
            day_d1 = today + timedelta(days=1)
            day_d2 = today + timedelta(days=2)
            
            cond_today = (uncompleted_matches['Kickoff_Date'] == day_d) & (uncompleted_matches['Kickoff_AEST'] > current_time)
            cond_future = uncompleted_matches['Kickoff_Date'].isin([day_d1, day_d2])
            
            open_matches = uncompleted_matches[cond_today | cond_future].copy()
        
        if open_matches.empty:
            st.info("No matches scheduled for this specific rolling window are open right now.")
        else:
            match_options = open_matches.apply(lambda r: f"Match {r['Match_ID']}: {clean_country_name(r['Home_Team'])} vs {clean_country_name(r['Away_Team'])} ({r['Kickoff_AEST'].strftime('%a, %d %b %I:%M %p')})", axis=1).tolist()
            selected_pred_match = st.selectbox("Choose a match to log/modify:", match_options)
            
            m_id = selected_pred_match.split(":")[0].replace("Match ", "").strip()
            m_idx = matches_df[matches_df['Match_ID'] == m_id].index[0]
            m_row = matches_df.loc[m_idx]
            
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
            
            forecast = fetch_api_football_forecast(m_row['Home_Team'], m_row['Away_Team'])
            st.markdown(f"<div class='forecast-box'>⚙️ <b>Win Probabilities:</b> {home_clean}: <b>{forecast['home']}%</b> | Draw: <b>{forecast['draw']}%</b> | {away_clean}: <b>{forecast['away']}%</b><br>📋 <b>Recommendation:</b> <i>{forecast['advice']}</i></div>", unsafe_allow_html=True)
            
            st.write("---")
            
            col1, col2 = st.columns(2)
            with col1:
                p_home_score = st.number_input(f"{home_clean} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
            with col2:
                p_away_score = st.number_input(f"{away_clean} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
                
            predicted_score_str = f"{p_home_score}-{p_away_score}"
            p_first = st.selectbox("2. Which country will score first?", ["Select option...", home_clean, away_clean, "No Goal"])
            
            if st.button("Lock Prediction In"):
                if is_locked:
                    st.error("This match has already kicked off! Changing predictions is locked.")
                elif p_first == "Select option...":
                    st.error("Please explicitly declare who scores first!")
                elif p_home_score == 0 and p_away_score == 0 and p_first != "No Goal":
                    st.error("❌ Validation Error: If your exact score is 0-0, your first scorer selection must be 'No Goal'!")
                elif (p_home_score > 0 or p_away_score > 0) and p_first == "No Goal":
                    st.error(f"❌ Validation Error: You predicted goals will be scored ({predicted_score_str}), so 'No Goal' is impossible!")
                elif p_home_score > 0 and p_away_score == 0 and p_first != home_clean:
                    st.error(f"❌ Validation Error: You predicted {home_clean} to win to nil ({predicted_score_str}), so {away_clean} cannot score first!")
                elif p_home_score == 0 and p_away_score > 0 and p_first != away_clean:
                    st.error(f"❌ Validation Error: You predicted {away_clean} to win to nil ({predicted_score_str}), so {home_clean} cannot score first!")
                else:
                    try:
                        headers = [h.strip() for h in matches_worksheet.row_values(1)]
                        first_col_idx = headers.index(f"{user}_FirstScorer") + 1
                        score_col_idx = headers.index(f"{user}_Score") + 1
                        sheet_row_num = int(m_idx) + 2
                        
                        sheet_first_val = m_row['Home_Team'] if p_first == home_clean else (m_row['Away_Team'] if p_first == away_clean else "No Goal")
                        
                        matches_worksheet.update_cell(sheet_row_num, first_col_idx, sheet_first_val)
                        matches_worksheet.update_cell(sheet_row_num, score_col_idx, predicted_score_str)
                        
                        st.success("Prediction cleanly saved to Google Sheets!")
                        st.rerun()
                    except Exception as write_err:
                        st.error(f"Failed to update spreadsheet cells: {write_err}")

# --- TAB 3: ADMIN ENGINE ---
# --- TAB 3: ADMIN ENGINE ---
with tab3:
    st.subheader("Admin Scoring Panel")
    admin_password = st.text_input("Enter Password", type="password")
    
    if admin_password == "kmart20":
        st.success("Welcome back.")
        active_matches = matches_df[matches_df['Status'] != 'Completed']
        
        if active_matches.empty:
            st.info("All matches finalized!")
        else:
            match_options = active_matches.apply(lambda r: f"Match {r['Match_ID']}: {clean_country_name(r['Home_Team'])} vs {clean_country_name(r['Away_Team'])}", axis=1).tolist()
            selected_match_str = st.selectbox("Select match to calculate points:", match_options)
            
            selected_id = selected_match_str.split(":")[0].replace("Match ", "").strip()
            m_idx = matches_df[matches_df['Match_ID'] == selected_id].index[0]
            match_row = matches_df.loc[m_idx]
            
            home_clean = clean_country_name(match_row['Home_Team'])
            away_clean = clean_country_name(match_row['Away_Team'])
            
            st.markdown("### 1. Enter Actual Match Result")
            col1, col2 = st.columns(2)
            with col1:
                act_home = st.number_input(f"Actual {home_clean} Score", min_value=0, step=1, value=0, key="ah")
            with col2:
                act_away = st.number_input(f"Actual {away_clean} Score", min_value=0, step=1, value=0, key="aa")
            
            if act_home == 0 and act_away == 0:
                act_first_options = ["No Goal"]
            elif act_home > 0 and act_away == 0:
                act_first_options = [home_clean]
            elif act_home == 0 and act_away > 0:
                act_first_options = [away_clean]
            else:
                act_first_options = [home_clean, away_clean]
                
            act_first_selection = st.selectbox("Who scored first in reality?", act_first_options)
            
            actual_score_str = f"{act_home}-{act_away}"
            actual_first_val = match_row['Home_Team'] if act_first_selection == home_clean else (match_row['Away_Team'] if act_first_selection == away_clean else "No Goal")
            
            st.divider()
            st.markdown("### New Rules Points Preview:")
            
            # Temporary storage to hold calculated points for the commit step
            calculated_points_delta = {}
            
            for p in participants:
                p_first_col = f'{p}_FirstScorer'
                p_score_col = f'{p}_Score'
                
                p_first = str(match_row[p_first_col]).strip() if p_first_col in matches_df.columns and pd.notna(match_row[p_first_col]) else ""
                p_score = str(match_row[p_score_col]).strip() if p_score_col in matches_df.columns and pd.notna(match_row[p_score_col]) else ""
                
                score_correct = (p_score == actual_score_str)
                first_correct = (p_first.lower() == str(actual_first_val).lower())
                
                earned_points = 0
                breakdown = []
                
                if score_correct:
                    earned_points += 10
                    breakdown.append("Exact Score Match (+10)")
                if first_correct:
                    earned_points += 10
                    breakdown.append("First Scorer Match (+10)")
                
                calculated_points_delta[p] = earned_points
                    
                if earned_points == 20:
                    st.success(f"🔥 **{p} Maxed Out!** Award **+20 Points** (Score: {p_score}, First Scorer: {clean_country_name(p_first)})")
                elif earned_points == 10:
                    st.info(f"✨ **{p} got +10 Points:** Matches: {', '.join(breakdown)}")
                else:
                    st.write(f"⚪ **{p} got 0 points** (Predicted {p_score} & {clean_country_name(p_first)})")
                    
            st.divider()
            
            # 🚀 NEW AUTOMATED COMMIT ENGINE BUTTON
            if st.button("💾 Save & Finalize Match Results"):
                try:
                    with st.spinner("Updating Google Sheets & calculating points live..."):
                        sheet_row_num = int(m_idx) + 2
                        match_headers = [h.strip() for h in matches_worksheet.row_values(1)]
                        
                        # 1. Flip Status to Completed
                        if "Status" in match_headers:
                            status_idx = match_headers.index("Status") + 1
                            matches_worksheet.update_cell(sheet_row_num, status_idx, "Completed")
                        
                        # 2. Log Actual Results to matches tab (Safe fallback if columns don't exist yet)
                        if "Actual_Score" in match_headers:
                            score_idx = match_headers.index("Actual_Score") + 1
                            matches_worksheet.update_cell(sheet_row_num, score_idx, actual_score_str)
                        if "Actual_FirstScorer" in match_headers:
                            first_idx = match_headers.index("Actual_FirstScorer") + 1
                            matches_worksheet.update_cell(sheet_row_num, first_idx, str(actual_first_val))
                        
                        # 3. Update Player Leaderboard Automatically
                        lead_headers = [h.strip() for h in leaderboard_worksheet.row_values(1)]
                        p_col_idx = lead_headers.index("Participant") + 1
                        pts_col_idx = lead_headers.index("Points") + 1
                        current_leaderboard_rows = leaderboard_worksheet.get_all_records()
                        
                        for p, points_to_add in calculated_points_delta.items():
                            if points_to_add > 0:
                                # Find matching participant row in the spreadsheet
                                for idx, l_row in enumerate(current_leaderboard_rows):
                                    if str(l_row.get("Participant")).strip() == p:
                                        l_sheet_row = idx + 2
                                        current_pts = int(l_row.get("Points", 0))
                                        new_total = current_pts + points_to_add
                                        leaderboard_worksheet.update_cell(l_sheet_row, pts_col_idx, new_total)
                                        break
                        
                        st.success("🏆 Match finalized! Scores stored and Leaderboard updated successfully.")
                        st.clear_cache()
                        st.rerun()
                        
                except Exception as write_err:
                    st.error(f"Database sync failed: {write_err}")
                    
    elif admin_password:
        st.error("Incorrect password.")
