from __future__ import annotations

from datetime import date

import pytest

from appeal_agent.business_calendar import BusinessCalendar
from appeal_agent.classifier import AppealClassifier
from appeal_agent.config import AgentConfig, load_config
from appeal_agent.data_gen import generate_appeals
from appeal_agent.sla import SLAEngine, SLARule

# 2026-10-26 (Mon) is a holiday in the test calendar; 2026-10-24/25 is a weekend.
HOLIDAY = date(2026, 10, 26)


@pytest.fixture
def calendar() -> BusinessCalendar:
    return BusinessCalendar(holidays=[HOLIDAY, date(2026, 12, 16), date(2027, 1, 1)])


@pytest.fixture
def engine(calendar: BusinessCalendar) -> SLAEngine:
    rules = {
        "water": SLARule(term_days=10, warning_days=2, urgent_term_days=2),
        "roads": SLARule(term_days=15, warning_days=3),
    }
    return SLAEngine(calendar, rules, default_rule=SLARule(term_days=15, warning_days=3))


@pytest.fixture(scope="session")
def config() -> AgentConfig:
    return load_config()


@pytest.fixture(scope="session")
def trained_model() -> AppealClassifier:
    appeals = generate_appeals(700, seed=7)
    model = AppealClassifier(review_threshold=0.55, random_state=7)
    return model.fit([a.text for a in appeals], [str(a.category) for a in appeals])
