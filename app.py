import math
import requests
import streamlit as st

# --- HELPER UTILITY ---
def clean_country_name(name):
    """
    Cleans and standardizes country names by stripping trailing formatting
    and removing structural text strings.
    """
    if not name:
        return ""
    # Strip common cleanups like 'Win', 'Draw', or whitespaces
    return str(name).replace(" Win", "").replace(" Draw", "").strip()

# --- CORE PARSING & SIMULATION ENGINE ---
@st.cache_data(ttl=3600)
def fetch_api_football_forecast(home_team, away_team):
    def normalize_name(name):
        n = clean_country_name(name).lower().strip()
        mapping = {
            'united states': 'usa', 'united states of america': 'usa',
            'korea republic': 'south korea', 'republic of korea': 'south korea',
            'czechia': 'czech republic', 'czech rep': 'czech republic',
            'bosnia & herz.': 'bosnia and herzegovina', 'bosnia & herzegovina': 'bosnia and herzegovina',
            "cote d'ivoire": "cote d'ivoire", 'ivory coast': "cote d'ivoire",
            'congo dr': 'dr congo', 'democratic republic of the congo': 'dr congo'
        }
        return mapping.get(n, n)

    def american_to_prob(odds_str):
        """Converts an American moneyline string (e.g. '-1200', '+2800') into implied probability."""
        if odds_str is None:
            return None
        try:
            odds = float(str(odds_str).replace('+', ''))
            if odds > 0:
                return 100.0 / (odds + 100.0)
            else:
                return abs(odds) / (abs(odds) + 100.0)
        except Exception:
            return None

    home_clean = normalize_name(home_team)
    away_clean = normalize_name(away_team)
    
    debug_line = ""
    api_success = False

    # Manual backup / baseline fallback system
    power_tiers = {
        'france': 95, 'argentina': 95, 'spain': 94, 'england': 92, 'brazil': 91,
        'portugal': 89, 'netherlands': 88, 'belgium': 88, 'germany': 87, 'morocco': 86,
        'croatia': 85, 'uruguay': 84, 'norway': 84, 'colombia': 83, 'usa': 83, 'japan': 82, 
        'senegal': 81, 'mexico': 81, 'denmark': 81, 'switzerland': 80, 'south korea': 79,
        'australia': 78, 'turkiye': 78, 'ecuador': 77, 'austria': 77, 'sweden': 77,
        'nigeria': 76, 'algeria': 76, 'egypt': 76, 'scotland': 76, 'canada': 75, 
        'czech republic': 75, 'ukraine': 75, 'poland': 74, 'wales': 74, 'panama': 74, 
        'paraguay': 74, 'ghana': 74, 'serbia': 73, 'tunisia': 73, 'cameroon': 73,
        'dr congo': 73, 'bosnia and herzegovina': 73, "cote d'ivoire": 73, 'qatar': 72, 
        'south africa': 72, 'uzbekistan': 71, 'saudi arabia': 71, 'iraq': 71, 
        'jordan': 69, 'cape verde': 69, 'haiti': 68, 'curacao': 67, 'new zealand': 66
    }
    
    h_str = power_tiers.get(home_clean, 74)
    a_str = power_tiers.get(away_clean, 74)
    
    rating_gap = (h_str + 2.0) - a_str
    expected_gd = rating_gap * 0.075
    total_expected_goals = 2.75
    
    best_lam = max(0.1, (total_expected_goals + expected_gd) / 2.0)
    best_mu = max(0.1, (total_expected_goals - expected_gd) / 2.0)

    try:
        espn_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
        response = requests.get(espn_url, timeout=5)
        
        if response.status_code == 200:
            events = response.json().get("events", [])
            match_found = False
            
            for ev in events:
                competitions = ev.get("competitions", [{}])
                if not competitions:
                    continue
                
                competitors = competitions[0].get("competitors", [])
                api_home_name = api_home_disp = api_home_abbr = ""
                api_away_name = api_away_disp = api_away_abbr = ""
                
                for comp in competitors:
                    role = comp.get("homeAway")
                    team_obj = comp.get("team", {})
                    t_name = team_obj.get("name", "").lower().strip()
                    t_disp = team_obj.get("displayName", "").lower().strip()
                    t_abbr = team_obj.get("abbreviation", "").lower().strip()
                    
                    if role == "home":
                        api_home_name, api_home_disp, api_home_abbr = t_name, t_disp, t_abbr
                    elif role == "away":
                        api_away_name, api_away_disp, api_away_abbr = t_name, t_disp, t_abbr

                # Check all naming properties for an accurate match intersection
                all_identifiers = [api_home_name, api_home_disp, api_home_abbr, api_away_name, api_away_disp, api_away_abbr]
                
                if home_clean in all_identifiers and away_clean in all_identifiers:
                    match_found = True
                    odds_list = competitions[0].get("odds", [])
                    
                    if odds_list:
                        moneyline = odds_list[0].get("moneyline", {})
                        h_odds_raw = moneyline.get("home", {}).get("close", {}).get("odds")
                        a_odds_raw = moneyline.get("away", {}).get("close", {}).get("odds")
                        d_odds_raw = moneyline.get("draw", {}).get("close", {}).get("odds")
                        
                        p_h = american_to_prob(h_odds_raw)
                        p_a = american_to_prob(a_odds_raw)
                        p_d = american_to_prob(d_odds_raw)
                        
                        if p_h is not None and p_a is not None and p_d is not None:
                            if home_clean in [api_home_name, api_home_disp, api_home_abbr]:
                                t_h_raw = p_h
                                t_a_raw = p_a
                            else:
                                t_h_raw = p_a
                                t_a_raw = p_h
                            t_d_raw = p_d
                            
                            # Standard clear normalization to strip bookmaker house vig
                            total_p = t_h_raw + t_a_raw + t_d_raw
                            t_h = t_h_raw / total_p
                            t_a = t_a_raw / total_p
                            t_d = t_d_raw / total_p
                            
                            # Multi-variable math optimization loop
                            best_err = float('inf')
                            for l_idx in range(2, 45):
                                l = l_idx / 10.0
                                for m_idx in range(2, 45):
                                    m = m_idx / 10.0
                                    sim_h, sim_d, sim_a = 0.0, 0.0, 0.0
                                    for i in range(7):
                                        p_i = (l**i * math.exp(-l)) / math.factorial(i)
                                        for j in range(7):
                                            p_j = (m**j * math.exp(-m)) / math.factorial(j)
                                            if i > j: sim_h += p_i * p_j
                                            elif i == j: sim_d += p_i * p_j
                                            else: sim_a += p_i * p_j
                                    err = (sim_h - t_h)**2 + (sim_d - t_d)**2 + (sim_a - t_a)**2
                                    if err < best_err:
                                        best_err = err
                                        best_lam, best_mu = l, m
                            
                            api_success = True
                            debug_line = f"⚡ LIVE API CONNECTED: Successfully loaded active DraftKings lines (Home Odds: {h_odds_raw} | Draw Odds: {d_odds_raw} | Away Odds: {a_odds_raw})"
                            break
                        else:
                            debug_line = "⚠️ API WARNING: Match located, but failed to parse moneyline structure contents into numeric formats."
                    else:
                        debug_line = "⚠️ API WARNING: Match found in payload, but the odds matrix array is currently empty."
            
            if not match_found:
                debug_line = f"⚙️ STATIC MODEL CALCULATOR ACTIVE: API was reached, but no matches matching '{home_clean}' vs '{away_clean}' are active on today's schedule."
        else:
            debug_line = f"⚙️ STATIC MODEL CALCULATOR ACTIVE: ESPN Server responded with a broken status code ({response.status_code})."
            
    except Exception as e:
        debug_line = f"⚙️ STATIC MODEL CALCULATOR ACTIVE: Network request hit a wall. Trace error: {str(e)}"

    # Generate complete score matrices
    score_list = []
    for i in range(6):
        p_i = (best_lam**i * math.exp(-best_lam)) / math.factorial(i)
        for j in range(6):
            p_j = (best_mu**j * math.exp(-best_mu)) / math.factorial(j)
            prob = p_i * p_j
            
            if i > j: desc = f"{clean_country_name(home_team)} Win"
            elif i == j: desc = "Draw"
            else: desc = f"{clean_country_name(away_team)} Win"
                
            score_list.append({
                "score": f"{i}-{j}",
                "prob": round(prob * 100, 1),
                "desc": desc
            })
            
    score_list = sorted(score_list, key=lambda x: x['prob'], reverse=True)

    p_no_goals = math.exp(-(best_lam + best_mu))
    p_any_goal = 1.0 - p_no_goals
    
    first_home = round((best_lam / (best_lam + best_mu)) * p_any_goal * 100, 1)
    first_away = round((best_mu / (best_lam + best_mu)) * p_any_goal * 100, 1)
    first_none = round(p_no_goals * 100, 1)

    h_disp = clean_country_name(home_team)
    a_disp = clean_country_name(away_team)
    if best_lam > best_mu + 0.8:
        advice = f"{h_disp} are heavy clear metrics favorites via active markets."
    elif best_mu > best_lam + 0.8:
        advice = f"{a_disp} showcase strong value trends via active analytical models."
    else:
        advice = f"A structurally tight match. Expect a highly competitive layout."

    return {
        "first_home": first_home,
        "first_away": first_away,
        "first_none": first_none,
        "top_scores": score_list[:5], # Slices top 5 elements
        "advice": advice,
        "debug_line": debug_line,     # Confidence tracking flag output
        "is_live_api": api_success
    }

