# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Introduction
# MAGIC %md
# MAGIC # 2026 Week 2 Slate Builder + Prediction
# MAGIC
# MAGIC **Purpose:** Generate fantasy football predictions for the **upcoming** 2026 NFL Week 2 slate.
# MAGIC
# MAGIC **Key difference from Week 1:** Week 1 has been played, so we now have one week of 2026 actual data. Instead of setting all rolling features to 0 (cold start), we compute them from Week 1 actuals extracted from the Gold table.
# MAGIC
# MAGIC **Prerequisite:** Run `ingestion/feature_building.ipynb` first (with 2026 added to SEASONS) so the Gold table includes 2026 Week 1 actual game data.
# MAGIC
# MAGIC **Inputs:**
# MAGIC - 2026 Week 2 schedule (Vegas lines, home/away, roof) from `nfl_data_py`
# MAGIC - 2026 rosters + depth charts (player list and roles)
# MAGIC - 2025 carryover stats (prev_season_ppg, prev_season_games)
# MAGIC - 2026 Week 1 actual stats from Gold (for rolling features)
# MAGIC
# MAGIC **Output:** Writes season=2026, week=2 rows to `fantasy_football.gold.predictions` via `replaceWhere`.

# COMMAND ----------

# DBTITLE 1,Install dependencies
# Install nfl_data_py dependencies and xgboost
%pip install appdirs fastparquet xgboost
%pip install --no-deps nfl_data_py

# Verify imports
import nfl_data_py as nfl
import pandas as pd
import numpy as np
from xgboost import XGBRegressor

print(f"✓ All packages imported successfully")
print(f"  pandas: {pd.__version__}")
print(f"  numpy: {np.__version__}")

# COMMAND ----------

# DBTITLE 1,Verify Gold table has 2026 Week 1 data
# Check that feature_building has been run with 2026 included
gold_check = spark.sql("""
    SELECT season, week, COUNT(*) as row_count
    FROM fantasy_football.gold.player_weeks
    WHERE season = 2026
    GROUP BY season, week
    ORDER BY week
""")
gold_2026 = gold_check.toPandas()

if len(gold_2026) == 0:
    raise RuntimeError(
        "No 2026 data in fantasy_football.gold.player_weeks! "
        "Run ingestion/feature_building.ipynb with 2026 added to SEASONS first."
    )

print(f"2026 data in Gold table:")
print(gold_2026.to_string(index=False))

wk1_count = gold_2026[gold_2026['week'] == 1]['row_count'].values
if len(wk1_count) > 0:
    print(f"\n✓ Week 1 actuals available ({wk1_count[0]} rows) — can compute rolling features")
else:
    raise RuntimeError("Week 1 data not found in Gold table. Run feature_building first.")

# COMMAND ----------

# DBTITLE 1,Load 2026 Week 2 schedule and game context
import pandas as pd
import numpy as np
import nfl_data_py as nfl

print("Loading 2026 NFL schedule and game context...")

# Load 2026 schedule
schedules_2026 = nfl.import_schedules([2026])
week2_games = schedules_2026[schedules_2026['week'] == 2].copy()

print(f"Found {len(week2_games)} games in 2026 Week 2")
print(f"Games with lines: {week2_games['spread_line'].notna().sum()} spread, {week2_games['total_line'].notna().sum()} total")

# Build home and away dataframes
home_df = week2_games[['home_team', 'away_team', 'spread_line', 'total_line', 'home_moneyline', 'roof']].copy()
home_df.columns = ['team', 'opponent', 'spread_line', 'total_line', 'moneyline', 'roof']
home_df['is_home'] = 1

away_df = week2_games[['away_team', 'home_team', 'spread_line', 'total_line', 'away_moneyline', 'roof']].copy()
away_df.columns = ['team', 'opponent', 'spread_line', 'total_line', 'moneyline', 'roof']
away_df['is_home'] = 0
away_df['spread_line'] = -away_df['spread_line']  # flip spread for away team

game_context = pd.concat([home_df, away_df], ignore_index=True)

# Calculate implied totals and win probabilities
game_context['implied_total'] = (
    game_context['total_line'].fillna(44.0) / 2
    + game_context['spread_line'].fillna(0) / 2
)

