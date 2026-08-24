---
name: fantasy-engine-architecture
description: >-
  Project blueprint and architecture for the Fantasy Football ML Prediction
  Engine: Databricks medallion data layer, XGBoost training, OpenAI (GPT-5.6
  Terra) insights, FastAPI (Databricks SQL Connector) serving, React frontend,
  and MAE accuracy targets.
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
2. **ML training + OpenAI insights**
   - Train traditional ML models (XGBoost / scikit-learn) in Databricks on the Gold table.
   - `insights/insights_pipeline.ipynb` passes player stats and ML projections to the OpenAI API (GPT-5.6 Terra, Responses API) for qualitative insights.
   - Final predictions + LLM insights → a `predictions` Delta table.
3. **FastAPI serving layer** (`api/`, implemented)
   - Queries Unity Catalog Delta tables directly via the Databricks SQL Connector (no Lakebase / SQLAlchemy copy).
   - Endpoints: `/health`, `/api/players`, `/api/predictions`, `/api/weeks`, `/api/teams`. Run with `uvicorn main:app --reload --host 0.0.0.0 --port 8000` from `api/`.
4. **React TypeScript frontend**
   - Dashboard fetches from FastAPI endpoints to display projections and LLM insights.

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
