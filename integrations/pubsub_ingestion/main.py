from __future__ import annotations

import argparse
import logging
from pathlib import Path

from integrations.pubsub_ingestion.common.processor import EventProcessor
from integrations.pubsub_ingestion.common.rejected_writer import RejectedEventWriter
from integrations.pubsub_ingestion.sources.local import read_records


PACKAGE_DIR = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and route e-commerce events to Glue/Flink handoff points."
    )
    parser.add_argument(
        "--source",
        choices=["local", "pubsub"],
        required=True,
        help="Read from a local JSON/JSONL file or from a real GCP Pub/Sub subscription.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "glue", "flink"],
        required=True,
        help=(
            "Route batch events to Glue, streaming events to Flink, or both. "
            "'all' is intended for local fan-out testing."
        ),
    )
    parser.add_argument(
        "--input",
        help="Local JSON/JSONL input file. Required when --source local.",
    )
    parser.add_argument(
        "--rejected-output",
        help="Optional path for the rejected-events JSON file.",
    )
    parser.add_argument(
        "--reset-rejected",
        action="store_true",
        help="Delete the selected rejected-events file before starting.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def default_rejected_path(source: str, target: str) -> Path:
    suffix = "local" if source == "local" else f"pubsub_{target}"
    return PACKAGE_DIR / "output" / f"rejected_{suffix}.json"


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def run_local(args: argparse.Namespace, processor: EventProcessor) -> None:
    if not args.input:
        raise RuntimeError("--input is required when --source local.")

    for record in read_records(args.input):
        if record.parse_error:
            processor.stats.received += 1
            processor.stats.rejected += 1
            processor.rejected_writer.write(
                source=processor.source_name,
                errors=[record.parse_error],
                raw_message=record.raw_message,
                record_number=record.record_number,
            )
            logging.getLogger("source.local").warning(
                "REJECTED record=%s reason=%s",
                record.record_number,
                record.parse_error,
            )
            continue

        processor.process(
            record.event,
            raw_message=record.raw_message,
            record_number=record.record_number,
        )

    stats = processor.stats
    logging.getLogger("source.local").info(
        "LOCAL TEST FINISHED | received=%s rejected=%s glue=%s flink=%s skipped=%s",
        stats.received,
        stats.rejected,
        stats.accepted_glue,
        stats.accepted_flink,
        stats.skipped,
    )


def run_pubsub(args: argparse.Namespace, processor: EventProcessor) -> None:
    if args.target == "all":
        raise RuntimeError(
            "Pub/Sub uses two independent subscriptions. Run one process with "
            "--target glue and another with --target flink."
        )

    from integrations.pubsub_ingestion.common.config import PubSubSettings
    from integrations.pubsub_ingestion.sources.pubsub import consume

    settings = PubSubSettings.from_env()
    subscription_id = settings.subscription_for(args.target)

    consume(
        project_id=settings.project_id,
        subscription_id=subscription_id,
        processor=processor,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)

    rejected_path = (
        Path(args.rejected_output)
        if args.rejected_output
        else default_rejected_path(args.source, args.target)
    )

    if args.reset_rejected and rejected_path.exists():
        rejected_path.unlink()

    processor = EventProcessor(
        target=args.target,
        rejected_writer=RejectedEventWriter(rejected_path),
        source_name=(
            "local"
            if args.source == "local"
            else f"pubsub:{args.target}"
        ),
    )

    if args.source == "local":
        run_local(args, processor)
    else:
        run_pubsub(args, processor)


if __name__ == "__main__":
    main()