# Win probability from moneyline (American odds)
def moneyline_to_prob(ml):
    if pd.isna(ml):
        return 0.5
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return abs(ml) / (abs(ml) + 100)

game_context['team_win_prob'] = game_context['moneyline'].apply(moneyline_to_prob)
game_context['team_spread'] = game_context['spread_line'].fillna(0)

# Dome flag
game_context['is_dome'] = game_context['roof'].isin(['dome', 'closed']).astype(int)

# Weather: set to neutral values (would be updated from weather API closer to game)
game_context['temp'] = 72
game_context['wind'] = 0
game_context['is_bad_weather'] = 0

# Flag games with missing Vegas lines
game_context['missing_vegas_lines'] = game_context['spread_line'].isna().astype(int)

print(f"\n✓ Game context built for {len(game_context)} team-game records")
print(f"  Missing Vegas lines: {game_context['missing_vegas_lines'].sum()} team-games")
print(f"  Dome games: {game_context['is_dome'].sum()} team-games")

# Rest advantage: days since last game. For Week 2, most teams played Sun Sep 13.
# We compute rest from the schedule (gameday difference between Week 1 and Week 2).
wk1_games = schedules_2026[schedules_2026['week'] == 1]
wk1_dates = pd.concat([
    wk1_games[['home_team', 'gameday']].rename(columns={'home_team': 'team'}),
    wk1_games[['away_team', 'gameday']].rename(columns={'away_team': 'team'})
])
wk1_dates['gameday'] = pd.to_datetime(wk1_dates['gameday'])
wk1_rest = wk1_dates.groupby('team')['gameday'].max().reset_index()
wk1_rest.columns = ['team', 'last_game_date']

wk2_dates = pd.concat([
    week2_games[['home_team', 'gameday']].rename(columns={'home_team': 'team'}),
    week2_games[['away_team', 'gameday']].rename(columns={'away_team': 'team'})
])
wk2_dates['gameday'] = pd.to_datetime(wk2_dates['gameday'])
wk2_rest = wk2_dates.groupby('team')['gameday'].max().reset_index()
wk2_rest.columns = ['team', 'this_game_date']

rest_df = wk1_rest.merge(wk2_rest, on='team', how='inner')
rest_df['rest_days'] = (rest_df['this_game_date'] - rest_df['last_game_date']).dt.days

# Rest advantage = this team's rest days - opponent's rest days
game_context = game_context.merge(rest_df[['team', 'rest_days']], on='team', how='left')
game_context = game_context.merge(
    rest_df[['team', 'rest_days']].rename(columns={'team': 'opponent', 'rest_days': 'opp_rest_days'}),
    on='opponent', how='left'
)
game_context['rest_advantage'] = (game_context['rest_days'] - game_context['opp_rest_days']).fillna(0)
game_context = game_context.drop(columns=['rest_days', 'opp_rest_days'])

print(f"  Rest advantage range: {game_context['rest_advantage'].min()} to {game_context['rest_advantage'].max()} days")

# COMMAND ----------

# DBTITLE 1,Load 2026 rosters and depth charts
print("\nLoading 2026 rosters and depth charts...")

# Load 2026 seasonal rosters
rosters_2026 = nfl.import_seasonal_rosters([2026])
rosters_2026 = rosters_2026[rosters_2026['position'].isin(['QB', 'RB', 'WR', 'TE'])].copy()

print(f"Found {len(rosters_2026)} fantasy-relevant players on 2026 rosters")

# Load 2026 depth charts (SNAPSHOT schema)
depth_charts_2026 = nfl.import_depth_charts([2026])

depth_off = depth_charts_2026[
    depth_charts_2026['pos_abb'].isin(['QB', 'RB', 'WR', 'TE', 'FB'])
].copy()
depth_off['snapshot_dt'] = pd.to_datetime(depth_off['dt']).dt.tz_localize(None)
depth_off['gsis_id'] = depth_off['gsis_id'].astype(str)

# Best (min) rank per player per snapshot day, then keep the latest snapshot
snap_ranks = (
    depth_off.groupby(['gsis_id', 'snapshot_dt'])['pos_rank'].min().reset_index()
    .sort_values('snapshot_dt')
)
latest_dc = snap_ranks.drop_duplicates('gsis_id', keep='last')

