"""Matplotlib figures for evaluation and monitoring reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: works in CI without a display

import matplotlib.pyplot as plt  # noqa: E402

STATUS_COLOURS = {
    "on_track": "#2e7d32",
    "at_risk": "#f9a825",
    "overdue": "#c62828",
    "closed_on_time": "#90a4ae",
    "closed_late": "#6d4c41",
}


def plot_confusion_matrix(
    matrix: Sequence[Sequence[int]], labels: Sequence[str], path: str | Path
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels=labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels=labels)
    ax.set_xlabel("Predicted category")
    ax.set_ylabel("True category")
    ax.set_title("Classifier confusion matrix (test set)")
    peak = max((max(row) for row in matrix), default=0)
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            colour = "white" if value > peak / 2 else "black"
            ax.text(j, i, str(value), ha="center", va="center", color=colour, fontsize=9)
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_status_summary(summary: Mapping[str, int], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(summary)
    values = [summary[n] for n in names]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, values, color=[STATUS_COLOURS.get(n, "#607d8b") for n in names])
    ax.bar_label(bars)
    ax.set_ylabel("Number of appeals")
    ax.set_title("SLA status of appeals")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
