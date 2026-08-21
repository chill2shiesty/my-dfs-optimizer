import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Free Sports Optimizer", page_icon="🔥", layout="wide")

st.sidebar.header("⚙️ Configuration")
API_KEY = st.sidebar.text_input("Enter your The Odds API Key:", type="password", value="")
SPORT = st.sidebar.selectbox("Select Sport:", options=["basketball_nba", "americanfootball_nfl", "baseball_mlb"], index=0)
MARKET = st.sidebar.selectbox("Select Line Market:", options=[("h2h", "Game Winner (Moneyline)"), ("spreads", "Point Spreads")], format_func=lambda x: x[1])[0]
TARGET_PROB = st.sidebar.slider("Minimum Win Probability (%)", min_value=50.0, max_value=60.0, value=52.5, step=0.5) / 100

def american_to_implied(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

if API_KEY:
    url = f"https://the-odds-api.com{SPORT}/odds/?apiKey={API_KEY}&regions=us&markets={MARKET}&oddsFormat=american"
    response = requests.get(url)
    
    if response.status_code == 200:
        games = response.json()
        rows = []
        for game in games:
            for book in game.get("bookmakers", []):
                for mkt in book.get("markets", []):
                    outcomes = mkt.get("outcomes", [])
                    if len(outcomes) >= 2:
                        o1, o2 = outcomes[0], outcomes[1]
                        p1, p2 = american_to_implied(o1.get("price")), american_to_implied(o2.get("price"))
                        f1, f2 = p1 / (p1 + p2), p2 / (p1 + p2)
                        
                        if f1 >= TARGET_PROB:
                            rows.append([game.get("home_team"), game.get("away_team"), o1.get("name"), o1.get("price"), book.get("title"), round(f1*100, 2)])
                        if f2 >= TARGET_PROB:
                            rows.append([game.get("home_team"), game.get("away_team"), o2.get("name"), o2.get("price"), book.get("title"), round(f2*100, 2)])
        
        if rows:
            df = pd.DataFrame(rows, columns=["Home", "Away", "Selection", "Odds", "Sportsbook", "True Win %"])
            st.dataframe(df.sort_values(by="True Win %", ascending=False), use_container_width=True)
        else:
            st.info("No major line discrepancies found right now. Try lowering the target slider.")
    else:
        st.error(f"API Error: {response.status_code}. Free keys do not support player props.")
