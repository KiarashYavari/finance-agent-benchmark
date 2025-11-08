# ============================================
# Test 1: Build the image
# ============================================
docker build -t fab .

# ============================================
# Test 2: Run with environment variables only
# ============================================
docker run --rm \
  --name finance-agents \
  -p 9000:9000 -p 9001:9001 -p 8000:8000 \
  -e LLM_API_KEY=your_actual_api_key_here \
  -e LLM_MODEL=gemini/gemini-2.5-flash-lite \
  -e NUM_TASKS=3 \
  fab

# ============================================
# Test 3: Run in detached mode with logs
# ============================================
docker run -d \
  --name finance-agents \
  -p 9000:9000 -p 9001:9001 -p 8000:8000 \
  -e LLM_API_KEY=your_key \
  -e LLM_MODEL=gemini/gemini-2.5-flash-lite \
  -e NUM_TASKS=5 \
  fab

# View logs (follow)
docker logs -f finance-agents

# ============================================
# Test 4: Override NUM_TASKS via CMD
# ============================================
docker run --rm \
  -p 9000:9000 -p 9001:9001 -p 8000:8000 \
  -e LLM_API_KEY=your_key \
  -e LLM_MODEL=gemini/gemini-2.5-flash-lite \
  fab python app/launcher.py --num_tasks 2

# ============================================
# Test 5: Interactive mode (see output live)
# ============================================
docker run --rm -it \
  -p 9000:9000 -p 9001:9001 -p 8000:8000 \
  -e LLM_API_KEY=your_key \
  -e LLM_MODEL=gemini/gemini-2.5-flash-lite \
  -e NUM_TASKS=2 \
  fab

# ============================================
# Test 6: Use secrets.env file
# ============================================
docker run --rm \
  -p 9000:9000 -p 9001:9001 -p 8000:8000 \
  --env-file secrets/secrets.env \
  fab

# ============================================
# Test 7: Check running containers
# ============================================
docker ps

# ============================================
# Test 8: Stop and remove container
# ============================================
docker stop finance-agents
docker rm finance-agents

# ============================================
# Test 9: Check container health
# ============================================
docker exec finance-agents curl http://localhost:9000/health
docker exec finance-agents curl http://localhost:8000/health

# ============================================
# Test 10: View last 100 log lines
# ============================================
docker logs --tail 100 finance-agents

# ============================================
# Test 11: Test from host machine
# ============================================
curl http://localhost:9000/health
curl http://localhost:8000/health
curl http://localhost:9000/card