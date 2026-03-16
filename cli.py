import csv
import argparse
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import math

from src.leagues.nhl.league import NHLLeague
from src.core.elo import calculate_elo
from src.tools.analytics import compare_elo_vs_standings, build_interdivision_matrix
from src.tools.simulator import simulate_season_and_playoffs_from_today

def save_csv(rows: List[dict], filename: str) -> None:
    if not rows: return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def plot_elo_history(team_history: Dict[str, List[Tuple[str, float]]], ratings: Dict[str, float], output_file: str, team_info: dict, season: str, top_n: int = 10) -> None:
    plt.figure(figsize=(16, 9))
    teams_to_plot = [team for team, _ in sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)[:top_n]]
    for team in teams_to_plot:
        series = team_history[team]
        x = list(range(len(series)))
        y = [elo for _, elo in series]
        plt.plot(x, y, label=f"{team} ({team_info[team]['division']})")
    plt.title(f"Elo over time ({season})")
    plt.xlabel("Games played by team")
    plt.ylabel("Elo")
    plt.legend(ncol=2)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()

def plot_elo_vs_standings(comparison: List[dict], output_file: str) -> None:
    plt.figure(figsize=(10, 8))
    x = [row["standings_rank"] for row in comparison]
    y = [row["elo_rank"] for row in comparison]
    plt.scatter(x, y)
    for row in comparison:
        plt.annotate(row["team"], (row["standings_rank"], row["elo_rank"]), textcoords="offset points", xytext=(4, 4))
    if x and y:
        max_rank = max(max(x), max(y))
        plt.plot([1, max_rank], [1, max_rank], linestyle="--")
    plt.gca().invert_xaxis()
    plt.gca().invert_yaxis()
    plt.title("Standings Rank vs Elo Rank")
    plt.xlabel("Standings rank")
    plt.ylabel("Elo rank")
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()

def plot_interdivision_matrix(divisions: List[str], rows: List[dict], output_file: str) -> None:
    matrix = []
    for row in rows:
        matrix_row = []
        for d in divisions:
            val = row[d]
            matrix_row.append(float("nan") if val is None else val)
        matrix.append(matrix_row)
    plt.figure(figsize=(8, 6))
    plt.imshow(matrix, aspect="auto")
    for i in range(len(divisions)):
        for j in range(len(divisions)):
            val = matrix[i][j]
            label = "---" if math.isnan(val) else f"{val:.3f}"
            plt.text(j, i, label, ha="center", va="center")
    plt.xticks(range(len(divisions)), divisions, rotation=20)
    plt.yticks(range(len(divisions)), divisions)
    plt.title("Interdivision Score Pct Matrix")
    plt.xlabel("Opponent division")
    plt.ylabel("Division")
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Hockey Elo Simulator")
    parser.add_argument("--league", default="NHL", help="League to simulate (NHL)")
    parser.add_argument("--season", default="20252026", help="Season string")
    parser.add_argument("--sims", type=int, default=1000, help="Number of Monte Carlo simulations")
    args = parser.parse_args()

    # Configuration defaults
    initial_elo = 1500.0
    k_factor = 20.0
    home_ice_advantage = 33.0
    win_weights = {
        'REG_WIN': 1.00, 'REG_LOSS': 0.00,
        'OT_WIN': 0.67, 'OT_LOSS': 0.33,
        'SO_WIN': 0.55, 'SO_LOSS': 0.45
    }

    if args.league.upper() == "NHL":
        league = NHLLeague()
    else:
        print(f"Unknown league {args.league}")
        return

    print(f"Fetching games for {args.league} {args.season}...")
    completed, remaining = league.fetch_games(args.season)

    print("Calculating Elo...")
    ratings, history, team_history = calculate_elo(league, completed, initial_elo, k_factor, home_ice_advantage, win_weights)
    
    print("Generating Analytics...")
    comparison = compare_elo_vs_standings(league, ratings, completed, team_history)
    divisions, interdivision_rows = build_interdivision_matrix(league, completed, win_weights)

    print(f"Running {args.sims} simulations from today...")
    cup_odds = simulate_season_and_playoffs_from_today(
        league, completed, remaining, ratings,
        simulations=args.sims,
        home_ice_advantage=home_ice_advantage,
        k_factor=k_factor,
        win_weights=win_weights
    )

    print("Saving artifacts...")
    save_csv(history, "elo_history.csv")
    save_csv(comparison, "elo_vs_standings.csv")
    save_csv(interdivision_rows, "interdivision.csv")
    save_csv(cup_odds, "cup_odds.csv")

    plot_elo_history(team_history, ratings, "elo_history.png", league.team_info(), args.season)
    plot_elo_vs_standings(comparison, "elo_vs_standings.png")
    plot_interdivision_matrix(divisions, interdivision_rows, "interdivision.png")
    print("Finished.")

if __name__ == "__main__":
    main()