# Map depth chart to roster
rosters_2026['player_id'] = rosters_2026['player_id'].astype(str)
rosters_2026 = rosters_2026.merge(
    latest_dc[['gsis_id', 'pos_rank']],
    left_on='player_id', right_on='gsis_id', how='left'
).drop(columns=['gsis_id'])
rosters_2026['depth_chart_rank'] = rosters_2026['pos_rank'].fillna(99).astype(int)

print(f"Depth chart ranks assigned: {(rosters_2026['depth_chart_rank'] < 99).sum()} players on depth chart")
print(f"Starters (depth_chart_rank=1): {(rosters_2026['depth_chart_rank'] == 1).sum()} players")

# QB/TE starter filter (same as Week 1 builder)
before_filter = len(rosters_2026)
qb_te_mask = rosters_2026['position'].isin(['QB', 'TE'])
rosters_2026 = rosters_2026[~qb_te_mask | (rosters_2026['depth_chart_rank'] == 1)].reset_index(drop=True)
print(f"\nQB/TE starter filter: {before_filter} → {len(rosters_2026)} players "
      f"({before_filter - len(rosters_2026)} backup QB/TE rows removed)")

# COMMAND ----------

# DBTITLE 1,Add 2025 carryover stats
print("\nAdding 2025 carryover stats (prev_season_ppg, prev_season_games)...")

# Load Gold table to get 2025 season stats for carryover
gold_df = spark.table("fantasy_football.gold.player_weeks").toPandas()
gold_2025 = gold_df[gold_df['season'] == 2025].copy()

# Calculate 2025 season averages (weeks 1-17 only)
gold_2025_reg = gold_2025[gold_2025['week'] <= 17]
carryover = gold_2025_reg.groupby('player_id').agg(
    prev_season_ppg=('fantasy_points_ppr', 'mean'),
    prev_season_games=('fantasy_points_ppr', 'count')
).reset_index()

carryover['player_id'] = carryover['player_id'].astype(str)

print(f"Calculated carryover stats for {len(carryover)} players from 2025 season")

# Merge carryover stats to 2026 roster
rosters_2026 = rosters_2026.merge(
    carryover[['player_id', 'prev_season_ppg', 'prev_season_games']],
    on='player_id', how='left'
)

# Rookies and players without 2025 data get 0
rosters_2026['prev_season_ppg'] = rosters_2026['prev_season_ppg'].fillna(0)
rosters_2026['prev_season_games'] = rosters_2026['prev_season_games'].fillna(0)

rookies = (rosters_2026['prev_season_games'] == 0).sum()
print(f"\nRookies or new players (prev_season_games=0): {rookies}")

# COMMAND ----------

# DBTITLE 1,Extract Week 1 actuals and compute rolling features
print("\nExtracting 2026 Week 1 actuals from Gold to compute rolling features...")

# Get 2026 Week 1 rows from Gold (actual game data)
wk1_actuals = gold_df[(gold_df['season'] == 2026) & (gold_df['week'] == 1)].copy()
wk1_actuals['player_id'] = wk1_actuals['player_id'].astype(str)

print(f"Found {len(wk1_actuals)} player-game records from 2026 Week 1")
print(f"  By position: {wk1_actuals['position'].value_counts().to_dict()}")

# ---------------------------------------------------------------------------
# Compute rolling features from Week 1 actuals.
# With shift(1).rolling(window=N, min_periods=1), and only 1 prior week,
# the rolling average is simply that week's actual value.
# ---------------------------------------------------------------------------

# Map: rolling_feature → Week 1 actual column
rolling_map = {
    'fantasy_points_3wk_avg': 'fantasy_points_ppr',
    'fantasy_points_5wk_avg': 'fantasy_points_ppr',
    'qb_pass_attempts_3wk_avg': 'pass_attempts',
    'qb_pass_attempts_5wk_avg': 'pass_attempts',
    'qb_rushing_yards_3wk_avg': 'rushing_yards',
    'qb_rushing_yards_5wk_avg': 'rushing_yards',
    'rb_opportunity_share_3wk_avg': 'opportunity_share',
    'rb_opportunity_share_5wk_avg': 'opportunity_share',
    'rb_hvts_3wk_avg': 'total_hvts',
    'rb_hvts_5wk_avg': 'total_hvts',
    'rb_snap_share_3wk_avg': 'snap_share',
    'rb_snap_share_5wk_avg': 'snap_share',
    'wr_te_target_share_3wk_avg': 'target_share',
    'wr_te_target_share_5wk_avg': 'target_share',
    'wr_te_air_yards_share_3wk_avg': 'air_yards_share',
    'wr_te_air_yards_share_5wk_avg': 'air_yards_share',
    'wr_te_wopr_3wk_avg': 'wopr',
    'wr_te_wopr_5wk_avg': 'wopr',
}

