---
name: clustering-and-rag
description: >-
  Design for player clustering (unsupervised archetype grouping) and the
  Retrieval-Augmented Generation flow that feeds player data into AWS Bedrock
  for qualitative insights. Use when implementing clustering, Bedrock
  integration, RAG retrieval, or the insights portion of the prediction API.
---

# Clustering & RAG Design

## Player Clustering

Unsupervised grouping of players with similar profiles — it explains prediction volatility rather than predicting points. Example: cluster WRs on target share, average depth of target (aDOT), and red zone targets:

- **Slot/PPR Machine**: high target share, low aDOT (e.g. Amon-Ra St. Brown).
- **Deep Threat/Boom-Bust**: low target share, high aDOT (e.g. Gabe Davis) — expect volatile predictions.
- **Elite Alpha**: high target share, high red zone usage (e.g. Justin Jefferson).

Attach each player's cluster label to their profile; surface it alongside predictions to contextualize model confidence.

## RAG Flow (AWS Bedrock)

The LLM doesn't know current injuries, weather, or this project's predictions, so every Bedrock call follows retrieve → augment → generate:

1. **Retrieve**: on a FastAPI query for a player, pull from Databricks (or a vector DB): the model's prediction, recent news, weather data, and the player's cluster profile.
2. **Augment**: inject the retrieved data into the prompt (e.g. projected points, recent target share, cluster label, game-day weather).
3. **Generate**: Bedrock writes a fluent summary grounded in that data (e.g. "CeeDee Lamb projects well this week (18.5 pts). Despite the snow, his elite 30% target share provides a safe floor...").
