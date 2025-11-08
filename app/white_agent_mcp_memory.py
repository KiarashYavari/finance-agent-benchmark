# app/white_agent_mcp_improved.py
"""
Finance-White Agent - Improved Tool Selection & Memory
"""

import os
import sys
import json
import litellm
import tomllib
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Dict, Any

from mcp.client.sse import sse_client
from mcp import ClientSession

from utils.env_setup import init_environment

init_environment()


class ConversationMemory:
    """
    Simple conversation memory for multi-turn reasoning
    Stores tool calls and results
    """
    def __init__(self, max_history: int = 10):
        self.history = []
        self.max_history = max_history
    
    def add_tool_call(self, tool: str, params: dict, result: Any):
        """Add a tool call to memory"""
        self.history.append({
            "type": "tool_call",
            "tool": tool,
            "params": params,
            "result": result,
            "timestamp": self._get_timestamp()
        })
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def add_reasoning(self, thought: str):
        """Add reasoning step to memory"""
        self.history.append({
            "type": "reasoning",
            "thought": thought,
            "timestamp": self._get_timestamp()
        })
    
    def get_summary(self, last_n: int = 5) -> str:
        """Get summary of recent history"""
        recent = self.history[-last_n:] if len(self.history) > last_n else self.history
        
        summary = []
        for item in recent:
            if item["type"] == "tool_call":
                summary.append(
                    f"Called {item['tool']} with {item['params']}\n"
                    f"Result: {str(item['result'])[:200]}..."
                )
            elif item["type"] == "reasoning":
                summary.append(f"Thought: {item['thought']}")
        
        return "\n\n".join(summary)
    
    def clear(self):
        """Clear memory"""
        self.history = []
    
    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().isoformat()


