import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from src.leagues.nhl.league import NHLLeague
from src.leagues.shl.league import SHLLeague
from src.core.elo import calculate_elo, build_elo_rankings
from src.tools.analytics import compare_elo_vs_standings, build_interdivision_matrix, estimate_home_ice_advantage
from src.tools.simulator import simulate_season_and_playoffs_from_today

BASE_ELO = 1000.0
SIM_RESULTS_SCHEMA_VERSION = "2026-03-17-placement-k-v1"

# Initialize session state for parameters
if 'k_factor' not in st.session_state:
    st.session_state.k_factor = 20.0
if 'placement_games' not in st.session_state:
    st.session_state.placement_games = 10
if 'placement_k_add' not in st.session_state:
    st.session_state.placement_k_add = 10.0
if 'home_ice_advantage' not in st.session_state:
    st.session_state.home_ice_advantage = 42.0
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
if 'use_date_cutoff' not in st.session_state:
    st.session_state.use_date_cutoff = False
if 'elo_cutoff_date' not in st.session_state:
    st.session_state.elo_cutoff_date = None
if 'cutoff_scope_key' not in st.session_state:
    st.session_state.cutoff_scope_key = ""
if 'home_ice_estimate_notice' not in st.session_state:
    st.session_state.home_ice_estimate_notice = ""
if 'pending_home_ice_advantage' not in st.session_state:
    st.session_state.pending_home_ice_advantage = None

# Apply pending slider updates before creating the Home Ice widget.
if st.session_state.pending_home_ice_advantage is not None:
    st.session_state.home_ice_advantage = st.session_state.pending_home_ice_advantage
    st.session_state.pending_home_ice_advantage = None

st.set_page_config(page_title="Hockey Elo Ratings", layout="wide")

st.title("Hockey Elo Ratings & Dashboard")

# Sidebar for parameters
st.sidebar.header("Data Source")
st.sidebar.selectbox("League", ["NHL", "SHL"], key="league_choice")
st.sidebar.caption("NHL = National Hockey League, SHL = Swedish Hockey League")

if st.session_state.league_choice == "SHL":
    league = SHLLeague()
else:
    league = NHLLeague()

available_seasons = league.get_available_seasons()
season_labels = list(available_seasons.keys())
season_label = st.sidebar.selectbox("Season", season_labels, index=0)
SEASON_SELECT = available_seasons[season_label]

st.sidebar.header("Elo Parameters")
st.sidebar.caption(f"Base Elo: {BASE_ELO:.0f} (fixed)")
st.sidebar.slider(
    "K-Factor",
    min_value=1.0,
    max_value=100.0,
    step=1.0,
    key="k_factor",
    help="Controls how much ratings change per game. Higher values react faster.",
)
st.sidebar.slider(
    "Placement Games (Early-Season Window)",
    min_value=0,
    max_value=30,
    step=1,
    key="placement_games",
    help="Number of games per team that use the temporary placement K bonus.",
)
st.sidebar.slider(
    "Placement K Add (Bonus)",
    min_value=0.0,
    max_value=100.0,
    step=1.0,
    key="placement_k_add",
    help="Added on top of base K during placement games. If either team is still in placement, the bonus applies.",
)
st.sidebar.slider(
    "Home Ice Advantage (Elo Points)",
    min_value=0.0,
    max_value=200.0,
    step=1.0,
    key="home_ice_advantage",
    help="Rating points added to the home team before win-probability calculation.",
)
estimate_home_ice_btn = st.sidebar.button("Estimate Home Ice From Data")
if st.session_state.home_ice_estimate_notice:
    st.sidebar.success(st.session_state.home_ice_estimate_notice)
    st.session_state.home_ice_estimate_notice = ""

st.sidebar.header("Game Type Weights")
st.sidebar.markdown("Define how much Elo credit the winner receives (loser gets 1 - weight). 1.0 = winner takes all, 0.5 = equal split.")
st.sidebar.slider(
    "Overtime Win (OTW) Weight",
    min_value=0.5,
    max_value=1.0,
    step=0.01,
    key="ot_win_weight",
    help="Elo share for the overtime winner.",
)
st.sidebar.slider(
    "Shootout Win (SOW) Weight",
    min_value=0.5,
    max_value=1.0,
    step=0.01,
    key="so_win_weight",
    help="Elo share for the shootout winner.",
)

st.sidebar.header("Margin of Victory")
st.sidebar.markdown("Optional multiplier based on goal differential. This affects regular-season Elo updates only.")
st.sidebar.toggle("Enable Margin of Victory (MoV) Multiplier", key="use_mov")
st.sidebar.slider(
    "MoV Goal Differential Cap",
    min_value=1,
    max_value=10,
    step=1,
    key="mov_cap",
    disabled=not st.session_state.use_mov,
    help="Maximum goal differential used in the MoV multiplier.",
)

