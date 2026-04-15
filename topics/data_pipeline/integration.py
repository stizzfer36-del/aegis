"""Data Pipeline — NATS / Kafka / Redpanda integrations."""
from __future__ import annotations
import os


class DataPipelineTopic:
    name = "data_pipeline"
    tools = ["nats", "kafka", "redpanda", "redpanda-connect", "vector", "risingwave", "flink"]

    async def nats_publish(self, subject: str, payload: bytes) -> bool:
        url = os.getenv("NATS_URL", "nats://localhost:4222")
        try:
            import nats
            nc = await nats.connect(url)
            await nc.publish(subject, payload)
            await nc.close()
            return True
        except Exception:
            return False
