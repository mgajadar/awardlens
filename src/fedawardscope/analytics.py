"""Business metrics, concentration analysis, anomaly detection, and forecasting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class SummaryMetrics:
    award_count: int
    total_awarded: float
    median_award: float
    unique_vendors: int
    unique_agencies: int


def _valid_awards(awards: pd.DataFrame) -> pd.DataFrame:
    frame = awards.copy()
    frame["award_amount"] = pd.to_numeric(frame["award_amount"], errors="coerce")
    frame["start_date"] = pd.to_datetime(frame["start_date"], errors="coerce")
    return frame.dropna(subset=["award_amount"])


def summary_metrics(awards: pd.DataFrame) -> SummaryMetrics:
    frame = _valid_awards(awards)
    return SummaryMetrics(
        award_count=len(frame),
        total_awarded=float(frame["award_amount"].sum()),
        median_award=float(frame["award_amount"].median()) if not frame.empty else 0.0,
        unique_vendors=int(frame["recipient_name"].nunique(dropna=True)),
        unique_agencies=int(frame["awarding_agency"].nunique(dropna=True)),
    )


def monthly_spend(awards: pd.DataFrame) -> pd.DataFrame:
    frame = _valid_awards(awards).dropna(subset=["start_date"])
    if frame.empty:
        return pd.DataFrame(columns=["month", "award_amount", "award_count"])
    frame["month"] = frame["start_date"].dt.to_period("M").dt.to_timestamp()
    return (
        frame.groupby("month", as_index=False)
        .agg(award_amount=("award_amount", "sum"), award_count=("award_id", "nunique"))
        .sort_values("month")
    )


def agency_spend(awards: pd.DataFrame) -> pd.DataFrame:
    frame = _valid_awards(awards)
    return (
        frame.fillna({"awarding_agency": "Unknown"})
        .groupby("awarding_agency", as_index=False)
        .agg(
            award_amount=("award_amount", "sum"),
            award_count=("award_id", "nunique"),
            vendors=("recipient_name", "nunique"),
        )
        .sort_values("award_amount", ascending=False)
    )


def vendor_concentration(awards: pd.DataFrame, *, top_n: int = 15) -> tuple[pd.DataFrame, float]:
    """Return vendor shares and the 0-10,000 Herfindahl-Hirschman Index."""

    frame = _valid_awards(awards).fillna({"recipient_name": "Unknown"})
    grouped = (
        frame.groupby("recipient_name", as_index=False)
        .agg(award_amount=("award_amount", "sum"), award_count=("award_id", "nunique"))
        .sort_values("award_amount", ascending=False)
    )
    total = float(grouped["award_amount"].sum())
    grouped["spend_share"] = grouped["award_amount"] / total if total else 0.0
    hhi = float((grouped["spend_share"].pow(2).sum()) * 10_000) if total else 0.0
    return grouped.head(top_n).reset_index(drop=True), hhi


def detect_award_anomalies(
    awards: pd.DataFrame, *, threshold: float = 3.5, minimum_group_size: int = 8
) -> pd.DataFrame:
    """Flag unusually large awards using a robust within-segment MAD score.

    Awards are compared within awarding-agency and NAICS segments. Small segments
    fall back to the global distribution. Log scaling reduces the influence of the
    naturally long-tailed contract-value distribution.
    """

    frame = _valid_awards(awards)
    if frame.empty:
        return frame.assign(anomaly_score=pd.Series(dtype=float), is_anomaly=False)

    frame = frame.copy()
    frame["_log_amount"] = np.log1p(frame["award_amount"].abs())
    frame["_segment"] = (
        frame["awarding_agency"].fillna("Unknown").astype(str)
        + " | "
        + frame["naics_code"].fillna("Unknown").astype(str)
    )

    global_median = float(frame["_log_amount"].median())
    global_mad = float((frame["_log_amount"] - global_median).abs().median())
    global_mad = global_mad if global_mad > 1e-9 else 1.0

    scores = pd.Series(index=frame.index, dtype=float)
    for _, group in frame.groupby("_segment"):
        if len(group) >= minimum_group_size:
            median = float(group["_log_amount"].median())
            mad = float((group["_log_amount"] - median).abs().median())
            if mad <= 1e-9:
                median, mad = global_median, global_mad
        else:
            median, mad = global_median, global_mad
        scores.loc[group.index] = 0.6745 * (group["_log_amount"] - median) / mad

    frame["anomaly_score"] = scores.round(3)
    frame["is_anomaly"] = frame["anomaly_score"] >= threshold
    return frame.drop(columns=["_log_amount", "_segment"]).sort_values(
        "anomaly_score", ascending=False
    )


def forecast_monthly_spend(awards: pd.DataFrame, *, horizon: int = 6) -> pd.DataFrame:
    """Forecast spend with an interpretable trend-plus-seasonality regression.

    This is intentionally a transparent baseline rather than a claim of causal or
    production-grade forecasting. Prediction bands use historical residual error.
    """

    history = monthly_spend(awards)
    if horizon < 1:
        raise ValueError("horizon must be positive")
    if len(history) < 6:
        return pd.DataFrame(
            columns=["month", "forecast", "lower_80", "upper_80", "is_forecast"]
        )

    full_months = pd.date_range(history["month"].min(), history["month"].max(), freq="MS")
    series = (
        history.set_index("month")["award_amount"]
        .reindex(full_months, fill_value=0.0)
        .astype(float)
    )
    time_index = np.arange(len(series), dtype=float)
    design = _forecast_design_matrix(time_index)
    coefficients, *_ = np.linalg.lstsq(design, series.to_numpy(), rcond=None)
    fitted = design @ coefficients
    residual_std = float(np.std(series.to_numpy() - fitted, ddof=min(1, len(series) - 1)))

    future_index = np.arange(len(series), len(series) + horizon, dtype=float)
    predictions = np.maximum(_forecast_design_matrix(future_index) @ coefficients, 0.0)
    future_months = pd.date_range(
        series.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS"
    )
    margin = 1.282 * residual_std
    return pd.DataFrame(
        {
            "month": future_months,
            "forecast": predictions,
            "lower_80": np.maximum(predictions - margin, 0.0),
            "upper_80": predictions + margin,
            "is_forecast": True,
        }
    )


def _forecast_design_matrix(time_index: np.ndarray) -> np.ndarray:
    angle = 2 * np.pi * time_index / 12
    return np.column_stack(
        [np.ones_like(time_index), time_index, np.sin(angle), np.cos(angle)]
    )

