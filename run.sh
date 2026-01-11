#!/usr/bin/env bash
set -e

export HOST=0.0.0.0
export AGENT_PORT=${PORT:-8080}   # Cloud Run's port becomes the agent's port

echo "Starting Finance-Agent-Benchmark launcher on $HOST:$AGENT_PORT..."
exec agentbeats run_ctrl
