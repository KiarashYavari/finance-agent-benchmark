# This is the only file that knows about:

# FastAPI

# A2A

# MCP

# Agent card

# src/server.py

# src/server.py

import os
import argparse
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import RequestHandler
from fastmcp import FastMCP

from src.executer import Executer


# ============================================================
# Request Handler (JSON-RPC)
# ============================================================

class GreenRequestHandler(RequestHandler):

    def __init__(self, executer: Executer):
        self.executer = executer

    async def rpc_discover(self):
        return {
            "name": "finance-green-agent",
            "description": "Evaluates white agent performance.",
            "methods": [
                {
                    "name": "run_assessment",
                    "description": "Run evaluation tasks on a white agent.",
                    "params": {
                        "white_address": "string",
                        "num_tasks": "integer"
                    }
                }
            ]
        }

    async def rpc_call(self, method: str, params: dict):

        if method == "run_assessment":

            white_address = params.get("white_address")
            num_tasks = params.get("num_tasks", 1)

            if not white_address:
                raise ValueError("white_address is required")

            return await self.executer.run_assessment(
                white_address=white_address,
                num_tasks=num_tasks
            )

        raise ValueError(f"Unknown method: {method}")


# ============================================================
# GreenAgent Wrapper (AgentBeats Compatible)
# ============================================================

class GreenAgent:

    def __init__(self):

        # These will be overridden by CLI
        self.agent_host = os.getenv("GREEN_AGENT_HOST", "0.0.0.0")
        self.agent_port = int(os.getenv("GREEN_AGENT_PORT", 9009))
        self.mcp_port = int(os.getenv("MCP_PORT", 9001))
        self.card_url = None

    def _create_mcp(self):

        mcp = FastMCP("finance-tools")

        @mcp.tool()
        async def health_check():
            return {"status": "ok"}

        return mcp

    def _create_app(self):

        executer = Executer(
            mcp_url=f"http://{self.agent_host}:{self.mcp_port}"
        )

        handler = GreenRequestHandler(executer)
        mcp = self._create_mcp()

        @asynccontextmanager
        async def lifespan(app: FastAPI):

            mcp_task = asyncio.create_task(
                mcp.run_async(
                    transport="sse",
                    host=self.agent_host,
                    port=self.mcp_port,
                )
            )

            print(f"[MCP] Running on {self.agent_host}:{self.mcp_port}")
            print(f"[A2A] Running on {self.agent_host}:{self.agent_port}")

            yield

            mcp_task.cancel()
            try:
                await mcp_task
            except asyncio.CancelledError:
                pass

            print("[Shutdown] MCP stopped")

        app = FastAPI(
            title="Finance Green Agent",
            lifespan=lifespan
        )

        a2a_app = A2AStarletteApplication(
            request_handler=handler,
            card_url=self.card_url  # Important for AgentBeats
        )

        app.mount("/", a2a_app)

        return app

    def run(self):

        app = self._create_app()

        uvicorn.run(
            app,
            host=self.agent_host,
            port=self.agent_port,
        )


# ============================================================
# CLI ENTRYPOINT (AgentBeats Requirement)
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Finance Green Agent")

    parser.add_argument(
        "--host",
        default=os.getenv("GREEN_AGENT_HOST", "0.0.0.0"),
        help="Host to bind the A2A server"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("GREEN_AGENT_PORT", 9009)),
        help="Port for the A2A server"
    )

    parser.add_argument(
        "--mcp-port",
        type=int,
        default=int(os.getenv("MCP_PORT", 9001)),
        help="Port for the MCP server"
    )

    parser.add_argument(
        "--card-url",
        type=str,
        help="Public URL where this agent's card is served"
    )

    args = parser.parse_args()

    agent = GreenAgent()

    # 🔥 REQUIRED FOR AGENTBEATS
    agent.agent_host = args.host
    agent.agent_port = args.port
    agent.mcp_port = args.mcp_port
    agent.card_url = args.card_url

    agent.run()