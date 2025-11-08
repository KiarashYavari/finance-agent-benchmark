# app/green_agent.py
# -*- coding: utf-8 -*-
"""
Finance-Green Agent for AgentBeats
Approach III: Dynamic MCP Server
Exposes tools via MCP for white agent to discover dynamically
"""

import asyncio
import os
import sys
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm as _tqdm
import uvicorn
import litellm
import httpx
import tomllib
#import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# MCP library - using fastmcp
from fastmcp import FastMCP

# Import tools
from tools.google_search import google_search
from tools.serp_search import serp_search
from tools.edgar_search import edgar_search
from tools.parse_html import parse_html
from tools.retrieve_information import retrieve_information

from utils.env_setup import init_environment

# ---- Initialize environment ----
init_environment()

#import logging
#from dotenv import load_dotenv, reset
#logging.info("Processing request")
#env_reset_res = env.reset(task_index=task_index)


class GreenAgent:
    """
    Finance-Green Agent for AgentBeats (Approach III).
    - Exposes A2A endpoints for AgentBeats platform
    - Hosts MCP server for dynamic tool discovery
    - White agent connects to MCP and loads tools on-the-fly
    """

    def __init__(self):
        self.agent_host = os.getenv("GREEN_AGENT_HOST", "0.0.0.0")
        self.agent_port = int(os.getenv("GREEN_AGENT_PORT", 9000))
        self.mcp_port = int(os.getenv("MCP_PORT", 9001))  # Separate port for MCP
        self.name = "finance-green-agent"
        self.verbose = os.getenv("VERBOSE", False)

        # Load agent card
        self.card_path = os.getenv(
            "GREEN_CARD", 
            Path(__file__).parent / "cards" / "green_card.toml"
        )
        if not os.path.exists(self.card_path):
            raise FileNotFoundError(f"Agent card {self.card_path} not found")
        
        with open(self.card_path, "rb") as f:
            self.agent_card = tomllib.load(f)

        # Environment and model setup
        self.safety_check = int(os.getenv("SAFETY_CHECK", 1))
        self.llm_model = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash-lite")
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.dataset = os.getenv("DATASET", "data/public.csv")

        # Data storage for retrieve_information tool
        self.data_storage = {}
        
        # Create FastAPI app for A2A
        self.app = FastAPI(title="Finance Green Agent")
        
        # Create FastMCP server for tools
        self.mcp_server = FastMCP("finance-tools")
        
        # Setup routes and register tools
        self._setup_a2a_routes()
        self._register_mcp_tools()

    def _setup_a2a_routes(self):
        """Setup A2A protocol endpoints"""
        
        @self.app.get("/card")
        @self.app.get("/.well-known/agent-card.json")
        async def get_card():
            return JSONResponse(self.agent_card)

        @self.app.post("/a2a")
        async def handle_a2a_message(request: Request):
            try:
                payload = await request.json()
                #print(f"[GREEN] Received A2A message: {payload}")
                
                if self.verbose:
                    print(f"[GREEN] Received A2A message: {payload}",file=sys.stderr)
                    
                method = payload.get("method")
                args = payload.get("args", {})
                
                if method == "run_assessment":
                    result = await self.run_assessment(
                        white_agent_address=args.get("white_address"),
                        config=args
                    )
                    return JSONResponse({
                        "status": "completed",
                        "result": result
                    })
                else:
                    return JSONResponse({
                        "status": "error",
                        "message": f"Unknown method: {method}"
                    }, status_code=400)
                    
            except Exception as e:
                print(f"[GREEN] Error: {e}")
                import traceback
                traceback.print_exc()
                return JSONResponse({
                    "status": "error",
                    "message": str(e)
                }, status_code=500)

        @self.app.get("/health")
        async def health():
            return {"status": "ok", "agent": self.name}

        @self.app.post("/reset")
        async def reset():
            """Reset agent state (AgentBeats requirement)"""
            print(f"[GREEN] Resetting agent state...", file=sys.stderr)
            
            # Clear data storage
            self.data_storage = {}
            
            # Reset any other state variables
            return JSONResponse({
                "status": "ok",
                "message": "Agent state reset successfully"
            })
    
    def _register_mcp_tools(self):
        """Register tools with FastMCP server for dynamic discovery"""
        
        @self.mcp_server.tool()
        async def google_search_handler(query: str) -> dict:
            """Google web search for financial information."""

            if self.verbose:
                print(f"[GREEN] Calling google_search...", file=sys.stderr)

            try:
                return await google_search(query, True if self.verbose else False)
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        async def serp_search_handler(query: str) -> dict:
            """SERP API search for rich organic results."""

            if self.verbose:
                print(f"[GREEN] Calling search_serp...", file=sys.stderr)

            try:
                return await serp_search(query, True if self.verbose else False)
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        async def edgar_search_handler(
            query: str,
            form_types: list = None,
            ciks: list = None,
            start_date: str = "2024-01-01",
            end_date: str = "2024-12-31",
            top_n: int = 5
        ) -> dict:
            """Search SEC EDGAR filings."""

            if self.verbose:
                print(f"[GREEN] Calling edgar_search...", file=sys.stderr)

            try:
                return await edgar_search(
                    query=query,
                    form_types=form_types or [],
                    ciks=ciks or [],
                    start_date=start_date,
                    end_date=end_date,
                    top_n_results=top_n
                )
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        async def parse_html_handler(url: str, key: str) -> dict:
            """Parse HTML page and store in data_storage."""

            if self.verbose:
                print(f"[GREEN] Calling parse_html...", file=sys.stderr)

            try:
                result = await parse_html(url)
                if "text" in result:
                    self.data_storage[key] = result["text"]
                    return {
                        "success": True,
                        "message": f"Saved to key '{key}'",
                        "available_keys": list(self.data_storage.keys())
                    }
                return result
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        async def retrieve_info_handler(
            prompt: str,
            input_character_ranges: dict = None
        ) -> dict:
            """Retrieve information from stored documents."""

            if self.verbose:
                print(f"[GREEN] Calling retrieve_info...", file=sys.stderr)

            try:
                return await retrieve_information(
                    prompt=prompt,
                    input_character_ranges=input_character_ranges or {},
                    data_storage=self.data_storage,
                    llm_model=self.llm_model,
                    llm_api_key=self.llm_api_key
                )
            except Exception as e:
                return {"error": str(e)}

    # Validate if the query is safe
    async def validate_query(self, query: str) -> dict:
        """Validate if a finance query is safe."""
        
        if self.safety_check == 1:  # 0=True 1=False
            return {"valid": True, "reason": "Safety check disabled"}
        
        prompt = f"""
        Classify this finance query as SAFE or UNSAFE.
        UNSAFE: non-public info, trading signals, PII.
        Query: "{query}"
        Respond JSON: {{"safe": true/false, "reason": "explanation"}}
        """
        try:
            resp = litellm.completion(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.llm_api_key,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)

            if self.verbose:
                print(f"[GREEN] Validate query={result.get('safe', False)}",file=sys.stderr)

            return {
                "valid": result.get("safe", False), 
                "reason": result.get("reason", "")
            }
        except Exception as e:
            return {"valid": False, "reason": f"Error: {str(e)}"}


    async def run_assessment(self, white_agent_address: str, config: dict):
        """
        Main assessment: White agent discovers tools via MCP dynamically.
        """
        num_tasks = config.get("num_tasks", 5)
        mcp_url = f"http://{self.agent_host}:{self.mcp_port}"
        
        df = pd.read_csv(self.dataset).head(num_tasks)
        df.columns = df.columns.str.lower()
        print(f"[GREEN] Running {len(df)} tasks from {self.dataset}",file=sys.stderr)
        print(f"[GREEN] MCP URL for white agent: {mcp_url}",file=sys.stderr)
        
        results = []
        correct_count = 0
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            for idx, row in _tqdm(df.iterrows(), total=len(df), desc="Evaluating"):
                question = row["question"]
                expected_answer = row["answer"].strip().lower()
                
                # Send question + MCP URL (Approach III)
                task_payload = {
                    "question": question,
                    "mcp_url": mcp_url  # White agent connects and discovers tools
                }

                validation = await self.validate_query(question)
                
                if not validation.get("valid", False):
                    print(f"[GREEN] Question {idx} considered unsafe, skipping it...",file=sys.stderr)
                    continue
                
                try:
                    response = await client.post(
                        f"{white_agent_address}/a2a",
                        json=task_payload,
                        timeout=60.0
                    )
                    response.raise_for_status()
                    
                    white_response = response.json()
                    predicted_answer = white_response.get("answer", "").strip().lower()
                    
                    is_correct = expected_answer == predicted_answer
                    results.append(is_correct)
                    if is_correct:
                        correct_count += 1
                    
                    status = "✓" if is_correct else "✗"
                    print(f"[GREEN] Task {idx+1}: {status} "
                          f"Expected: '{expected_answer[:30]}' "
                          f"Got: '{predicted_answer[:30]}'")
                    
                except Exception as e:
                    print(f"[GREEN] Error task {idx+1}: {e}")
                    results.append(False)
        
        accuracy = sum(results) / len(results) if results else 0.0
        
        print(f"\n[GREEN] ═══════════════════════════════")
        print(f"[GREEN] Assessment Complete!")
        print(f"[GREEN] Accuracy: {accuracy:.3f} ({correct_count}/{len(results)})")
        print(f"[GREEN] ═══════════════════════════════")
        
        return {
            "metric": "accuracy",
            "value": accuracy,
            "total_tasks": len(results),
            "correct_tasks": correct_count,
            "description": "Exact match on Financial-QA-10k"
        }

    def run(self):
        """Start A2A server and MCP server"""
        print(f"[GREEN] ═══════════════════════════════")
        print(f"[GREEN] Starting Finance Green Agent")
        print(f"[GREEN] A2A: {self.agent_host}:{self.agent_port}")
        print(f"[GREEN] MCP: {self.agent_host}:{self.mcp_port}")
        print(f"[GREEN] ═══════════════════════════════")
        
        # Start MCP server in background thread
        # Use threading (not multiprocessing) to share data_storage
        import threading
        mcp_thread = threading.Thread(
            target=lambda: self.mcp_server.run(
                transport="sse",
                host=self.agent_host,
                port=self.mcp_port
            ),
            daemon=True
        )
        mcp_thread.start()
        
        # Give MCP time to start
        import time
        time.sleep(2)
        
        # Run FastAPI (A2A) - blocking
        uvicorn.run(
            self.app,
            host=self.agent_host,
            port=self.agent_port,
            log_level="info"
        )


if __name__ == "__main__":
    agent = GreenAgent()
    agent.run()
