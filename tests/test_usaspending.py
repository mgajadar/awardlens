from datetime import date

import httpx

from awardlens.usaspending import AwardQuery, USAspendingClient, normalize_award_rows


def test_query_payload_contains_required_contract_filters() -> None:
    query = AwardQuery(
        date(2025, 1, 1),
        date(2025, 12, 31),
        agencies=("Department of Defense",),
    )
    payload = USAspendingClient.build_payload(query, page=2)

    assert payload["page"] == 2
    assert payload["filters"]["award_type_codes"] == ["A", "B", "C", "D"]
    assert payload["filters"]["agencies"][0]["name"] == "Department of Defense"
    assert payload["filters"]["time_period"][0]["start_date"] == "2025-01-01"


def test_normalize_award_rows_handles_classification_objects() -> None:
    rows = [
        {
            "Award ID": "ABC-123",
            "Recipient Name": "Example Vendor",
            "Recipient UEI": "EXAMPLE123",
            "Awarding Agency": "Department of Defense",
            "Award Amount": 125000,
            "Start Date": "2025-01-05",
            "NAICS": {"code": "541512", "description": "Systems Design"},
            "PSC": "D399: Other IT Services",
        }
    ]

    normalized = normalize_award_rows(rows, page=3)

    assert normalized.iloc[0]["award_id"] == "ABC-123"
    assert normalized.iloc[0]["naics_code"] == "541512"
    assert normalized.iloc[0]["naics_description"] == "Systems Design"
    assert normalized.iloc[0]["psc_code"] == "D399"
    assert normalized.iloc[0]["source_page"] == 3


def test_client_paginates_mocked_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(__import__("json").loads(request.content)["page"])
        result = {
            "results": [{"Award ID": f"AWARD-{page}", "Award Amount": page * 100}],
            "page_metadata": {"hasNext": page == 1},
        }
        return httpx.Response(200, json=result)

    client = USAspendingClient(transport=httpx.MockTransport(handler))
    query = AwardQuery(date(2025, 1, 1), date(2025, 1, 31), max_pages=5)

    frame = client.fetch_awards(query)

    assert frame["award_id"].tolist() == ["AWARD-1", "AWARD-2"]

