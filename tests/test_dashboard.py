from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_renders_offline_demo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AWARDLENS_DATABASE_PATH", str(tmp_path / "dashboard.duckdb"))
    app_path = Path(__file__).resolve().parents[1] / "app.py"

    dashboard = AppTest.from_file(app_path).run(timeout=20)

    assert not dashboard.exception
    assert dashboard.title[0].value == "AwardLens"
    assert len(dashboard.metric) >= 6
