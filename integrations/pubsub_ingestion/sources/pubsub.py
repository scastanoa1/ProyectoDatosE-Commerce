from __future__ import annotations

import json
import logging

from integrations.pubsub_ingestion.common.processor import EventProcessor


logger = logging.getLogger("source.pubsub")


def consume(
    *,
    project_id: str,
    subscription_id: str,
    processor: EventProcessor,
) -> None:
    """Consume one real Pub/Sub subscription continuously."""
    try:
        from google.cloud import pubsub_v1
    except ImportError as exc:
        raise RuntimeError(
            "Pub/Sub mode requires google-cloud-pubsub. "
            "Install integrations/pubsub_ingestion/requirements.txt."
        ) from exc

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        project_id,
        subscription_id,
    )

    logger.info("Listening on %s", subscription_path)

    def callback(message) -> None:
        try:
            try:
                raw = message.data.decode("utf-8")
            except UnicodeDecodeError as exc:
                processor.rejected_writer.write(
                    source=processor.source_name,
                    errors=[f"Message is not valid UTF-8: {exc}"],
                    raw_message=repr(message.data),
                    message_id=message.message_id,
                )
                processor.stats.received += 1
                processor.stats.rejected += 1
                message.ack()
                return

            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                processor.rejected_writer.write(
                    source=processor.source_name,
                    errors=[
                        f"Invalid JSON: {exc.msg} at line {exc.lineno}, "
                        f"column {exc.colno}"
                    ],
                    raw_message=raw,
                    message_id=message.message_id,
                )
                processor.stats.received += 1
                processor.stats.rejected += 1
                message.ack()
                return

            processor.process(
                event,
                raw_message=raw,
                message_id=message.message_id,
            )

            # Accepted, skipped, and deterministic validation failures are ACKed.
            message.ack()

        except Exception:
            # Operational/unexpected failure: request redelivery.
            logger.exception(
                "Unexpected processing failure for message_id=%s; NACK requested.",
                message.message_id,
            )
            message.nack()

    future = subscriber.subscribe(
        subscription_path,
        callback=callback,
    )

    try:
        future.result()
    except KeyboardInterrupt:
        logger.info("Stopping Pub/Sub consumer...")
        future.cancel()
    finally:
        subscriber.close()
