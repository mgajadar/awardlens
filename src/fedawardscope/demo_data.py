"""Deterministic synthetic procurement data for an offline product demo."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

AGENCIES = {
    "Department of Defense": "Defense Logistics Agency",
    "General Services Administration": "Federal Acquisition Service",
    "Department of Health and Human Services": "Centers for Disease Control and Prevention",
    "Department of Homeland Security": "Federal Emergency Management Agency",
}

VENDORS = [
    "Apex Systems Group",
    "Beacon Analytics LLC",
    "Cobalt Manufacturing Inc.",
    "Delta Mission Services",
    "Evergreen Technology Partners",
    "Frontier Logistics Corp.",
    "Granite Cyber Solutions",
    "Harbor Medical Supply",
    "Ion Research Labs",
    "Juniper Federal Services",
]

NAICS = [
    ("541512", "Computer Systems Design Services"),
    ("541611", "Administrative Management Consulting Services"),
    ("334511", "Search and Navigation Instrument Manufacturing"),
    ("493110", "General Warehousing and Storage"),
    ("423450", "Medical Equipment Merchant Wholesalers"),
]

STATES = ["CA", "CO", "FL", "MD", "NY", "TX", "VA", "WA"]


def generate_demo_awards(
    *, months: int = 36, awards_per_month: int = 12, seed: int = 42
) -> pd.DataFrame:
    """Generate repeatable, realistic-looking award-level records.

    The dataset is explicitly synthetic. Several high-value records are injected so
    the anomaly-analysis screen has explainable examples during a demonstration.
    """

    rng = np.random.default_rng(seed)
    month_starts = pd.date_range(end="2026-08-01", periods=months, freq="MS")
    records: list[dict[str, object]] = []
    agency_names = list(AGENCIES)
    now = datetime.now(UTC).replace(microsecond=0)

    for month_index, month_start in enumerate(month_starts):
        for position in range(awards_per_month):
            agency = rng.choice(agency_names, p=[0.48, 0.18, 0.2, 0.14])
            vendor = rng.choice(VENDORS)
            naics_code, naics_description = NAICS[int(rng.integers(0, len(NAICS)))]
            trend = 1 + (month_index / max(months - 1, 1)) * 0.32
            amount = float(rng.lognormal(mean=12.3, sigma=1.0) * trend)
            if (month_index, position) in {(8, 2), (21, 7), (33, 4)}:
                amount *= 18
            start_date = month_start + pd.Timedelta(days=int(rng.integers(0, 25)))
            duration_days = int(rng.integers(120, 1_095))

            records.append(
                {
                    "award_id": f"DEMO-{month_start:%Y%m}-{position:03d}",
                    "recipient_name": vendor,
                    "recipient_uei": f"UEI{abs(hash(vendor)) % 10**9:09d}",
                    "awarding_agency": agency,
                    "awarding_sub_agency": AGENCIES[agency],
                    "description": (
                        f"Synthetic {naics_description.lower()} procurement for analytics demo"
                    ),
                    "start_date": start_date,
                    "end_date": start_date + pd.Timedelta(days=duration_days),
                    "award_amount": round(amount, 2),
                    "total_outlays": round(amount * float(rng.uniform(0.15, 0.92)), 2),
                    "contract_award_type": rng.choice(
                        ["Definitive Contract", "Delivery Order", "Purchase Order"]
                    ),
                    "naics_code": naics_code,
                    "naics_description": naics_description,
                    "psc_code": rng.choice(["R408", "D399", "6515", "J015"]),
                    "psc_description": "Synthetic product or service classification",
                    "place_of_performance_state": rng.choice(STATES),
                    "source_page": 0,
                    "ingested_at": now,
                    "source": "synthetic_demo",
                }
            )

    return pd.DataFrame.from_records(records)