class WhiteAgent:
    """
    Improved Finance White Agent with:
    - Better tool selection logic
    - Conversation memory
    - Multi-step reasoning
    """

    def __init__(self):
        self.agent_host = os.getenv("WHITE_AGENT_HOST", "0.0.0.0")
        self.agent_port = int(os.getenv("WHITE_AGENT_PORT", 8000))
        self.name = "finance-white-agent"
        
        # Load agent card
        self.card_path = os.getenv(
            "WHITE_CARD",
            Path(__file__).parent / "cards" / "white_card.toml"
        )
        if not os.path.exists(self.card_path):
            raise FileNotFoundError(f"Agent card {self.card_path} not found")
        
        with open(self.card_path, "rb") as f:
            self.agent_card = tomllib.load(f)
        
        # LLM configuration
        self.model = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash-lite")
        self.api_key = os.getenv("LLM_API_KEY")
        self.max_iterations = int(os.getenv("WHITE_AGENT_MAX_ITER", 5))
        
        # Memory
        self.memory = ConversationMemory(max_history=10)
        
        # Create FastAPI app
        self.app = FastAPI(title="Finance White Agent")
        self._setup_routes()

    def _setup_routes(self):
        """Setup A2A protocol endpoints"""
        
        @self.app.get("/card")
        @self.app.get("/.well-known/agent-card.json")
        async def get_card():
            return JSONResponse(self.agent_card)
        
        @self.app.post("/a2a")
        async def handle_task(request: Request):
            try:
                payload = await request.json()
                question = payload.get("question")
                mcp_url = payload.get("mcp_url")
                
                print(f"[WHITE] ═══════════════════════════════")
                print(f"[WHITE] Q: {question[:80]}...")
                print(f"[WHITE] MCP: {mcp_url}")
                print(f"[WHITE] ═══════════════════════════════")
                
                # Clear memory for new question
                self.memory.clear()
                
                # Generate answer
                answer = await self.answer_question(question, mcp_url)
                
                print(f"[WHITE] A: {answer[:80]}...")
                
                return JSONResponse({
                    "status": "completed",
                    "answer": answer
                })
                
            except Exception as e:
                print(f"[WHITE] Error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return JSONResponse({
                    "status": "error",
                    "message": str(e),
                    "answer": "ERROR"
                }, status_code=500)
        
        @self.app.get("/health")
        async def health():
            return {"status": "ok", "agent": self.name}

    async def answer_question(self, question: str, mcp_url: str) -> str:
        """
        IMPROVED reasoning loop with:
        - Better tool selection prompts
        - Memory of previous steps
        - Strategic tool usage
        """
        
        # Parse MCP URL
        import re
        match = re.match(r"http://([^:]+):(\d+)", mcp_url)
        if not match:
            return "ERROR: Invalid MCP URL"
        
        mcp_host = match.group(1)
        mcp_port = int(match.group(2))
        
        sse_url = f"http://{mcp_host}:{mcp_port}/sse" if not mcp_url.endswith("/sse") else mcp_url
        
        print(f"[WHITE] Connecting to: {sse_url}", file=sys.stderr)
        
        try:
            async with sse_client(sse_url) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize
                    await session.initialize()
                    print(f"[WHITE] MCP initialized", file=sys.stderr)
                    
                    # Discover tools
                    tools_result = await session.list_tools()
                    available_tools = tools_result.tools
                    
                    # Add 1 because first iteraction is the instruction to LLM. 
                    self.max_iterations = len(available_tools) + 1 
                    print(f"[WHITE] {self.max_iterations} tools: {[t.name for t in available_tools]}", file=sys.stderr)
                    
                    # Multi-turn reasoning with improved prompts
                    for iteration in range(self.max_iterations):
                        print(f"\n[WHITE] --- Iteration {iteration+1}/{self.max_iterations} ---", file=sys.stderr)
                        
                        # Build context-aware prompt
                        if iteration == 0:
                            system_prompt = self._build_initial_prompt(question, available_tools)
                        else:
                            system_prompt = self._build_followup_prompt(question, available_tools)
                        
                        # Get LLM decision
                        try:
                            response = litellm.completion(
                                model=self.model,
                                messages=[
                                    {"role": "system", "content": "You are a JSON-only assistant. Always respond with valid JSON in the exact format requested. Never generate code or explanations."},
                                    {"role": "user", "content": system_prompt}
                                ],
                                api_key=self.api_key,
                                response_format={"type": "json_object"},
                                temperature=0.2  # Lower temp for more focused decisions
                            )
                            
                            # Parse LLM response
                            response_text = response.choices[0].message.content
                            print(f"[WHITE] LLM Response: {response_text[:250]}", file=sys.stderr)
                            
                            try:
                                decision = json.loads(response_text)
                            except json.JSONDecodeError as e:
                                print(f"[WHITE] JSON parse error: {e}", file=sys.stderr)
                                print(f"[WHITE] Response was: {response_text}", file=sys.stderr)
                                continue
                            
                            action = decision.get("action")
                            
                            # Handle malformed responses (LLM generating code instead of JSON)
                            if not action and "tool_code" in decision:
                                print(f"[WHITE] LLM generated code instead of JSON, skipping...", file=sys.stderr)
                                continue
                            
                            if not action:
                                print(f"[WHITE] No action in decision: {decision}", file=sys.stderr)
                                continue
                            
                            print(f"[WHITE] Decision: {action}", file=sys.stderr)
                            
                            # Handle decision
                            if action == "answer":
                                final_answer = decision.get("answer", "")
                                reasoning = decision.get("reasoning", "")
                                self.memory.add_reasoning(reasoning)
                                return final_answer
                            
                            elif action == "tool_call":
                                tool = decision.get("tool")
                                params = decision.get("params", {})
                                reasoning = decision.get("reasoning", "")
                                
                                # Verify tool exists
                                if not any(t.name == tool for t in available_tools):
                                    print(f"[WHITE] Tool '{tool}' not found", file=sys.stderr)
                                    continue
                                
                                # Normalize parameter names (common LLM mistakes)
                                if "search_term" in params and "query" not in params:
                                    params["query"] = params.pop("search_term")
                                if "search_query" in params and "query" not in params:
                                    params["query"] = params.pop("search_query")
                                
                                print(f"[WHITE] Calling: {tool}({params})", file=sys.stderr)
                                self.memory.add_reasoning(reasoning)
                                
                                # Call tool
                                tool_result = await session.call_tool(tool, arguments=params)
                                result_data = self._extract_text_from_tool_result(tool_result)
                                
                                # Check if tool call failed
                                is_error = "error" in str(result_data).lower() or "missing" in str(result_data).lower()
                                
                                if is_error:
                                    print(f"[WHITE] Tool failed: {result_data[:100]}", file=sys.stderr)
                                    self.memory.add_reasoning(f"Tool {tool} failed: {result_data[:100]}")
                                    # Don't store failed results, let LLM try another tool
                                    continue
                                
                                # Store in memory only if successful
                                self.memory.add_tool_call(tool, params, result_data)
                                print(f"[WHITE] Result: {str(result_data)[:100]}...", file=sys.stderr)
                                
                        except json.JSONDecodeError as e:
                            print(f"[WHITE] LLM JSON error: {e}", file=sys.stderr)
                            print(f"[WHITE] Response: {response_text[:500]}", file=sys.stderr)
                            break
                        except Exception as e:
                            print(f"[WHITE] LLM/Tool error: {e}", file=sys.stderr)
                            import traceback
                            traceback.print_exc()
                            break
                    
                    # Max iterations reached - generate final answer
                    return self._generate_final_answer(question)
            
        except Exception as e:
            print(f"[WHITE] MCP error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return f"ERROR: {str(e)}"

    def _build_initial_prompt(self, question: str, tools: List) -> str:
        """Build initial reasoning prompt"""
        tools_desc = "\n".join([
            f"- {t.name}: {t.description or 'No description'}"
            for t in tools if t.name != "validate_query"  # Skip validation tool
        ])
        
        return f"""You are a financial question-answering agent. You have access to these tools to help answer questions:

AVAILABLE TOOLS:
{tools_desc}

QUESTION: {question}

YOUR TASK:
1. Choose ONE tool to call that will help answer the question
2. OR provide the final answer if you already know it

TOOL SELECTION GUIDE:
- For definitions (revenue, EBITDA, assets): Use google_search_handler OR serp_search_handler
- For company data (Apple revenue, NVIDIA earnings): Use edgar_search_handler OR serp_search_handler  
- For documents: Use parse_html_handler + retrieve_info_handler
- If one tool fails, try a different tool next iteration

IMPORTANT: You must respond with EXACTLY this JSON format (no code, no explanations):

To call a tool:
{{
    "action": "tool_call",
    "tool": "google_search_handler",
    "params": {{"query": "your search query here"}},
    "reasoning": "why this tool"
}}

To answer:
{{
    "action": "answer",
    "answer": "your final answer here",
    "reasoning": "why this is the answer"
}}

Do NOT generate code. Do NOT use print() or .search(). Just return pure JSON as shown above.
"""

    def _build_followup_prompt(self, question: str, tools: List) -> str:
        """Build follow-up prompt with memory"""
        memory_summary = self.memory.get_summary(last_n=3)
        
        tools_desc = "\n".join([
            f"- {t.name}: {t.description or 'No description'}"
            for t in tools if t.name != "validate_query"
        ])
        
        return f"""QUESTION: {question}

AVAILABLE TOOLS:
{tools_desc}

WHAT HAPPENED SO FAR:
{memory_summary}

YOUR TASK:
Based on what happened, either:
1. If a tool FAILED, try a DIFFERENT tool (e.g., try serp_search_handler if google_search_handler failed)
2. If you got useful information, provide the FINAL ANSWER
3. If you need more info, call another tool
4. If one tool fails, do NOT call it again

IMPORTANT: Respond with EXACTLY this JSON format (no code):

To call a tool:
{{
    "action": "tool_call",
    "tool": "serp_search_handler",
    "params": {{"query": "your search query"}},
    "reasoning": "why this tool"
}}

To answer:
{{
    "action": "answer",
    "answer": "your final answer",
    "reasoning": "why this is correct"
}}

Do NOT generate code. Do NOT use print() or .search(). Just return pure JSON.
"""

    def _generate_final_answer(self, question: str) -> str:
        """Generate final answer from memory"""
        memory_summary = self.memory.get_summary()
        
        if not memory_summary:
            return "NO_ANSWER_FOUND"
        
        prompt = f"""Question: {question}

Based on these research steps:
{memory_summary}

Provide a concise, accurate final answer.
"""
        
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[WHITE] Final answer error: {e}", file=sys.stderr)
            return "ERROR_GENERATING_ANSWER"

    def _extract_json_from_tool_result(self, result) -> dict:
        """Extract JSON from MCP tool result"""
        if result.content:
            for content in result.content:
                if hasattr(content, 'text'):
                    try:
                        return json.loads(content.text)
                    except:
                        return {"valid": True}
        return {"valid": True}

    def _extract_text_from_tool_result(self, result) -> str:
        """Extract text from MCP tool result"""
        if result.content:
            texts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    texts.append(content.text)
            return "\n".join(texts)
        return ""

    def run(self):
        """Start agent server"""
        print(f"[WHITE] ═══════════════════════════════")
        print(f"[WHITE] Finance White Agent (Improved)")
        print(f"[WHITE] Server: {self.agent_host}:{self.agent_port}")
        print(f"[WHITE] Memory: Enabled")
        print(f"[WHITE] ═══════════════════════════════")
        
        uvicorn.run(
            self.app,
            host=self.agent_host,
            port=self.agent_port,
            log_level="info"
        )


if __name__ == "__main__":
    agent = WhiteAgent()
    agent.run()
