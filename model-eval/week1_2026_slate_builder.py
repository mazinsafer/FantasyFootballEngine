# Databricks notebook source
# DBTITLE 1,Introduction
# MAGIC %md
# MAGIC # 2026 Week 1 Slate Builder + Prediction
# MAGIC
# MAGIC **Purpose:** Generate fantasy football predictions for the **future** 2026 NFL Week 1 slate before any games are played.
# MAGIC
# MAGIC **Why this is different from historical Week 1 predictions:**
# MAGIC - The Gold table (`fantasy_football.gold.player_weeks`) is built from play-by-play data of games already played
# MAGIC - 2026 Week 1 rows don't exist yet — we must construct them as a **forward-looking slate**
# MAGIC - Build one row per fantasy-relevant player from: 2026 schedules (game context), 2026 rosters (who's on which team), 2026 depth charts (role), and 2025 carryover stats (established level)
# MAGIC - All in-season rolling features (3/5-week averages, target share, etc.) are set to 0, exactly what the model saw for historical Week 1 rows
# MAGIC
# MAGIC **Data-timing caveats** (running this before ~Sept 1, 2026 gives degraded results):
# MAGIC 1. **Vegas lines** (spread/total/moneyline) are preliminary until early September; some games may have null lines — fill win_prob with 0.5 and flag missing-line rows
# MAGIC 2. **Depth charts** are unreliable until final 53-man roster cuts (~Sept 1); before then, depth_chart_rank reflects camp bodies, not real starters
# MAGIC 3. **Weather** (temp/wind) is unknowable pre-game-week — set to season-normal values or 0, keep dome flag from stadium roof
# MAGIC 4. **Rookies** have prev_season_ppg=0, so the model will systematically underrate them — known, accepted limitation
# MAGIC
# MAGIC **Production schedule:** Build this notebook now for validation, but schedule the actual production run for the **first week of September 2026** when the inputs are reliable.
# MAGIC
# MAGIC **Output:** Writes season=2026, week=1 rows to `fantasy_football.gold.predictions` via MERGE (appends alongside existing 2025 Week 17 seed data).

# COMMAND ----------

# DBTITLE 1,Install dependencies
# Install required packages
%pip install nfl_data_py xgboost scikit-learn

# COMMAND ----------

# DBTITLE 1,Load 2026 schedule and game context
import pandas as pd
import numpy as np
import nfl_data_py as nfl
from xgboost import XGBRegressor

print("Loading 2026 NFL schedule and game context...")

# Load 2026 schedule (spread_line, total_line, home/away, roof for dome flag)
schedules_2026 = nfl.import_schedules([2026])
week1_games = schedules_2026[schedules_2026['week'] == 1].copy()

print(f"Found {len(week1_games)} games in 2026 Week 1")
print(f"Games with lines: {week1_games['spread_line'].notna().sum()} spread, {week1_games['total_line'].notna().sum()} total")

# Build home and away dataframes
home_df = week1_games[['home_team', 'away_team', 'spread_line', 'total_line', 'home_moneyline', 'roof']].copy()
home_df.columns = ['team', 'opponent', 'spread_line', 'total_line', 'moneyline', 'roof']
home_df['is_home'] = 1

away_df = week1_games[['away_team', 'home_team', 'spread_line', 'total_line', 'away_moneyline', 'roof']].copy()
away_df.columns = ['team', 'opponent', 'spread_line', 'total_line', 'moneyline', 'roof']
away_df['is_home'] = 0
away_df['spread_line'] = -away_df['spread_line']  # flip spread for away team

game_context = pd.concat([home_df, away_df], ignore_index=True)

# Calculate implied totals and win probabilities.
# spread_line is already from THIS team's perspective (away rows were flipped
# above), positive = this team favored — so favorites get the HIGHER share of
# the total: implied_total = total/2 + spread/2 (same convention as
# feature_building, where home_implied = total/2 + spread/2 with a
# positive-means-home-favored spread).
game_context['implied_total'] = (
    game_context['total_line'].fillna(44.0) / 2   # league-average total when line missing
    + game_context['spread_line'].fillna(0) / 2
)

# Win probability from moneyline (American odds)
def moneyline_to_prob(ml):
    if pd.isna(ml):
        return 0.5  # neutral when line missing
    if ml > 0:
        return 100 / (ml + 100)
    else:
        return abs(ml) / (abs(ml) + 100)

game_context['team_win_prob'] = game_context['moneyline'].apply(moneyline_to_prob)
game_context['team_spread'] = game_context['spread_line'].fillna(0)

# Dome flag (roof type: 'dome', 'closed', 'open', 'outdoors')
game_context['is_dome'] = game_context['roof'].isin(['dome', 'closed']).astype(int)

