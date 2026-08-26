from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any


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
    """Publish events once to a GCP Pub/Sub topic with routing attributes."""

    def __init__(
        self,
        project_id: str,
        topic_name: str,
        publisher_client: Any | None = None,
    ) -> None:
        if publisher_client is None:
            try:
                from google.cloud import pubsub_v1
            except ImportError as error:
                raise RuntimeError(
                    "Pub/Sub requires google-cloud-pubsub. "
                    "Install it with: pip install -r requirements.txt"
                ) from error
            publisher_client = pubsub_v1.PublisherClient()

        self._publisher = publisher_client
        self._topic_path = self._publisher.topic_path(project_id, topic_name)

    def publish(self, event: dict) -> None:
        targets = event["processing"]["targets"]
        attributes = {
            "batch": str("batch" in targets).lower(),
            "streaming": str("streaming" in targets).lower(),
        }
        payload = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        # Esperar el resultado deja visible un error de publicación al simulador,
        # sin volver a publicar ni alterar el JSON original.
        self._publisher.publish(self._topic_path, payload, **attributes).result()
