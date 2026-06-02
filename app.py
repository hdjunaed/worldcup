import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials

# Page setup for modern mobile responsiveness
st.set_page_config(page_title="World Cup Challenge", page_icon="🏆", layout="centered")

st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# Helper function to get current AEST time safely
def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

# 🔐 Establish Direct Google Sheets Connection Engine
@st.cache_resource(ttl=3)  # Low TTL during configuration testing
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

# 🚨 CRITICAL: Check this ID very closely against your browser URL string!
SPREADSHEET_ID = "1Cc0MnMtMfwfhyGWpPeQULLVjuSs1dNs91Yf98PW0SL0"

try:
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # Dynamic worksheet finder that ignores trailing/leading spaces
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
    
    st.markdown("---")
    st.markdown("### 🔍 Live Connection Diagnostic Engine")
    st.info("Scanning Google Drive to see exactly what files this bot has explicit permission to open right now...")
    
    try:
        visible_sheets = gc.openall()
        if not visible_sheets:
            st.error("⚠️ **The bot logged in successfully, but finds 0 spreadsheets.**")
            st.write("This means Google's servers haven't applied the permission update yet, or the sheet was shared to a slightly different service account email than what is in your secrets.")
        else:
            st.success(f"✅ **The bot successfully found {len(visible_sheets)} spreadsheet(s) on your account:**")
            for sheet in visible_sheets:
                st.write(f"• 📂 **Title:** `{sheet.title}` | 🔑 **ID:** `{sheet.id}`")
            st.info("👉 Match the ID above with the `SPREADSHEET_ID` inside your code to fix the mismatch instantly!")
    except Exception as diag_err:
        st.error(f"Diagnostic tool failed to search: {diag_err}")
        
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
    
    if not leaderboard_sorted.empty and leaderboard_sorted.loc[0, 'Points'] > 0:
        leaderboard_sorted.loc[0, 'Participant'] = "🥇 " + leaderboard_sorted.loc[0, 'Participant']
        
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
        
        # Opening days evaluation parameters
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
            st.info("No matches scheduled right now are available for prediction.")
        else:
            match_options = open_matches.apply(lambda r: f"Match {r['Match_ID']}: {r['Home_Team']} vs {r['Away_Team']} ({r['Kickoff_AEST'].strftime('%d %b')})", axis=1).tolist()
            selected_pred_match = st.selectbox("Choose an upcoming match:", match_options)
            
            m_id = selected_pred_match.split(":")[0].replace("Match ", "").strip()
            m_idx = matches_df[matches_df['Match_ID'] == m_id].index[0]
            m_row = matches_df.loc[m_idx]
            
            is_locked = current_time >= m_row['Kickoff_AEST']
            lock_status = "🔒 LOCKED" if is_locked else "⏳ Open for Predictions"
            st.write(f"⏰ **Kickoff:** {m_row['Kickoff_AEST'].strftime('%d %b, %I:%M %p')} AEST ({lock_status})")
            
            existing_out = str(m_row[f'{user}_Outcome']) if f'{user}_Outcome' in matches_df.columns and pd.notna(m_row[f'{user}_Outcome']) else "None"
            existing_score = str(m_row[f'{user}_Score']) if f'{user}_Score' in matches_df.columns and pd.notna(m_row[f'{user}_Score']) else "None"
            
            st.info(f"Current saved lock in sheet: **{existing_out}** | **{existing_score}**")
            st.divider()
            
            if is_locked:
                st.warning("This match has already kicked off! You can no longer modify entries.")
            else:
                p_out = st.selectbox("1. Who will win?", ["Select outcome...", m_row['Home_Team'], m_row['Away_Team'], "Draw"])
                
                col1, col2 = st.columns(2)
                with col1:
                    p_home_score = st.number_input(f"{m_row['Home_Team']} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
                with col2:
                    p_away_score = st.number_input(f"{m_row['Away_Team']} Predicted Goals", min_value=0, max_value=20, step=1, value=0)
                    
                predicted_score_str = f"{p_home_score}-{p_away_score}"
                
                if st.button("Lock Prediction In"):
                    if p_out == "Select outcome...":
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
                            
                            st.success("🔥 Prediction saved straight to the Google Sheet!")
                            st.rerun()
                        except Exception as write_err:
                            st.error(f"Failed to update spreadsheet cells: {write_err}")

# --- TAB 3: ADMIN ENGINE ---
with tab3:
    st.subheader("Admin Scoring Panel")
    admin_password = st.text_input("Enter Password", type="password")
    
    if admin_password == "kmart20":
        st.success("Welcome back, HD.")
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
            
            st.markdown("### 🧮 Points Calculations for HD to update in Sheet:")
            
            for p in participants:
                p_out_col = f'{p}_Outcome'
                p_score_col = f'{p}_Score'
                
                p_out = str(match_row[p_out_col]).strip() if p_out_col in matches_df.columns and pd.notna(match_row[p_out_col]) else ""
                p_score = str(match_row[p_score_col]).strip() if p_score_col in matches_df.columns and pd.notna(match_row[p_score_col]) else ""
                
                outcome_correct = (p_out.lower() == actual_outcome.lower())
                score_correct = (p_score == actual_score_str)
                
                if outcome_correct and score_correct:
                    st.success(f"🔥 **{p}** got BOTH right! Outcome: {p_out} | Score: {p_score} — **Award +20 Points!**")
                elif outcome_correct:
                    st.info(f"👍 **{p}** got the Winner/Draw RIGHT (`{p_out}`), but score wrong — **Award +10 Points!**")
                else:
                    st.write(f"❌ {p} got 0 points.")
                    
            st.info("📌 **Next Step:** Manually update your Google Sheet 'Leaderboard' tab with these points, set the match 'Status' to 'Completed', and you're good to go!")
    elif admin_password:
        st.error("Incorrect password.")
