import pandas as pd
import pytest

from awardlens.analytics import (
    detect_award_anomalies,
    forecast_monthly_spend,
    monthly_spend,
    summary_metrics,
    vendor_concentration,
)
from awardlens.demo_data import generate_demo_awards


@pytest.fixture
def awards() -> pd.DataFrame:
    return generate_demo_awards()


def test_summary_metrics(awards: pd.DataFrame) -> None:
    metrics = summary_metrics(awards)

    assert metrics.award_count == 432
    assert metrics.total_awarded > 0
    assert metrics.median_award > 0
    assert metrics.unique_vendors == 10
    assert metrics.unique_agencies == 4


def test_monthly_spend_has_complete_demo_history(awards: pd.DataFrame) -> None:
    monthly = monthly_spend(awards)

    assert len(monthly) == 36
    assert monthly["award_count"].eq(12).all()
    assert monthly["award_amount"].sum() == pytest.approx(awards["award_amount"].sum())


def test_vendor_concentration_returns_hhi(awards: pd.DataFrame) -> None:
    vendors, hhi = vendor_concentration(awards, top_n=5)

    assert len(vendors) == 5
    assert vendors["spend_share"].between(0, 1).all()
    assert 0 < hhi <= 10_000


def test_anomaly_detector_finds_injected_large_awards(awards: pd.DataFrame) -> None:
    analyzed = detect_award_anomalies(awards)

    assert "anomaly_score" in analyzed
    assert "is_anomaly" in analyzed
    assert analyzed["is_anomaly"].sum() >= 1
    assert analyzed.iloc[0]["anomaly_score"] >= analyzed.iloc[-1]["anomaly_score"]


def test_forecast_has_requested_horizon_and_intervals(awards: pd.DataFrame) -> None:
    forecast = forecast_monthly_spend(awards, horizon=6)

    assert len(forecast) == 6
    assert forecast["forecast"].ge(0).all()
    assert forecast["lower_80"].le(forecast["forecast"]).all()
    assert forecast["upper_80"].ge(forecast["forecast"]).all()


def test_forecast_rejects_nonpositive_horizon(awards: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="horizon"):
        forecast_monthly_spend(awards, horizon=0)

