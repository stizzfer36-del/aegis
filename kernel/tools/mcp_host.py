from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class MCPTool:
    server: str
    name: str
    description: str


class MCPHost:
    def __init__(self) -> None:
        self.tools: Dict[str, MCPTool] = {}

    def startup(self) -> None:
        # Lightweight local discovery; full MCP wiring is optional.
        candidates = {
            "filesystem": "npx",
            "git": "npx",
            "playwright": "npx",
            "fetch": "npx",
            "screenpipe": "npx",
        }
        for server, binary in candidates.items():
            if shutil.which(binary):
                name = f"mcp_{server}_status"
                self.tools[name] = MCPTool(server=server, name=name, description=f"MCP proxy placeholder for {server}")

    def list_tools(self) -> List[MCPTool]:
        return list(self.tools.values())

    def call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self.tools:
            return {"error": f"unknown MCP tool {tool_name}"}
        return {"status": "stub", "tool": tool_name, "arguments": arguments}
