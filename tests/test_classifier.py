from pathlib import Path

import pytest

from appeal_agent.classifier import AppealClassifier, NotFittedError, dataset_fingerprint
from appeal_agent.data_gen import generate_appeals
from appeal_agent.evaluation import evaluate_classifier


def test_accuracy_on_held_out_data(trained_model: AppealClassifier) -> None:
    test = generate_appeals(300, seed=99)
    metrics = evaluate_classifier(
        trained_model, [a.text for a in test], [str(a.category) for a in test]
    )
    assert metrics["accuracy"] >= 0.85
    assert metrics["macro_f1"] >= 0.85
    assert 0.0 <= metrics["review_rate"] <= 1.0
    assert len(metrics["confusion_matrix"]) == len(metrics["labels"])


def test_predicts_obvious_cases(trained_model: AppealClassifier) -> None:
    preds = trained_model.predict(
        ["There is a huge pothole in the asphalt", "The street lights do not work at night"]
    )
    assert [p.category for p in preds] == ["roads", "lighting"]
    assert all(0.0 <= p.confidence <= 1.0 for p in preds)


def test_threshold_one_sends_everything_to_review(trained_model: AppealClassifier) -> None:
    strict = AppealClassifier(review_threshold=1.0)
    strict.pipeline, strict.metadata = trained_model.pipeline, trained_model.metadata
    assert all(p.needs_review for p in strict.predict(["pothole on the road", "no light"]))


def test_empty_input_returns_empty_list(trained_model: AppealClassifier) -> None:
    assert trained_model.predict([]) == []


def test_save_and_load_roundtrip(trained_model: AppealClassifier, tmp_path: Path) -> None:
    path = tmp_path / "models" / "m.joblib"
    trained_model.save(path)
    loaded = AppealClassifier.load(path)
    texts = ["garbage containers are overflowing", "bus skipped our stop"]
    assert loaded.predict(texts) == trained_model.predict(texts)
    assert loaded.version == trained_model.version


def test_version_is_tied_to_dataset(trained_model: AppealClassifier) -> None:
    assert trained_model.version.startswith("tfidf-logreg-")
    assert dataset_fingerprint(["a"], ["x"]) != dataset_fingerprint(["a"], ["y"])


def test_untrained_model_errors(tmp_path: Path) -> None:
    model = AppealClassifier()
    assert model.version == "untrained"
    with pytest.raises(NotFittedError):
        model.predict(["text"])
    with pytest.raises(NotFittedError):
        model.save(tmp_path / "m.joblib")
    with pytest.raises(NotFittedError):
        _ = model.classes


@pytest.mark.parametrize(("texts", "labels"), [(["a", "b"], ["x"]), (["a", "b"], ["x", "x"])])
def test_invalid_training_data(texts: list[str], labels: list[str]) -> None:
    with pytest.raises(ValueError):
        AppealClassifier().fit(texts, labels)


def test_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        AppealClassifier(review_threshold=2.0)


def test_empty_evaluation_set(trained_model: AppealClassifier) -> None:
    with pytest.raises(ValueError):
        evaluate_classifier(trained_model, [], [])
