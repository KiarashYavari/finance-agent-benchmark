# Base image
FROM python:3.13-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/app/cache \
    GREEN_AGENT_HOST=0.0.0.0 \
    GREEN_AGENT_PORT=9009

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    libstdc++6 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy green agent code and utils
COPY green_agent_mcp_a2a_judge_rag.py .
COPY utils/ ./utils/
COPY cards/green_card.toml ./cards/green_card.toml
COPY data/public.csv /app/data/public.csv
# Copy models and cache
COPY tools/ ./tools/
RUN mkdir -p /app/cache

# # Make scripts executable (if any)
# COPY run.sh run_launcher.sh kill_agentbeats.sh ./
# RUN chmod +x run.sh run_launcher.sh kill_agentbeats.sh

# Run green agent directly
ENTRYPOINT ["python", "green_agent_mcp_a2a_judge_rag.py"]
