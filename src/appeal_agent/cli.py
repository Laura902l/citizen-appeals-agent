"""Command-line interface: ``appeal-agent <command> [options]``.

Commands:
    generate   create a reproducible synthetic dataset
    train      train and evaluate the classifier, write metrics and figures
    monitor    classify appeals and compute SLA statuses for a given day
    deadline   print the deadline for one appeal
    serve      start the REST API and the web dashboard
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from appeal_agent import __version__
from appeal_agent.agent import AppealAgent, status_summary
from appeal_agent.api import DashboardService, create_server
from appeal_agent.classifier import AppealClassifier
from appeal_agent.config import load_config
from appeal_agent.data_gen import generate_appeals
from appeal_agent.evaluation import evaluate_classifier
from appeal_agent.io import read_appeals, write_appeals, write_processed
from appeal_agent.viz import plot_confusion_matrix, plot_status_summary


def _cmd_generate(args: argparse.Namespace) -> int:
    appeals = generate_appeals(args.n, seed=args.seed, reference_date=args.reference_date)
    write_appeals(appeals, args.out)
    print(f"Wrote {len(appeals)} appeals to {args.out} (seed={args.seed})")
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    appeals = [a for a in read_appeals(args.data) if a.category]
    if len(appeals) < 10:
        print("error: need at least 10 labelled appeals to train", file=sys.stderr)
        return 2
    rng = random.Random(args.seed)
    rng.shuffle(appeals)
    split = int(len(appeals) * (1 - args.test_size))
    train, test = appeals[:split], appeals[split:]

    model = AppealClassifier(review_threshold=config.review_threshold, random_state=args.seed)
    model.fit([a.text for a in train], [str(a.category) for a in train])
    model.save(args.model)

    metrics = evaluate_classifier(model, [a.text for a in test], [str(a.category) for a in test])
    metrics.update({"seed": args.seed, "n_train": len(train), "package_version": __version__})
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    plot_confusion_matrix(
        metrics["confusion_matrix"], metrics["labels"], report_dir / "confusion_matrix.png"
    )

    print(
        f"Model {model.version}: accuracy={metrics['accuracy']:.3f} "
        f"macro_f1={metrics['macro_f1']:.3f} review_rate={metrics['review_rate']:.3f}"
    )
    if args.min_accuracy is not None and metrics["accuracy"] < args.min_accuracy:
        print(
            f"error: accuracy {metrics['accuracy']:.3f} is below the quality gate "
            f"{args.min_accuracy:.3f}",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_monitor(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    model = AppealClassifier.load(args.model)
    agent = AppealAgent(config, model)
    processed = agent.process(read_appeals(args.data), today=args.today)
    write_processed(processed, args.out)
    summary = status_summary(processed)
    plot_status_summary(summary, Path(args.out).with_name("sla_status.png"))
    review = sum(p.needs_review for p in processed)
    print(f"Processed {len(processed)} appeals on {args.today.isoformat()}:")
    for status, count in summary.items():
        print(f"  {status:<15} {count}")
    print(f"  {'needs_review':<15} {review}")
    return 0


def _load_service(args: argparse.Namespace) -> DashboardService:
    config = load_config(args.config)
    metrics_path = Path(args.metrics)
    metrics = (
        json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else None
    )
    agent = AppealAgent(config, AppealClassifier.load(args.model))
    return DashboardService(
        agent, read_appeals(args.data), args.today, metrics, data_path=Path(args.data)
    )


def _cmd_serve(args: argparse.Namespace) -> int:  # pragma: no cover - blocking loop
    service = _load_service(args)
    static = Path(args.static) if args.static and Path(args.static).is_dir() else None
    server = create_server(service, args.host, args.port, static)
    print(f"Dashboard: http://{args.host}:{server.server_address[1]}  (Ctrl+C to stop)")
    if static is None:
        print("  note: dashboard is not built, only /api/* works (cd dashboard && npm run build)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _cmd_deadline(args: argparse.Namespace) -> int:
    engine = load_config(args.config).sla_engine()
    result = engine.evaluate(args.submitted, args.category, args.today, urgent=args.urgent)
    print(
        f"deadline={result.deadline.isoformat()} "
        f"remaining_business_days={result.remaining_business_days} status={result.status.value}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="appeal-agent", description="Classify citizen appeals and monitor their SLA deadlines."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", default=None, help="TOML config (default: packaged config)")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a synthetic labelled dataset")
    gen.add_argument("--n", type=int, default=2000)
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--reference-date", type=date.fromisoformat, default=date(2026, 10, 5))
    gen.add_argument("--out", default="data/appeals.csv")
    gen.set_defaults(func=_cmd_generate)

    tr = sub.add_parser("train", help="train and evaluate the classifier")
    tr.add_argument("--data", default="data/appeals.csv")
    tr.add_argument("--model", default="models/classifier.joblib")
    tr.add_argument("--report-dir", default="reports")
    tr.add_argument("--test-size", type=float, default=0.2)
    tr.add_argument("--seed", type=int, default=42)
    tr.add_argument(
        "--min-accuracy",
        type=float,
        default=None,
        help="exit with code 1 if test accuracy is below this value",
    )
    tr.set_defaults(func=_cmd_train)

    mon = sub.add_parser("monitor", help="classify appeals and compute SLA statuses")
    mon.add_argument("--data", default="data/appeals.csv")
    mon.add_argument("--model", default="models/classifier.joblib")
    mon.add_argument("--today", type=date.fromisoformat, default=date.today())
    mon.add_argument("--out", default="reports/monitoring.csv")
    mon.set_defaults(func=_cmd_monitor)

    dl = sub.add_parser("deadline", help="compute the deadline of one appeal")
    dl.add_argument("--submitted", type=date.fromisoformat, required=True)
    dl.add_argument("--category", required=True)
    dl.add_argument("--today", type=date.fromisoformat, default=date.today())
    dl.add_argument("--urgent", action="store_true")
    dl.set_defaults(func=_cmd_deadline)

    srv = sub.add_parser("serve", help="start the REST API and the web dashboard")
    srv.add_argument("--data", default="data/appeals.csv")
    srv.add_argument("--model", default="models/classifier.joblib")
    srv.add_argument("--metrics", default="reports/metrics.json")
    srv.add_argument("--today", type=date.fromisoformat, default=date.today())
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8000)
    srv.add_argument("--static", default="dashboard/dist", help="built dashboard directory")
    srv.set_defaults(func=_cmd_serve)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
