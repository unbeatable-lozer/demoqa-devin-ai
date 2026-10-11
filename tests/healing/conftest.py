import pytest

from healing import Healer, HealingConfig, HealingPage


@pytest.fixture
def healer(tmp_path):
    """An isolated healer so these tests never touch the shared baseline or report."""
    return Healer(HealingConfig(
        wait_ms=500,
        baseline_path=tmp_path / "baseline.json",
        events_path=tmp_path / "events.jsonl",
    ))


@pytest.fixture
def hpage(page, healer) -> HealingPage:
    return HealingPage(page, healer)