# ---------------------------------------------------------------------------
# Cross-season blended rolling features.
# Week 2 has only 1 current-season game (Week 1). Blend it with the previous
# season's final games (weight=0.3) using the same logic as feature_building.
# This avoids noisy 1-game averages and matches the training data's blend.
# ---------------------------------------------------------------------------
PREV_WEIGHT = 0.3
prev_season = PREDICT_SEASON - 1  # 2025

prev_season_df = gold_df[gold_df['season'] == prev_season].sort_values(['player_id', 'week']).copy()
prev_season_df['player_id'] = prev_season_df['player_id'].astype(str)

wk1_rolling = wk1_actuals[['player_id', 'position']].copy()
wk1_rolling['player_id'] = wk1_rolling['player_id'].astype(str)

for roll_col, actual_col in rolling_map.items():
    window = 3 if '3wk' in roll_col else 5
    n_prev_needed = window - 1  # 1 current-season game, need (window-1) from prev season

    # Current-season value (Week 1 2026)
    if actual_col in wk1_actuals.columns:
        cur_series = wk1_actuals.set_index('player_id')[actual_col].fillna(0)
    else:
        cur_series = pd.Series(0, index=wk1_actuals['player_id'])

    # Previous-season: last N games per player
    if actual_col in prev_season_df.columns:
        prev_last_n = prev_season_df.groupby('player_id').tail(n_prev_needed)
        prev_sum = prev_last_n.groupby('player_id')[actual_col].sum().fillna(0)
        prev_count = prev_last_n.groupby('player_id')[actual_col].count()
    else:
        prev_sum = pd.Series(0, index=[])
        prev_count = pd.Series(0, index=[])

    # Blend: (cur * 1.0 + prev_sum * 0.3) / (1.0 + prev_count * 0.3)
    blended = []
    for pid in wk1_rolling['player_id']:
        cv = cur_series.get(pid, 0)
        ps = prev_sum.get(pid, 0)
        pc = prev_count.get(pid, 0)
        if pc > 0:
            blended.append((cv + ps * PREV_WEIGHT) / (1.0 + pc * PREV_WEIGHT))
        else:
            blended.append(cv)
    wk1_rolling[roll_col] = blended

# Add rolling_games_count (always 1 for Week 2 — only 1 current-season game)
wk1_rolling['rolling_games_count'] = 1

print(f"\n✓ Computed {len(rolling_map)} cross-season blended rolling features")
print(f"  Current-season weight: 1.0, previous-season ({prev_season}) weight: {PREV_WEIGHT}")
print(f"  Players with rolling data: {len(wk1_rolling)}")

# ---------------------------------------------------------------------------
# Compute opponent defense PPG allowed from Week 1.
# Group by (opponent, position), average fantasy_points_ppr allowed.
# ---------------------------------------------------------------------------
wk1_def = wk1_actuals.groupby(['opponent', 'position']).agg(
    opp_def_ppg_allowed=('fantasy_points_ppr', 'mean')
).reset_index()

print(f"\n✓ Computed opponent defense PPG allowed for {len(wk1_def)} defense-position combos")

# ---------------------------------------------------------------------------
# Compute starting QB AY/A from Week 1.
# AY/A = (pass_yds + 20*pass_tds - 45*ints) / pass_attempts
# ---------------------------------------------------------------------------
wk1_qbs = wk1_actuals[wk1_actuals['position'] == 'QB'].copy()
wk1_qbs['starting_qb_aya'] = np.where(
    wk1_qbs['pass_attempts'] > 0,
    (wk1_qbs['passing_yards'] + 20 * wk1_qbs['passing_tds'] - 45 * wk1_qbs['interceptions'])
    / wk1_qbs['pass_attempts'],
    0
)
# Map: team → QB player_id → AY/A
wk1_qb_aya = wk1_qbs[['player_id', 'starting_qb_aya']].copy()
wk1_qb_aya = wk1_qb_aya.rename(columns={'player_id': 'starting_qb_id'})
wk1_qb_aya['starting_qb_id'] = wk1_qb_aya['starting_qb_id'].astype(str)

