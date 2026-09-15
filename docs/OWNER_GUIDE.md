# FedAwardScope Owner's Guide

This guide is the shortest path from "I can run it" to "I can own and modify it."

## Product story

FedAwardScope answers four screening questions:

1. How is awarded value changing over time?
2. Which agencies and vendors account for the largest shares?
3. Which unusually large awards deserve contextual review?
4. What does a simple, explainable continuation of recent patterns look like?

It intentionally does **not** decide whether a contract is overpriced, fraudulent, competitive,
or operationally justified. Public award totals lack the unit, scope, performance, and negotiation
context required for those conclusions.

## Run the complete workflow

```bash
uv sync --extra dev
uv run fedawardscope demo
uv run fedawardscope summary
uv run streamlit run app.py
```

Follow one record through the system:

1. `generate_demo_awards()` or `USAspendingClient.fetch_awards()` creates a DataFrame.
2. `normalize_award_rows()` enforces the canonical schema for live data.
3. `AwardRepository.save_awards()` upserts the batch into DuckDB.
4. `AwardRepository.load_awards()` returns canonical records.
5. Functions in `analytics.py` transform those records without touching the database or UI.
6. `dashboard.py` renders and explains the outputs.

## What to understand in each file

### `usaspending.py`

- `AwardQuery` validates the date range and pagination bounds.
- `build_payload` translates typed criteria into the public API contract.
- `iter_pages` owns remote pagination.
- `_post_with_retry` handles temporary service failures without retrying forever.
- `normalize_award_rows` is the anti-corruption layer between the API and FedAwardScope.

### `database.py`

- The DDL is explicit so types and grain are reviewable.
- The repository pattern stops database logic leaking into the dashboard.
- Delete-then-insert by primary key creates simple, deterministic upsert behavior.
- Parameter binding is used for the export destination.

### `analytics.py`

- Metrics are pure functions: DataFrame in, result out.
- `vendor_concentration` computes shares across all vendors before limiting display rows.
- `detect_award_anomalies` uses within-segment robust statistics and a global fallback.
- `forecast_monthly_spend` fills missing months and fits a transparent baseline.

### `dashboard.py`

- Repository and data reads are cached separately.
- Filters are applied before every metric so all tabs reconcile.
- Method warnings are placed beside results, not hidden in documentation.
- CSV export uses the same filtered records visible to the user.

## Exercises that prove ownership

Complete these in order after the walkthrough:

1. Add a recipient-name filter to the sidebar.
2. Add a metric for total outlays and explain missing values.
3. Change the anomaly threshold through a sidebar control.
4. Add a table of spend by NAICS description.
5. Add an ingestion-run table with start time, query, row count, and status.
6. Add rolling-origin forecast evaluation and compare against a naive baseline.

If you can implement and explain the first four without copying a solution, you own the v1
codebase. The last two are strong v2 enhancements.

## Debugging map

| Symptom | First place to inspect |
|---|---|
| API returns 400 | Generated payload and USAspending field compatibility |
| API returns repeated 503 | Retry logs, query size, page cap, service status |
| Duplicate-looking records | Award grain and `award_id` assumptions |
| Dashboard shows no rows | Database path and active sidebar filters |
| Strange anomaly results | Segment sizes, null NAICS values, amount distribution |
| Forecast is flat or negative | Monthly history length, missing months, trend fit |
| CI fails but local passes | Python version, untracked files, dependency lock state |

## Honest authorship statement

A strong, accurate explanation is:

> I designed and developed FedAwardScope as a portfolio data product with AI-assisted implementation.
> I can explain the architecture, tests, analytical methods, limitations, and tradeoffs, and I
> validated the complete workflow myself.

Using assistance is not the weakness. Being unable to explain or change the system would be.
