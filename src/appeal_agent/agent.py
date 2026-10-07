"""Agent orchestrator: the single place that coordinates the processing pipeline.

intake -> personal-data masking -> classification -> urgency -> SLA evaluation
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date

from appeal_agent.classifier import AppealClassifier
from appeal_agent.config import AgentConfig
from appeal_agent.models import Appeal, ProcessedAppeal
from appeal_agent.privacy import mask_personal_data
from appeal_agent.sla import SLAEngine, SLAStatus
from appeal_agent.urgency import is_urgent


class AppealAgent:
    def __init__(self, config: AgentConfig, classifier: AppealClassifier) -> None:
        self.config = config
        self.classifier = classifier
        self.sla: SLAEngine = config.sla_engine()

    def process(self, appeals: Sequence[Appeal], today: date) -> list[ProcessedAppeal]:
        """Classify every appeal and evaluate its SLA status on ``today``.

        The function is idempotent: running it twice on the same input and day
        gives the same result, so the periodic recheck can safely be retried.
        """
        predictions = self.classifier.predict([a.text for a in appeals])
        results = []
        for appeal, pred in zip(appeals, predictions, strict=True):
            urgent = is_urgent(appeal.text, self.config.urgency_keywords)
            sla = self.sla.evaluate(
                appeal.submitted_on,
                pred.category,
                today,
                urgent=urgent,
                closed_on=appeal.closed_on,
            )
            results.append(
                ProcessedAppeal(
                    appeal_id=appeal.appeal_id,
                    submitted_on=appeal.submitted_on,
                    masked_text=mask_personal_data(appeal.text),
                    location=appeal.location,
                    category=pred.category,
                    confidence=round(pred.confidence, 4),
                    needs_review=pred.needs_review,
                    urgent=urgent,
                    deadline=sla.deadline,
                    remaining_business_days=sla.remaining_business_days,
                    status=sla.status,
                    model_version=self.classifier.version,
                    closed_on=appeal.closed_on,
                )
            )
        return results


def status_summary(processed: Iterable[ProcessedAppeal]) -> dict[str, int]:
    """Number of appeals per SLA status, in a fixed order (zeros included)."""
    counts = Counter(p.status for p in processed)
    return {status.value: counts.get(status, 0) for status in SLAStatus}
