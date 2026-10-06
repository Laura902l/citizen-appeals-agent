"""Loading and validating the agent configuration (TOML)."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

from appeal_agent.business_calendar import BusinessCalendar
from appeal_agent.sla import SLAEngine, SLARule


class ConfigError(ValueError):
    """Raised when the configuration file is missing keys or has invalid values."""


@dataclass(frozen=True)
class AgentConfig:
    categories: tuple[str, ...]
    holidays: tuple[date, ...]
    weekend: tuple[int, ...]
    review_threshold: float
    urgency_keywords: tuple[str, ...]
    default_rule: SLARule
    rules: dict[str, SLARule]

    def calendar(self) -> BusinessCalendar:
        return BusinessCalendar(self.holidays, self.weekend)

    def sla_engine(self) -> SLAEngine:
        return SLAEngine(self.calendar(), self.rules, self.default_rule)


def _rule(raw: dict[str, Any], where: str) -> SLARule:
    try:
        return SLARule(
            term_days=int(raw["term_days"]),
            warning_days=int(raw["warning_days"]),
            urgent_term_days=(int(raw["urgent_term_days"]) if "urgent_term_days" in raw else None),
        )
    except KeyError as exc:
        raise ConfigError(f"{where}: missing key {exc}") from exc
    except ValueError as exc:
        raise ConfigError(f"{where}: {exc}") from exc


def parse_config(raw: dict[str, Any]) -> AgentConfig:
    """Build an :class:`AgentConfig` from an already parsed TOML mapping."""
    try:
        categories = tuple(raw["categories"])
        holidays = tuple(date.fromisoformat(d) for d in raw["calendar"]["holidays"])
        weekend = tuple(int(d) for d in raw["calendar"].get("weekend", [5, 6]))
        threshold = float(raw["classifier"]["review_threshold"])
        keywords = tuple(k.lower() for k in raw["urgency"]["keywords"])
        sla = raw["sla"]
    except KeyError as exc:
        raise ConfigError(f"missing configuration key {exc}") from exc
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

    if not categories:
        raise ConfigError("at least one category is required")
    if not 0.0 <= threshold <= 1.0:
        raise ConfigError("classifier.review_threshold must be between 0 and 1")

    rules = {name: _rule(r, f"sla.rules.{name}") for name, r in sla.get("rules", {}).items()}
    unknown = set(rules) - set(categories)
    if unknown:
        raise ConfigError(f"SLA rules for unknown categories: {sorted(unknown)}")

    return AgentConfig(
        categories=categories,
        holidays=holidays,
        weekend=weekend,
        review_threshold=threshold,
        urgency_keywords=keywords,
        default_rule=_rule(sla.get("default", {}), "sla.default"),
        rules=rules,
    )


def load_config(path: str | Path | None = None) -> AgentConfig:
    """Load a TOML configuration file, or the packaged default if ``path`` is ``None``."""
    if path is None:
        text = (
            resources.files("appeal_agent")
            .joinpath("data/default_config.toml")
            .read_text(encoding="utf-8")
        )
    else:
        text = Path(path).read_text(encoding="utf-8")
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}") from exc
    return parse_config(raw)