# Also build team → starting_qb_id mapping from Week 1
wk1_qb_team = wk1_qbs[['player_id', 'recent_team']].copy()
wk1_qb_team.columns = ['starting_qb_id', 'team']
wk1_qb_team['starting_qb_id'] = wk1_qb_team['starting_qb_id'].astype(str)

print(f"✓ Computed starting QB AY/A for {len(wk1_qb_aya)} QBs from Week 1")

# ---------------------------------------------------------------------------
# Defense sack rates and efficiency — these need play-by-play data.
# With only 1 week, they're noisy. Set to 0 (same as Week 1 cold start).
# The model handles this gracefully — these are less important than
# player-level rolling features.
# ---------------------------------------------------------------------------
print("\n⚠️  Defense sack rates and efficiency set to 0 (1 week of pbp data is noisy)")

# COMMAND ----------

# DBTITLE 1,Build 2026 Week 2 slate DataFrame
print("\nBuilding 2026 Week 2 slate DataFrame...")

# Merge rosters with game context
slate_2026 = rosters_2026.merge(
    game_context[['team', 'opponent', 'implied_total', 'team_spread', 'team_win_prob',
                  'is_home', 'is_dome', 'temp', 'wind', 'is_bad_weather', 'rest_advantage',
                  'missing_vegas_lines']],
    left_on='team',
    right_on='team',
    how='inner'
)

# Set week and season
slate_2026['week'] = 2
slate_2026['season'] = 2026

# Rename columns to match Gold table schema
slate_2026 = slate_2026.rename(columns={
    'team': 'recent_team',
    'full_name': 'player_name'
})

# ---------------------------------------------------------------------------
# Merge Week 1 rolling features (the key improvement over Week 1 cold start)
# ---------------------------------------------------------------------------
slate_2026 = slate_2026.merge(
    wk1_rolling.drop(columns=['position']),
    on='player_id',
    how='left'
)

# Players who didn't play in Week 1 get 0 for rolling features (same as cold start)
players_with_wk1 = slate_2026[list(rolling_map.keys())[0]].notna().sum()
for roll_col in rolling_map.keys():
    slate_2026[roll_col] = slate_2026[roll_col].fillna(0)

# Fill rolling_games_count for players without Week 1 data (0 current-season games)
slate_2026['rolling_games_count'] = slate_2026['rolling_games_count'].fillna(0)

print(f"  Players with Week 1 rolling data: {players_with_wk1}")
print(f"  Players without (filling with 0): {len(slate_2026) - players_with_wk1}")

# ---------------------------------------------------------------------------
# Merge opponent defense PPG allowed
# ---------------------------------------------------------------------------
slate_2026 = slate_2026.merge(
    wk1_def,
    left_on=['opponent', 'position'],
    right_on=['opponent', 'position'],
    how='left'
)
slate_2026['opp_def_ppg_allowed'] = slate_2026['opp_def_ppg_allowed'].fillna(0)

# ---------------------------------------------------------------------------
# Merge starting QB AY/A
# ---------------------------------------------------------------------------
# Map each team to their starting QB from Week 1
slate_2026 = slate_2026.merge(
    wk1_qb_team,
    left_on='recent_team',
    right_on='team',
    how='left'
).drop(columns=['team'], errors='ignore')

slate_2026 = slate_2026.merge(
    wk1_qb_aya,
    on='starting_qb_id',
    how='left'
)
slate_2026['starting_qb_aya'] = slate_2026['starting_qb_aya'].fillna(0)

# For QBs, set their own starting_qb_id
qb_mask = slate_2026['position'] == 'QB'
slate_2026.loc[qb_mask, 'starting_qb_id'] = slate_2026.loc[qb_mask, 'player_id']
# Update AY/A for QB rows using map to avoid column collision
qb_aya_map = wk1_qb_aya.set_index('starting_qb_id')['starting_qb_aya'].to_dict()
slate_2026.loc[qb_mask, 'starting_qb_aya'] = slate_2026.loc[qb_mask, 'starting_qb_id'].map(qb_aya_map)
slate_2026['starting_qb_aya'] = slate_2026['starting_qb_aya'].fillna(0)

