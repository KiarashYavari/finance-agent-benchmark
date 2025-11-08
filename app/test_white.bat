@echo off
echo.
echo === AgentBeats White Agent Test ===
echo Sends a POST request to the white agent A2A endpoint with inline JSON.
echo Make sure both, the white and the green agents are running
echo.
echo. 

curl -X POST http://localhost:8000/a2a ^
     -H "Content-Type: application/json" ^
     -d "{\"question\": \"What is revenue?\", \"mcp_url\": \"http://localhost:9001/mcp\"}"

echo.
echo.
echo === Test completed ===