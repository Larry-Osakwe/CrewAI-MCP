"""
Test script for running CrewAI crews with Keycard-secured tools from a LOCAL MCP server.

This connects to a locally running MCP server (http://localhost:8000) instead of
spawning the server via uvx.

Usage:
    # Terminal 1: Start the MCP server
    ./run_server_local.sh

    # Terminal 2: Run this test
    python test_with_local_server.py

Environment Variables (set in .env file):
    OPENAI_API_KEY - Your OpenAI API key
    KEYCARD_ZONE_ID - Your Keycard zone ID (for reference)
"""

import asyncio
import logging
import os
import traceback
from dotenv import load_dotenv
from keycardai.mcp.client import Client as MCPClient
from keycardai.mcp.client.integrations.crewai_agents import create_client
from src.crews.pr_summarizer import run_pr_summary_crew

# Load environment variables from .env file
load_dotenv()

# Enable DEBUG logging for MCP client
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific loggers to DEBUG
logging.getLogger('keycardai.mcp').setLevel(logging.DEBUG)
logging.getLogger('keycardai.agents').setLevel(logging.DEBUG)


async def test_pr_summarizer_local():
    """Test the PR summarizer crew with local MCP server."""
    print("\n" + "="*80)
    print("TEST: PR Summarizer with Local MCP Server")
    print("="*80 + "\n")

    # Configure MCP client to connect to LOCAL HTTP server
    # The server should already be running at http://localhost:8000
    # NOTE: Pass servers dict directly, NOT wrapped in "mcpServers"
    mcp_config = {
        "github": {  # Server name as top-level key
            "url": "https://image-raise-palm-archives.trycloudflare.com/mcp",  # Connect via Cloudflare tunnel
            "transport": "http",  # Streamable HTTP transport (only supported transport)
            "auth": {"type": "oauth"}  # Enable OAuth authentication with server
        }
    }

    try:
        print(f"\n📋 MCP Config:")
        print(f"  Server: github")
        print(f"  URL: {mcp_config['github']['url']}")
        print(f"  Transport: {mcp_config['github']['transport']}")
        print(f"  Auth: {mcp_config['github']['auth']}")
        print(f"\n🔧 Environment:")
        print(f"  MCP_BASE_URL: {os.getenv('MCP_BASE_URL', 'NOT SET')}")
        print(f"  KEYCARD_ZONE_ID: {os.getenv('KEYCARD_ZONE_ID', 'NOT SET')[:10]}...")
        print(f"  KEYCARD_CLIENT_ID: {os.getenv('KEYCARD_CLIENT_ID', 'NOT SET')}")
        print()

        mcp_client = MCPClient(mcp_config)

        # Get Keycard-secured tools
        print("🔌 Attempting to connect to MCP server...")
        async with create_client(mcp_client) as client:
            print("✓ Connection successful\n")

            # Check for auth challenges
            print("🔍 Checking for auth challenges...")
            auth_challenges = await mcp_client.get_auth_challenges()
            if auth_challenges:
                print(f"⚠️  Found {len(auth_challenges)} auth challenge(s):")
                for challenge in auth_challenges:
                    print(f"  Server: {challenge.get('server')}")
                    auth_url = challenge.get('authorization_url', 'N/A')
                    print(f"  Auth URL: {auth_url[:80] if len(auth_url) > 80 else auth_url}...")
                    print(f"\n  ⚠️  Browser should have opened automatically!")
                    print(f"  If not, manually visit the URL above to authorize.")
                    print()
            else:
                print("✓ No auth challenges (already authenticated)\n")

            tools = await client.get_tools()
            auth_tools = await client.get_auth_tools()

            print(f"✓ Connected to local MCP server")
            print(f"✓ Loaded {len(tools)} tools: {[t.name for t in tools]}")
            if auth_tools:
                print(f"⚠ Authentication required - {len(auth_tools)} auth tools available")
            print()

            if len(tools) == 0:
                print("❌ No tools loaded from MCP server!")
                print("\nPossible issues:")
                print("  1. Server not running (run: ./run_server_local.sh)")
                print("  2. KEYCARD_CLIENT_ID/SECRET not set in .env")
                print("  3. MCP_BASE_URL in .env doesn't match tunnel URL")
                print("  4. Server not restarted after changing .env")
                print("  5. GitHub provider not configured in Keycard")
                print("\nCheck the server logs for errors.")
                return

            # Run the crew with Keycard-secured tools (NO TOKEN!)
            print("Running crew to analyze PR...")
            result = run_pr_summary_crew(
                repo="anthropics/anthropic-sdk-python",
                pr_number=588,
                tools=tools  # Keycard-secured tools
            )

            print("\n" + "="*80)
            print("RESULT:")
            print("="*80)
            print(result)

    except Exception as e:
        print(f"\n❌ Error connecting to MCP server:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")

        print(f"\n📋 Full traceback:")
        traceback.print_exc()

        print("\n🔧 Troubleshooting:")
        print("  1. Make sure the server is running: ./run_server_local.sh")
        print("  2. Check server logs in the other terminal")
        print("  3. Test tunnel connectivity:")
        print("     curl https://image-raise-palm-archives.trycloudflare.com/")
        print("  4. Verify .env has correct MCP_BASE_URL with trailing slash")
        print("  5. Restart server after changing .env")


