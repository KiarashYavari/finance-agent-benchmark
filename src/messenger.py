# Handles communication (white agent + MCP endpoint passing)
# src/messenger.py

import httpx
import uuid


class Messenger:

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    async def ask_white_agent(self, white_address: str, question: str):

        request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "method": "answer_question",  # must match white agent method
            "params": {
                "question": question,
                "mcp_url": self.mcp_url
            },
            "id": request_id
        }

        async with httpx.AsyncClient(timeout=200.0) as client:
            response = await client.post(
                f"{white_address}/a2a",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()

            if "error" in data:
                raise Exception(f"A2A error: {data['error']}")

            return data.get("result", {})