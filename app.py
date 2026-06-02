import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# Page setup for modern mobile responsiveness
st.set_page_config(page_title="World Cup Challenge", page_icon="🏆", layout="centered")

st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# Directly link the public Google Sheet CSV export URLs
SHEET_ID = "1Cc0MnMtMfwfhyGWpPeQULLVjuSs1dNs91Yf98PW0SL0"
MATCHES_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matches"
LEADERBOARD_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Leaderboard"

# Helper function to get current AEST time safely
def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

# Load Data Safely
try:
    matches_df = pd.read_csv(MATCHES_URL)
    leaderboard_df = pd.read_csv(LEADERBOARD_URL)
except Exception as e:
    st.error("Could not read data from Google Sheets. Make sure 'Anyone with the link' is set to Editor/Viewer in your Share settings.")
    st.stop()

# Clean up column names
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
        
        # Only show matches that haven't kicked off yet
        open_matches = matches_df[matches_df['Kickoff_AEST'] > current_time].copy()
        
        if open_matches.empty:
            st.info("No upcoming matches available for prediction right now.")
        else:
            match_options = open_matches.apply(lambda r: f"Match {r['Match_ID']}: {r['Home_Team']} vs {r['Away_Team']}", axis=1).tolist()
            selected_pred_match = st.selectbox("Choose a match:", match_options)
            
            m_id = selected_pred_match.split(":")[0].replace("Match ", "").strip()
            m_row = matches_df[matches_df['Match_ID'] == m_id].iloc[0]
            
            st.write(f"⏰ **Kickoff:** {m_row['Kickoff_AEST'].strftime('%d %b, %I:%M %p')} AEST")
            
            # Show current locked values from the spreadsheet if they exist
            existing_out = str(m_row[f'{user}_Outcome']) if f'{user}_Outcome' in matches_df.columns and pd.notna(m_row[f'{user}_Outcome']) else "None"
            existing_score = str(m_row[f'{user}_Score']) if f'{p}_Score' in matches_df.columns and pd.notna(m_row[f'{user}_Score']) else "None"
            
            st.info(f"Current saved lock: **{existing_out}** | **{existing_score}**")
            st.divider()
            
            # Input via Dropdowns to eliminate free-text typos
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
                else:
                    # --- DRAW VALIDATION CHECKS ---
                    if p_out == "Draw" and p_home_score != p_away_score:
                        st.error(f"❌ Validation Error: You selected 'Draw', but your score prediction ({predicted_score_str}) is not a tie! Please update your choices.")
                    elif p_out != "Draw" and p_home_score == p_away_score:
                        st.error(f"❌ Validation Error: You predicted a tie score ({predicted_score_str}), but did not select 'Draw' as the outcome! Please update your choices.")
                    else:
                        # Success instructions
                        st.success("✅ Prediction Validated! Copy and paste these exact values into the Google Sheet columns:")
                        st.code(f"For column {user}_Outcome: {p_out}\nFor column {user}_Score: {predicted_score_str}")
                        st.warning("Note: Because this is the lightweight, secure version, paste these values directly into your row in the shared Google Sheet to finalize the lock!")

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
            
            # Determine Actual Outcome
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
