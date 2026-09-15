# Canonical Data Dictionary

| Column | Type | Meaning |
|---|---|---|
| `award_id` | text | Public award identifier and idempotent primary key |
| `recipient_name` | text | Name of the prime award recipient |
| `recipient_uei` | text | Recipient Unique Entity Identifier when available |
| `awarding_agency` | text | Top-tier agency issuing the award |
| `awarding_sub_agency` | text | Sub-agency issuing the award |
| `description` | text | Public award description |
| `start_date` | date | Award period start date |
| `end_date` | date | Award period end date |
| `award_amount` | double | USAspending award-level amount; not a unit price |
| `total_outlays` | double | Reported award outlays when available |
| `contract_award_type` | text | Human-readable contract award type |
| `naics_code` | text | North American Industry Classification System code |
| `naics_description` | text | NAICS label when returned by the source |
| `psc_code` | text | Product or Service Code |
| `psc_description` | text | PSC label when returned by the source |
| `place_of_performance_state` | text | State code for primary performance location |
| `source_page` | integer | API page used for traceability; zero means demo data |
| `ingested_at` | timestamp | UTC normalization time |
| `source` | text | `usaspending_api` or `synthetic_demo` |

## Grain

One row represents one prime contract award returned by the Spending by Award endpoint. It is not
one transaction, invoice, line item, or unit purchased. Transaction-level questions require a
different endpoint and model.