# Set defense features that need pbp data to 0
for feat in ['opp_def_sack_rate', 'team_sack_rate_allowed', 'opp_def_ypc_allowed', 'opp_def_ypp_allowed']:
    slate_2026[feat] = 0

# Set other features that can't be known pre-game to 0
for feat in ['pass_rate_diff', 'blitz_rate_diff', 'opp_def_pressure_rate', 'injury_severity']:
    slate_2026[feat] = 0

# WR1/WR2 health: assume healthy unless we have injury data (set to 1 = healthy)
slate_2026['wr1_wr2_healthy'] = 1

print(f"\n✓ Built slate for {len(slate_2026)} player-game records in 2026 Week 2")
print(f"  By position: {slate_2026['position'].value_counts().to_dict()}")
print(f"  Games with missing Vegas lines: {slate_2026['missing_vegas_lines'].sum()} player-games")
print(f"\n  Rolling features summary (non-zero counts):")
for col in ['fantasy_points_3wk_avg', 'rb_opportunity_share_3wk_avg', 'wr_te_target_share_3wk_avg']:
    if col in slate_2026.columns:
        nz = (slate_2026[col] != 0).sum()
        print(f"    {col}: {nz} non-zero")

# COMMAND ----------

# DBTITLE 1,Match feature columns to training data
print("\nAligning feature columns to match training data schema...")

# Load training data (2020-2025 + 2026 Week 1, weeks 1-17)
training_data = gold_df[gold_df['week'] <= 17].copy()

# Get feature columns from training data (drop identifiers and same-week outcomes)
TARGET = 'fantasy_points_ppr'
identifier_cols = ['player_id', 'player_name', 'recent_team', 'opponent', 'starting_qb_id', 'gameday']
same_week_outcome_cols = [
    'pass_attempts', 'completions', 'passing_yards', 'passing_tds', 'interceptions',
    'rush_attempts', 'rushing_yards', 'rushing_tds',
    'targets', 'receptions', 'receiving_yards', 'receiving_tds',
    'player_opportunities', 'team_total_opportunities', 'opportunity_share',
    'hvt_carries', 'hvt_targets', 'total_hvts',
    'team_pass_attempts', 'target_share',
    'player_air_yards', 'team_air_yards', 'air_yards_share',
    'wopr', 'snap_share',
]

training_features = [c for c in training_data.columns 
                     if c not in identifier_cols + same_week_outcome_cols + [TARGET]]

# Ensure slate has all training features (add missing cols as 0)
for feat in training_features:
    if feat not in slate_2026.columns:
        slate_2026[feat] = 0

# One-hot encode position (must match training)
slate_2026_encoded = pd.get_dummies(slate_2026, columns=['position'], prefix='pos')

# Align columns exactly to training feature set + position dummies
training_data_encoded = pd.get_dummies(training_data, columns=['position'], prefix='pos')
training_features_with_pos = [c for c in training_data_encoded.columns 
                              if c not in identifier_cols + same_week_outcome_cols + [TARGET]]

# Ensure slate has all position dummies (QB/RB/WR/TE)
for col in training_features_with_pos:
    if col not in slate_2026_encoded.columns:
        slate_2026_encoded[col] = 0

# Select only the exact feature columns in exact order
slate_features = slate_2026_encoded[training_features_with_pos].fillna(0)

print(f"✓ Feature alignment complete: {len(training_features_with_pos)} features")
print(f"  Slate shape: {slate_features.shape}")
print(f"  Training data shape: {training_data_encoded.shape}")

# COMMAND ----------

# DBTITLE 1,Train model on 2020-2025 + 2026 Week 1
print("\nTraining XGBoost model on 2020-2025 + 2026 Week 1 data (weeks 1-17), early-stopping on 2025 Week 1...")

# Prepare training data
train_df = training_data_encoded.copy()

# Early stopping on 2025 Week 1 (most recent week-1-like distribution)
val_mask = (train_df['season'] == 2025) & (train_df['week'] == 1)
train_mask = ~val_mask  # everything except 2025 Week 1

X_train = train_df.loc[train_mask, training_features_with_pos].fillna(0)
y_train = train_df.loc[train_mask, TARGET]
X_val = train_df.loc[val_mask, training_features_with_pos].fillna(0)
y_val = train_df.loc[val_mask, TARGET]

