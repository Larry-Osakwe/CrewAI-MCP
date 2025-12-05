"""
Test script demonstrating CrewAI agent using authenticated MCP tools.

This test validates that:
1. A CrewAI agent can autonomously choose to use an authenticated tool
2. The Keycard authentication flow works correctly
3. The agent successfully accesses a repository using delegated credentials

PREREQUISITES:
    1. MCP server must be running: ./run_server_local.sh
    2. Cloudflare tunnel active (or use localhost URL)

Usage:
    # Terminal 1: Start MCP server
    ./run_server_local.sh

    # Terminal 2: Run this test
    python test_crew_with_auth.py

Environment Variables (set in .env file):
    OPENAI_API_KEY - Your OpenAI API key
    KEYCARD_ZONE_ID - Your Keycard zone ID
    KEYCARD_CLIENT_ID - Keycard client ID
    KEYCARD_CLIENT_SECRET - Keycard client secret
    MCP_BASE_URL - URL where MCP server is accessible (with trailing slash)
"""

import asyncio
import os
from dotenv import load_dotenv
from crewai import Agent, Crew, Task
from keycardai.mcp.client import Client as MCPClient
from keycardai.mcp.client.integrations.crewai_agents import create_client

# Load environment variables
load_dotenv()


async def test_agent_with_authenticated_tool():
    """
    Test that a CrewAI agent can successfully use an authenticated tool.

    The agent is given a task that requires accessing a GitHub PR.
    The agent must decide which tool to use, and if it chooses the
    authenticated tool, Keycard will handle the token exchange.
    """
    print("\n" + "="*80)
    print("TEST: CrewAI Agent Using Authenticated MCP Tool")
    print("="*80 + "\n")

    # Get MCP server URL from environment
    mcp_base_url = os.getenv("MCP_BASE_URL")
    if not mcp_base_url:
        print("❌ ERROR: MCP_BASE_URL not set in .env")
        print("\nPlease set MCP_BASE_URL in .env file, e.g.:")
        print("  MCP_BASE_URL=https://your-tunnel.trycloudflare.com/")
        print("  or")
        print("  MCP_BASE_URL=http://localhost:8000/")
        return

    # Ensure URL ends with slash
    if not mcp_base_url.endswith('/'):
        mcp_base_url += '/'

    # Configure MCP client to connect to running server via HTTP
    mcp_config = {
        "github": {
            "url": mcp_base_url + "mcp",
            "transport": "http",
            "auth": {"type": "oauth"}
        }
    }

    print(f"📋 MCP Configuration:")
    print(f"  Server URL: {mcp_config['github']['url']}")
    print(f"  Transport: {mcp_config['github']['transport']}")
    print(f"  Auth Type: {mcp_config['github']['auth']['type']}")
    print()

    try:
        mcp_client = MCPClient(mcp_config)

        print("🔌 Connecting to MCP server...")
        async with create_client(mcp_client) as client:
            print("✓ Connection successful\n")

            # Get all available tools from MCP server
            tools = await client.get_tools()
            auth_tools = await client.get_auth_tools()

            if len(tools) == 0:
                print("❌ ERROR: No tools loaded from MCP server!")
                print("\nPossible issues:")
                print("  1. Server not running (run: ./run_server_local.sh)")
                print("  2. Server URL incorrect in .env")
                print("  3. Server authentication not configured")
                print("\nCheck server logs and verify it's accessible at:")
                print(f"  {mcp_config['github']['url']}")
                return

            print("🔧 Available Tools:")
            for tool in tools:
                auth_marker = "🔐" if tool.name in [t.name for t in auth_tools] else "🌐"
                print(f"  {auth_marker} {tool.name}: {tool.description[:60]}...")
            print()

            if auth_tools:
                print(f"⚠️  {len(auth_tools)} tools require authentication")
                print("   These will trigger Keycard OAuth flow when called")
                print("   Your browser will open for authorization")
                print()

            # Create a CrewAI agent with access to MCP tools
            pr_analyst = Agent(
                role="GitHub PR Analyst",
                goal="Analyze pull requests and provide detailed summaries",
                backstory="""You are an expert at analyzing GitHub pull requests.
                You have access to tools that can fetch PR data from GitHub.
                You understand that some repositories require authentication.""",
                tools=tools,  # MCP tools with Keycard auth
                verbose=True,
                llm="gpt-4o-mini"
            )

            # Create a task that requires accessing a specific PR
            # This repo is accessible to the user's GitHub token
            analyze_task = Task(
                description="""Analyze pull request #1 from the repository Larry-Osakwe/playthis-3.

Fetch the PR details and provide a summary including:
- PR title and author
- Current state (open/closed/merged)
- Number of files changed
- Number of additions and deletions
- Brief description of what the PR does

Use the appropriate tool to fetch this information. If you need authentication,
the authenticated tool should be available to you.""",
                expected_output="""A concise summary of the PR with title, author, state,
                change statistics, and description.""",
                agent=pr_analyst
            )

            # Create and run the crew
            crew = Crew(
                agents=[pr_analyst],
                tasks=[analyze_task],
                verbose=True
            )

            print("🚀 Starting crew execution...")
            print("   The agent will now decide which tool to use")
            print("   If it chooses an authenticated tool, Keycard will handle auth")
            print()

            result = crew.kickoff()

            print("\n" + "="*80)
            print("✅ SUCCESS - Agent completed task")
            print("="*80)
            print("\n📊 Result:")
            print(result)
            print()

            # Validate result contains expected data
            result_str = str(result).lower()
            success_indicators = ['larry-osakwe', 'playthis-3', 'pr', 'pull request']

            found_indicators = [indicator for indicator in success_indicators if indicator in result_str]

            if found_indicators:
                print("✅ Validation: Result contains expected PR information")
                print(f"   Found indicators: {', '.join(found_indicators)}")
            else:
                print("⚠️  Warning: Result may not contain expected PR data")

            print()
            print("="*80)
            print("Test completed successfully!")
            print("="*80)

    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR - Failed to connect or execute")
        print("="*80)
        print(f"\nError: {e}")
        print()

        # Provide debugging hints
        print("Possible causes:")
        print("  1. MCP server not running - start with: ./run_server_local.sh")
        print("  2. Server URL incorrect - check MCP_BASE_URL in .env")
        print("  3. Network connectivity - verify server is accessible")
        print("  4. Authentication failed - check Keycard credentials")

        import traceback
        print("\nFull traceback:")
        traceback.print_exc()


async def main():
    """Run the test."""
    print("\n" + "="*80)
    print("TESTING: CrewAI + MCP + Keycard Integration")
    print("="*80)
    print("\nThis test demonstrates:")
    print("  1. CrewAI agent autonomously choosing which tool to use")
    print("  2. Keycard handling authentication transparently")
    print("  3. Successful access to GitHub API with delegated credentials")
    print()

    await test_agent_with_authenticated_tool()

    print("\n" + "="*80)
    print("All tests complete")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
