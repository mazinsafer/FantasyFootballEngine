---
name: fantasy-engine-architecture
description: >-
  Project blueprint and architecture for the Fantasy Football ML Prediction
  Engine: Databricks medallion data layer, XGBoost training, AWS Bedrock
  insights, FastAPI/Lakebase serving, React frontend, and MAE accuracy targets.
  Use when planning project structure, adding pipeline stages, deciding where
  code should live, or evaluating model accuracy.
---

# Fantasy Football Engine Architecture

## Pipeline Phases

1. **Databricks data layer (medallion architecture)**
   - Ingestion notebooks pull historical NFL data (`nfl_data_py`, APIs, CSVs).
   - Raw data → **Bronze** Delta table.
   - Cleaned/transformed data → **Silver** Delta table.
   - Engineered features (moving averages, target shares) → **Gold** Delta table. Models train on Gold only.
2. **ML training + AWS Bedrock**
   - Train traditional ML models (XGBoost / scikit-learn) in Databricks on the Gold table.
   - A Python script passes player stats and preliminary ML projections to AWS Bedrock for qualitative insights.
   - Final predictions + Bedrock insights → a `predictions` Delta table.
3. **FastAPI serving layer**
   - Sync the predictions Delta table into Lakebase (Databricks-managed PostgreSQL).
   - FastAPI app connects via SQLAlchemy; endpoints like `/api/predictions/{player_id}`.
4. **React TypeScript frontend**
   - Dashboard fetches from FastAPI endpoints to display projections and Bedrock insights.

## Accuracy Targets (Walk-Forward Validation, MAE)

Measure Mean Absolute Error between projected and actual fantasy points over a season. Competitive, production-ready targets by position:

| Position | Target MAE |
|----------|-----------|
| QB | 60–75 |
| RB | 50–55 |
| WR | 45–55 |
| TE | 30–35 |

## Conventions

- All historical/rolling features must be shifted by 1 week to prevent data leakage (week N predictions only see weeks 1 through N-1).
- Use time-series (walk-forward) cross-validation, never random splits.
