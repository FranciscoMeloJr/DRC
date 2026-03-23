#!/bin/bash

# ==========================================================
# DRC ADVISOR v2.6 - STARTUP CONTROLLER
# ==========================================

# 1. NETWORKING CONFIG
export PORT=${PORT:-8080}

# 2. AI ENGINE SECRETS (Mandatory for Bot Synthesis)
# If running locally, ensure these match your .env or OCP secrets
export USER_KEY="${USER_KEY:-your_default_user_key}"
export MODEL_API="${MODEL_API:-your_model_api_url}"
export MODEL_ID="${MODEL_ID:-your_model_id}"

# 3. LIVE RULE TOGGLE (v2.6 Feature)
# Set to 'true' to pull jvm-rules.yaml from GitHub branch drc-advisor-v2.6
# Set to 'false' for air-gapped / offline local mode
export DRC_ONLINE_ENABLED=${DRC_ONLINE_ENABLED:-false}

# 4. PRE-FLIGHT CHECKS
echo "--------------------------------------------------"
echo "🔍 DRC PRE-FLIGHT CHECK"
echo "--------------------------------------------------"
echo "📡 PORT: $PORT"
echo "🤖 AI MODEL: $MODEL_ID"

if [ "$DRC_ONLINE_ENABLED" = "true" ]; then
    echo "🌐 MODE: ONLINE (Syncing with GitHub franciscoMeloJr/DRC)"
else
    echo "🏠 MODE: OFFLINE (Using local /rules folder)"
fi

# Validate critical AI variables
if [ -z "$USER_KEY" ] || [ -z "$MODEL_API" ]; then
    echo "⚠️  WARNING: AI Credentials missing. Bot Synthesis will be disabled."
else
    echo "✅ AI Credentials verified."
fi
echo "--------------------------------------------------"

# 5. EXECUTION
# We use 'exec' so the python process handles OS signals (SIGTERM) directly
echo "🚀 Starting Bridge Server..."
exec python3 js/bridge_server.py