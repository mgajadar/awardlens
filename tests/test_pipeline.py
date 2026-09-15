from pathlib import Path

from awardlens.database import AwardRepository
from awardlens.pipeline import load_demo


def test_demo_pipeline_is_end_to_end(tmp_path: Path) -> None:
    repository = AwardRepository(tmp_path / "awardlens.duckdb")

    result = load_demo(repository)

    assert result.source == "synthetic_demo"
    assert result.received == 432
    assert result.stored_total == 432

