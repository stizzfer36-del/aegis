from kernel.core.tools.base import ToolCall, ToolResult
from kernel.core.tools.dispatcher import ToolDispatcher
from kernel.core.tools.sandbox import Sandbox


def register_default_tools(dispatcher: ToolDispatcher) -> ToolDispatcher:
    return dispatcher


__all__ = ["ToolDispatcher", "Sandbox", "ToolResult", "ToolCall", "register_default_tools"]