# Weather: unknowable pre-game-week. Set to neutral values.
# (In production, this would be populated from weather API ~1 week before game)
game_context['temp'] = 72  # season-neutral temp
game_context['wind'] = 0   # assume calm until weather known
game_context['is_bad_weather'] = 0  # flag set to 1 if temp<30 or wind>15

# Flag games with missing Vegas lines (preliminary schedule)
game_context['missing_vegas_lines'] = game_context['spread_line'].isna().astype(int)

print(f"\n✓ Game context built for {len(game_context)} team-game records")
print(f"  Missing Vegas lines: {game_context['missing_vegas_lines'].sum()} team-games")
print(f"  Dome games: {game_context['is_dome'].sum()} team-games")

# COMMAND ----------

# DBTITLE 1,Load 2026 rosters and depth charts
print("\nLoading 2026 rosters and depth charts...")

# Load 2026 seasonal rosters (who's on which team)
rosters_2026 = nfl.import_seasonal_rosters([2026])
rosters_2026 = rosters_2026[rosters_2026['position'].isin(['QB', 'RB', 'WR', 'TE'])].copy()  # fantasy-relevant positions

print(f"Found {len(rosters_2026)} fantasy-relevant players on 2026 rosters")

# Load 2026 depth charts. 2025+ depth charts use the SNAPSHOT schema
# (dt / pos_abb / pos_rank / gsis_id) — the pre-2025 week/depth_team/full_name
# columns do not exist. Join on gsis_id (name joins are fragile), mirroring
# feature_building's snapshot-era logic.
depth_charts_2026 = nfl.import_depth_charts([2026])

depth_off = depth_charts_2026[
    depth_charts_2026['pos_abb'].isin(['QB', 'RB', 'WR', 'TE', 'FB'])
].copy()
depth_off['snapshot_dt'] = pd.to_datetime(depth_off['dt']).dt.tz_localize(None)
depth_off['gsis_id'] = depth_off['gsis_id'].astype(str)

# Best (min) rank per player per snapshot day, then keep the latest snapshot
# (the one closest to Week 1 — role entering the season)
snap_ranks = (
    depth_off.groupby(['gsis_id', 'snapshot_dt'])['pos_rank'].min().reset_index()
    .sort_values('snapshot_dt')
)
latest_dc = snap_ranks.drop_duplicates('gsis_id', keep='last')

# Map depth chart to roster (depth_chart_rank: 1=starter, 2=backup, etc.)
rosters_2026['player_id'] = rosters_2026['player_id'].astype(str)
rosters_2026 = rosters_2026.merge(
    latest_dc[['gsis_id', 'pos_rank']],
    left_on='player_id', right_on='gsis_id', how='left'
).drop(columns=['gsis_id'])
rosters_2026['depth_chart_rank'] = rosters_2026['pos_rank'].fillna(99).astype(int)  # 99=not on depth chart

print(f"Depth chart ranks assigned: {(rosters_2026['depth_chart_rank'] < 99).sum()} players on depth chart")
print(f"Starters (depth_chart_rank=1): {(rosters_2026['depth_chart_rank'] == 1).sum()} players")

# CAVEAT: Depth charts before final roster cuts (~Sept 1) include camp bodies, not real starters!
print("\n⚠️  WARNING: If running before Sept 1, 2026, depth charts reflect camp rosters, not final starters.")

# Match the Gold table's business rule: QB and TE are one-man positions, so
# only depth-1 starters are evaluated. The model was trained exclusively on
# starter QB/TE rows — predictions for backups would be meaningless.
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
carryover = gold_2025.groupby('player_id').agg(
    prev_season_ppg=('fantasy_points_ppr', 'mean'),
    prev_season_games=('fantasy_points_ppr', 'count')
).reset_index()

print(f"Calculated carryover stats for {len(carryover)} players from 2025 season")

# Merge carryover stats to 2026 roster
rosters_2026 = rosters_2026.merge(
    carryover[['player_id', 'prev_season_ppg', 'prev_season_games']],
    on='player_id',
    how='left'
)

# Rookies and players without 2025 data get 0 (known limitation — model will underrate them)
rosters_2026['prev_season_ppg'] = rosters_2026['prev_season_ppg'].fillna(0)
rosters_2026['prev_season_games'] = rosters_2026['prev_season_games'].fillna(0)

rookies = (rosters_2026['prev_season_games'] == 0).sum()
print(f"\nRookies or new players (prev_season_games=0): {rookies}")
print(f"⚠️  Model will systematically underrate rookies — this is a known, accepted limitation.")

# COMMAND ----------