async def validate_connection():
    """Quick validation that we can connect to the local server."""
    print("\n" + "="*80)
    print("VALIDATION: Testing Connection to Local MCP Server")
    print("="*80 + "\n")

    # NOTE: Pass servers dict directly, NOT wrapped in "mcpServers"
    mcp_config = {
        "github": {  # Server name as top-level key
            "url": "https://image-raise-palm-archives.trycloudflare.com/mcp",  # Connect via Cloudflare tunnel
            "transport": "http",
            "auth": {"type": "oauth"}
        }
    }

    try:
        print(f"📋 Connecting to: {mcp_config['github']['url']}")
        print(f"🔐 Auth type: {mcp_config['github']['auth']}\n")

        mcp_client = MCPClient(mcp_config)
        async with create_client(mcp_client) as client:
            print("✓ Connection established\n")

            # Check sessions status (safely handle disconnected sessions)
            from keycardai.mcp.client.session import SessionStatus

            for server_name, session in mcp_client.sessions.items():
                print(f"📊 Session '{server_name}' status:")
                print(f"  Status: {session.status}")
                # keycardai-mcp Session doesn't have status_category or requires_user_action
                # Just show the connection status
                print(f"  Connected: {session.status == SessionStatus.CONNECTED}")
                print()

            tools = await client.get_tools()

            print(f"✓ Successfully connected to local MCP server")
            print(f"✓ Loaded {len(tools)} tools")

            if len(tools) > 0:
                print(f"\nAvailable tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description[:60]}...")
            else:
                print("\n⚠️ No tools available - check server authentication")

                # Check for auth challenges
                auth_challenges = await mcp_client.get_auth_challenges()
                if auth_challenges:
                    print(f"\n🔐 Auth challenges found:")
                    for challenge in auth_challenges:
                        print(f"  Server: {challenge.get('server')}")
                        auth_url = challenge.get('authorization_url', 'N/A')
                        print(f"  URL: {auth_url[:80] if len(auth_url) > 80 else auth_url}")
                        print(f"\n  ⚠️  Browser should have opened automatically!")
                        print(f"  If not, manually visit the URL above to authorize.")

            return len(tools) > 0

    except Exception as e:
        print(f"❌ Failed to connect:")
        print(f"   {type(e).__name__}: {str(e)}\n")

        traceback.print_exc()

        print("\n🔧 Is the server running? Start it with:")
        print("  ./run_server_local.sh")
        return False


async def main():
    """Run validation and test."""
    print("\n" + "="*80)
    print("TESTING CREWAI + KEYCARD INTEGRATION (Local Server)")
    print("="*80)

    # First validate connection
    connected = await validate_connection()

    if not connected:
        print("\n⚠️ Skipping crew test - fix connection first")
        return

    # Run the actual test
    await test_pr_summarizer_local()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
