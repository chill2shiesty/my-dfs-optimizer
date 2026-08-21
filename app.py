import streamlit as st
import requests
import pandas as pd

# =====================================================================
# CONFIGURATION & PAGE SETUP
# =====================================================================
st.set_page_config(
    page_title="Free DFS Prop Optimizer",
    page_icon="🔥",
    layout="wide"
)

# --- CONFIGURATION BAR ---
st.sidebar.header("⚙️ Configuration")
# Sign up at https://the-odds-api.com for a free key
API_KEY = st.sidebar.text_input("Enter your The Odds API Key:", type="password", value="")

# Interactive dropdown options
SPORT = st.sidebar.selectbox(
    "Select Sport:",
    options=["basketball_nba", "americanfootball_nfl", "basketball_ncaab", "baseball_mlb"],
    index=0
)

MARKET = st.sidebar.selectbox(
    "Select Prop Market:",
    options=[
        ("player_points", "Player Points"),
        ("player_pass_yds", "Passing Yards"),
        ("player_rush_yds", "Rushing Yards"),
        ("player_rebounds", "Rebounds"),
        ("player_assists", "Assists")
    ],
    format_func=lambda x: x[1]
)[0]

# Math benchmark: DFS slips need > 54.25% to break even in the long run
TARGET_PROB = st.sidebar.slider("Minimum Win Probability (%)", min_value=50.0, max_value=60.0, value=54.25, step=0.05) / 100

# =====================================================================
# MATHEMATICAL CONVERSION FUNCTIONS
# =====================================================================
def american_to_implied(odds):
    """Converts American moneyline odds into raw probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def calculate_fair_probability(over_odds, under_odds):
    """Strips the sportsbook juice to isolate the true fair win percentage."""
    p_over = american_to_implied(over_odds)
    p_under = american_to_implied(under_odds)
    total_implied = p_over + p_under
    return (p_over / total_implied), (p_under / total_implied)

# =====================================================================
# DATA RETRIEVAL
# =====================================================================
def fetch_data():
    if not API_KEY:
        st.warning("Please input your API key in the sidebar menu.")
        return None
        
url = f"https://the-odds-api.com{SPORT}/odds/"

    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": MARKET,
        "oddsFormat": "american"
    }
    
    with st.spinner("Fetching live market lines from sportsbooks..."):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error. Status Code: {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Network error: {e}")
            return None

# =====================================================================
# MAIN USER INTERFACE
# =====================================================================
st.title("🔥 Free DFS Positive Expected Value (+EV) Optimizer")
st.markdown("This dashboard finds player prop lines where sportsbooks heavily favor one side, making them profitable to target on flat-rate fantasy platforms.")

if st.button("🔄 Refresh Live Odds Data"):
    st.cache_data.clear()

raw_games = fetch_data()

if raw_games:
    rows = []
    
    # Process nested JSON data into a clean data list
    for game in raw_games:
        for bookmaker in game.get("bookmakers", []):
            book_name = bookmaker.get("title")
            for market in bookmaker.get("markets", []):
                if market.get("key") == MARKET:
                    player_data = {}
                    for outcome in market.get("outcomes", []):
                        player = outcome.get("description")
                        name = outcome.get("name") # Over or Under
                        odds = outcome.get("price")
                        point = outcome.get("point")
                        
                        if player not in player_data:
                            player_data[player] = {"line": point}
                        player_data[player][name] = odds

                    for player, odds_info in player_data.items():
                        over_odds = odds_info.get("Over")
                        under_odds = odds_info.get("Under")
                        line = odds_info.get("line")
                        
                        if over_odds and under_odds:
                            fair_over, fair_under = calculate_fair_probability(over_odds, under_odds)
                            
                            # Log the best target side based on your threshold filter
                            if fair_over >= TARGET_PROB:
                                rows.append([player, "OVER", line, f"{over_odds}/{under_odds}", book_name, round(fair_over * 100, 2)])
                            elif fair_under >= TARGET_PROB:
                                rows.append([player, "UNDER", line, f"{over_odds}/{under_odds}", book_name, round(fair_under * 100, 2)])

    # Display findings in an interactive table if any exist
    if rows:
        df = pd.DataFrame(rows, columns=["Player Name", "Target Bet", "Line Projection", "Bookmaker Odds (O/U)", "Sportsbook Source", "True Win %"])
        # Always rank the absolute highest math edge at the very top
        df = df.sort_values(by="True Win %", ascending=False).reset_index(drop=True)
        
        st.success(f"Discovered {len(df)} positive value opportunities matching your parameters!")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No props currently cross your minimum win percentage threshold. Try lowering the target slider slightly.")