@st.cache_data(ttl=3600)
def fetch_game_data(season):
    cache_schema_version = "2026-03-16-shl-game-type-v1"
    completed, remaining = league.fetch_games(season)
    return completed, remaining, league.get_teams(), league.team_info()

@st.cache_data(ttl=3600)
def compute_ratings(
    _completed_games,
    k_factor,
    placement_games,
    placement_k_add,
    home_ice,
    ot_win,
    so_win,
    use_mov,
    mov_cap,
    league_name,
    season_id,
    cutoff_date_key,
):
    win_weights = {
        'REG_WIN': 1.0, 'REG_LOSS': 0.0,
        'OT_WIN': ot_win, 'OT_LOSS': 1.0 - ot_win,
        'SO_WIN': so_win, 'SO_LOSS': 1.0 - so_win
    }
    
    ratings, history, team_history = calculate_elo(
        league, _completed_games, BASE_ELO,
        k_factor, home_ice, win_weights, use_mov, mov_cap,
        placement_games=placement_games,
        placement_k_add=placement_k_add,
    )
    comparison = compare_elo_vs_standings(league, ratings, _completed_games, team_history)
    records = league.build_team_records(_completed_games)
    divisions, interdivision_rows = build_interdivision_matrix(league, _completed_games, win_weights)
    return ratings, history, team_history, comparison, records, divisions, interdivision_rows

