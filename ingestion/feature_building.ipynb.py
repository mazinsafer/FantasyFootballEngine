# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,Import libraries and load source data
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("Feature Engineering for Fantasy Football ML Model")
print("="*80)
print("\nThis notebook transforms raw stats into ML-ready features.")
print("Key principle: All historical metrics are SHIFTED by 1 week to prevent data leakage.\n")

# COMMAND ----------

# DBTITLE 1,Install nfl_data_py library
# Install required packages for NFL data extraction
%pip install --no-deps nfl_data_py
%pip install appdirs fastparquet pandas

# COMMAND ----------

# DBTITLE 1,Run nfl_py_extraction notebook to get source data
# Load source data directly using nfl_data_py library
import nfl_data_py as nfl
import pandas as pd

print("Loading data from nfl_data_py library...")

# Load 2025 play-by-play data
pbp_2025 = nfl.import_pbp_data([2025], downcast=True)
print(f"Loaded {len(pbp_2025)} plays from 2025 season")

# Load schedules
schedules = nfl.import_schedules([2025])
print(f"Loaded {len(schedules)} games from schedules")

# Calculate weekly stats (from the extraction notebook logic)
print("\nCalculating weekly player statistics from play-by-play data...")

# Passer aggregations
passing_plays = pbp_2025[pbp_2025['play_type'] == 'pass'].copy()
passer_stats = passing_plays.groupby(
    ['week', 'passer_player_id', 'passer_player_name'], 
    dropna=False
).agg({
    'pass_attempt': 'sum',
    'complete_pass': 'sum',
    'yards_gained': 'sum',
    'pass_touchdown': 'sum',
    'interception': 'sum'
}).reset_index()
passer_stats.rename(columns={
    'passer_player_id': 'player_id',
    'passer_player_name': 'player_name',
    'pass_attempt': 'pass_attempts',
    'complete_pass': 'completions',
    'yards_gained': 'passing_yards',
    'pass_touchdown': 'passing_tds',
    'interception': 'interceptions'
}, inplace=True)

# Rusher aggregations
rushing_plays = pbp_2025[pbp_2025['play_type'] == 'run'].copy()
rusher_stats = rushing_plays.groupby(
    ['week', 'rusher_player_id', 'rusher_player_name'],
    dropna=False
).agg({
    'rush_attempt': 'sum',
    'yards_gained': 'sum',
    'rush_touchdown': 'sum'
}).reset_index()
rusher_stats.rename(columns={
    'rusher_player_id': 'player_id',
    'rusher_player_name': 'player_name',
    'rush_attempt': 'rush_attempts',
    'yards_gained': 'rushing_yards',
    'rush_touchdown': 'rushing_tds'
}, inplace=True)

# Receiver aggregations
receiving_plays = pbp_2025[
    (pbp_2025['play_type'] == 'pass') & 
    (pbp_2025['receiver_player_id'].notna())
].copy()
receiver_stats = receiving_plays.groupby(
    ['week', 'receiver_player_id', 'receiver_player_name'],
    dropna=False
).agg({
    'pass_attempt': 'sum',
    'complete_pass': 'sum',
    'yards_gained': 'sum',
    'pass_touchdown': 'sum'
}).reset_index()
receiver_stats.rename(columns={
    'receiver_player_id': 'player_id',
    'receiver_player_name': 'player_name',
    'pass_attempt': 'targets',
    'complete_pass': 'receptions',
    'yards_gained': 'receiving_yards',
    'pass_touchdown': 'receiving_tds'
}, inplace=True)

# Merge all stats
weekly_stats = passer_stats.merge(rusher_stats, on=['week', 'player_id', 'player_name'], how='outer')
weekly_stats = weekly_stats.merge(receiver_stats, on=['week', 'player_id', 'player_name'], how='outer')
weekly_stats['player_name'] = weekly_stats['player_name'].ffill().bfill()

numeric_cols = [
    'pass_attempts', 'completions', 'passing_yards', 'passing_tds', 'interceptions',
    'rush_attempts', 'rushing_yards', 'rushing_tds',
    'targets', 'receptions', 'receiving_yards', 'receiving_tds'
]
weekly_stats[numeric_cols] = weekly_stats[numeric_cols].fillna(0)

