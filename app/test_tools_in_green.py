#!/usr/bin/env python
"""
Test all MCP tools to ensure they work correctly
Run this before starting the full assessment
"""
import asyncio
import json
from mcp.client.sse import sse_client
from mcp import ClientSession

async def test_all_tools():
    """Test each tool individually"""
    mcp_url = "http://127.0.0.1:9001/sse"
    
    print("=" * 60)
    print("Testing MCP Tools")
    print("=" * 60)
    
    try:
        async with sse_client(mcp_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize
                await session.initialize()
                print("✓ MCP session initialized\n")
                
                # List tools
                tools_result = await session.list_tools()
                available_tools = tools_result.tools
                print(f"✓ Found {len(available_tools)} tools:")
                for tool in available_tools:
                    print(f"  - {tool.name}: {tool.description or 'No description'}")
                print()
                
                """
                # Test 0: validate_query
                print("Test 0: validate_query")
                try:
                    result = await session.call_tool(
                        "validate_query",
                        arguments={"query": "What is revenue?"}
                    )
                    print(f"✓ Result: {extract_text(result)}\n")
                except Exception as e:
                    print(f"✗ Error: {e}\n")
                """
                
                # Test 1: google_search_handler
                print("Test 1: google_search_handler")
                try:
                    result = await session.call_tool(
                        "google_search_handler",
                        arguments={"query": "revenue definition"}
                    )
                    response = extract_text(result)
                    if "error" in response.lower():
                        print(f"⚠ Result: {response[:200]}")
                        print("  (This is expected if no API key configured)\n")
                    else:
                        print(f"✓ Result: {response[:200]}...\n")
                except Exception as e:
                    print(f"✗ Error: {e}\n")
                
                # Test 2: serp_search_handler
                print("Test 2: serp_search_handler")
                try:
                    result = await session.call_tool(
                        "serp_search_handler",
                        arguments={"query": "revenue definition"}
                    )
                    response = extract_text(result)
                    if "error" in response.lower():
                        print(f"⚠ Result: {response[:200]}")
                        print("  (This is expected if no API key configured)\n")
                    else:
                        print(f"✓ Result: {response[:200]}...\n")
                except Exception as e:
                    print(f"✗ Error: {e}\n")
                
                # Test 3: edgar_search_handler
                print("Test 3: edgar_search_handler")
                try:
                    result = await session.call_tool(
                        "edgar_search_handler",
                        arguments={
                            "query": "revenue",
                            "form_types": ["10-K"],
                            "ciks": ["0000320193"],  # Apple
                            "start_date": "2024-01-01",
                            "end_date": "2024-12-31",
                            "top_n": 2
                        }
                    )
                    response = extract_text(result)
                    if "error" in response.lower():
                        print(f"⚠ Result: {response[:200]}")
                        print("  (This is expected if no API key configured)\n")
                    else:
                        print(f"✓ Result: {response[:200]}...\n")
                except Exception as e:
                    print(f"✗ Error: {e}\n")
                
                # Test 4: parse_html_handler
                print("Test 4: parse_html_handler")
                try:
                    result = await session.call_tool(
                        "parse_html_handler",
                        arguments={
                            "url": "https://example.com",
                            "key": "test_html"
                        }
                    )
                    print(f"✓ Result: {extract_text(result)[:200]}...\n")
                except Exception as e:
                    print(f"✗ Error: {e}\n")
                
                # Test 5: retrieve_info_handler
                print("Test 5: retrieve_info_handler")
                try:
                    result = await session.call_tool(
                        "retrieve_info_handler",
                        arguments={
                            "prompt": "What is in the document? {{test_html}}",
                            "input_character_ranges": {"test_html": [0, 500]}
                        }
                    )
                    print(f"✓ Result: {extract_text(result)[:200]}...\n")
                except Exception as e:
                    print(f"✗ Error: {e}\n")
                
                print("=" * 60)
                print("Tool Testing Complete")
                print("=" * 60)
                
    except Exception as e:
        print(f"✗ MCP connection error: {e}")
        import traceback
        traceback.print_exc()


def extract_text(result) -> str:
    """Extract text from MCP tool result"""
    if result.content:
        texts = []
        for content in result.content:
            if hasattr(content, 'text'):
                texts.append(content.text)
        return "\n".join(texts)
    return ""


if __name__ == "__main__":
    print("\n🧪 Starting Tool Tests...\n")
    print("Make sure green agent is running on port 9001!")
    print("(Run: python green_agent_mcp_a2a.py)\n")
    
    try:
        asyncio.run(test_all_tools())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
