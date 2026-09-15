# Interview Defense Pack

## Thirty-second pitch

> AwardLens is an end-to-end Python and SQL analytics product built around public federal contract
> data. It ingests and normalizes USAspending awards, stores them in DuckDB, and exposes spending
> trends, vendor concentration, robust anomaly screening, and an interpretable forecast through a
> Streamlit dashboard. I focused on reproducibility and responsible interpretation, so it also has
> offline demo data, automated tests, CI, Docker, lineage fields, and explicit method limitations.

## Two-minute walkthrough

> I chose federal procurement because it is financially meaningful public data with real data-
> engineering problems. The USAspending client builds valid contract-award filters, retries
> temporary failures, paginates safely, and normalizes source-specific fields into a canonical
> schema. An `AwardRepository` persists that model in DuckDB with idempotent upserts. Pure analytics
> functions calculate reconciled KPIs, monthly trends, vendor shares and HHI, a segment-aware robust
> anomaly score, and a transparent seasonal trend baseline. Streamlit provides a usable analytical
> interface, while the CLI makes ingestion, demo loading, summary reporting, and export repeatable.
> The test suite avoids network dependence by mocking the API and covers the pipeline from data
> creation through storage and analysis.

## Recruiter and hiring-manager questions

### Why did you choose this project?

I wanted one project that demonstrated the complete analyst workflow rather than another notebook:
source acquisition, data modeling, SQL persistence, statistical analysis, communication, testing,
and deployment. Federal awards are public, consequential, and complex enough to expose realistic
tradeoffs without using confidential employer data.

### What business problem does it solve?

It reduces the effort required to turn public award records into an initial procurement-spending
review. An analyst can locate major trends, concentration, and records requiring context before
performing deeper investigation.

### What was your contribution?

I owned the product definition, architecture, data contract, analytical choices, validation,
documentation, and end-to-end integration. I used AI assistance during implementation, then tested,
reviewed, and learned each component so I could modify and defend it.

### What did you learn?

The most important lesson was that analytical correctness begins with grain and definitions.
USAspending's award amount is not a unit price, and award-level records are not transactions.
Stating those limits correctly matters as much as calculating the metrics.

## Data and Python questions

### How did you retrieve the data?

The client sends POST requests to USAspending's Spending by Award endpoint with contract award-type
codes and a date range. It paginates until `hasNext` is false or a caller-controlled cap is reached.
Transient rate-limit and server errors receive bounded exponential retry.

### Why normalize the response?

The public API uses display names, nullable fields, and sometimes structured classifications.
Normalizing once gives downstream code stable names and types and isolates future API changes.

### How did you prevent duplicate loads?

`award_id` is the canonical primary key. Each batch deletes existing matching keys and inserts the
new records. Re-running a query therefore updates the stored representation rather than appending
duplicates.

### Why DuckDB instead of PostgreSQL?

DuckDB makes an analytical portfolio project runnable with no infrastructure and performs well for
local columnar analysis. PostgreSQL would be preferable for concurrent users and transactional
services. The repository abstraction makes that replacement contained.

### Where is SQL used?

DuckDB DDL defines the canonical model, and the repository uses SQL for keyed replacement, ordered
reads, counts, and exports. The same design can be extended with SQL marts or migrated to a cloud
warehouse.

## Statistics questions

### How does anomaly detection work?

I log-transform absolute award values because they are highly right-skewed. Within each agency and
NAICS segment, I calculate the median and MAD, then assign a robust standardized score. Small or
degenerate segments use the global distribution. Records above 3.5 are review candidates.

### Why not use Isolation Forest?

The first version prioritizes transparency. A reviewer can calculate and explain a MAD score,
whereas an Isolation Forest adds model complexity without solving the missing-context problem.
I would benchmark multivariate methods after adding better contract features and labeled review
outcomes.

### Does a flagged award mean fraud or overpricing?

No. It only means the award value is unusual relative to the selected statistical comparison.
Scope, quantity, urgency, contract structure, and performance requirements can fully explain it.

### How does the forecast work?

I aggregate award amounts monthly, fill missing months with zero, and fit least squares with an
intercept, trend, and annual sine/cosine terms. It is an interpretable baseline. A production model
would require rolling-origin evaluation, naive benchmarks, external drivers, and calibrated
intervals.

## Engineering questions

### How is the project tested?

Tests cover deterministic demo generation, metric reconciliation, concentration, anomaly flags,
forecast shape, database upsert/export, request construction, mocked pagination, and an end-to-end
demo pipeline. CI runs Ruff and pytest with a coverage threshold on every pull request.

### Why include synthetic data?

It guarantees a working, reproducible demo when the public API is slow or unavailable. It also
makes CI deterministic. The interface labels synthetic data explicitly to prevent confusion.

### How would you scale it?

I would retain raw responses in object storage, record ingestion metadata, move canonical tables to
a managed warehouse, schedule incremental loads, expose analytics through an API, and add
authentication, observability, and deployment controls.

### What would fail first in production?

The synchronous page-by-page API ingestion and single-process embedded database. They are excellent
for a transparent local product but not for large, concurrent workloads. Source schema drift is
another major risk, so I would add contract tests and raw-response retention.

## Questions you should ask the interviewer

- How does your team define and validate analytical data contracts?
- How are business users involved when selecting anomaly thresholds or model outputs?
- What distinguishes a successful analyst in the first six months?
- How does the team move work from exploratory analysis into repeatable production workflows?

## Dangerous answers to avoid

- "The model finds fraudulent contracts."
- "Award amount is the price paid for each item."
- "The forecast predicts government budgets."
- "DuckDB is always better than PostgreSQL."
- "The data is accurate because it comes from the government."
- "AI built it, so I do not know that part."