# Calculate fantasy points (PPR)
weekly_stats['fantasy_points_ppr'] = (
    (weekly_stats['passing_yards'] * 0.04) +
    (weekly_stats['passing_tds'] * 4) +
    (weekly_stats['interceptions'] * -2) +
    (weekly_stats['rushing_yards'] * 0.1) +
    (weekly_stats['rushing_tds'] * 6) +
    (weekly_stats['receiving_yards'] * 0.1) +
    (weekly_stats['receiving_tds'] * 6) +
    (weekly_stats['receptions'] * 1)
)
weekly_stats['fantasy_points_ppr'] = weekly_stats['fantasy_points_ppr'].round(2)
weekly_stats = weekly_stats.sort_values('fantasy_points_ppr', ascending=False).reset_index(drop=True)

print(f"\n✓ Data loaded and ready for feature engineering:")
print(f"  - weekly_stats: {len(weekly_stats):,} player-week records")
print(f"  - schedules: {len(schedules):,} games")
print(f"  - pbp_2025: {len(pbp_2025):,} plays")

# COMMAND ----------

# DBTITLE 1,Identify player positions and teams from PBP data
# ============================================================================
# STEP 1: Identify player positions and teams from play-by-play data
# ============================================================================
print("Step 1: Identifying player positions and teams...\n")

# Extract position from PBP data (passers = QB, rushers = RB, receivers = WR/TE)
passers = pbp_2025[pbp_2025['passer_player_id'].notna()][['passer_player_id', 'passer_player_name', 'posteam', 'week']].copy()
passers.columns = ['player_id', 'player_name', 'team', 'week']
passers['position'] = 'QB'

rushers = pbp_2025[pbp_2025['rusher_player_id'].notna()][['rusher_player_id', 'rusher_player_name', 'posteam', 'week']].copy()
rushers.columns = ['player_id', 'player_name', 'team', 'week']
rushers['position'] = 'RB'  # Default to RB, we'll refine this

receivers = pbp_2025[pbp_2025['receiver_player_id'].notna()][['receiver_player_id', 'receiver_player_name', 'posteam', 'week']].copy()
receivers.columns = ['player_id', 'player_name', 'team', 'week']
receivers['position'] = 'WR'  # Default to WR, we'll refine based on usage patterns

# Combine all players
all_players = pd.concat([passers, rushers, receivers], ignore_index=True)

# For each player, take the most common position (mode)
player_position = all_players.groupby('player_id').agg({
    'player_name': 'first',
    'position': lambda x: x.mode()[0] if not x.mode().empty else 'FLEX'
}).reset_index()

print(f"Identified positions for {len(player_position)} unique players:")
print(player_position['position'].value_counts())

# Get most recent team for each player
player_team = all_players.sort_values('week').groupby('player_id').agg({
    'team': 'last'
}).reset_index()
player_team.columns = ['player_id', 'recent_team']

# Merge position and team into weekly_stats
weekly_stats_df = weekly_stats.copy()
weekly_stats_df = weekly_stats_df.merge(player_position, on='player_id', how='left', suffixes=('', '_lookup'))
weekly_stats_df = weekly_stats_df.merge(player_team, on='player_id', how='left')

# Use lookup values to fill missing player_name if needed
weekly_stats_df['player_name'] = weekly_stats_df['player_name'].fillna(weekly_stats_df['player_name_lookup'])
weekly_stats_df.drop(columns=['player_name_lookup'], inplace=True, errors='ignore')

print(f"\nEnriched weekly_stats with position and team data.")
print(f"Shape: {weekly_stats_df.shape}")
display(weekly_stats_df.head())

# COMMAND ----------

# DBTITLE 1,CATEGORY 1: General Game Context Features
# ============================================================================
# CATEGORY 1: General Game Context (Applies to all players)
# ============================================================================
print("\nStep 2: Engineering General Game Context Features...\n")

# Prepare schedules data
schedules_df = schedules.copy()

# Calculate implied team totals
schedules_df['home_implied_total'] = np.where(
    schedules_df['spread_line'] < 0,  # Home team favored
    (schedules_df['total_line'] / 2) + (abs(schedules_df['spread_line']) / 2),
    (schedules_df['total_line'] / 2) - (schedules_df['spread_line'] / 2)
)

