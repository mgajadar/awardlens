from awardlens.demo_data import generate_demo_awards
from awardlens.schema import AWARD_COLUMNS


def test_demo_data_is_deterministic_and_canonical() -> None:
    first = generate_demo_awards(months=8, awards_per_month=5, seed=7)
    second = generate_demo_awards(months=8, awards_per_month=5, seed=7)

    assert list(first.columns) == AWARD_COLUMNS
    assert len(first) == 40
    assert first["award_id"].is_unique
    assert first["award_amount"].tolist() == second["award_amount"].tolist()
    assert set(first["source"]) == {"synthetic_demo"}

