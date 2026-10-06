"""Text classifier for appeal categories with a confidence-based review queue."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from appeal_agent.privacy import mask_personal_data


@dataclass(frozen=True)
class Prediction:
    category: str
    confidence: float
    needs_review: bool


class NotFittedError(RuntimeError):
    """Raised when predicting with a classifier that has not been trained."""


def dataset_fingerprint(texts: Sequence[str], labels: Sequence[str]) -> str:
    """Short SHA-256 hash that identifies the exact training data."""
    digest = hashlib.sha256()
    for text, label in zip(texts, labels, strict=True):
        digest.update(f"{label}\t{text}\n".encode())
    return digest.hexdigest()[:12]


class AppealClassifier:
    """TF-IDF + logistic regression classifier.

    Predictions whose highest class probability is below ``review_threshold``
    are flagged with ``needs_review=True`` and go to a human operator.
    Personal data is masked before both training and prediction.
    """

    def __init__(self, review_threshold: float = 0.55, random_state: int = 42) -> None:
        if not 0.0 <= review_threshold <= 1.0:
            raise ValueError("review_threshold must be between 0 and 1")
        self.review_threshold = review_threshold
        self.random_state = random_state
        self.pipeline: Pipeline | None = None
        self.metadata: dict[str, Any] = {}

    def _build(self) -> Pipeline:
        return Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
                ("clf", LogisticRegression(max_iter=2000, random_state=self.random_state)),
            ]
        )

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> AppealClassifier:
        if len(texts) != len(labels):
            raise ValueError("texts and labels must have the same length")
        if len(set(labels)) < 2:
            raise ValueError("at least two categories are needed for training")
        masked = [mask_personal_data(t) for t in texts]
        self.pipeline = self._build().fit(masked, list(labels))
        fingerprint = dataset_fingerprint(texts, labels)
        self.metadata = {
            "dataset_fingerprint": fingerprint,
            "n_samples": len(texts),
            "classes": sorted(set(labels)),
            "review_threshold": self.review_threshold,
            "model_version": f"tfidf-logreg-{fingerprint}",
        }
        return self

    @property
    def version(self) -> str:
        return str(self.metadata.get("model_version", "untrained"))

    @property
    def classes(self) -> list[str]:
        if self.pipeline is None:
            raise NotFittedError("classifier is not trained")
        return [str(c) for c in self.pipeline.classes_]

    def predict(self, texts: Sequence[str]) -> list[Prediction]:
        if self.pipeline is None:
            raise NotFittedError("classifier is not trained; call fit() or load() first")
        if not texts:
            return []
        masked = [mask_personal_data(t) for t in texts]
        proba = np.asarray(self.pipeline.predict_proba(masked))
        best = proba.argmax(axis=1)
        classes = self.classes
        return [
            Prediction(
                category=classes[idx],
                confidence=float(proba[row, idx]),
                needs_review=bool(proba[row, idx] < self.review_threshold),
            )
            for row, idx in enumerate(best)
        ]

    def save(self, path: str | Path) -> None:
        if self.pipeline is None:
            raise NotFittedError("cannot save an untrained classifier")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "metadata": self.metadata,
                "review_threshold": self.review_threshold,
            },
            path,
        )

    @classmethod
    def load(cls, path: str | Path) -> AppealClassifier:
        """Load a model saved with :meth:`save`. Only load files you trust (pickle)."""
        payload = joblib.load(path)
        model = cls(review_threshold=payload["review_threshold"])
        model.pipeline = payload["pipeline"]
        model.metadata = payload["metadata"]
        return model
