"""Canonical AwardLens data contract."""

from __future__ import annotations

AWARD_COLUMNS = [
    "award_id",
    "recipient_name",
    "recipient_uei",
    "awarding_agency",
    "awarding_sub_agency",
    "description",
    "start_date",
    "end_date",
    "award_amount",
    "total_outlays",
    "contract_award_type",
    "naics_code",
    "naics_description",
    "psc_code",
    "psc_description",
    "place_of_performance_state",
    "source_page",
    "ingested_at",
    "source",
]

TEXT_COLUMNS = [
    "award_id",
    "recipient_name",
    "recipient_uei",
    "awarding_agency",
    "awarding_sub_agency",
    "description",
    "contract_award_type",
    "naics_code",
    "naics_description",
    "psc_code",
    "psc_description",
    "place_of_performance_state",
    "source",
]

