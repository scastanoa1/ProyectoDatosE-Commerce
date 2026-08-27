from __future__ import annotations

import logging

logger = logging.getLogger("target.flink")


def send(event: dict) -> None:
    """Current PoC handoff point for the future PyFlink integration."""
    logger.info(
        "FLINK_HANDOFF_READY event_id=%s event_type=%s",
        event["event_id"],
        event["event_type"],
    )
