from pathlib import Path

from fedawardscope.database import AwardRepository
from fedawardscope.demo_data import generate_demo_awards


def test_repository_round_trip_and_upsert(tmp_path: Path) -> None:
    repository = AwardRepository(tmp_path / "test.duckdb")
    awards = generate_demo_awards(months=2, awards_per_month=4)

    assert repository.save_awards(awards) == 8
    assert repository.count_awards() == 8

    changed = awards.iloc[[0]].copy()
    changed.loc[:, "award_amount"] = 999_999.0
    repository.save_awards(changed)

    stored = repository.load_awards()
    assert len(stored) == 8
    changed_amount = stored.loc[
        stored["award_id"] == changed.iloc[0]["award_id"], "award_amount"
    ].item()
    assert changed_amount == 999_999.0


def test_repository_replace_and_export(tmp_path: Path) -> None:
    repository = AwardRepository(tmp_path / "test.duckdb")
    repository.save_awards(generate_demo_awards(months=2, awards_per_month=4))
    replacement = generate_demo_awards(months=1, awards_per_month=3, seed=9)

    repository.save_awards(replacement, replace=True)
    output = repository.export_csv(tmp_path / "exports" / "awards.csv")

    assert repository.count_awards() == 3
    assert output.exists()
    assert "award_id" in output.read_text(encoding="utf-8").splitlines()[0]
