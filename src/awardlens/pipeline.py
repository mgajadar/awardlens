"""End-to-end data loading workflows."""

from __future__ import annotations

from dataclasses import dataclass

from awardlens.database import AwardRepository
from awardlens.demo_data import generate_demo_awards
from awardlens.usaspending import AwardQuery, USAspendingClient


@dataclass(frozen=True, slots=True)
class PipelineResult:
    received: int
    stored_total: int
    source: str


def load_demo(repository: AwardRepository) -> PipelineResult:
    awards = generate_demo_awards()
    received = repository.save_awards(awards, replace=True)
    return PipelineResult(received, repository.count_awards(), "synthetic_demo")


def ingest_usaspending(
    repository: AwardRepository,
    client: USAspendingClient,
    query: AwardQuery,
) -> PipelineResult:
    awards = client.fetch_awards(query)
    received = repository.save_awards(awards)
    return PipelineResult(received, repository.count_awards(), "usaspending_api")

