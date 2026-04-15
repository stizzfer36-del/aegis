"""API Gateway — Kong / Traefik / Caddy integrations."""
from __future__ import annotations


class APIGatewayTopic:
    name = "api_gateway"
    tools = ["kong", "traefik", "envoy", "istio", "apisix", "nginx", "caddy"]

    async def health_check(self, url: str) -> dict:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(url)
                return {"status": r.status_code, "ok": r.status_code < 400}
        except Exception as e:
            return {"status": 0, "ok": False, "error": str(e)}