# --- STREAMLIT FRONTEND RENDERING INTERFACE ---
def main():
    st.set_page_config(page_title="Tournament Analytics Dashboard", page_icon="⚽", layout="wide")
    
    st.title("🏆 World Football Prediction Dashboard")
    st.markdown("This system evaluates upcoming fixtures, reads real-time API market positions, and simulates exact metrics breakdowns.")
    
    # Pre-populating a collection of dummy options representing active fixture records
    sample_fixtures = [
        {"Home_Team": "Spain", "Away_Team": "Cape Verde", "Group": "Group A"},
        {"Home_Team": "Egypt", "Away_Team": "Belgium", "Group": "Group B"},
        {"Home_Team": "Uruguay", "Away_Team": "Saudi Arabia", "Group": "Group A"},
        {"Home_Team": "New Zealand", "Away_Team": "Iran", "Group": "Group C"},
        {"Home_Team": "Iraq", "Away_Team": "Norway", "Group": "Group D"}
    ]
    
    # UI Selector for current game focuses
    st.sidebar.header("Fixture Control Room")
    match_labels = [f"{fix['Home_Team']} vs {fix['Away_Team']} ({fix['Group']})" for fix in sample_fixtures]
    selected_idx = st.sidebar.selectbox("Select Active Match To Analyze:", range(len(match_labels)), format_func=lambda x: match_labels[x])
    
    active_match = sample_fixtures[selected_idx]
    
    st.subheader(f"🏟️ Current Match Analysis: {active_match['Home_Team']} vs {active_match['Away_Team']}")
    
    # Execute backend forecasting processing pipelines
    with st.spinner("Fetching data pipelines and executing matrix simulations..."):
        forecast = fetch_api_football_forecast(active_match['Home_Team'], active_match['Away_Team'])
    
    # Render layout visual containers
    with st.container(border=True):
        st.markdown("### 📊 TAB-Calibrated Match Analysis")
        
        # CONFIDENCE PIPELINE BADGE RENDER
        if forecast["is_live_api"]:
            st.success(forecast["debug_line"])
        else:
            st.info(forecast["debug_line"])
            
        st.caption("Live bookmaker market expectations transformed into plain mathematical probabilities:")
        st.divider()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**⚽ Chance to Score First:**")
            st.markdown(f"• 🏃‍♂️ **{active_match['Home_Team']}**: `{forecast['first_home']}%` chance")
            st.markdown(f"• 🏃‍♂️ **{active_match['Away_Team']}**: `{forecast['first_away']}%` chance")
            st.markdown(f"• 🚫 **No Goals (0-0 Tie)**: `{forecast['first_none']}%` chance")
            
            st.write("")
            st.markdown("**💡 Strategic Advice:**")
            st.info(forecast["advice"])
            
        with col2:
            st.markdown("**🎯 Top 5 Most Likely Exact Final Scores:**")
            for idx, scr in enumerate(forecast["top_scores"]):
                # Medals for high distribution visualization weights
                medal = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else "🔹"
                st.markdown(f"{medal} Score **{scr['score']}** → `{scr['prob']}%` probability *({scr['desc']})*")

if __name__ == "__main__":
    main()
