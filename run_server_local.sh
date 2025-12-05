#!/bin/bash

echo "Starting local MCP server with Keycard integration..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: python -m venv venv && source venv/bin/activate && pip install -e ."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Load and validate environment variables
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Create one with:"
    echo "   - KEYCARD_CLIENT_ID"
    echo "   - KEYCARD_CLIENT_SECRET"
    echo "   - MCP_BASE_URL"
    exit 1
fi

# Export variables from .env
export $(cat .env | grep -v '^#' | xargs)

# Validate required variables
if [ -z "$KEYCARD_CLIENT_ID" ]; then
    echo "❌ KEYCARD_CLIENT_ID not set in .env"
    exit 1
fi

if [ -z "$KEYCARD_CLIENT_SECRET" ]; then
    echo "❌ KEYCARD_CLIENT_SECRET not set in .env"
    exit 1
fi

if [ -z "$MCP_BASE_URL" ]; then
    echo "❌ MCP_BASE_URL not set in .env"
    exit 1
fi

# Display configuration (mask secrets)
echo "✓ Configuration loaded:"
echo "  KEYCARD_ZONE_ID: ${KEYCARD_ZONE_ID:0:10}..."
echo "  KEYCARD_CLIENT_ID: ${KEYCARD_CLIENT_ID}"
echo "  KEYCARD_CLIENT_SECRET: ${KEYCARD_CLIENT_SECRET:0:10}...****"
echo "  MCP_BASE_URL: ${MCP_BASE_URL}"
echo ""

# Check if base URL has trailing slash
if [[ ! "$MCP_BASE_URL" =~ /$ ]]; then
    echo "⚠️  WARNING: MCP_BASE_URL should end with a trailing slash!"
    echo "   Current: $MCP_BASE_URL"
    echo "   Should be: ${MCP_BASE_URL}/"
    echo "   Update .env and restart"
    echo ""
fi

echo "Starting uvicorn server..."
echo "Server will be available at: http://localhost:8000"
echo "MCP endpoint: http://localhost:8000/mcp"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the server
uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload
