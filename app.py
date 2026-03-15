import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from src.leagues.nhl.league import NHLLeague
from src.leagues.shl.league import SHLLeague
from src.core.elo import calculate_elo, build_elo_rankings
from src.tools.analytics import compare_elo_vs_standings, build_interdivision_matrix
from src.tools.simulator import simulate_season_and_playoffs_from_today

# Initialize session state for parameters
if 'k_factor' not in st.session_state:
    st.session_state.k_factor = 32.0
if 'home_ice_advantage' not in st.session_state:
    st.session_state.home_ice_advantage = 33.0
if 'initial_elo' not in st.session_state:
    st.session_state.initial_elo = 1500.0
if 'ot_win_weight' not in st.session_state:
    st.session_state.ot_win_weight = 0.67
if 'so_win_weight' not in st.session_state:
    st.session_state.so_win_weight = 0.55
if 'num_simulations' not in st.session_state:
    st.session_state.num_simulations = 1000
if 'league_choice' not in st.session_state:
    st.session_state.league_choice = "NHL"
if 'use_mov' not in st.session_state:
    st.session_state.use_mov = False
if 'mov_cap' not in st.session_state:
    st.session_state.mov_cap = 5

st.set_page_config(page_title="Hockey ELO Ratings", layout="wide")

st.title("Hockey ELO Ratings & Dashboard")

# Sidebar for parameters
st.sidebar.header("Data Source")
st.sidebar.selectbox("League", ["NHL", "SHL"], key="league_choice")

if st.session_state.league_choice == "SHL":
    league = SHLLeague()
else:
    league = NHLLeague()

available_seasons = league.get_available_seasons()
season_labels = list(available_seasons.keys())
season_label = st.sidebar.selectbox("Season", season_labels, index=0)
SEASON_SELECT = available_seasons[season_label]

st.sidebar.header("ELO Parameters")
st.sidebar.slider("Initial ELO", min_value=1000.0, max_value=2000.0, step=50.0, key="initial_elo")
st.sidebar.slider("K-Factor", min_value=1.0, max_value=100.0, step=1.0, key="k_factor")
st.sidebar.slider("Home Ice Advantage", min_value=0.0, max_value=200.0, step=1.0, key="home_ice_advantage")

st.sidebar.header("Game Type Weights")
st.sidebar.markdown("Define ELO points gained for wins (loser gets 1 - weight). 1.0 means winner takes all, 0.5 means a tie.")
st.sidebar.slider("Overtime Win (OTW) Weight", min_value=0.5, max_value=1.0, step=0.01, key="ot_win_weight")
st.sidebar.slider("Shootout Win (SOW) Weight", min_value=0.5, max_value=1.0, step=0.01, key="so_win_weight")

st.sidebar.header("Margin of Victory")
st.sidebar.markdown("Enable a multiplier based on goal differential for more dynamic ELO changes. Cap limits the max multiplier.")
st.sidebar.toggle("Enable MoV Multiplier", key="use_mov")
st.sidebar.slider("MoV Goal Differential Cap", min_value=1, max_value=10, step=1, key="mov_cap", disabled=not st.session_state.use_mov)

@st.cache_data(ttl=3600)
def fetch_game_data_v2(season, league_name):
    # This caching now implicitly ties into the resolved league class above.
    completed, remaining = league.fetch_games(season)
    return completed, remaining, league.get_teams(), league.team_info()

@st.cache_data(ttl=3600)
def compute_ratings(_completed_games, k_factor, home_ice, ot_win, so_win, initial_elo, use_mov, mov_cap, league_name, season_id):
    win_weights = {
        'REG_WIN': 1.0, 'REG_LOSS': 0.0,
        'OT_WIN': ot_win, 'OT_LOSS': 1.0 - ot_win,
        'SO_WIN': so_win, 'SO_LOSS': 1.0 - so_win
    }
    
    ratings, history, team_history = calculate_elo(
        league, _completed_games, initial_elo,
        k_factor, home_ice, win_weights, use_mov, mov_cap
    )
    comparison = compare_elo_vs_standings(league, ratings, _completed_games)
    records = league.build_team_records(_completed_games)
    divisions, interdivision_rows = build_interdivision_matrix(league, _completed_games, win_weights)
    return ratings, history, team_history, comparison, records, divisions, interdivision_rows

@st.cache_data(ttl=3600, show_spinner=False)
def get_sim_results(_completed, _remaining, ratings_dict, count, k, home, ot_win, so_win, use_mov, mov_cap, season_id, league_id):
    ww = {
        'REG_WIN': 1.0, 'REG_LOSS': 0.0,
        'OT_WIN': ot_win, 'OT_LOSS': 1.0 - ot_win,
        'SO_WIN': so_win, 'SO_LOSS': 1.0 - so_win
    }
    return simulate_season_and_playoffs_from_today(
        league, _completed, _remaining, ratings_dict, count,
        home_ice_advantage=home, k_factor=k, win_weights=ww,
        use_mov=use_mov, mov_cap=mov_cap
    )

try:
    with st.spinner('Loading data...'):
        completed_games, remaining_games, c_teams, c_team_info = fetch_game_data_v2(SEASON_SELECT, st.session_state.league_choice)
        if hasattr(league, '_teams'):
            league._teams = c_teams
        if hasattr(league, '_team_info'):
            league._team_info = c_team_info
        ratings, history, team_history, comparison, records, divisions, interdivision_rows = compute_ratings(
            completed_games, st.session_state.k_factor, st.session_state.home_ice_advantage,
            st.session_state.ot_win_weight, st.session_state.so_win_weight, st.session_state.initial_elo,
            st.session_state.use_mov, st.session_state.mov_cap,
            st.session_state.league_choice, SEASON_SELECT
        )
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()


# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Current Ratings", "ELO History", "ELO vs Standings", "Simulations", "Interdivision"])

with tab1:
    st.subheader(f"Current Ratings ({season_label})")
    
    df = pd.DataFrame(comparison)
    display_cols = ['elo_rank', 'standings_rank', 'rank_diff', 'team', 'conference', 'division', 'elo', 'Pts', 'GP', 'W', 'OTW', 'L', 'OTL']
    col_names = {
        'elo_rank': 'ELO Rank', 'standings_rank': 'Points Rank', 'rank_diff': 'Rank Diff',
        'team': 'Team', 'conference': 'Conference', 'division': 'Division',
        'elo': 'ELO', 'Pts': 'Points', 'OTW': 'OTW'
    }
    
    st.dataframe(df[display_cols].rename(columns=col_names), width="stretch", hide_index=True)

with tab2:
    st.subheader("ELO Rating History")
    
    ranked_teams = [t for r, t, e in build_elo_rankings(ratings)]
    selected_teams = st.multiselect("Select teams to plot:", options=sorted(ranked_teams), default=ranked_teams[:5])
    
    if selected_teams:
        fig = go.Figure()
        
        for team in selected_teams:
            history_data = team_history[team]
            x_vals = list(range(len(history_data)))
            y_vals = []
            for item in history_data:
                if isinstance(item, tuple) and len(item) == 2:
                    y_vals.append(item[1])
                elif isinstance(item, dict):
                    y_vals.append(item.get('elo_after', item.get('elo')))
                else:
                    y_vals.append(float(item))

            fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name=team))
            
        fig.update_layout(
            title="Team ELO Trajectories",
            xaxis_title="Games Played",
            yaxis_title="ELO Rating",
            height=600,
            hovermode="x unified"
        )
        st.plotly_chart(fig, width="stretch")

with tab3:
    st.subheader("ELO Rank vs Standings Rank")
    
    df = pd.DataFrame(comparison)
    
    fig = px.scatter(
        df, 
        x="standings_rank", 
        y="elo_rank", 
        text="team",
        hover_data=["elo", "Pts"],
        color="conference",
        title="Standings Rank vs ELO Rank"
    )
    
    fig.add_trace(go.Scatter(
        x=[1, len(ranked_teams)], y=[1, len(ranked_teams)], mode='lines', name='Ideal Alignment', line=dict(dash='dash', color='gray')
    ))
    
    fig.update_traces(textposition='top center')
    fig.update_layout(
        xaxis_title="Standings Rank", 
        yaxis_title="ELO Rank",
        height=600,
        xaxis=dict(autorange="reversed"),
        yaxis=dict(autorange="reversed")
    )
    
    st.plotly_chart(fig, width="stretch")

