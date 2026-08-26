from __future__ import annotations

import argparse
import random
import time

from simulator.data_catalog import DataCatalog
from simulator.error_injector import ErrorInjector
from simulator.publisher import (
    CompositePublisher,
    ConsolePublisher,
    JsonlPublisher,
    PubSubPublisher,
)
from simulator.session_generator import SessionGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate coherent synthetic e-commerce events for a Pub/Sub ingress."
    )
    parser.add_argument(
        "--events",
        type=int,
        required=True,
        help="Exact number of events to generate (minimum 3 to preserve complete sessions).",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Publishing rate in events per second. Default: 1.0",
    )
    parser.add_argument(
        "--error-rate",
        type=float,
        required=True,
        help="Probability [0,1] that each event receives one controlled quality error.",
    )
    parser.add_argument(
        "--output",
        default="output/events.jsonl",
        help="Local JSONL output path. Default: output/events.jsonl",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Also print every generated event to stdout.",
    )
    parser.add_argument(
        "--pubsub-project-id",
        help="GCP project ID used to publish events to Pub/Sub.",
    )
    parser.add_argument(
        "--pubsub-topic",
        help="Pub/Sub topic name; requires --pubsub-project-id.",
    )
    parser.add_argument(
        "--no-sleep",
        action="store_true",
        help="Disable pacing (useful for local tests).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible simulations.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.events < 3:
        raise SystemExit("--events must be at least 3 to keep sessions complete.")
    if args.rate <= 0:
        raise SystemExit("--rate must be greater than 0.")
    if not 0.0 <= args.error_rate <= 1.0:
        raise SystemExit("--error-rate must be between 0 and 1.")
    if bool(args.pubsub_project_id) != bool(args.pubsub_topic):
        raise SystemExit(
            "--pubsub-project-id and --pubsub-topic must be provided together."
        )


def build_exact_stream(session_generator: SessionGenerator, total_events: int):
    """Yield complete sessions whose combined length is exactly total_events."""
    remaining = total_events

    while remaining > 0:
        if remaining <= 30:
            # The final session is shaped to consume the exact remaining number of slots.
            session_events = session_generator.generate_exact_browsing_session(remaining)
        else:
            session_events = session_generator.generate()

            # Never cut a session and never leave an impossible 1-2 event remainder.
            if len(session_events) > remaining or remaining - len(session_events) in {1, 2}:
                # A small complete browsing session leaves enough room for future sessions.
                safe_length = 5 if remaining - 5 >= 3 else remaining
                session_events = session_generator.generate_exact_browsing_session(safe_length)

        for event in session_events:
            yield event
        remaining -= len(session_events)


def main() -> None:
    args = parse_args()
    validate_args(args)

    rng = random.Random(args.seed)
    catalog = DataCatalog()
    session_generator = SessionGenerator(catalog, rng)
    error_injector = ErrorInjector(args.error_rate, rng)

    publishers = [JsonlPublisher(args.output)]
    if args.console:
        publishers.append(ConsolePublisher())
    if args.pubsub_project_id:
        publishers.append(PubSubPublisher(args.pubsub_project_id, args.pubsub_topic))
    publisher = CompositePublisher(publishers)

    delay = 1.0 / args.rate
    emitted = 0

    try:
        for event in build_exact_stream(session_generator, args.events):
            event = error_injector.process(event)
            publisher.publish(event)
            emitted += 1

            if not args.no_sleep and emitted < args.events:
                time.sleep(delay)
    finally:
        publisher.close()

    print(
        f"Generated {emitted} events -> {args.output} "
        f"(rate={args.rate}/s, error_rate={args.error_rate:.2%})"
    )


if __name__ == "__main__":
    main()