@st.cache_data(ttl=3600, show_spinner=False)
def get_sim_results(
    _completed,
    _remaining,
    ratings_dict,
    count,
    k,
    placement_games,
    placement_k_add,
    home,
    ot_win,
    so_win,
    use_mov,
    mov_cap,
    season_id,
    league_id,
    cutoff_date_key,
    sim_schema_version,
):
    sim_logic_version = "2026-03-16-shl-playoff-hardcode-v1"
    ww = {
        'REG_WIN': 1.0, 'REG_LOSS': 0.0,
        'OT_WIN': ot_win, 'OT_LOSS': 1.0 - ot_win,
        'SO_WIN': so_win, 'SO_LOSS': 1.0 - so_win
    }
    return simulate_season_and_playoffs_from_today(
        league, _completed, _remaining, ratings_dict, count,
        home_ice_advantage=home, k_factor=k, win_weights=ww,
        use_mov=use_mov, mov_cap=mov_cap,
        placement_games=placement_games,
        placement_k_add=placement_k_add,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def estimate_home_ice_value(
    _completed_games,
    k_factor,
    placement_games,
    placement_k_add,
    ot_win,
    so_win,
    use_mov,
    mov_cap,
    league_name,
    season_id,
    cutoff_date_key,
):
    win_weights = {
        'REG_WIN': 1.0, 'REG_LOSS': 0.0,
        'OT_WIN': ot_win, 'OT_LOSS': 1.0 - ot_win,
        'SO_WIN': so_win, 'SO_LOSS': 1.0 - so_win
    }
    estimated, objective = estimate_home_ice_advantage(
        league=league,
        games=_completed_games,
        win_weights=win_weights,
        initial_elo=BASE_ELO,
        k_factor=k_factor,
        use_mov=use_mov,
        mov_cap=mov_cap,
        placement_games=placement_games,
        placement_k_add=placement_k_add,
    )
    return estimated, objective

try:
    with st.spinner('Loading data...'):
        completed_games, remaining_games, c_teams, c_team_info = fetch_game_data(SEASON_SELECT)
        if hasattr(league, '_teams'):
            league._teams = c_teams
        if hasattr(league, '_team_info'):
            league._team_info = c_team_info
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

completed_dates = league.sorted_unique_game_dates(completed_games)
if not completed_dates:
    st.error("No completed games were returned for the selected season.")
    st.stop()

cutoff_scope_key = f"{st.session_state.league_choice}:{SEASON_SELECT}"
latest_completed_date = completed_dates[-1]

if st.session_state.cutoff_scope_key != cutoff_scope_key:
    st.session_state.cutoff_scope_key = cutoff_scope_key
    st.session_state.elo_cutoff_date = latest_completed_date

if (
    st.session_state.elo_cutoff_date is None
    or not isinstance(st.session_state.elo_cutoff_date, date)
    or st.session_state.elo_cutoff_date < completed_dates[0]
    or st.session_state.elo_cutoff_date > latest_completed_date
):
    st.session_state.elo_cutoff_date = latest_completed_date

st.sidebar.header("Historical Data Cutoff (What-If)")
st.sidebar.toggle(
    "Enable Date Cutoff",
    key="use_date_cutoff",
    help="Freeze ratings/analytics at a chosen date, then simulate only games after that date.",
)
st.sidebar.date_input(
    "Calculate Elo Through",
    min_value=completed_dates[0],
    max_value=latest_completed_date,
    key="elo_cutoff_date",
    disabled=not st.session_state.use_date_cutoff,
)

selected_cutoff_date = st.session_state.elo_cutoff_date if st.session_state.use_date_cutoff else None
cutoff_date_key = selected_cutoff_date.isoformat() if selected_cutoff_date else "none"

completed_games_for_elo = completed_games
sim_games_from_cutoff = remaining_games

if selected_cutoff_date is not None:
    completed_games_for_elo, completed_after_cutoff = league.split_games_by_cutoff(completed_games, selected_cutoff_date)
    sim_games_from_cutoff = league.sort_games_by_date(completed_after_cutoff + remaining_games)
    st.sidebar.caption(
        f"Using games through {cutoff_date_key} for Elo/analytics. Simulations run after that date."
    )

if estimate_home_ice_btn:
    min_games_for_estimate = 100
    if len(completed_games_for_elo) < min_games_for_estimate:
        st.sidebar.warning(
            f"Need at least {min_games_for_estimate} games to estimate home ice (found {len(completed_games_for_elo)})."
        )
    else:
        with st.spinner("Estimating home ice advantage..."):
            estimated_home_ice, objective = estimate_home_ice_value(
                completed_games_for_elo,
                st.session_state.k_factor,
                st.session_state.placement_games,
                st.session_state.placement_k_add,
                st.session_state.ot_win_weight,
                st.session_state.so_win_weight,
                st.session_state.use_mov,
                st.session_state.mov_cap,
                st.session_state.league_choice,
                SEASON_SELECT,
                cutoff_date_key,
            )
        estimated_home_ice = float(max(0.0, min(200.0, round(estimated_home_ice))))
        st.session_state.pending_home_ice_advantage = estimated_home_ice
        st.session_state.home_ice_estimate_notice = (
            f"Estimated home ice set to {estimated_home_ice:.0f} Elo points from {len(completed_games_for_elo)} games "
            f"(MSE: {objective:.4f})."
        )
        st.rerun()

ratings, history, team_history, comparison, records, divisions, interdivision_rows = compute_ratings(
    completed_games_for_elo,
    st.session_state.k_factor,
    st.session_state.placement_games,
    st.session_state.placement_k_add,
    st.session_state.home_ice_advantage,
    st.session_state.ot_win_weight,
    st.session_state.so_win_weight,
    st.session_state.use_mov,
    st.session_state.mov_cap,
    st.session_state.league_choice,
    SEASON_SELECT,
    cutoff_date_key,
)

if selected_cutoff_date is not None:
    st.info(
        f"What-if mode is active: ratings and analytics include games through {cutoff_date_key}. "
        f"Simulations use {len(sim_games_from_cutoff)} games after the cutoff."
    )


# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Current Ratings",
    "Elo History",
    "Elo vs Standings",
    "Simulations",
    "Interdivision Matrix",
    "Help",
])

with tab1:
    st.subheader(f"Current Ratings ({season_label})")
    
    df = pd.DataFrame(comparison)
    display_cols = ['elo_rank', 'standings_rank', 'rank_diff', 'team', 'conference', 'division', 'elo', 'elo_trend_10g', 'Pts', 'GP', 'W', 'OTW', 'L', 'OTL']
    col_names = {
        'elo_rank': 'Elo Rank', 'standings_rank': 'Standings Rank', 'rank_diff': 'Elo vs Standings',
        'team': 'Team', 'conference': 'Conference', 'division': 'Division',
        'elo': 'Elo', 'elo_trend_10g': 'Elo Trend (Last 10 Games)', 'Pts': 'Points', 'OTW': 'OTW'
    }

    df_display = df[display_cols].rename(columns=col_names)
    st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        column_config={
            "Elo vs Standings": st.column_config.NumberColumn(
                "Elo vs Standings",
                format="%d",
                help="Standings rank minus Elo rank. Positive means Elo rates the team stronger than the standings do.",
            ),
            "Elo Trend (Last 10 Games)": st.column_config.NumberColumn(
                "Elo Trend (Last 10 Games)",
                format="%+.1f",
                help="Current Elo minus Elo from 10 games ago. Positive = improving trend.",
            )
        },
    )

