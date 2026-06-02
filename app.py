import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials

# Page setup - wide layout to maximize workspace and kill horizontal scrollbars
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
        
        /* 3. High-Contrast Buttons: Deep Royal Blue with Clean White Text */
        div.stButton > button {
            background-color: #0056B3 !important;
            color: #FFFFFF !important;
            border: 1px solid #004085 !important;
            border-radius: 6px !important;
            font-weight: bold !important;
            padding: 0.6rem 1.2rem !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.2s ease-in-out !important;
        }
        div.stButton > button:hover {
            background-color: #004085 !important;
            border-color: #002752 !important;
            color: #FFFFFF !important;
            transform: translateY(-1px) !important;
        }
        
        /* 4. High-Contrast Form Inputs (Dropdowns, Number Toggles, Passwords) */
        input, select, div[data-baseweb="select"], div[data-testid="stNumberInput"] input {
            background-color: #F8F9FA !important;
            color: #111111 !important;
            border: 1px solid #DEE2E6 !important;
            border-radius: 4px !important;
        }
        
        /* 5. Pandas Dataframe High-Contrast Framing Panel */
        div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E9ECEF !important;
            border-radius: 8px !important;
            padding: 10px !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }

        /* 6. Clean Navigation Tabs on White Canvas */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #FFFFFF !important;
            border-bottom: 2px solid #F1F3F5;
        }
        .stTabs [data-baseweb="tab"] {
            color: #495057 !important;
            font-weight: 500 !important;
        }
        .stTabs [aria-selected="true"] {
            color: #0056B3 !important;
            font-weight: bold !important;
            border-bottom-color: #0056B3 !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# Helper function to get current AEST time safely
def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

# 🔐 Establish Direct Google Sheets Connection Engine
@st.cache_resource(ttl=3)
def get_gspread_client():
    try:
        secret_info = st.secrets["connections"]["gsheets"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials = Credentials.from_service_account_info(secret_info, scopes=scopes)
        return gspread.authorize(credentials)
    except Exception as e:
        st.error(f"❌ Google Authentication Failed: {e}")
        st.stop()

# Initialize Client and Fetch Data Rows
gc = get_gspread_client()

# Hardcoded Sheet ID Engine Link
SPREADSHEET_ID = "1Cc0MnMtMfwfhyGWpPeQULLVjuSs1dNs91Yf98PW0SL0"

try:
    sh = gc.open_by_key(SPREADSHEET_ID)
    all_worksheets = {ws.title.strip().lower(): ws for ws in sh.worksheets()}
    
    if "matches" in all_worksheets:
        matches_worksheet = all_worksheets["matches"]
    else:
        st.error("❌ Could not find a tab named 'Matches' in your spreadsheet.")
        st.stop()
        
    if "leaderboard" in all_worksheets:
        leaderboard_worksheet = all_worksheets["leaderboard"]
    else:
        st.error("❌ Could not find a tab named 'Leaderboard' in your spreadsheet.")
        st.stop()

    # Pull datasets into memory
    matches_df = pd.DataFrame(matches_worksheet.get_all_records())
    leaderboard_df = pd.DataFrame(leaderboard_worksheet.get_all_records())
except Exception as e:
    st.error(f"❌ Connection Blocked: Error type `{type(e).__name__}`")
    st.info("Ensure your spreadsheet remains shared with the bot's service account email.")
    st.stop()

# Clean up dataframe column headers
matches_df.columns = matches_df.columns.str.strip()
leaderboard_df.columns = leaderboard_df.columns.str.strip()

# Ensure types are correct
matches_df['Match_ID'] = matches_df['Match_ID'].astype(str)
matches_df['Kickoff_AEST'] = pd.to_datetime(matches_df['Kickoff_AEST'])
participants = ['HD', 'LS', 'CD', 'ND', 'GB', 'SB']

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
        tomorrow = today + timedelta(days=1)
        matches_df['Kickoff_Date'] = matches_df['Kickoff_AEST'].dt.date
        
        # 📋 1. LIVE CURRENT & FUTURE PREDICTIONS OVERVIEW
        st.markdown(f"### Your Active Predictions Overview ({user})")
        
        active_matches = matches_df[matches_df['Status'] != 'Completed'].copy()
        
        overview_rows = []
        for _, row in active_matches.iterrows():
            m_id = row['Match_ID']
            match_name = f"{row['Home_Team']} vs {row['Away_Team']}"
            kickoff_str = row['Kickoff_AEST'].strftime('%d %b, %I:%M %p')
            
            # Check current saved locks
            saved_out = row.get(f'{user}_Outcome', "")
            saved_score = row.get(f'{user}_Score', "")
            
            out_display = str(saved_out) if pd.notna(saved_out) and str(saved_out).strip() != "" else "Not Submitted Yet"
            score_display = str(saved_score) if pd.notna(saved_score) and str(saved_score).strip() != "" else "Not Submitted Yet"
            
            overview_rows.append({
                "Match ID": m_id,
                "Fixture": match_name,
                "Kickoff Time (AEST)": kickoff_str,
                "Your Predicted Winner": out_display,
                "Your Predicted Score": score_display
            })
            
        if overview_rows:
            overview_df = pd.DataFrame(overview_rows)
            st.dataframe(overview_df, use_container_width=True, hide_index=True)
        else:
            st.info("No active or upcoming matches listed right now.")
            
        st.divider()
        
        # ✍️ 2. PREDICTION SUBMISSION FORM
        st.markdown("### ✍️ Submit or Edit a Prediction")
        
        opening_day_1 = datetime.strptime("2026-06-12", "%Y-%m-%d").date()
        opening_day_2 = datetime.strptime("2026-06-13", "%Y-%m-%d").date()
        
        if today < opening_day_1:
            open_matches = matches_df[
                (matches_df['Status'] != 'Completed') & 
                (matches_df['Kickoff_Date'].isin([opening_day_1, opening_day_2]))
            ].copy()
        else:
            open_matches = matches_df[
                (matches_df['Status'] != 'Completed') & 
                (matches_df['Kickoff_Date'].isin([today, tomorrow]))
            ].copy()
        
        if open_matches.empty:
            st.info("No matches scheduled for this window are open for entry updates right now.")
        else:
            match_options = open_matches.apply(lambda r: f"Match {r['Match_ID']}: {r['Home_Team']} vs {r['Away_Team']} ({r['Kickoff_AEST'].strftime('%d %b')})", axis=1).tolist()
            selected_pred_match = st.selectbox("Choose a match to log/modify:", match_options)
            
            m_id = selected_pred_match.split(":")[0].replace("Match ", "").strip()
            m_idx = matches_df[matches_df['Match_ID'] == m_id].index[0]
            m_row = matches_df.loc[m_idx]
            
            is_locked = current_time >= m_row['Kickoff_AEST']
            lock_status = "LOCKED" if is_locked else "Open for Changes"
            st.write(f"⏰ **Kickoff:** {m_row['Kickoff_AEST'].strftime('%d %b, %I:%M %p')} AEST ({lock_status})")
            
            p_out = st.selectbox("1. Who will win?", ["Select outcome...", m_row['Home_Team'], m_row['Away_Team'], "Draw"])
            
            col1, col2 = st.columns(2)
            with col1:
                p_home_score = st.number_input(f"{m_row['Home_Team']} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
            with col2:
                p_away_score = st.number_input(f"{m_row['Away_Team']} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
                
            predicted_score_str = f"{p_home_score}-{p_away_score}"
            
            if st.button("Lock Prediction In"):
                if is_locked:
                    st.error("This match has already kicked off! You can no longer modify entries.")
                elif p_out == "Select outcome...":
                    st.error("Please pick a winner or select 'Draw' before submitting!")
                elif p_out == "Draw" and p_home_score != p_away_score:
                    st.error(f"❌ Validation Error: You selected 'Draw', but your score prediction ({predicted_score_str}) is not a tie!")
                elif p_out != "Draw" and p_home_score == p_away_score:
                    st.error(f"❌ Validation Error: You predicted a tie score ({predicted_score_str}), but did not select 'Draw' as the outcome!")
                elif p_out == m_row['Home_Team'] and p_home_score < p_away_score:
                    st.error(f"❌ Validation Error: You picked {m_row['Home_Team']} to win, but your score ({predicted_score_str}) has them losing!")
                elif p_out == m_row['Away_Team'] and p_away_score < p_home_score:
                    st.error(f"❌ Validation Error: You picked {m_row['Away_Team']} to win, but your score ({predicted_score_str}) has them losing!")
                else:
                    try:
                        headers = [h.strip() for h in matches_worksheet.row_values(1)]
                        outcome_col_idx = headers.index(f"{user}_Outcome") + 1
                        score_col_idx = headers.index(f"{user}_Score") + 1
                        
                        sheet_row_num = int(m_idx) + 2
                        
                        matches_worksheet.update_cell(sheet_row_num, outcome_col_idx, p_out)
                        matches_worksheet.update_cell(sheet_row_num, score_col_idx, predicted_score_str)
                        
                        st.success("Prediction saved straight to the Google Sheet!")
                        st.rerun()
                    except Exception as write_err:
                        st.error(f"Failed to update spreadsheet cells: {write_err}")

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
            match_options = active_matches.apply(lambda r: f"Match {r['Match_ID']}: {r['Home_Team']} vs {r['Away_Team']}", axis=1).tolist()
            selected_match_str = st.selectbox("Select match to calculate points:", match_options)
            
            selected_id = selected_match_str.split(":")[0].replace("Match ", "").strip()
            match_row = matches_df[matches_df['Match_ID'] == selected_id].iloc[0]
            
            st.markdown("### 1. Enter Actual Match Result")
            col1, col2 = st.columns(2)
            with col1:
                act_home = st.number_input(f"{match_row['Home_Team']} Score", min_value=0, step=1, value=0, key="ah")
            with col2:
                act_away = st.number_input(f"{match_row['Away_Team']} Score", min_value=0, step=1, value=0, key="aa")
            
            if act_home > act_away:
                actual_outcome = str(match_row['Home_Team'])
            elif act_away > act_home:
                actual_outcome = str(match_row['Away_Team'])
            else:
                actual_outcome = "Draw"
                
            actual_score_str = f"{act_home}-{act_away}"
            
            st.write(f"**Calculated Reality:** Outcome = `{actual_outcome}`, Score = `{actual_score_str}`")
            st.divider()
            
            st.markdown("### Points Calculations for Spreadsheet:")
            
            for p in participants:
                p_out_col = f'{p}_Outcome'
                p_score_col = f'{p}_Score'
                
                p_out = str(match_row[p_out_col]).strip() if p_out_col in matches_df.columns and pd.notna(match_row[p_out_col]) else ""
                p_score = str(match_row[p_score_col]).strip() if p_score_col in matches_df.columns and pd.notna(match_row[p_score_col]) else ""
                
                outcome_correct = (p_out.lower() == actual_outcome.lower())
                score_correct = (p_score == actual_score_str)
                
                if outcome_correct and score_correct:
                    st.success(f"Winner! {p} got BOTH right! Outcome: {p_out} | Score: {p_score} — Award +20 Points!")
                elif outcome_correct:
                    st.info(f"Good job! {p} got the Winner/Draw RIGHT ({p_out}), but score wrong — Award +10 Points!")
                else:
                    st.write(f"{p} got 0 points.")
                    
            st.info("📌 Next Step: Manually update your Google Sheet 'Leaderboard' tab with these points, set the match 'Status' to 'Completed', and you're good to go!")
    elif admin_password:
        st.error("Incorrect password.")
