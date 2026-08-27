from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class LocalRecord:
    record_number: int
    event: Any | None
    raw_message: str
    parse_error: str | None = None


def read_records(path: str | Path) -> Iterator[LocalRecord]:
    """Read JSON object, JSON array, or JSONL.

    The simulator currently emits JSONL, so JSONL is the primary local-test
    format. JSON object/array support is included for manual test files.
    """
    input_path = Path(path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    raw = input_path.read_text(encoding="utf-8")
    stripped = raw.strip()

    if not stripped:
        return

    # Try conventional JSON first: one object or an array of objects.
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            for index, item in enumerate(parsed, start=1):
                yield LocalRecord(
                    record_number=index,
                    event=item,
                    raw_message=json.dumps(item, ensure_ascii=False),
                )
            return

        yield LocalRecord(
            record_number=1,
            event=parsed,
            raw_message=stripped,
        )
        return

    except json.JSONDecodeError:
        pass

    # Fall back to JSONL: each non-empty line is one event.
    record_number = 0
    for line in raw.splitlines():
        if not line.strip():
            continue

        record_number += 1
        try:
            event = json.loads(line)
            yield LocalRecord(
                record_number=record_number,
                event=event,
                raw_message=line,
            )
        except json.JSONDecodeError as exc:
            yield LocalRecord(
                record_number=record_number,
                event=None,
                raw_message=line,
                parse_error=(
                    f"Invalid JSON: {exc.msg} at line {exc.lineno}, "
                    f"column {exc.colno}"
                ),
            )
