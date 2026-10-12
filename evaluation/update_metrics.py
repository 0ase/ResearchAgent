"""Collect and publish a local aggregate snapshot; optional low-frequency watch."""
import argparse
from pathlib import Path
import time

from evaluation.collect import ROOT, atomic_json, collect
from evaluation.evaluate import evaluate, load_labels, markdown


def update(logs: Path, db: Path, observations: Path, labels: Path | None, since: str | None, output: Path):
    snapshot = collect(list(logs.glob("backend.log*")), db, observations, since)
    report = evaluate(snapshot, load_labels(labels))
    atomic_json(ROOT / "evaluation/runs/collected.json", snapshot)
    atomic_json(output, report, allow_locked_rewrite=True)
    report_file = ROOT / "evaluation/reports/latest.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(markdown(report), encoding="utf-8")
    print(f"Updated local metrics: {report['population']['started']} runs, {report['population']['completed']} completed. No research calls.")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=ROOT / "logs")
    parser.add_argument("--db", type=Path, default=ROOT / "data/research.db")
    parser.add_argument("--observations", type=Path, default=ROOT / "evaluation/runs/observed")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--since", help="ISO time with timezone")
    parser.add_argument("--output", type=Path, default=ROOT / "web/public/metrics/summary.json")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=30)
    args = parser.parse_args()
    if args.interval < 5:
        parser.error("--interval must be at least 5 seconds")
    try:
        while True:
            update(args.logs, args.db, args.observations, args.labels, args.since, args.output)
            if not args.watch:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
