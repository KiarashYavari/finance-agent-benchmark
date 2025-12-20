#!/bin/bash
# run.sh - AgentBeats compatible launcher
# When called without parameters (by AgentBeats), processes ALL dataset questions
# When called with --num_tasks (for local testing), processes specified number

set -e

# Default values
#NUM_TASKS=""  # Empty = process all questions
NUM_TASKS=5   # Empty = process all questions
ENV_FILE="secrets/secrets.env"
AUTO_START=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --num_tasks)
            NUM_TASKS="$2"
            shift 2
            ;;
        --env)
            ENV_FILE="$2"
            shift 2
            ;;
        --auto_start)
            AUTO_START="--auto_start"
            shift 1
            ;;
        --port)
            AGENT_PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🚀 Starting AgentBeats Finance Benchmark..."
echo "============================================="
if [ -z "$NUM_TASKS" ]; then
    echo "Mode:      FULL BENCHMARK (all questions)"
else
    echo "Mode:      TESTING ($NUM_TASKS questions)"
fi
echo "Env file:  $ENV_FILE"
if [ -z "$AUTO_START" ]; then
    echo "Auto-start: No"
else
    echo "Auto-start: Yes"
fi
echo "============================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "🐍 Using: $PYTHON_VERSION"

# Load environment variables if file exists
if [ -f "$ENV_FILE" ]; then
    echo "🔑 Loading environment variables from $ENV_FILE..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️  Warning: $ENV_FILE not found, using defaults"
fi

# Set NUM_TASKS in environment for green agent
if [ -n "$NUM_TASKS" ]; then
    export NUM_TASKS_OVERRIDE=$NUM_TASKS
    echo "📊 Processing $NUM_TASKS questions"
else
    export NUM_TASKS_OVERRIDE=""
    echo "📊 Processing ALL questions in dataset"
fi


echo "============================================="
echo "🔍 AgentBeats Environment Variables:"
echo "   HOST: ${HOST:-not set}"
echo "   AGENT_PORT: ${AGENT_PORT:-not set}"
echo "============================================="

# Run launcher
echo "🎯 Starting launcher on port ${AGENT_PORT:-7000}..."
#python3 main.py run --port ${AGENT_PORT:-7000} --auto_start
python3 main.py run --port ${AGENT_PORT:-7000} 


