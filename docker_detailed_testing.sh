#!/bin/bash
# test_docker.sh - Quick Docker testing script

set -e

echo "=========================================="
echo "Finance Agent Benchmark - Docker Test"
echo "=========================================="

# Check if API key is set
if [ -z "$LLM_API_KEY" ]; then
    echo "❌ Error: LLM_API_KEY not set"
    echo "Usage: LLM_API_KEY=your_key ./test_docker.sh"
    exit 1
fi

# Build image
echo ""
echo "Step 1: Building Docker image..."
docker build -t fab .

# Run container
echo ""
echo "Step 2: Starting container with NUM_TASKS=2..."
docker run -d \
  --name finance-agents-test \
  -p 9000:9000 -p 9001:9001 -p 8000:8000 \
  -e LLM_API_KEY=$LLM_API_KEY \
  -e LLM_MODEL=gemini/gemini-2.5-flash-lite \
  -e NUM_TASKS=2 \
  fab

# Wait for startup
echo ""
echo "Step 3: Waiting for agents to start (30s)..."
sleep 30

# Test endpoints
echo ""
echo "Step 4: Testing endpoints..."
echo "  - Green agent health..."
curl -s http://localhost:9000/health | jq .

echo "  - White agent health..."
curl -s http://localhost:8000/health | jq .

echo "  - Green agent card..."
curl -s http://localhost:9000/card | jq '.name'

# Show logs
echo ""
echo "Step 5: Container logs (last 50 lines)..."
docker logs --tail 50 finance-agents-test

# Wait for completion
echo ""
echo "Step 6: Waiting for assessment to complete..."
echo "  (This may take 1-2 minutes depending on NUM_TASKS)"
echo ""

# Follow logs until done
docker logs -f finance-agents-test &
LOGS_PID=$!

# Wait for completion (check for "ASSESSMENT COMPLETE" in logs)
for i in {1..120}; do
    if docker logs finance-agents-test 2>&1 | grep -q "ASSESSMENT COMPLETE"; then
        echo ""
        echo "✅ Assessment complete!"
        kill $LOGS_PID 2>/dev/null || true
        break
    fi
    sleep 1
done

# Show final results
echo ""
echo "=========================================="
echo "Final Results:"
echo "=========================================="
docker logs finance-agents-test 2>&1 | grep -A 10 "ASSESSMENT COMPLETE"

# Cleanup
echo ""
read -p "Stop and remove container? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop finance-agents-test
    docker rm finance-agents-test
    echo "✅ Cleanup complete"
fi