# DBTITLE 1,Build 2026 Week 1 slate DataFrame
print("\nBuilding 2026 Week 1 slate DataFrame...")

# Merge rosters with game context
slate_2026 = rosters_2026.merge(
    game_context[['team', 'opponent', 'implied_total', 'team_spread', 'team_win_prob',
                  'is_home', 'is_dome', 'temp', 'wind', 'is_bad_weather', 'missing_vegas_lines']],
    on='team',
    how='inner'
)

# Set all in-season rolling features to 0 (exactly what historical Week 1 rows had)
rolling_features = [
    'fantasy_points_3wk_avg', 'fantasy_points_5wk_avg',
    'hvt_3wk_avg', 'hvt_5wk_avg',
    'qb_pass_attempts_3wk_avg', 'qb_pass_attempts_5wk_avg',
    'qb_rushing_yards_3wk_avg', 'qb_rushing_yards_5wk_avg',
    'pass_rate_diff', 'blitz_rate_diff',
    'opp_def_ppg_allowed', 'opp_def_pressure_rate',
    'opp_def_sack_rate', 'team_sack_rate_allowed',
    'injury_severity'
]

for feat in rolling_features:
    slate_2026[feat] = 0

# Set week and season
slate_2026['week'] = 1
slate_2026['season'] = 2026

# Rename columns to match Gold table schema
slate_2026 = slate_2026.rename(columns={
    'team': 'recent_team',
    'full_name': 'player_name'
})

print(f"✓ Built slate for {len(slate_2026)} player-game records in 2026 Week 1")
print(f"  By position: {slate_2026['position'].value_counts().to_dict()}")
print(f"  Games with missing Vegas lines: {slate_2026['missing_vegas_lines'].sum()} player-games")

# COMMAND ----------

# DBTITLE 1,Match feature columns to training data
print("\nAligning feature columns to match training data schema...")

# Load training data (2020-2025 Gold table, weeks 1-17)
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
    'wopr', 'snap_share'
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

# COMMAND ----------

# DBTITLE 1,Train model on 2020-2025 Week 1-17 data
print("\nTraining XGBoost model on 2020-2025 data (weeks 1-17), early-stopping on 2025 Week 1...")

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

# DBTITLE 1,Generate 2026 Week 1 predictions
print("\nGenerating 2026 Week 1 predictions...")

# Predict
predictions_2026 = np.clip(model.predict(slate_features), 0, None)

# Build predictions DataFrame
predictions_df = slate_2026[['player_id', 'player_name', 'recent_team', 'position', 
                              'opponent', 'season', 'week']].copy()
predictions_df['projected_ppr'] = predictions_2026.astype(float).round(1)

# Add context features (for RAG retrieval in insights pipeline)
context_cols = ['implied_total', 'team_spread', 'team_win_prob', 'is_home',
                'temp', 'wind', 'is_bad_weather', 'is_dome',
                'prev_season_ppg', 'depth_chart_rank', 'missing_vegas_lines']

for col in context_cols:
    if col in slate_2026.columns:
        predictions_df[col] = slate_2026[col].values

# Add opponent defense PPG allowed (not available for future, set to 0)
predictions_df['opp_def_ppg_allowed'] = 0
predictions_df['fantasy_points_3wk_avg'] = 0  # no in-season form yet

# Sort by projection
predictions_df = predictions_df.sort_values('projected_ppr', ascending=False).reset_index(drop=True)

print(f"✓ Generated predictions for {len(predictions_df)} players")
print(f"\nTop 10 projected players:")
print(predictions_df[['player_name', 'position', 'recent_team', 'projected_ppr']].head(10))

# COMMAND ----------

# DBTITLE 1,Write predictions to Delta table
print("\nWriting 2026 Week 1 predictions to fantasy_football.gold.predictions...")

# Convert to Spark DataFrame
predictions_spark = spark.createDataFrame(predictions_df)

# MERGE into predictions table (history table, not snapshot)
# Use replaceWhere to partition by (season=2026, week=1)
predictions_spark.write \
    .format("delta") \
    .mode("overwrite") \
    .option("replaceWhere", "season = 2026 AND week = 1") \
    .saveAsTable("fantasy_football.gold.predictions")

print(f"✓ Merged 2026 Week 1 predictions into fantasy_football.gold.predictions")
print(f"  Rows written: {len(predictions_df)}")
print(f"  Partition: season=2026, week=1")
print(f"\n✅ 2026 Week 1 slate build complete!")
print(f"\n⚠️  REMINDER: Schedule production run for FIRST WEEK OF SEPTEMBER 2026")
print(f"   (Vegas lines, depth charts, and roster cuts finalize by then)")

# COMMAND ----------