print(f"Training samples: {len(X_train):,}")
print(f"Validation samples (2025 Week 1): {len(X_val):,}")
print(f"  (Training data now includes 2026 Week 1: {(train_df['season'] == 2026).sum()} rows)")

# Train model (hyperparameters from walk_forward tuning)
model = XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=4,
    min_child_weight=5,
    subsample=0.8,
    colsample_bytree=0.8,
    early_stopping_rounds=20,
    random_state=42,
    n_jobs=-1
)

model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    verbose=False
)

print(f"✓ Model trained with {model.best_iteration} boosting rounds (early stopping on 2025 Week 1)")

# COMMAND ----------

# DBTITLE 1,Generate 2026 Week 2 predictions
print("\nGenerating 2026 Week 2 predictions...")

# Predict
predictions_2026 = np.clip(model.predict(slate_features), 0, None)

# Build predictions DataFrame
predictions_df = slate_2026[['player_id', 'player_name', 'recent_team', 'position', 
                       'opponent', 'season', 'week']].copy()
predictions_df['projected_ppr'] = predictions_2026.astype(float).round(1)

# Add context features (for RAG retrieval in insights pipeline)
context_cols = ['implied_total', 'team_spread', 'team_win_prob', 'is_home',
                'temp', 'wind', 'is_bad_weather', 'is_dome',
                'prev_season_ppg', 'depth_chart_rank', 'missing_vegas_lines',
                'fantasy_points_3wk_avg', 'opp_def_ppg_allowed']

for col in context_cols:
    if col in slate_2026.columns:
        predictions_df[col] = slate_2026[col].values

# Sort by projection
predictions_df = predictions_df.sort_values('projected_ppr', ascending=False).reset_index(drop=True)

print(f"✓ Generated predictions for {len(predictions_df)} players")
print(f"\nTop 10 projected players:")
print(predictions_df[['player_name', 'position', 'recent_team', 'projected_ppr']].head(10))

print(f"\nTop 5 by position:")
for pos in ['QB', 'RB', 'WR', 'TE']:
    top = predictions_df[predictions_df['position'] == pos].head(5)
    print(f"\n  {pos}:")
    print(top[['player_name', 'recent_team', 'projected_ppr']].to_string(index=False))

# COMMAND ----------

# DBTITLE 1,Write predictions to Delta table
print("\nWriting 2026 Week 2 predictions to fantasy_football.gold.predictions...")

from pyspark.sql.functions import col
from pyspark.sql.types import IntegerType, DoubleType

# Convert to Spark DataFrame
predictions_spark = spark.createDataFrame(predictions_df)

# Cast columns to match existing table schema
predictions_spark = predictions_spark \
    .withColumn("week", col("week").cast(IntegerType())) \
    .withColumn("is_home", col("is_home").cast(DoubleType())) \
    .withColumn("temp", col("temp").cast(DoubleType())) \
    .withColumn("wind", col("wind").cast(DoubleType())) \
    .withColumn("is_bad_weather", col("is_bad_weather").cast(DoubleType())) \
    .withColumn("is_dome", col("is_dome").cast(DoubleType())) \
    .withColumn("opp_def_ppg_allowed", col("opp_def_ppg_allowed").cast(DoubleType())) \
    .withColumn("fantasy_points_3wk_avg", col("fantasy_points_3wk_avg").cast(DoubleType()))

# Drop the missing_vegas_lines column (not in target table)
if "missing_vegas_lines" in predictions_spark.columns:
    predictions_spark = predictions_spark.drop("missing_vegas_lines")

# Write with replaceWhere to partition by (season=2026, week=2)
predictions_spark.write \
    .format("delta") \
    .mode("overwrite") \
    .option("replaceWhere", "season = 2026 AND week = 2") \
    .saveAsTable("fantasy_football.gold.predictions")

print(f"✓ Merged 2026 Week 2 predictions into fantasy_football.gold.predictions")
print(f"  Rows written: {len(predictions_df)}")
print(f"  Partition: season=2026, week=2")
print(f"\n✅ 2026 Week 2 slate build complete!")
print(f"\nNext step: Run insights/insights_pipeline.ipynb to generate GPT insights for Week 2.")

# COMMAND ----------