with tab4:
    st.subheader("Season & Playoffs Simulations")
    st.write("Run Monte Carlo simulations to predict playoff odds and Stanley Cup winners based on remaining schedule and current ELO.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.number_input("Simulation Iterations", min_value=100, max_value=50000, step=500, key="num_simulations")
        run_btn = st.button("Run Simulations", type="primary")
        
    with col2:
        st.info("Simulating the remainder of the season and playoffs takes a few seconds. Lower iteration counts are faster but more volatile.")
        
    if run_btn:
        with st.spinner(f"Running {st.session_state.num_simulations} simulations..."):
            results = get_sim_results(
                completed_games, remaining_games, ratings, st.session_state.num_simulations,
                st.session_state.k_factor, st.session_state.home_ice_advantage,
                st.session_state.ot_win_weight, st.session_state.so_win_weight,
                st.session_state.use_mov, st.session_state.mov_cap,
                SEASON_SELECT, st.session_state.league_choice
            )
            
            df_sim = pd.DataFrame(results)
            st.write(f"### Simulation Results ({st.session_state.num_simulations} runs)")
            
            playoff_cols_dict = league.get_playoff_column_names()
            format_dict = {
                'Cur. ELO': '{:.2f}', 
                playoff_cols_dict.get('make_playoffs', 'Make Playoffs'): '{:.1%}', 
                playoff_cols_dict.get('make_qf', 'Round 2'): '{:.1%}', 
                playoff_cols_dict.get('make_sf', 'Conf Finals'): '{:.1%}', 
                playoff_cols_dict.get('make_final', 'Finals'): '{:.1%}', 
                playoff_cols_dict.get('win_champ', 'Champ'): '{:.1%}'
            }
            
            display_cols = [
                'team', 'conference', 'division', 'current_elo', 
                'make_playoffs_prob', 'make_qf_prob', 'make_sf_prob', 
                'make_final_prob', 'win_champ_prob'
            ]
            
            rename_cols = {
                'team': 'Team', 'conference': 'Conf', 'division': 'Div', 'current_elo': 'Cur. ELO',
                'make_playoffs_prob': playoff_cols_dict.get('make_playoffs', 'Make Playoffs'), 
                'make_qf_prob': playoff_cols_dict.get('make_qf', 'Round 2'),
                'make_sf_prob': playoff_cols_dict.get('make_sf', 'Conf Finals'), 
                'make_final_prob': playoff_cols_dict.get('make_final', 'Finals'), 
                'win_champ_prob': playoff_cols_dict.get('win_champ', 'Champ')
            }
            
            df_display = df_sim[display_cols].rename(columns=rename_cols)
            styled_df = df_display.style.format(format_dict)
            
            st.dataframe(styled_df, width="stretch", hide_index=True)
            
            st.write("### Championship Probabilities")
            fig_sim = px.bar(
                df_sim.head(16), 
                x='team', y='win_champ_prob',
                title=f"Top 16 Championship Probabilities ({st.session_state.num_simulations} Sims)",
                labels={'win_champ_prob': playoff_cols_dict.get('win_champ', 'Championship Probability'), 'team': 'Team'},
                color='conference'
            )
            fig_sim.update_layout(yaxis_tickformat='.1%')
            st.plotly_chart(fig_sim, width="stretch")

with tab5:
    st.subheader("Interdivision Score Percentage Matrix")
    st.write("Values represent average ELO-style game scores by row division vs column division.")
    st.write("*(1.0 means the row division won every game in regulation, 0.0 means they lost every game in regulation)*")
    
    matrix_data = []
    
    for row_idx, row in enumerate(interdivision_rows):
        matrix_row = []
        for col_idx, d in enumerate(divisions):
            val = row[d]
            matrix_row.append(float("nan") if val is None else val)
        matrix_data.append(matrix_row)
        
    fig_heat = px.imshow(
        matrix_data,
        x=divisions, y=divisions,
        labels=dict(x="Opponent Division", y="Division", color="Average Score Pct"),
        text_auto=".3f", color_continuous_scale="RdBu_r", aspect="auto"
    )
    
    fig_heat.update_layout(
        title="Interdivision Win/Loss Matrix", height=500,
        xaxis_title="Opponent Division", yaxis_title="Division", coloraxis_colorbar=dict(title="%")
    )
    st.plotly_chart(fig_heat, width="stretch")