from datetime import date
from pathlib import Path

import pytest

from appeal_agent.config import AgentConfig, ConfigError, load_config

MINIMAL = """
categories = ["roads", "other"]
[calendar]
holidays = ["2026-12-16"]
[classifier]
review_threshold = 0.5
[urgency]
keywords = ["Danger"]
[sla.default]
term_days = 15
warning_days = 3
[sla.rules.roads]
term_days = 10
warning_days = 2
"""


def test_default_config_is_valid(config: AgentConfig) -> None:
    assert "water" in config.categories
    assert set(config.rules) <= set(config.categories)
    assert config.calendar().is_business_day(date(2026, 10, 5))
    assert not config.calendar().is_business_day(date(2026, 12, 16))


def test_load_custom_file(tmp_path: Path) -> None:
    path = tmp_path / "cfg.toml"
    path.write_text(MINIMAL, encoding="utf-8")
    cfg = load_config(path)
    assert cfg.weekend == (5, 6)
    assert cfg.urgency_keywords == ("danger",)
    assert cfg.sla_engine().rule_for("roads").term_days == 10


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('categories = ["roads", "other"]', ""),
        ("review_threshold = 0.5", "review_threshold = 1.5"),
        ('categories = ["roads", "other"]', "categories = []"),
        ('categories = ["roads", "other"]', 'categories = ["other"]'),
        ("term_days = 10", "term_days = 0"),
        ("warning_days = 2", ""),
        ('"2026-12-16"', '"not-a-date"'),
        ("[classifier]", "[classifier"),
    ],
)
def test_invalid_config_raises(tmp_path: Path, old: str, new: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(MINIMAL.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)
