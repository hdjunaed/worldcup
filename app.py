import streamlit as st
import pandas as pd
from datetime import datetime
import pytz

# Set up page config for a modern mobile-responsive look
st.set_page_config(page_title="World Cup Challenge", page_icon="🏆", layout="centered")

# App title and header
st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# Directly link the public Google Sheet CSV export URLs
SHEET_ID = "1Cc0MnMtMfwfhyGWpPeQULLVjuSs1dNs91Yf98PW0SL0"
MATCHES_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Matches"
LEADERBOARD_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Leaderboard"

# Helper function to get current AEST time safely
def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

# 1. Load Data Directly via CSV links
try:
    matches_df = pd.read_csv(MATCHES_URL)
    leaderboard_df = pd.read_csv(LEADERBOARD_URL)
except Exception as e:
    st.error("Could not read data from Google Sheets. Make sure 'Anyone with the link' is set to Editor/Viewer in your Share settings.")
    st.stop()

# Clean up column names in case of hidden spaces
matches_df.columns = matches_df.columns.str.strip()
leaderboard_df.columns = leaderboard_df.columns.str.strip()

# Ensure types are correct
matches_df['Match_ID'] = matches_df['Match_ID'].astype(str)
matches_df['Kickoff_AEST'] = pd.to_datetime(matches_df['Kickoff_AEST'])

# --- APP TABS ---
tab1, tab2 = st.tabs(["📊 Leaderboard", "🔒 Admin Engine"])

# --- TAB 1: LEADERBOARD ---
with tab1:
    st.subheader("Current Standings")
    
    # Sort leaderboard by highest points
    leaderboard_sorted = leaderboard_df.sort_values(by="Points", ascending=False).reset_index(drop=True)
    
    # Add a golden crown to whoever is sitting in 1st place
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
    st.info("💡 Tip: To log predictions, type your scores directly into your column in the shared Google Sheet before kickoff!")

# --- TAB 2: ADMIN ENGINE ---
with tab2:
    st.subheader("Admin Score Entry")
    st.write("HD, use this panel to finalize matches and view points calculation instructions.")
    
    admin_password = st.text_input("Enter Admin Password", type="password")
    
    if admin_password == "kmart20":
        st.success("Access Granted, Welcome HD.")
        
        # Filter down to matches that don't have a result yet
        upcoming_matches = matches_df[matches_df['Status'] != 'Completed']
        
        if upcoming_matches.empty:
            st.info("All listed matches have been finalized!")
        else:
            match_options = upcoming_matches.apply(lambda r: f"Match {r['Match_ID']}: {r['Home_Team']} vs {r['Away_Team']}", axis=1).tolist()
            selected_match_str = st.selectbox("Select match to check scores:", match_options)
            
            selected_id = selected_match_str.split(":")[0].replace("Match ", "").strip()
            match_row = matches_df[matches_df['Match_ID'] == selected_id].iloc[0]
            
            st.write(f"**Kickoff:** {match_row['Kickoff_AEST'].strftime('%Y-%m-%d %H:%M')} AEST")
            
            col1, col2 = st.columns(2)
            with col1:
                act_home = st.number_input(f"{match_row['Home_Team']} Score", min_value=0, step=1, value=0)
            with col2:
                act_away = st.number_input(f"{match_row['Away_Team']} Score", min_value=0, step=1, value=0)
                
            actual_score_str = f"{act_home}-{act_away}"
            
            st.markdown("### 🧮 Points Summary for this score:")
            participants = ['HD', 'LS', 'CD', 'ND', 'GB', 'SB']
            
            for p in participants:
                guess = str(match_row[f'{p}_Guess']).strip()
                if guess == actual_score_str:
                    st.write(f"✅ **{p}** guessed {guess} — **+10 Points!**")
                else:
                    st.write(f"❌ {p} guessed {guess} — 0 Points")
                    
            st.info("📌 Since we are using the simple direct-link layout, type the final score into your Google Sheet's 'Actual_Result' column, change Status to 'Completed', and update the Leaderboard tab. The app webpage will refresh instantly for everyone!")
            
    elif admin_password:
        st.error("Incorrect password.")
