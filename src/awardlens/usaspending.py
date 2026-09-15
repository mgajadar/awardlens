"""Resilient client for USAspending's public Spending by Award API."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pandas as pd

from awardlens.schema import AWARD_COLUMNS

CONTRACT_AWARD_TYPE_CODES = ("A", "B", "C", "D")
AWARD_FIELDS = (
    "Award ID",
    "Recipient Name",
    "Recipient UEI",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Description",
    "Start Date",
    "End Date",
    "Award Amount",
    "Total Outlays",
    "Contract Award Type",
    "NAICS",
    "PSC",
    "Place of Performance State Code",
)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class USAspendingError(RuntimeError):
    """Raised when USAspending cannot provide a valid response."""


@dataclass(frozen=True, slots=True)
class AwardQuery:
    """Search criteria for prime contract awards."""

    start_date: date
    end_date: date
    agencies: tuple[str, ...] = ()
    limit_per_page: int = 100
    max_pages: int = 10

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if not 1 <= self.limit_per_page <= 100:
            raise ValueError("limit_per_page must be between 1 and 100")
        if self.max_pages < 1:
            raise ValueError("max_pages must be positive")


class USAspendingClient:
    """Small synchronous API client with pagination and exponential retry."""

    endpoint = "/api/v2/search/spending_by_award/"

    def __init__(
        self,
        *,
        base_url: str = "https://api.usaspending.gov",
        timeout_seconds: float = 30,
        max_retries: int = 4,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.transport = transport

    @staticmethod
    def build_payload(query: AwardQuery, page: int) -> dict[str, Any]:
        filters: dict[str, Any] = {
            "award_type_codes": list(CONTRACT_AWARD_TYPE_CODES),
            "time_period": [
                {
                    "start_date": query.start_date.isoformat(),
                    "end_date": query.end_date.isoformat(),
                }
            ],
        }
        if query.agencies:
            filters["agencies"] = [
                {"type": "awarding", "tier": "toptier", "name": agency}
                for agency in query.agencies
            ]

        return {
            "subawards": False,
            "spending_level": "awards",
            "limit": query.limit_per_page,
            "page": page,
            "sort": "Award Amount",
            "order": "desc",
            "filters": filters,
            "fields": list(AWARD_FIELDS),
        }

    def iter_pages(self, query: AwardQuery) -> Iterator[tuple[int, list[dict[str, Any]]]]:
        """Yield API result pages until the API or configured page limit is exhausted."""

        headers = {"User-Agent": "AwardLens/0.1 (public-data analytics project)"}
        with httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            headers=headers,
            transport=self.transport,
        ) as client:
            for page in range(1, query.max_pages + 1):
                payload = self.build_payload(query, page)
                data = self._post_with_retry(client, payload)
                results = data.get("results", [])
                if not isinstance(results, list):
                    raise USAspendingError("USAspending returned a non-list results value")
                yield page, results

                metadata = data.get("page_metadata", {})
                has_next = bool(metadata.get("hasNext", metadata.get("has_next", False)))
                if not results or not has_next:
                    break

    def fetch_awards(self, query: AwardQuery) -> pd.DataFrame:
        frames = [normalize_award_rows(rows, page=page) for page, rows in self.iter_pages(query)]
        if not frames:
            return pd.DataFrame(columns=AWARD_COLUMNS)
        return pd.concat(frames, ignore_index=True)[AWARD_COLUMNS]

    def _post_with_retry(
        self, client: httpx.Client, payload: dict[str, Any]
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = client.post(self.endpoint, json=payload)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    raise httpx.HTTPStatusError(
                        "retryable USAspending response",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                result = response.json()
                if not isinstance(result, dict):
                    raise USAspendingError("USAspending returned a non-object response")
                return result
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2**attempt, 8))

        raise USAspendingError(
            f"USAspending request failed after {self.max_retries + 1} attempts"
        ) from last_error


def _classification_parts(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        code = value.get("code") or value.get("naics") or value.get("psc")
        description = value.get("description") or value.get("name")
        return _clean_text(code), _clean_text(description)
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    if ":" in text:
        code, description = text.split(":", maxsplit=1)
        return _clean_text(code), _clean_text(description)
    return text, None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_award_rows(rows: list[dict[str, Any]], *, page: int) -> pd.DataFrame:
    """Convert the external API schema into AwardLens's stable internal contract."""

    ingested_at = datetime.now(UTC).replace(microsecond=0)
    normalized: list[dict[str, Any]] = []

    for row in rows:
        naics_code, naics_description = _classification_parts(row.get("NAICS"))
        psc_code, psc_description = _classification_parts(row.get("PSC"))
        normalized.append(
            {
                "award_id": _clean_text(row.get("Award ID")),
                "recipient_name": _clean_text(row.get("Recipient Name")),
                "recipient_uei": _clean_text(row.get("Recipient UEI")),
                "awarding_agency": _clean_text(row.get("Awarding Agency")),
                "awarding_sub_agency": _clean_text(row.get("Awarding Sub Agency")),
                "description": _clean_text(row.get("Description")),
                "start_date": pd.to_datetime(row.get("Start Date"), errors="coerce"),
                "end_date": pd.to_datetime(row.get("End Date"), errors="coerce"),
                "award_amount": pd.to_numeric(row.get("Award Amount"), errors="coerce"),
                "total_outlays": pd.to_numeric(row.get("Total Outlays"), errors="coerce"),
                "contract_award_type": _clean_text(row.get("Contract Award Type")),
                "naics_code": naics_code,
                "naics_description": naics_description,
                "psc_code": psc_code,
                "psc_description": psc_description,
                "place_of_performance_state": _clean_text(
                    row.get("Place of Performance State Code")
                ),
                "source_page": page,
                "ingested_at": ingested_at,
                "source": "usaspending_api",
            }
        )

    frame = pd.DataFrame.from_records(normalized, columns=AWARD_COLUMNS)
    if not frame.empty:
        frame = frame.dropna(subset=["award_id"]).drop_duplicates("award_id", keep="last")
    return frame