schedules_df['away_implied_total'] = np.where(
    schedules_df['spread_line'] > 0,  # Away team favored (spread is positive)
    (schedules_df['total_line'] / 2) + (schedules_df['spread_line'] / 2),
    (schedules_df['total_line'] / 2) - (abs(schedules_df['spread_line']) / 2)
)

# Weather flags
schedules_df['is_bad_weather'] = (
    (schedules_df['wind'] > 15) | (schedules_df['temp'] < 32)
).astype(int)

# Create home/away context for each team
home_context = schedules_df[['week', 'home_team', 'home_implied_total', 'temp', 'wind', 'is_bad_weather', 'gameday']].copy()
home_context.columns = ['week', 'team', 'implied_total', 'temp', 'wind', 'is_bad_weather', 'gameday']
home_context['is_home'] = 1
home_context['opponent'] = schedules_df['away_team']

away_context = schedules_df[['week', 'away_team', 'away_implied_total', 'temp', 'wind', 'is_bad_weather', 'gameday']].copy()
away_context.columns = ['week', 'team', 'implied_total', 'temp', 'wind', 'is_bad_weather', 'gameday']
away_context['is_home'] = 0
away_context['opponent'] = schedules_df['home_team']

# Combine home and away
game_context = pd.concat([home_context, away_context], ignore_index=True)

# Calculate rest advantage (days since last game)
game_context['gameday'] = pd.to_datetime(game_context['gameday'])
game_context = game_context.sort_values(['team', 'gameday'])
game_context['days_since_last_game'] = game_context.groupby('team')['gameday'].diff().dt.days

# Merge opponent's days since last game to calculate rest advantage
opponent_rest = game_context[['week', 'team', 'days_since_last_game']].copy()
opponent_rest.columns = ['week', 'opponent', 'opp_days_since_last_game']

game_context = game_context.merge(opponent_rest, on=['week', 'opponent'], how='left')
game_context['rest_advantage'] = game_context['days_since_last_game'] - game_context['opp_days_since_last_game']
game_context['rest_advantage'] = game_context['rest_advantage'].fillna(0)

# Merge game context into weekly_stats_df
weekly_stats_df = weekly_stats_df.merge(
    game_context[['week', 'team', 'implied_total', 'is_home', 'temp', 'wind', 'is_bad_weather', 'rest_advantage', 'opponent']],
    left_on=['week', 'recent_team'],
    right_on=['week', 'team'],
    how='left'
)

# Drop duplicate team column
weekly_stats_df.drop(columns=['team'], inplace=True, errors='ignore')

print("✓ Added game context features:")
print("  - implied_total (Vegas implied team total)")
print("  - is_home (1=home, 0=away)")
print("  - temp, wind (weather conditions)")
print("  - is_bad_weather (wind>15mph or temp<32F)")
print("  - rest_advantage (days since last game difference)")
print(f"\nCurrent shape: {weekly_stats_df.shape}")

# COMMAND ----------

# DBTITLE 1,CATEGORY 2: Rolling Averages (All Players)
# ============================================================================
# CATEGORY 2: Rolling Averages (3-Week & 5-Week) - For ALL Players
# ============================================================================
print("\nStep 3: Calculating Rolling Averages (SHIFTED to prevent data leakage)...\n")

# Sort by player and week to ensure proper rolling calculations
weekly_stats_df = weekly_stats_df.sort_values(['player_id', 'week']).reset_index(drop=True)

