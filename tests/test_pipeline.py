"""Data generation, CSV I/O, the agent orchestrator, figures and the CLI end to end."""

import json
from datetime import date
from pathlib import Path

import pytest

from appeal_agent.agent import AppealAgent, status_summary
from appeal_agent.classifier import AppealClassifier
from appeal_agent.cli import main
from appeal_agent.config import AgentConfig
from appeal_agent.data_gen import PROBLEMS, generate_appeals, generate_text
from appeal_agent.io import read_appeals, write_appeals, write_processed
from appeal_agent.privacy import PHONE_TOKEN
from appeal_agent.sla import SLAStatus
from appeal_agent.viz import plot_confusion_matrix, plot_status_summary

TODAY = date(2026, 10, 5)


def test_generator_is_reproducible() -> None:
    assert generate_appeals(50, seed=1) == generate_appeals(50, seed=1)
    assert generate_appeals(50, seed=1) != generate_appeals(50, seed=2)


def test_generator_covers_all_categories() -> None:
    appeals = generate_appeals(len(PROBLEMS))
    assert {a.category for a in appeals} == set(PROBLEMS)
    assert all(a.submitted_on <= TODAY for a in appeals)


def test_generator_rejects_bad_input() -> None:
    import random

    with pytest.raises(ValueError):
        generate_appeals(-1)
    with pytest.raises(ValueError):
        generate_text("unknown", random.Random(0))


def test_csv_roundtrip(tmp_path: Path) -> None:
    appeals = generate_appeals(30, seed=3)
    path = tmp_path / "appeals.csv"
    write_appeals(appeals, path)
    assert read_appeals(path) == appeals


def test_csv_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("id,text\n1,hello\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        read_appeals(path)


def test_agent_process(
    config: AgentConfig, trained_model: AppealClassifier, tmp_path: Path
) -> None:
    appeals = generate_appeals(120, seed=11, reference_date=TODAY)
    agent = AppealAgent(config, trained_model)
    processed = agent.process(appeals, today=TODAY)

    assert len(processed) == len(appeals)
    assert processed == agent.process(appeals, today=TODAY)  # idempotent recheck
    assert all("+7 7" not in p.masked_text for p in processed)
    assert any(PHONE_TOKEN in p.masked_text for p in processed)
    assert all(p.model_version == trained_model.version for p in processed)

    summary = status_summary(processed)
    assert list(summary) == [s.value for s in SLAStatus]
    assert sum(summary.values()) == len(appeals)

    write_processed(processed, tmp_path / "out.csv")
    header = (tmp_path / "out.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "remaining_business_days" in header


def test_figures_are_written(tmp_path: Path) -> None:
    cm = plot_confusion_matrix([[3, 1], [0, 4]], ["a", "b"], tmp_path / "cm.png")
    bars = plot_status_summary({"on_track": 3, "overdue": 1}, tmp_path / "s.png")
    assert cm.stat().st_size > 0 and bars.stat().st_size > 0


def test_cli_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data, model = tmp_path / "appeals.csv", tmp_path / "model.joblib"
    reports = tmp_path / "reports"
    assert main(["generate", "--n", "500", "--seed", "5", "--out", str(data)]) == 0
    assert (
        main(
            [
                "train",
                "--data",
                str(data),
                "--model",
                str(model),
                "--report-dir",
                str(reports),
                "--seed",
                "5",
                "--min-accuracy",
                "0.8",
            ]
        )
        == 0
    )
    metrics = json.loads((reports / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["accuracy"] >= 0.8 and metrics["seed"] == 5
    assert (reports / "confusion_matrix.png").exists()

    out = reports / "monitoring.csv"
    assert (
        main(
            [
                "monitor",
                "--data",
                str(data),
                "--model",
                str(model),
                "--today",
                "2026-10-05",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert out.exists() and (reports / "sla_status.png").exists()
    assert "needs_review" in capsys.readouterr().out


def test_cli_quality_gate_fails(tmp_path: Path) -> None:
    data = tmp_path / "appeals.csv"
    main(["generate", "--n", "200", "--out", str(data)])
    code = main(
        [
            "train",
            "--data",
            str(data),
            "--model",
            str(tmp_path / "m.joblib"),
            "--report-dir",
            str(tmp_path),
            "--min-accuracy",
            "1.01",
        ]
    )
    assert code == 1


def test_cli_train_needs_data(tmp_path: Path) -> None:
    data = tmp_path / "appeals.csv"
    main(["generate", "--n", "5", "--out", str(data)])
    assert main(["train", "--data", str(data), "--model", str(tmp_path / "m.joblib")]) == 2


def test_cli_deadline(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "deadline",
                "--submitted",
                "2026-10-23",
                "--category",
                "waste",
                "--today",
                "2026-10-27",
                "--urgent",
            ]
        )
        == 0
    )
    # waste urgent term = 3 business days; 26 Oct is a holiday -> 27, 28, 29 Oct.
    assert "deadline=2026-10-29" in capsys.readouterr().out
