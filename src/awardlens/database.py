"""DuckDB persistence and analytical query boundary."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from awardlens.schema import AWARD_COLUMNS

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS awards (
    award_id VARCHAR PRIMARY KEY,
    recipient_name VARCHAR,
    recipient_uei VARCHAR,
    awarding_agency VARCHAR,
    awarding_sub_agency VARCHAR,
    description VARCHAR,
    start_date DATE,
    end_date DATE,
    award_amount DOUBLE,
    total_outlays DOUBLE,
    contract_award_type VARCHAR,
    naics_code VARCHAR,
    naics_description VARCHAR,
    psc_code VARCHAR,
    psc_description VARCHAR,
    place_of_performance_state VARCHAR,
    source_page INTEGER,
    ingested_at TIMESTAMPTZ,
    source VARCHAR
)
"""


class AwardRepository:
    """Repository that keeps SQL isolated from UI and pipeline code."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> duckdb.DuckDBPyConnection:
        connection = duckdb.connect(str(self.database_path))
        connection.execute("SET TimeZone = 'UTC'")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(SCHEMA_SQL)

    def save_awards(self, awards: pd.DataFrame, *, replace: bool = False) -> int:
        """Upsert canonical award records and return the number received."""

        if awards.empty:
            return 0
        missing = sorted(set(AWARD_COLUMNS) - set(awards.columns))
        if missing:
            raise ValueError(f"Missing canonical award columns: {', '.join(missing)}")

        incoming = awards[AWARD_COLUMNS].copy()
        incoming["start_date"] = pd.to_datetime(incoming["start_date"], errors="coerce")
        incoming["end_date"] = pd.to_datetime(incoming["end_date"], errors="coerce")
        incoming["ingested_at"] = pd.to_datetime(
            incoming["ingested_at"], errors="coerce", utc=True
        )

        with self.connect() as connection:
            connection.register("incoming_awards", incoming)
            if replace:
                connection.execute("DELETE FROM awards")
            connection.execute(
                "DELETE FROM awards WHERE award_id IN "
                "(SELECT award_id FROM incoming_awards WHERE award_id IS NOT NULL)"
            )
            columns = ", ".join(AWARD_COLUMNS)
            connection.execute(
                f"INSERT INTO awards ({columns}) "  # noqa: S608 - static trusted column list
                f"SELECT {columns} FROM incoming_awards WHERE award_id IS NOT NULL"
            )
        return len(incoming)

    def load_awards(self) -> pd.DataFrame:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM awards ORDER BY start_date, award_id"
            ).fetch_df()

    def count_awards(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM awards").fetchone()[0])

    def export_csv(self, output_path: str | Path) -> Path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                "COPY (SELECT * FROM awards ORDER BY start_date, award_id) "
                "TO ? (HEADER, DELIMITER ',')",
                [str(destination)],
            )
        return destination
