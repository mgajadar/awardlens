"""Interactive Streamlit dashboard for the FedAwardScope analytical product."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from fedawardscope.analytics import (
    agency_spend,
    detect_award_anomalies,
    forecast_monthly_spend,
    monthly_spend,
    summary_metrics,
    vendor_concentration,
)
from fedawardscope.config import Settings
from fedawardscope.database import AwardRepository
from fedawardscope.pipeline import load_demo

st.set_page_config(page_title="FedAwardScope", page_icon="🔎", layout="wide")


@st.cache_resource
def get_repository(database_path: str) -> AwardRepository:
    return AwardRepository(database_path)


@st.cache_data(ttl=300)
def load_awards(database_path: str) -> pd.DataFrame:
    return get_repository(database_path).load_awards()


def currency(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return f"${value:,.0f}"


def apply_filters(awards: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    agencies = sorted(awards["awarding_agency"].dropna().unique().tolist())
    selected_agencies = st.sidebar.multiselect("Awarding agency", agencies)
    states = sorted(awards["place_of_performance_state"].dropna().unique().tolist())
    selected_states = st.sidebar.multiselect("Performance state", states)

    valid_dates = pd.to_datetime(awards["start_date"], errors="coerce").dropna()
    filtered = awards.copy()
    if not valid_dates.empty:
        date_range = st.sidebar.date_input(
            "Award start date",
            value=(valid_dates.min().date(), valid_dates.max().date()),
            min_value=valid_dates.min().date(),
            max_value=valid_dates.max().date(),
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            dates = pd.to_datetime(filtered["start_date"], errors="coerce")
            filtered = filtered[
                dates.between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
            ]
    if selected_agencies:
        filtered = filtered[filtered["awarding_agency"].isin(selected_agencies)]
    if selected_states:
        filtered = filtered[
            filtered["place_of_performance_state"].isin(selected_states)
        ]
    return filtered


def render() -> None:
    settings = Settings.from_env()
    database_path = os.getenv("FEDAWARDSCOPE_DATABASE_PATH", str(settings.database_path))
    repository = get_repository(database_path)
    if repository.count_awards() == 0:
        load_demo(repository)
        load_awards.clear()

    awards = load_awards(database_path)
    filtered = apply_filters(awards)

    st.title("FedAwardScope")
    st.caption(
        "Federal procurement intelligence: spending trends, vendor concentration, "
        "transparent anomaly screening, and baseline forecasting."
    )
    if filtered.empty:
        st.warning("No awards match the selected filters.")
        return

    metrics = summary_metrics(filtered)
    _, hhi = vendor_concentration(filtered)
    columns = st.columns(6)
    columns[0].metric("Awards", f"{metrics.award_count:,}")
    columns[1].metric("Total awarded", currency(metrics.total_awarded))
    columns[2].metric("Median award", currency(metrics.median_award))
    columns[3].metric("Vendors", f"{metrics.unique_vendors:,}")
    columns[4].metric("Agencies", f"{metrics.unique_agencies:,}")
    columns[5].metric("Vendor HHI", f"{hhi:,.0f}", help="0–10,000 concentration index")

    trend_tab, vendor_tab, anomaly_tab, forecast_tab, data_tab = st.tabs(
        ["Spend trends", "Vendor concentration", "Anomalies", "Forecast", "Data explorer"]
    )

    with trend_tab:
        monthly = monthly_spend(filtered)
        agencies = agency_spend(filtered)
        left, right = st.columns([3, 2])
        with left:
            st.plotly_chart(
                px.line(
                    monthly,
                    x="month",
                    y="award_amount",
                    markers=True,
                    labels={"award_amount": "Award amount", "month": "Month"},
                    title="Monthly awarded value",
                ),
                width="stretch",
            )
        with right:
            st.plotly_chart(
                px.bar(
                    agencies.head(10),
                    x="award_amount",
                    y="awarding_agency",
                    orientation="h",
                    labels={"award_amount": "Award amount", "awarding_agency": "Agency"},
                    title="Spend by awarding agency",
                ).update_layout(yaxis={"categoryorder": "total ascending"}),
                width="stretch",
            )

    with vendor_tab:
        vendors, concentration = vendor_concentration(filtered, top_n=20)
        st.markdown(
            f"**HHI: {concentration:,.0f}.** Higher values indicate that awarded value is "
            "concentrated among fewer vendors; this is a screening metric, not a risk verdict."
        )
        st.plotly_chart(
            px.bar(
                vendors,
                x="recipient_name",
                y="spend_share",
                hover_data=["award_amount", "award_count"],
                labels={"recipient_name": "Vendor", "spend_share": "Share of value"},
                title="Leading vendors by share of awarded value",
            ),
            width="stretch",
        )
        st.dataframe(vendors, width="stretch", hide_index=True)

    with anomaly_tab:
        anomalies = detect_award_anomalies(filtered)
        flagged = anomalies[anomalies["is_anomaly"]]
        st.markdown(
            "Awards are screened against comparable agency/NAICS segments with a robust "
            "median-absolute-deviation score. A flag means **review**, not fraud or error."
        )
        st.metric("Awards flagged for review", f"{len(flagged):,}")
        display_columns = [
            "award_id",
            "recipient_name",
            "awarding_agency",
            "naics_code",
            "award_amount",
            "anomaly_score",
            "description",
        ]
        st.dataframe(flagged[display_columns], width="stretch", hide_index=True)

    with forecast_tab:
        history = monthly_spend(filtered)
        forecast = forecast_monthly_spend(filtered)
        figure = go.Figure()
        figure.add_scatter(
            x=history["month"], y=history["award_amount"], name="Actual", mode="lines+markers"
        )
        if not forecast.empty:
            figure.add_scatter(
                x=forecast["month"], y=forecast["forecast"], name="Baseline forecast"
            )
            figure.add_scatter(
                x=list(forecast["month"]) + list(forecast["month"])[::-1],
                y=list(forecast["upper_80"]) + list(forecast["lower_80"])[::-1],
                fill="toself",
                fillcolor="rgba(99, 110, 250, 0.15)",
                line={"color": "rgba(255,255,255,0)"},
                hoverinfo="skip",
                name="80% interval",
            )
        figure.update_layout(
            title="Six-month trend-and-seasonality baseline",
            xaxis_title="Month",
            yaxis_title="Award amount",
        )
        st.plotly_chart(figure, width="stretch")
        st.info(
            "The forecast is descriptive and intentionally interpretable. It should not be "
            "used for budgeting or procurement decisions without additional validation."
        )

    with data_tab:
        st.dataframe(filtered, width="stretch", hide_index=True)
        st.download_button(
            "Download filtered CSV",
            filtered.to_csv(index=False).encode("utf-8"),
            file_name="fedawardscope_filtered_awards.csv",
            mime="text/csv",
        )


render()
