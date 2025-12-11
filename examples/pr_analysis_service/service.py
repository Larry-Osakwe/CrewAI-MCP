"""PR Analysis Service - Phase 2A Example.

This service demonstrates service-to-service delegation in Phase 2A:
- Fetches PR data from GitHub (via MCP tool)
- Analyzes code quality
- Generates summary
- Delegates to Echo Service (via A2A) for testing

Architecture:
    User → PR Analysis Service
      ├─ Uses MCP GitHub tools → GitHub API
      └─ Delegates to Echo Service (for testing A2A)

Delegation chain: user → pr_analyzer → echo_service

Note: This uses Echo Service for initial A2A testing.
      Replace with Slack Notification Service once Echo works.
"""

import os
import asyncio
import logging
from typing import Any

from crewai import Agent, Crew, Task
from keycardai.agents import AgentServiceConfig, serve_agent
from keycardai.agents.integrations.crewai_a2a import get_a2a_tools
from keycardai.mcp.client import Client as MCPClient
from keycardai.mcp.client.integrations.crewai_agents import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_pr_analysis_crew(mcp_tools: list[Any], a2a_tools: list[Any]) -> Crew:
    """Create PR analysis crew with MCP and A2A tools.

    Args:
        mcp_tools: MCP tools for GitHub access
        a2a_tools: A2A tools for delegating to other services

    Returns:
        Crew instance
    """
    # PR Fetcher Agent
    pr_fetcher = Agent(
        role="PR Data Fetcher",
        goal="Fetch pull request data from GitHub",
        backstory="""You are an expert at retrieving pull request information.
        You use GitHub API tools to fetch PR details, files, and metadata.""",
        tools=[t for t in mcp_tools if "pr" in t.name.lower() or "github" in t.name.lower()],
        verbose=True,
    )

    # Code Reviewer Agent
    code_reviewer = Agent(
        role="Code Reviewer",
        goal="Analyze code quality and identify issues",
        backstory="""You are a senior code reviewer with expertise in software quality.
        You analyze code changes for potential bugs, security issues, and best practices.""",
        tools=[],  # Uses context from PR fetcher
        verbose=True,
    )

    # Orchestrator Agent (has A2A delegation capability)
    orchestrator = Agent(
        role="Orchestrator",
        goal="Coordinate PR analysis and send to Echo Service",
        backstory="""You orchestrate the entire PR analysis workflow.
        After the team analyzes a PR, you send the summary to the Echo Service
        to test the A2A delegation pattern.""",
        tools=a2a_tools,  # Can delegate to other services
        verbose=True,
    )

    # Tasks
    fetch_task = Task(
        description="""Fetch pull request #{pr_number} from repository {repo}.
        Get the PR title, description, changed files, and current status.""",
        expected_output="PR details including title, description, files, and status",
        agent=pr_fetcher,
    )

    review_task = Task(
        description="""Review the code changes in the pull request.
        Identify:
        - Code quality issues
        - Potential bugs
        - Security concerns
        - Best practice violations

        Provide a concise analysis with severity ratings.""",
        expected_output="Code review analysis with identified issues",
        agent=code_reviewer,
        context=[fetch_task],
    )

    orchestrate_task = Task(
        description="""Synthesize the PR analysis into a summary.
        Then delegate to the Echo Service to test A2A delegation.

        Use the delegate_to_echo_service tool to send the summary.""",
        expected_output="Confirmation that summary was sent to Echo Service",
        agent=orchestrator,
        context=[fetch_task, review_task],
    )

    # Create crew
    crew = Crew(
        agents=[pr_fetcher, code_reviewer, orchestrator],
        tasks=[fetch_task, review_task, orchestrate_task],
        verbose=True,
    )

    return crew


# Global tool cache initialized at startup
_mcp_tools = None
_a2a_tools = None


async def initialize_tools():
    """Initialize MCP and A2A tools once at startup.

    This avoids the need to create tools on every request and eliminates
    the nested event loop issue with uvloop.
    """
    global _mcp_tools, _a2a_tools

    logger.info("Initializing MCP and A2A tools...")

    # MCP client configuration for GitHub tools
    mcp_config = {
        "github": {
            "url": os.getenv("GITHUB_MCP_SERVER_URL", "http://localhost:8000/mcp"),
        }
    }
    mcp_client = MCPClient(mcp_config)

    # Service configuration for A2A delegation
    service_config = AgentServiceConfig(
        service_name="PR Analysis Service",
        client_id=os.getenv("KEYCARD_CLIENT_ID", "pr_analyzer_service"),
        client_secret=os.getenv("KEYCARD_CLIENT_SECRET"),
        identity_url=os.getenv("SERVICE_IDENTITY_URL", "https://pr-analyzer.example.com"),
        zone_id=os.getenv("KEYCARD_ZONE_ID"),
        description="Analyzes GitHub pull requests for code quality and security",
        capabilities=["pr_analysis", "code_review", "github_integration"],
    )

    # Get MCP tools
    async with create_client(mcp_client) as crewai_client:
        _mcp_tools = await crewai_client.get_tools()

    # Get A2A delegation tools
    echo_service = {
        "name": "Echo Service",
        "url": os.getenv("ECHO_SERVICE_URL", "http://localhost:8002"),
        "description": "Simple echo service for testing A2A delegation",
        "capabilities": ["echo", "testing", "a2a_delegation"],
    }
    _a2a_tools = await get_a2a_tools(service_config, delegatable_services=[echo_service])

    logger.info(f"Initialized {len(_mcp_tools)} MCP tools and {len(_a2a_tools)} A2A tools")


def crew_factory_sync() -> Crew:
    """Synchronous crew factory using pre-initialized tools.

    This is called by the agent service framework when handling requests.
    Tools are initialized once at startup to avoid async/event loop issues.
    """
    if _mcp_tools is None or _a2a_tools is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() at startup.")

    return create_pr_analysis_crew(_mcp_tools, _a2a_tools)


def main():
    """Start PR Analysis Service."""
    # Validate environment variables
    required_vars = [
        "KEYCARD_CLIENT_SECRET",
        "KEYCARD_ZONE_ID",
        "SERVICE_IDENTITY_URL",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        exit(1)

    # Initialize MCP and A2A tools before starting server
    logger.info("Initializing tools...")
    asyncio.run(initialize_tools())

    # Service configuration
    config = AgentServiceConfig(
        service_name="PR Analysis Service",
        client_id=os.getenv("KEYCARD_CLIENT_ID", "pr_analyzer_service"),
        client_secret=os.getenv("KEYCARD_CLIENT_SECRET"),
        identity_url=os.getenv("SERVICE_IDENTITY_URL"),
        zone_id=os.getenv("KEYCARD_ZONE_ID"),
        port=int(os.getenv("PORT", "8000")),
        host=os.getenv("HOST", "0.0.0.0"),
        description="Analyzes GitHub pull requests for code quality and security",
        capabilities=["pr_analysis", "code_review", "github_integration"],
        crew_factory=crew_factory_sync,
    )

    # Start service (blocking)
    logger.info("Starting PR Analysis Service...")
    logger.info(f"Service URL: {config.identity_url}")
    logger.info(f"Agent card: {config.agent_card_url}")

    serve_agent(config)


if __name__ == "__main__":
    main()
