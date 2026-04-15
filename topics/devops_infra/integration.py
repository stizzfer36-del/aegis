"""DevOps / Infra — Docker / Kubernetes / Prometheus integrations."""
from __future__ import annotations
import asyncio


class DevOpsInfraTopic:
    name = "devops_infra"
    tools = ["docker", "kubernetes", "terraform", "ansible", "prometheus", "grafana", "argocd"]

    async def docker_ps(self) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "ps", "--format", "table {{.Names}}\t{{.Status}}",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            return stdout.decode()
        except (FileNotFoundError, asyncio.TimeoutError) as e:
            return f"docker error: {e}"
