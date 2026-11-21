"""Connexion de l'agent à ses serveurs MCP (outils Kubernetes et Prometheus)."""
from __future__ import annotations

import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

MCP_DIR = Path(__file__).resolve().parents[2] / "mcp-servers"


def mcp_connections() -> dict:
    """Chaque serveur MCP est un petit programme Python lancé par l'agent (transport stdio)."""
    # transmet KUBECONFIG, HOME, PROMETHEUS_URL... (sans les variables du prompt du terminal)
    env = {k: v for k, v in os.environ.items() if k not in ("PS1", "PS2", "PROMPT_COMMAND")}
    return {
        "k8s": {"transport": "stdio", "command": sys.executable,
                "args": [str(MCP_DIR / "k8s_inspector" / "server.py")], "env": env},
        "prometheus": {"transport": "stdio", "command": sys.executable,
                       "args": [str(MCP_DIR / "prom_inspector" / "server.py")], "env": env},
    }


async def open_tools(stack: AsyncExitStack) -> list[BaseTool]:
    """Ouvre une session par serveur MCP (gardée ouverte pendant toute l'enquête) et charge leurs outils."""
    client = MultiServerMCPClient(mcp_connections())
    tools: list[BaseTool] = []
    for name in mcp_connections():
        session = await stack.enter_async_context(client.session(name))
        tools += await load_mcp_tools(session)
    return tools
