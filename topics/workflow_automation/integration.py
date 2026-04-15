"""Workflow Automation — n8n / Temporal / Prefect integrations."""
from __future__ import annotations


class WorkflowAutomationTopic:
    name = "workflow_automation"
    tools = ["n8n", "temporal", "prefect", "airflow", "windmill", "activepieces", "huginn"]

    async def trigger_n8n_webhook(self, webhook_url: str, payload: dict) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(webhook_url, json=payload)
                return r.json()
        except Exception as e:
            return {"error": str(e)}
