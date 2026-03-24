#!/bin/bash

# ==========================================================
# DRC ADVISOR v2.6 - NINETAILS STARTUP CONTROLLER
# ==========================================================

# 1. PATH RESOLUTION
# Ensure we are always executing relative to the script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 2. NETWORKING & IDENTITY
export PORT=${PORT:-8080}
VERSION="2.6 - Ninetails"

# 3. AI ENGINE SECRETS (Mandatory for Bot Synthesis)
# Default values removed for security; must be provided via env or secret
export USER_KEY="${USER_KEY:-}"
export MODEL_API="${MODEL_API:-}"
export MODEL_ID="${MODEL_ID:-}"

# 4. LIVE RULE REGISTRY CONFIG
# true  -> Fetch rules from GitHub (FranciscoMeloJr/DRC)
# false -> Strict local-only mode (Air-gapped/Security)
export DRC_ONLINE_ENABLED=${DRC_ONLINE_ENABLED:-false}

# ==========================================================
# PRE-FLIGHT DIAGNOSTICS
# ==========================================================
echo "=================================================="
echo "🦊 DRC ADVISOR v$VERSION"
echo "=================================================="
echo "📡 STATUS: Listening on Port $PORT"

# Check Python Dependencies
python3 -c "import requests, yaml" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Missing dependencies (requests or pyyaml). Run: pip install requests pyyaml"
    exit 1
fi

# Online/Offline Mode Logic
if [ "$DRC_ONLINE_ENABLED" = "true" ]; then
    echo "🌐 MODE: ONLINE SYNC (Branch: drc-advisor-v2.6)"
    echo "   Checking connectivity to GitHub..."
    curl -Is --connect-timeout 2 https://github.com | grep -q "HTTP/1.1 200"
    if [ $? -ne 0 ]; then
        echo "   ⚠️  GitHub unreachable. Registry will use local fallback."
    fi
else
    echo "🏠 MODE: OFFLINE (Local /rules directory only)"
fi

# AI Credentials Guard
if [[ -z "$USER_KEY" || -z "$MODEL_API" ]]; then
    echo "⚠️  BOT STATUS: Disabled (Missing AI Credentials)"
else
    echo "✅ BOT STATUS: Enabled (Credentials Verified)"
fi

echo "--------------------------------------------------"
echo "🚀 Booting Bridge Server..."

# 5. EXECUTION
# exec ensures Python receives SIGTERM/SIGINT signals from OCP/Docker
exec python3 js/bridge_server.py