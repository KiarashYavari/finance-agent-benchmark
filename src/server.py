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

from a2a.types import (
    MessageSendParams,
    Message,
    Task,
    TaskStatus,
)

from src.executer import Executer
from fastmcp import FastMCP


# ============================================================
# Request Handler (JSON-RPC)
# ============================================================

class GreenRequestHandler(RequestHandler):

    def __init__(self, executer: Executer):
        self.executer = executer

    async def on_message_send(self, params: MessageSendParams, context=None):

        # Extract message content
        message_text = params.message.content

        # Example expected format
        # { "white_address": "...", "num_tasks": 3 }

        white_address = message_text.get("white_address")
        num_tasks = message_text.get("num_tasks", 1)

        result = await self.executer.run_assessment(
            white_address=white_address,
            num_tasks=num_tasks
        )

        return Message(
            role="assistant",
            content=result
        )
    
    async def on_get_task(self, params, context=None):
        return None


    async def on_cancel_task(self, params, context=None):
        return None


    async def on_set_task_push_notification_config(self, params, context=None):
        return params


    async def on_get_task_push_notification_config(self, params, context=None):
        return None


    async def on_list_task_push_notification_config(self, params, context=None):
        return []


    async def on_delete_task_push_notification_config(self, params, context=None):
        return None


    async def on_resubscribe_to_task(self, params, context=None):
        raise ServerError(error=UnsupportedOperationError())

# ============================================================
# GreenAgent Wrapper (AgentBeats Compatible)
# ============================================================

class GreenAgent:

    def __init__(self):
        self.agent_host = "0.0.0.0"
        self.agent_port = 9009
        self.mcp_port = 9001
        self.card_url = None

    def create_mcp(self):

        mcp = FastMCP("finance-tools")

        @mcp.tool()
        async def health_check():
            return {"status": "ok"}

        return mcp

    def create_app(self):

        executer = Executer(
            mcp_url=f"http://{self.agent_host}:{self.mcp_port}"
        )

        handler = GreenRequestHandler(executer)

        mcp = self.create_mcp()

        @asynccontextmanager
        async def lifespan(app: FastAPI):

            mcp_task = asyncio.create_task(
                mcp.run_async(
                    transport="sse",
                    host=self.agent_host,
                    port=self.mcp_port,
                )
            )

            print(f"A2A running on {self.agent_host}:{self.agent_port}")
            print(f"MCP running on {self.agent_host}:{self.mcp_port}")

            yield

            mcp_task.cancel()

        app = FastAPI(lifespan=lifespan)

        a2a_app = A2AStarletteApplication(
            request_handler=handler,
            card_url=self.card_url,
        )

        app.mount("/", a2a_app)

        return app

    def run(self):

        app = self.create_app()

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