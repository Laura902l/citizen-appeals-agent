"""Evaluation metrics for the classifier."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from appeal_agent.classifier import AppealClassifier


def evaluate_classifier(
    model: AppealClassifier, texts: Sequence[str], labels: Sequence[str]
) -> dict[str, Any]:
    """Compute accuracy, macro-F1, review rate and the confusion matrix on a test set."""
    if not texts:
        raise ValueError("evaluation set is empty")
    predictions = model.predict(texts)
    predicted = [p.category for p in predictions]
    auto = [(p.category, y) for p, y in zip(predictions, labels, strict=True) if not p.needs_review]
    classes = sorted(set(labels) | set(predicted))
    return {
        "model_version": model.version,
        "n_test": len(texts),
        "accuracy": float(accuracy_score(labels, predicted)),
        "macro_f1": float(f1_score(labels, predicted, average="macro", zero_division=0)),
        "review_rate": sum(p.needs_review for p in predictions) / len(predictions),
        "auto_accepted_accuracy": (sum(p == y for p, y in auto) / len(auto) if auto else None),
        "labels": classes,
        "confusion_matrix": confusion_matrix(labels, predicted, labels=classes).tolist(),
    }
