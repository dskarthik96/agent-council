"""
MCP (Model Context Protocol) client adapter for the council.

Connect MCP servers by adding entries under `mcp.servers` in config.yaml.
Each connected server's tools become available to the orchestrator
and are passed as tool_choice options to agent calls.

Usage (once a server is connected):
    mcp = MCPClient(config["mcp"]["servers"])
    mcp.connect()
    tools = mcp.to_anthropic_tools()   # pass to agent calls
    result = mcp.call_tool("tool_name", {"arg": "value"})
"""
import json
import subprocess
from typing import Any


class MCPClient:
    def __init__(self, servers: list[dict]):
        self.servers = servers
        self._tools: dict[str, dict] = {}
        self._processes: dict[str, subprocess.Popen] = {}

    def connect(self) -> None:
        """Start configured MCP server processes and fetch their tool lists."""
        for srv in self.servers:
            try:
                self._start_server(srv)
            except Exception as e:
                print(f"[mcp] Warning: could not start {srv.get('name')}: {e}")

    def _start_server(self, srv: dict) -> None:
        name = srv["name"]
        proc = subprocess.Popen(
            [srv["command"]] + srv.get("args", []),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=srv.get("env"),
            text=True,
        )
        self._processes[name] = proc
        # Send MCP initialise + tools/list over stdio-JSON-RPC
        self._send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "council", "version": "0.1"},
        }})
        self._send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        resp = self._recv(proc)
        for tool in resp.get("result", {}).get("tools", []):
            self._tools[tool["name"]] = tool

    def _send(self, proc: subprocess.Popen, payload: dict) -> None:
        line = json.dumps(payload) + "\n"
        proc.stdin.write(line)
        proc.stdin.flush()

    def _recv(self, proc: subprocess.Popen) -> dict:
        line = proc.stdout.readline()
        return json.loads(line) if line.strip() else {}

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        # Find which server owns this tool
        for name, proc in self._processes.items():
            if tool_name in self._tools:
                self._send(proc, {
                    "jsonrpc": "2.0", "id": 3,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                })
                resp = self._recv(proc)
                return resp.get("result", {}).get("content")
        raise ValueError(f"Tool '{tool_name}' not found in any connected MCP server")

    def to_anthropic_tools(self) -> list[dict]:
        """Format tools for passing to anthropic.messages.create(tools=...)."""
        return [
            {
                "name": name,
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", {"type": "object", "properties": {}}),
            }
            for name, t in self._tools.items()
        ]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
