from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv_if_available() -> None:
    """Load the package .env file when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@dataclass(frozen=True)
class PubSubSettings:
    project_id: str
    flink_subscription: str
    glue_subscription: str
    log_level: str

    @classmethod
    def from_env(cls) -> "PubSubSettings":
        _load_dotenv_if_available()

        project_id = os.getenv("GCP_PROJECT_ID", "").strip()
        flink_subscription = os.getenv(
            "PUBSUB_FLINK_SUBSCRIPTION", ""
        ).strip()
        glue_subscription = os.getenv(
            "PUBSUB_GLUE_SUBSCRIPTION", ""
        ).strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

        return cls(
            project_id=project_id,
            flink_subscription=flink_subscription,
            glue_subscription=glue_subscription,
            log_level=log_level,
        )

    def subscription_for(self, target: str) -> str:
        if not self.project_id:
            raise RuntimeError("Missing environment variable: GCP_PROJECT_ID")

        if target == "flink":
            if not self.flink_subscription:
                raise RuntimeError(
                    "Missing environment variable: PUBSUB_FLINK_SUBSCRIPTION"
                )
            return self.flink_subscription

        if target == "glue":
            if not self.glue_subscription:
                raise RuntimeError(
                    "Missing environment variable: PUBSUB_GLUE_SUBSCRIPTION"
                )
            return self.glue_subscription

        raise ValueError("target must be 'flink' or 'glue'")
