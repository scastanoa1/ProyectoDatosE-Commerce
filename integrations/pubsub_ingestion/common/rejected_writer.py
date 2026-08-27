from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any


class RejectedEventWriter:
    """Persist rejected records in a JSON array.

    This local file is for the Sprint 1 proof of concept. It can later be
    replaced by an S3/DLQ destination without changing validation logic.
    """

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        if not self.output_path.exists():
            self.output_path.write_text("[]", encoding="utf-8")

    def write(
        self,
        *,
        source: str,
        errors: list[str],
        event: dict[str, Any] | None = None,
        raw_message: str | None = None,
        message_id: str | None = None,
        record_number: int | None = None,
    ) -> None:
        record = {
            "rejected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": source,
            "message_id": message_id,
            "record_number": record_number,
            "errors": errors,
            "event": event,
            "raw_message": raw_message,
        }

        with self._lock:
            current = self._read()
            current.append(record)

            temp_path = self.output_path.with_suffix(
                self.output_path.suffix + ".tmp"
            )
            temp_path.write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.output_path)

    def _read(self) -> list[dict[str, Any]]:
        try:
            raw = self.output_path.read_text(encoding="utf-8").strip()
            parsed = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{self.output_path} is not a valid JSON file."
            ) from exc

        if not isinstance(parsed, list):
            raise RuntimeError(
                f"{self.output_path} must contain a JSON array."
            )

        return parsed