with tab2:
    st.subheader("Elo Rating History")
    st.caption("Track how each team's Elo changes as games are played.")
    
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
            title="Team Elo Trajectories",
            xaxis_title="Games Played",
            yaxis_title="Elo Rating",
            height=600,
            hovermode="x unified"
        )
        st.plotly_chart(fig, width="stretch")

with tab3:
    st.subheader("Elo Rank vs Standings Rank")
    st.caption("The dashed line shows perfect agreement between standings and Elo rankings.")
    
    df = pd.DataFrame(comparison)
    
    fig = px.scatter(
        df, 
        x="standings_rank", 
        y="elo_rank", 
        text="team",
        hover_data=["elo", "Pts"],
        color="conference",
        title="Standings Rank vs Elo Rank"
    )
    
    fig.add_trace(go.Scatter(
        x=[1, len(ranked_teams)], y=[1, len(ranked_teams)], mode='lines', name='Ideal Alignment', line=dict(dash='dash', color='gray')
    ))
    
    fig.update_traces(textposition='top center')
    fig.update_layout(
        xaxis_title="Standings Rank", 
        yaxis_title="Elo Rank",
        height=600,
        xaxis=dict(autorange="reversed"),
        yaxis=dict(autorange="reversed")
    )
    
    st.plotly_chart(fig, width="stretch")

with tab4:
    st.subheader("Season & Playoffs Simulations")
    st.write("Run statistical simulations to estimate final standings points and playoff probabilities from the remaining schedule.")
    if st.session_state.league_choice == "SHL":
        st.info("SHL playoff format used here: Top 6 go directly to Kvartsfinal (Quarterfinals). Seeds 7-10 play Åttondelsfinal (Play-in).")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.number_input("Simulation Iterations", min_value=100, max_value=10000, step=500, key="num_simulations")
        run_btn = st.button("Run Simulations", type="primary")
        
    with col2:
        st.info("Each simulation run plays out the remaining regular season and playoffs. Lower iteration counts run faster but are more volatile.")
        
    if run_btn:
        if not sim_games_from_cutoff:
            st.info("No games remain after the selected cutoff date, so there is nothing to simulate.")
        else:
            with st.spinner(f"Running {st.session_state.num_simulations} simulations..."):
                results = get_sim_results(
                    completed_games_for_elo, sim_games_from_cutoff, ratings, st.session_state.num_simulations,
                    st.session_state.k_factor, st.session_state.placement_games, st.session_state.placement_k_add,
                    st.session_state.home_ice_advantage,
                    st.session_state.ot_win_weight, st.session_state.so_win_weight,
                    st.session_state.use_mov, st.session_state.mov_cap,
                    SEASON_SELECT, st.session_state.league_choice, cutoff_date_key, SIM_RESULTS_SCHEMA_VERSION
                )
            
                df_sim = pd.DataFrame(results)
                if 'final_points_avg' not in df_sim.columns:
                    points_by_team = {row['team']: float(row.get('Pts', 0.0)) for row in records}
                    df_sim['final_points_avg'] = df_sim['team'].map(points_by_team).fillna(0.0)
                st.write(f"### Simulation Results ({st.session_state.num_simulations} runs)")
            
                playoff_cols_dict = league.get_playoff_column_names()
                percent_cols = [
                    playoff_cols_dict.get('make_playoffs', 'Make Playoffs'),
                    playoff_cols_dict.get('make_qf', 'Round 2'),
                    playoff_cols_dict.get('make_sf', 'Conf Finals'),
                    playoff_cols_dict.get('make_final', 'Finals'),
                    playoff_cols_dict.get('win_champ', 'Champ'),
                ]
            
                display_cols = [
                    'team', 'conference', 'division', 'current_elo', 'final_points_avg',
                    'make_playoffs_prob', 'make_qf_prob', 'make_sf_prob', 
                    'make_final_prob', 'win_champ_prob'
                ]
            
                rename_cols = {
                    'team': 'Team', 'conference': 'Conference', 'division': 'Division', 'current_elo': 'Current Elo', 'final_points_avg': 'Expected Final Points',
                    'make_playoffs_prob': playoff_cols_dict.get('make_playoffs', 'Make Playoffs'), 
                    'make_qf_prob': playoff_cols_dict.get('make_qf', 'Round 2'),
                    'make_sf_prob': playoff_cols_dict.get('make_sf', 'Conf Finals'), 
                    'make_final_prob': playoff_cols_dict.get('make_final', 'Finals'), 
                    'win_champ_prob': playoff_cols_dict.get('win_champ', 'Champ')
                }
            
                df_display = df_sim[display_cols].rename(columns=rename_cols).copy()

                # SHL presentation tweak: teams that already have direct QF qualification
                # should also show 100% in the first playoff-stage column.
                if st.session_state.league_choice == "SHL":
                    first_stage_col = rename_cols['make_playoffs_prob']
                    qf_col = rename_cols['make_qf_prob']
                    df_display[first_stage_col] = df_display[[first_stage_col, qf_col]].max(axis=1)

                # Keep numeric types for proper sorting, then format as percentages in the grid.
                for column in percent_cols:
                    df_display[column] = df_display[column] * 100.0

                sim_col_config = {
                    "Current Elo": st.column_config.NumberColumn("Current Elo", format="%.2f"),
                    "Expected Final Points": st.column_config.NumberColumn(
                        "Expected Final Points",
                        format="%.2f",
                        help="Average regular-season points across all simulation runs.",
                    ),
                }
                for column in percent_cols:
                    sim_col_config[column] = st.column_config.NumberColumn(
                        column,
                        format="%.1f%%",
                        help="Probability from simulation runs.",
                    )

                st.dataframe(
                    df_display,
                    width="stretch",
                    hide_index=True,
                    column_config=sim_col_config,
                )
            
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
    st.subheader("Interdivisional Head-to-Head (%)")
    st.write("Rows are the division being evaluated; columns are opponent divisions.")
    st.write("Values show average Elo-style game score percentages from completed games (100% = all regulation wins, 0% = all regulation losses).")
    
    matrix_data = []
    
    for row_idx, row in enumerate(interdivision_rows):
        matrix_row = []
        for col_idx, d in enumerate(divisions):
            val = row[d]
            matrix_row.append(float("nan") if val is None else val * 100.0)
        matrix_data.append(matrix_row)
        
    fig_heat = px.imshow(
        matrix_data,
        x=divisions, y=divisions,
        labels=dict(x="Opponent Division", y="Division", color="Average Score (%)"),
        text_auto=True, color_continuous_scale="RdBu_r", aspect="auto"
    )
    fig_heat.update_traces(texttemplate="%{z:.1f}%", hovertemplate="Division: %{y}<br>Opponent: %{x}<br>Average Score: %{z:.1f}%<extra></extra>")
    
    fig_heat.update_layout(
        title="Interdivisional Head-to-Head Matrix", height=500,
        xaxis_title="Opponent Division", yaxis_title="Division", coloraxis_colorbar=dict(title="Average %")
    )
    st.plotly_chart(fig_heat, width="stretch")