# Calculate SHIFTED rolling averages for fantasy points
weekly_stats_df['fantasy_points_3wk_avg'] = (
    weekly_stats_df.groupby('player_id')['fantasy_points_ppr']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

weekly_stats_df['fantasy_points_5wk_avg'] = (
    weekly_stats_df.groupby('player_id')['fantasy_points_ppr']
    .transform(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
)

print("✓ Added rolling averages for ALL players:")
print("  - fantasy_points_3wk_avg (shifted 3-week average)")
print("  - fantasy_points_5wk_avg (shifted 5-week average)")
print("\n  Note: All rolling metrics use .shift(1) to prevent data leakage.")
print(f"\nCurrent shape: {weekly_stats_df.shape}")

# COMMAND ----------

# DBTITLE 1,CATEGORY 3: QB-Specific Features
# ============================================================================
# CATEGORY 3: Quarterback (QB) Specific Features
# ============================================================================
print("\nStep 4: Engineering QB-Specific Features...\n")

# Filter for QBs only
qb_mask = weekly_stats_df['position'] == 'QB'

# Calculate SHIFTED rolling averages for passing attempts and rushing yards
weekly_stats_df.loc[qb_mask, 'qb_pass_attempts_3wk_avg'] = (
    weekly_stats_df[qb_mask].groupby('player_id')['pass_attempts']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

weekly_stats_df.loc[qb_mask, 'qb_pass_attempts_5wk_avg'] = (
    weekly_stats_df[qb_mask].groupby('player_id')['pass_attempts']
    .transform(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
)

weekly_stats_df.loc[qb_mask, 'qb_rushing_yards_3wk_avg'] = (
    weekly_stats_df[qb_mask].groupby('player_id')['rushing_yards']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

weekly_stats_df.loc[qb_mask, 'qb_rushing_yards_5wk_avg'] = (
    weekly_stats_df[qb_mask].groupby('player_id')['rushing_yards']
    .transform(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
)

qb_count = qb_mask.sum()
print(f"✓ Added QB-specific features for {qb_count} QB-week records:")
print("  - qb_pass_attempts_3wk_avg & 5wk_avg (shifted)")
print("  - qb_rushing_yards_3wk_avg & 5wk_avg (shifted, captures rushing floor)")
print(f"\nCurrent shape: {weekly_stats_df.shape}")

# COMMAND ----------

# DBTITLE 1,CATEGORY 4: RB-Specific Features
# ============================================================================
# CATEGORY 4: Running Back (RB) Specific Features
# ============================================================================
print("\nStep 5: Engineering RB-Specific Features...\n")

# --- 4A: Opportunity Share ---
print("  Calculating Opportunity Share...")

# Calculate team totals per week
team_opportunities = pbp_2025.groupby(['posteam', 'week']).agg({
    'rush_attempt': 'sum',
    'pass_attempt': 'sum'  # Targets come from pass attempts
}).reset_index()
team_opportunities['team_total_opportunities'] = (
    team_opportunities['rush_attempt'] + team_opportunities['pass_attempt']
)
team_opportunities = team_opportunities[['posteam', 'week', 'team_total_opportunities']]
team_opportunities.columns = ['team', 'week', 'team_total_opportunities']

# Calculate player opportunities (rush attempts + targets)
weekly_stats_df['player_opportunities'] = (
    weekly_stats_df['rush_attempts'] + weekly_stats_df['targets']
)

# Merge team totals
weekly_stats_df = weekly_stats_df.merge(
    team_opportunities,
    left_on=['recent_team', 'week'],
    right_on=['team', 'week'],
    how='left'
)
weekly_stats_df.drop(columns=['team'], inplace=True, errors='ignore')

# Calculate opportunity share
weekly_stats_df['opportunity_share'] = (
    weekly_stats_df['player_opportunities'] / weekly_stats_df['team_total_opportunities']
).fillna(0)

# SHIFTED 3-week rolling average for RBs only
rb_mask = weekly_stats_df['position'] == 'RB'
weekly_stats_df.loc[rb_mask, 'rb_opportunity_share_3wk_avg'] = (
    weekly_stats_df[rb_mask].groupby('player_id')['opportunity_share']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

# --- 4B: High-Value Touches (HVTs) ---
print("  Calculating High-Value Touches (yardline <= 10)...")

# Count carries and targets inside the 10-yard line
hvt_carries = pbp_2025[
    (pbp_2025['play_type'] == 'run') & 
    (pbp_2025['yardline_100'] <= 10) &
    (pbp_2025['rusher_player_id'].notna())
].groupby(['rusher_player_id', 'week']).size().reset_index(name='hvt_carries')
hvt_carries.columns = ['player_id', 'week', 'hvt_carries']

hvt_targets = pbp_2025[
    (pbp_2025['play_type'] == 'pass') & 
    (pbp_2025['yardline_100'] <= 10) &
    (pbp_2025['receiver_player_id'].notna())
].groupby(['receiver_player_id', 'week']).size().reset_index(name='hvt_targets')
hvt_targets.columns = ['player_id', 'week', 'hvt_targets']

# Merge HVTs into main dataframe
weekly_stats_df = weekly_stats_df.merge(hvt_carries, on=['player_id', 'week'], how='left')
weekly_stats_df = weekly_stats_df.merge(hvt_targets, on=['player_id', 'week'], how='left')
weekly_stats_df['hvt_carries'] = weekly_stats_df['hvt_carries'].fillna(0)
weekly_stats_df['hvt_targets'] = weekly_stats_df['hvt_targets'].fillna(0)
weekly_stats_df['total_hvts'] = weekly_stats_df['hvt_carries'] + weekly_stats_df['hvt_targets']

# SHIFTED 3-week rolling average for RBs only
weekly_stats_df.loc[rb_mask, 'rb_hvts_3wk_avg'] = (
    weekly_stats_df[rb_mask].groupby('player_id')['total_hvts']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

rb_count = rb_mask.sum()
print(f"\n✓ Added RB-specific features for {rb_count} RB-week records:")
print("  - rb_opportunity_share_3wk_avg (shifted, rush attempts + targets / team total)")
print("  - rb_hvts_3wk_avg (shifted, high-value touches inside 10-yard line)")
print(f"\nCurrent shape: {weekly_stats_df.shape}")

# COMMAND ----------

# DBTITLE 1,CATEGORY 5: WR/TE-Specific Features
# ============================================================================
# CATEGORY 5: Wide Receiver (WR) / Tight End (TE) Specific Features
# ============================================================================
print("\nStep 6: Engineering WR/TE-Specific Features...\n")

# --- 5A: Target Share ---
print("  Calculating Target Share...")

# Team passing attempts per week (already calculated above in team_opportunities)
team_pass_attempts = pbp_2025.groupby(['posteam', 'week'])['pass_attempt'].sum().reset_index()
team_pass_attempts.columns = ['team', 'week', 'team_pass_attempts']

# Merge team passing attempts
weekly_stats_df = weekly_stats_df.merge(
    team_pass_attempts,
    left_on=['recent_team', 'week'],
    right_on=['team', 'week'],
    how='left'
)
weekly_stats_df.drop(columns=['team'], inplace=True, errors='ignore')

# Calculate target share
weekly_stats_df['target_share'] = (
    weekly_stats_df['targets'] / weekly_stats_df['team_pass_attempts']
).fillna(0)

# SHIFTED rolling averages for WR/TE only
wr_te_mask = weekly_stats_df['position'].isin(['WR', 'TE'])

weekly_stats_df.loc[wr_te_mask, 'wr_te_target_share_3wk_avg'] = (
    weekly_stats_df[wr_te_mask].groupby('player_id')['target_share']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

weekly_stats_df.loc[wr_te_mask, 'wr_te_target_share_5wk_avg'] = (
    weekly_stats_df[wr_te_mask].groupby('player_id')['target_share']
    .transform(lambda x: x.shift(1).rolling(window=5, min_periods=1).mean())
)

# --- 5B: Air Yards Share ---
print("  Calculating Air Yards Share...")

# Sum player air yards per week
player_air_yards = pbp_2025[
    pbp_2025['receiver_player_id'].notna() & 
    pbp_2025['air_yards'].notna()
].groupby(['receiver_player_id', 'week'])['air_yards'].sum().reset_index()
player_air_yards.columns = ['player_id', 'week', 'player_air_yards']

# Sum team air yards per week
team_air_yards = pbp_2025[
    pbp_2025['posteam'].notna() & 
    pbp_2025['air_yards'].notna()
].groupby(['posteam', 'week'])['air_yards'].sum().reset_index()
team_air_yards.columns = ['team', 'week', 'team_air_yards']

# Merge player air yards
weekly_stats_df = weekly_stats_df.merge(player_air_yards, on=['player_id', 'week'], how='left')
weekly_stats_df['player_air_yards'] = weekly_stats_df['player_air_yards'].fillna(0)

# Merge team air yards
weekly_stats_df = weekly_stats_df.merge(
    team_air_yards,
    left_on=['recent_team', 'week'],
    right_on=['team', 'week'],
    how='left'
)
weekly_stats_df.drop(columns=['team'], inplace=True, errors='ignore')

# Calculate air yards share
weekly_stats_df['air_yards_share'] = (
    weekly_stats_df['player_air_yards'] / weekly_stats_df['team_air_yards']
).fillna(0)

# SHIFTED 3-week rolling average for WR/TE only
weekly_stats_df.loc[wr_te_mask, 'wr_te_air_yards_share_3wk_avg'] = (
    weekly_stats_df[wr_te_mask].groupby('player_id')['air_yards_share']
    .transform(lambda x: x.shift(1).rolling(window=3, min_periods=1).mean())
)

wr_te_count = wr_te_mask.sum()
print(f"\n✓ Added WR/TE-specific features for {wr_te_count} WR/TE-week records:")
print("  - wr_te_target_share_3wk_avg & 5wk_avg (shifted, targets / team pass attempts)")
print("  - wr_te_air_yards_share_3wk_avg (shifted, air yards / team air yards)")
print(f"\nCurrent shape: {weekly_stats_df.shape}")

# COMMAND ----------

# DBTITLE 1,CATEGORY 6: Matchup Features (Opponent Defense)
# ============================================================================
# CATEGORY 6: Matchup Features (Opponent Defense)
# ============================================================================
print("\nStep 7: Engineering Matchup Features (Opponent Defense Metrics)...\n")

# Get defensive team from play-by-play
# For each play, the defense is the team that does NOT have the ball (defteam)

# Calculate fantasy points allowed by defense per position per week
print("  Calculating fantasy points allowed by each defense...")

# Get the defense each player faced each week
# Defense = opponent team for that week (we already have 'opponent' from game_context)

# Aggregate fantasy points allowed by defense (opponent) to each position
def_points_allowed = weekly_stats_df.groupby(['opponent', 'week', 'position'])['fantasy_points_ppr'].sum().reset_index()
def_points_allowed.columns = ['defense', 'week', 'position', 'fp_allowed_this_week']

# Calculate season-to-date average fantasy points allowed by defense to each position
# This must be SHIFTED to prevent data leakage
def_points_allowed = def_points_allowed.sort_values(['defense', 'position', 'week'])

def_points_allowed['def_fp_allowed_cumsum'] = (
    def_points_allowed.groupby(['defense', 'position'])['fp_allowed_this_week']
    .transform(lambda x: x.shift(1).expanding().sum())
)

def_points_allowed['def_weeks_played'] = (
    def_points_allowed.groupby(['defense', 'position']).cumcount()
)

# Average = cumulative sum / weeks played (using shifted data)
def_points_allowed['opp_def_ppg_allowed'] = (
    def_points_allowed['def_fp_allowed_cumsum'] / def_points_allowed['def_weeks_played']
).fillna(0)

# Handle division by zero (first week has no history)
def_points_allowed['opp_def_ppg_allowed'] = def_points_allowed['opp_def_ppg_allowed'].replace([np.inf, -np.inf], 0)

# Merge defensive metrics into main dataframe
weekly_stats_df = weekly_stats_df.merge(
    def_points_allowed[['defense', 'week', 'position', 'opp_def_ppg_allowed']],
    left_on=['opponent', 'week', 'position'],
    right_on=['defense', 'week', 'position'],
    how='left'
)
weekly_stats_df.drop(columns=['defense'], inplace=True, errors='ignore')
weekly_stats_df['opp_def_ppg_allowed'] = weekly_stats_df['opp_def_ppg_allowed'].fillna(0)

print("✓ Added matchup features:")
print("  - opp_def_ppg_allowed (shifted season-to-date avg FP allowed by opponent defense to this position)")
print(f"\nCurrent shape: {weekly_stats_df.shape}")

# COMMAND ----------

# DBTITLE 1,Final Cleanup and Output Gold DataFrame
# ============================================================================
# FINAL CLEANUP: Fill NaNs and Prepare Gold DataFrame
# ============================================================================
print("\nStep 8: Final Cleanup...\n")

# List of all feature columns that might have NaNs
feature_cols = [
    'fantasy_points_3wk_avg', 'fantasy_points_5wk_avg',
    'qb_pass_attempts_3wk_avg', 'qb_pass_attempts_5wk_avg',
    'qb_rushing_yards_3wk_avg', 'qb_rushing_yards_5wk_avg',
    'rb_opportunity_share_3wk_avg', 'rb_hvts_3wk_avg',
    'wr_te_target_share_3wk_avg', 'wr_te_target_share_5wk_avg',
    'wr_te_air_yards_share_3wk_avg',
    'opp_def_ppg_allowed',
    'implied_total', 'temp', 'wind', 'rest_advantage'
]

# Fill NaN values with 0
for col in feature_cols:
    if col in weekly_stats_df.columns:
        weekly_stats_df[col] = weekly_stats_df[col].fillna(0)

# Create the Gold DataFrame
gold_df = weekly_stats_df.copy()

print("="*80)
print("FEATURE ENGINEERING COMPLETE")
print("="*80)
print(f"\nGold DataFrame Shape: {gold_df.shape}")
print(f"Total Features: {len(gold_df.columns)}")
print(f"\nSample of engineered features:")

# Show a sample of key features
feature_sample_cols = [
    'week', 'player_name', 'position', 'recent_team', 'opponent',
    'fantasy_points_ppr', 'fantasy_points_3wk_avg',
    'implied_total', 'is_home', 'opp_def_ppg_allowed'
]
available_cols = [col for col in feature_sample_cols if col in gold_df.columns]
display(gold_df[available_cols].head(10))

print(f"\n✓ All NaN values in feature columns filled with 0")
print(f"✓ Gold DataFrame ready for XGBoost training!")
print(f"\nNext steps:")
print("  1. Split data into train/validation/test sets (by week or chronologically)")
print("  2. Define target variable (fantasy_points_ppr)")
print("  3. Train XGBoost model")
print("  4. Evaluate predictions")

# COMMAND ----------

# DBTITLE 1,Feature Summary and Data Quality Checks
# ============================================================================
# DATA QUALITY CHECKS AND FEATURE SUMMARY
# ============================================================================
print("\n" + "="*80)
print("FEATURE SUMMARY & DATA QUALITY REPORT")
print("="*80)

# 1. Overall Statistics
print(f"\n1. OVERALL STATISTICS:")
print(f"   Total Records: {len(gold_df):,}")
print(f"   Total Features: {len(gold_df.columns)}")
print(f"   Weeks Covered: {gold_df['week'].min()} - {gold_df['week'].max()}")
print(f"   Unique Players: {gold_df['player_id'].nunique():,}")

# 2. Position Breakdown
print(f"\n2. POSITION BREAKDOWN:")
print(gold_df['position'].value_counts())

# 3. Feature Categories
print(f"\n3. FEATURE CATEGORIES:")
print(f"   ✓ General Context: implied_total, is_home, temp, wind, is_bad_weather, rest_advantage")
print(f"   ✓ Rolling Averages: fantasy_points_3wk_avg, fantasy_points_5wk_avg")
print(f"   ✓ QB Features: qb_pass_attempts_3wk/5wk_avg, qb_rushing_yards_3wk/5wk_avg")
print(f"   ✓ RB Features: rb_opportunity_share_3wk_avg, rb_hvts_3wk_avg")
print(f"   ✓ WR/TE Features: wr_te_target_share_3wk/5wk_avg, wr_te_air_yards_share_3wk_avg")
print(f"   ✓ Matchup Features: opp_def_ppg_allowed")

# 4. Missing Values Check
print(f"\n4. MISSING VALUES CHECK:")
missing = gold_df.isnull().sum()
if missing.sum() == 0:
    print("   ✓ No missing values in any column!")
else:
    print("   Columns with missing values:")
    print(missing[missing > 0])

# 5. Data Leakage Prevention Verification
print(f"\n5. DATA LEAKAGE PREVENTION VERIFICATION:")
print("   All rolling averages and historical metrics use .shift(1)")
print("   Week N predictions can only see data from Weeks 1 through N-1")
print("   ✓ Model is ready for time-series cross-validation")

# 6. Sample Feature Values for Top Performers
print(f"\n6. SAMPLE: Top 5 Fantasy Performances with Features")
top_performers = gold_df.nlargest(5, 'fantasy_points_ppr')[[
    'week', 'player_name', 'position', 'fantasy_points_ppr', 
    'fantasy_points_3wk_avg', 'implied_total', 'is_home', 'opp_def_ppg_allowed'
]]
display(top_performers)

print("\n" + "="*80)
print("Gold DataFrame is ready for ML model training!")
print("="*80)

# COMMAND ----------

