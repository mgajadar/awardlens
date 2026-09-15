# Architecture and Design Decisions

## System boundaries

AwardLens separates acquisition, persistence, analysis, and presentation. The separation is more
important than the specific libraries: it prevents Streamlit callbacks from becoming the data
pipeline and keeps external API changes away from business calculations.

| Layer | Module | Responsibility |
|---|---|---|
| Configuration | `config.py` | Convert environment variables into typed runtime settings |
| Source adapter | `usaspending.py` | Build valid requests, retry, paginate, normalize external fields |
| Demo source | `demo_data.py` | Produce deterministic offline records for reviewers and CI |
| Storage | `database.py` | Own DuckDB schema, idempotent upserts, reads, and exports |
| Orchestration | `pipeline.py` | Connect sources to storage without UI coupling |
| Analytics | `analytics.py` | Pure, testable business/statistical transformations |
| Interfaces | `cli.py`, `dashboard.py` | Human workflows and interactive presentation |

## Why DuckDB?

DuckDB is embedded, analytical, SQL-native, and works directly with pandas. A reviewer can clone
the repository and run the product without provisioning infrastructure. PostgreSQL would be a
better choice for concurrent writes, authentication, and a multi-user service; AwardLens keeps
database access behind `AwardRepository` so that migration is localized.

## Why Streamlit?

The purpose is to demonstrate analytical reasoning rather than front-end engineering. Streamlit
turns the data product into something a reviewer can use while leaving the Python analytics
visible. A React/FastAPI architecture would provide greater interface control and independent
scaling, but it would add deployment surface without improving the central portfolio signal.

## Why a canonical schema?

External APIs change independently of internal consumers. The normalization function maps fields
such as `Award Amount`, nested NAICS objects, and nullable classifications into stable snake-case
columns. Dashboard and analytics code do not depend on USAspending's response format.

## Idempotency

`award_id` is the primary key. Before inserting a page or batch, the repository removes existing
rows with matching identifiers and inserts the newest canonical record. Re-running the same query
therefore updates records rather than multiplying them.

## Failure handling

- HTTP 429 and common transient 5xx responses receive bounded exponential retry.
- Request timeouts and retry counts are configurable.
- Pagination is capped by the caller.
- Empty results are valid and do not corrupt the database.
- The dashboard loads a deterministic demo when no records exist.
- CI never relies on network access; HTTP behavior is tested through `MockTransport`.

## Statistical design

The anomaly method uses log-scaled values and robust MAD scoring because procurement values are
long-tailed and ordinary z-scores are easily distorted by the records they are supposed to flag.
Segmentation improves comparability, while a global fallback avoids unstable statistics for small
groups.

The forecast uses a transparent regression baseline. A production forecasting program would add
rolling-origin evaluation, benchmark models, external drivers, prediction-interval calibration,
and documented selection criteria before operational use.

## Scaling path

1. Land immutable raw API responses in object storage.
2. Add ingestion-run and data-quality audit tables.
3. Move canonical tables to PostgreSQL, BigQuery, or Snowflake.
4. Schedule incremental ingestion with an orchestrator.
5. Publish analytics through a FastAPI service.
6. Add authentication, authorization, observability, and deployment promotion controls.