with tab6:
    st.subheader("Help & Glossary")
    st.markdown("Use this page as a quick reference for anyone new to the dashboard.")

    with st.expander("Quick Start", expanded=True):
        st.markdown("""
1. Pick a **League** and **Season** in the sidebar.
2. Review **Current Ratings** to compare Elo vs standings.
3. Run **Simulations** to estimate playoff and championship probabilities.
4. Tune Elo settings in the sidebar only after a baseline run.
""")

    with st.expander("Core Concepts"):
        st.markdown("""
- **Elo**: A rating system that updates after each game.
- **K-Factor**: How quickly ratings move. Higher K means faster movement.
- **Placement Games / Placement K Add**: Early-season boost. If either team is still in placement games, base K gets the bonus.
- **Home Ice Advantage**: Elo points added to the home team when computing win probability.
- **OTW/SOW Weights**: How much Elo credit overtime and shootout winners receive.
- **MoV Multiplier**: Optional margin-of-victory adjustment for regular-season Elo updates.
""")

    with st.expander("How To Read The Tabs"):
        st.markdown("""
- **Current Ratings**: Elo rank, standings rank, and trend metrics.
- **Elo History**: Team rating trajectories over games played.
- **Elo vs Standings**: Visual alignment (or mismatch) between standings and Elo.
- **Simulations**: Expected final points and playoff/championship probabilities.
- **Interdivision Matrix**: Division-vs-division scoring percentages from completed games.
""")

    with st.expander("League-Specific Playoff Terms"):
        if st.session_state.league_choice == "SHL":
            st.markdown("""
- **Åttondelsfinal (Play-in)**: SHL seeds 7-10 play for quarterfinal spots.
- **Kvartsfinal (Quarterfinals)**
- **Semifinal**
- **Final**
""")
        else:
            st.markdown("""
- **Make Playoffs**
- **Round 2**
- **Conference Finals**
- **Stanley Cup Finals**
- **Win Championship**
""")

    with st.expander("What-If Cutoff Mode"):
        st.markdown("""
Enable **Date Cutoff** in the sidebar to freeze ratings/analytics at a chosen date.
Simulations then run only on games after that date.
""")