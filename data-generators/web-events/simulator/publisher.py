"""Publisher abstraction.

The simulator itself does not configure Google Cloud credentials because that
integration is assigned to another team member. The rest of the project only depends
on the publish(event) interface, so Pub/Sub can be added here without touching event
or session generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path


class Publisher(ABC):
    @abstractmethod
    def publish(self, event: dict) -> None:
        raise NotImplementedError

    def close(self) -> None:
        """Optional cleanup hook."""


class JsonlPublisher(Publisher):
    """Write one JSON event per line for local debugging/profiling."""

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.output_path.open("w", encoding="utf-8")

    def publish(self, event: dict) -> None:
        self._file.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class ConsolePublisher(Publisher):
    def publish(self, event: dict) -> None:
        print(json.dumps(event, ensure_ascii=False))


class CompositePublisher(Publisher):
    def __init__(self, publishers: list[Publisher]) -> None:
        self.publishers = publishers

    def publish(self, event: dict) -> None:
        for publisher in self.publishers:
            publisher.publish(event)

    def close(self) -> None:
        for publisher in self.publishers:
            publisher.close()


class PubSubPublisher(Publisher):
    """Integration point reserved for the teammate who connects Google Pub/Sub.

    Expected usage by the rest of the simulator:

        publisher.publish(event)

    The implementation should serialize the event as UTF-8 JSON and publish it to the
    configured GCP topic. No credentials, project IDs or topic IDs are hard-coded here.
    """

    def publish(self, event: dict) -> None:
        raise NotImplementedError(
            "Pub/Sub connection intentionally left unimplemented. "
            "Implement it in simulator/publisher.py without changing the generators."
        )
