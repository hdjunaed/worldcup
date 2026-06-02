import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# Set up page config for a modern mobile-responsive look
st.set_page_config(page_title="World Cup Challenge", page_icon="🏆", layout="centered")

# App title and header
st.title("🏆 WORLD CUP PREDICTION CHALLENGE")
st.caption("Broadcast live on SBS | All times shown in AEST")

# Establish connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Helper function to get current AEST time safely
def get_current_aest():
    return datetime.now(pytz.timezone('Australia/Sydney')).replace(tzinfo=None)

# 1. Load Data
try:
    matches_df = conn.read(worksheet="Matches", ttl=10)
    leaderboard_df = conn.read(worksheet="Leaderboard", ttl=10)
except Exception as e:
    st.error("Could not connect to Google Sheets. Check your configuration secrets.")
    st.stop()

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
    st.write("HD, use this secure panel to finalize matches and calculate group points automatically.")
    
    admin_password = st.text_input("Enter Admin Password", type="password")
    
    # Simple clear-text lock. Change "kmart20" to whatever passcode you want.
    if admin_password == "kmart20":
        st.success("Access Granted, Welcome HD.")
        
        # Filter down to matches that don't have a result yet
        upcoming_matches = matches_df[matches_df['Status'] != 'Completed']
        
        if upcoming_matches.empty:
            st.info("All listed matches have been finalized!")
        else:
            # Dropdown to pick which match to settle
            match_options = upcoming_matches.apply(lambda r: f"Match {r['Match_ID']}: {r['Home_Team']} vs {r['Away_Team']}", axis=1).tolist()
            selected_match_str = st.selectbox("Select match to finalize:", match_options)
            
            # Extract Match ID from selected string
            selected_id = selected_match_str.split(":")[0].replace("Match ", "").strip()
            match_row = matches_df[matches_df['Match_ID'] == selected_id].iloc[0]
            
            st.write(f"**Kickoff:** {match_row['Kickoff_AEST'].strftime('%Y-%m-%d %H:%M')} AEST")
            
            # Numeric inputs for the actual final result
            col1, col2 = st.columns(2)
            with col1:
                act_home = st.number_input(f"{match_row['Home_Team']} Score", min_value=0, step=1, value=0)
            with col2:
                act_away = st.number_input(f"{match_row['Away_Team']} Score", min_value=0, step=1, value=0)
                
            if st.button("Finalise Match & Update Ladder"):
                actual_score_str = f"{act_home}-{act_away}"
                
                # Update match values inside our local dataframe copy
                idx = matches_df[matches_df['Match_ID'] == selected_id].index[0]
                matches_df.at[idx, 'Actual_Result'] = actual_score_str
                matches_df.at[idx, 'Status'] = 'Completed'
                
                # Point Calculation Matrix
                # Players: HD, LS, CD, ND, GB, SB
                participants = ['HD', 'LS', 'CD', 'ND', 'GB', 'SB']
                points_to_add = {p: 0 for p in participants}
                
                for p in participants:
                    guess = str(match_row[f'{p}_Guess']).strip()
                    # Check if guess matches the actual final score string exactly (e.g. "2-1")
                    if guess == actual_score_str:
                        points_to_add[p] = 10
                
                # Update Leaderboard numbers
                for p in participants:
                    l_idx = leaderboard_df[leaderboard_df['Participant'] == p].index[0]
                    leaderboard_df.at[l_idx, 'Points'] += points_to_add[p]
                
                # Push updates live to your Google Sheets tabs
                try:
                    conn.update(worksheet="Matches", data=matches_df)
                    conn.update(worksheet="Leaderboard", data=leaderboard_df)
                    st.success(f"Successfully processed Match {selected_id}! Scores updated.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Failed to update spreadsheet: {ex}")
    elif admin_password:
        st.error("Incorrect password.")