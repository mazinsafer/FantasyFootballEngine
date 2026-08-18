---
name: feature-engineering-rules
description: >-
  Business rules for engineering fantasy football ML features by position (QB,
  RB, WR/TE), general game context features (Vegas implied totals, weather,
  rest), and the nfl_data_py source mapping for each feature. Use when adding,
  modifying, or reviewing features in the feature-building notebook or Gold
  table.
---

# Feature Engineering Business Rules

All rolling/historical features use past 3 and 5 game windows and must be shifted 1 week to prevent data leakage.

**Evaluation scope**: only depth-chart starters (rank 1) are evaluated at QB and TE; RB and WR keep all depth ranks (committees and WR2/WR3 are fantasy-relevant). `depth_chart_rank` is also a model feature for every position, taken from the latest `nfl.import_depth_charts()` daily snapshot before each game (as-of join on gameday, leakage-free).

**Fantasy season scope**: models train and evaluate on **weeks 1–17 only**. Week 18 (starters rest) and playoff weeks 19–22 are excluded from both training and prediction.

**Season carryover**: `prev_season_ppg` and `prev_season_games` (a player's prior-season PPR average and games played, shifted forward one season) give the model a leakage-free prior for week 1 and early-season predictions, when all in-season rolling features are zero.

## 1. General Game Context (all players)

- **Vegas Implied Team Total**: `(Over/Under / 2) + (Spread / 2)` — arguably the most powerful predictive feature. High team totals = more fantasy points.
- **Vegas Win Probability**: implied probability from the moneyline (`-ml/(-ml+100)` if negative, `100/(ml+100)` if positive). Historical **player prop lines are not freely available** (nfl_data_py has none; archives are paid APIs) — game-level spread/total/moneyline is the full obtainable betting-market signal.
- **Home/Away**: binary (1 = home).
- **Weather**: wind speed (mph, crucial for passing/kicking), precipitation (binary), temperature (degrees).
- **Rest Advantage**: days since team's last game minus days since opponent's last game.

## 2. Quarterback (QB)

Volume, matchup, and rushing upside:

- Rolling: fantasy PPG, pass attempts per game, rushing yards per game (rushing QBs have a higher, safer floor).
- Matchup: opponent defense fantasy PPG allowed to QBs (season avg), opponent pass DVOA (if available), opponent sack rate.
- Supporting cast: offensive line rank (or sack rate allowed as proxy), WR1/WR2 healthy (binary).

## 3. Running Back (RB)

Game script and opportunity share dominate:

- Opportunity (rolling 3/5): snap share (% offensive snaps), opportunity share (% of team rush attempts + targets — volume is king), High-Value Touches (receptions + carries inside the 10-yard line).
- Game script/matchup: Vegas spread (favorite = positive script = more rushing), opponent rush DVOA or yards-per-carry allowed, opponent fantasy PPG allowed to RBs.

## 4. Wide Receiver / Tight End (WR/TE)

Target volume, QB play, and defensive scheme:

- Volume (rolling 3/5): target share (% of team pass attempts), air yards share (% of team air yards), WOPR (weighted combination of target share and air yards share).
- Matchup: opponent fantasy PPG allowed to WRs/TEs, coverage scheme rates (zone vs man, if accessible).
- QB context: starting QB's adjusted yards per attempt.

## Data Source Mapping (nfl_data_py)

| Need | Source |
|------|--------|
| Rolling averages, target/air-yards shares, opponent PPG allowed | Computable from weekly stats aggregation |
| Vegas spread, over/under, home/away, weather, rest | `nfl.import_schedules([years])`, join to weekly data |
| Snap share | `nfl.import_snap_counts([years])` |
| High-value touches (inside 10), sack rates | `nfl.import_pbp_data([years])` |
| Supporting-cast injuries | `nfl.import_injuries([years])` |

### Data gotchas (verified empirically)

- `spread_line` in schedules is **positive when the home team is favored** (nflverse convention). Implied totals: home = total/2 + spread/2, away = total/2 − spread/2.
- Schedules have **no precipitation column** (only `temp`, `wind`, `roof`); use `is_dome` (`roof` in dome/closed) as the weather-proof-venue flag.
- Snap counts are keyed by **PFR player ids** (`pfr_player_id`), not GSIS ids; map via `nfl.import_seasonal_rosters()` which has both `player_id` (GSIS) and `pfr_id`.
- Rosters also provide official positions (incl. TE) — prefer them over inferring position from play-by-play roles.
- Schedules include `home_qb_id`/`away_qb_id` (scheduled starters) — use for starting-QB context features like AY/A.

### Premium data gaps and workarounds

- **DVOA** (FTN proprietary): use opponent PPG allowed and opponent yards-per-play allowed instead.
- **Man/zone coverage rates** (PFF proprietary): leave out unless scraped or purchased.
- **O-line rankings** (proprietary): compute "sack rate allowed" from play-by-play as a proxy.
