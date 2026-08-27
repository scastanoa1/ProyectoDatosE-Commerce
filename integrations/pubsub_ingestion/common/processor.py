from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from integrations.pubsub_ingestion.common.rejected_writer import RejectedEventWriter
from integrations.pubsub_ingestion.common.validator import EventValidator
from integrations.pubsub_ingestion.targets import flink, glue


logger = logging.getLogger("event.processor")


@dataclass
class ProcessingStats:
    received: int = 0
    accepted_glue: int = 0
    accepted_flink: int = 0
    skipped: int = 0
    rejected: int = 0


@dataclass
class EventProcessor:
    target: str
    rejected_writer: RejectedEventWriter
    source_name: str
    validator: EventValidator = field(default_factory=EventValidator)
    stats: ProcessingStats = field(default_factory=ProcessingStats)
    seen_event_ids: set[str] = field(default_factory=set)

    def process(
        self,
        event: Any,
        *,
        raw_message: str | None = None,
        message_id: str | None = None,
        record_number: int | None = None,
    ) -> bool:
        """Validate and route one event.

        Returns True when the event was deterministically handled, including
        accepted, skipped or rejected records. Unexpected exceptions are allowed
        to bubble up so Pub/Sub can NACK and retry.
        """
        self.stats.received += 1

        result = self.validator.validate(event)
        errors = list(result.errors)

        if isinstance(event, dict):
            event_id = event.get("event_id")
            if isinstance(event_id, str) and event_id.strip():
                if event_id in self.seen_event_ids:
                    errors.append(
                        "Duplicate event_id detected in the current process run."
                    )
                else:
                    self.seen_event_ids.add(event_id)

        if errors:
            self.rejected_writer.write(
                source=self.source_name,
                errors=errors,
                event=event if isinstance(event, dict) else None,
                raw_message=raw_message if not isinstance(event, dict) else None,
                message_id=message_id,
                record_number=record_number,
            )
            self.stats.rejected += 1
            logger.warning(
                "REJECTED event_id=%s errors=%s",
                event.get("event_id") if isinstance(event, dict) else None,
                errors,
            )
            return True

        targets = set(event["processing"]["targets"])
        sent = False

        if self.target in {"all", "glue"} and "batch" in targets:
            glue.send(event)
            self.stats.accepted_glue += 1
            sent = True

        if self.target in {"all", "flink"} and "streaming" in targets:
            flink.send(event)
            self.stats.accepted_flink += 1
            sent = True

        if not sent:
            self.stats.skipped += 1
            logger.info(
                "SKIPPED event_id=%s event_type=%s configured_target=%s targets=%s",
                event["event_id"],
                event["event_type"],
                self.target,
                sorted(targets),
            )

        return True
