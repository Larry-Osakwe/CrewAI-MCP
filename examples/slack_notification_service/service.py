"""Slack Notification Service - Phase 2A Example.

This service demonstrates a simple agent service that can be called by other services:
- Receives task delegation from other services (e.g., PR Analysis Service)
- Formats messages for Slack
- Posts to Slack via MCP tool

Architecture:
    PR Analysis Service → Slack Notification Service
      └─ Uses MCP Slack tool → Slack API

This service is typically called by other services, not directly by users.
"""

import os
import asyncio
import logging
from typing import Any

from crewai import Agent, Crew, Task
from keycardai.agents import AgentServiceConfig, serve_agent
from keycardai.mcp.client import Client as MCPClient
from keycardai.mcp.client.integrations.crewai_agents import create_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_slack_notification_crew(mcp_tools: list[Any]) -> Crew:
    """Create Slack notification crew with MCP tools.

    Args:
        mcp_tools: MCP tools for Slack access

    Returns:
        Crew instance
    """
    # Message Formatter Agent
    formatter = Agent(
        role="Message Formatter",
        goal="Format messages for Slack with proper markdown and structure",
        backstory="""You are an expert at formatting messages for Slack.
        You ensure messages are clear, well-structured, and use Slack markdown effectively.""",
        tools=[],
        verbose=True,
    )

    # Slack Poster Agent
    poster = Agent(
        role="Slack Poster",
        goal="Post formatted messages to Slack channels",
        backstory="""You are responsible for posting messages to Slack.
        You use the Slack API tools to send messages to the appropriate channels.""",
        tools=[t for t in mcp_tools if "slack" in t.name.lower()],
        verbose=True,
    )

    # Tasks
    format_task = Task(
        description="""Format the following message for Slack: {message}

        Add appropriate Slack markdown, emojis, and structure.
        Target channel: {channel}""",
        expected_output="Formatted Slack message with markdown",
        agent=formatter,
    )

    post_task = Task(
        description="""Post the formatted message to Slack channel {channel}.

        Use the Slack MCP tools to send the message.""",
        expected_output="Confirmation that message was posted",
        agent=poster,
        context=[format_task],
    )

    # Create crew
    crew = Crew(
        agents=[formatter, poster],
        tasks=[format_task, post_task],
        verbose=True,
    )

    return crew


async def crew_factory() -> Crew:
    """Factory function to create crew with tools.

    This is called by the agent service framework when handling requests.
    """
    # MCP client configuration for Slack tools
    mcp_config = {
        "slack": {
            "url": os.getenv("SLACK_MCP_SERVER_URL", "http://localhost:8002/mcp"),
        }
    }

    mcp_client = MCPClient(mcp_config)

    # Get MCP tools
    async with create_client(mcp_client) as crewai_client:
        mcp_tools = await crewai_client.get_tools()

    logger.info(f"Loaded {len(mcp_tools)} MCP tools")

    # Create and return crew
    return create_slack_notification_crew(mcp_tools)


def main():
    """Start Slack Notification Service."""
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

    # Service configuration
    config = AgentServiceConfig(
        service_name="Slack Notification Service",
        client_id=os.getenv("KEYCARD_CLIENT_ID", "slack_poster_service"),
        client_secret=os.getenv("KEYCARD_CLIENT_SECRET"),
        identity_url=os.getenv("SERVICE_IDENTITY_URL"),
        zone_id=os.getenv("KEYCARD_ZONE_ID"),
        port=int(os.getenv("PORT", "8001")),
        host=os.getenv("HOST", "0.0.0.0"),
        description="Posts notifications to Slack channels with formatting",
        capabilities=["slack_posting", "message_formatting"],
        crew_factory=lambda: asyncio.run(crew_factory()),
    )

    # Start service (blocking)
    logger.info("Starting Slack Notification Service...")
    logger.info(f"Service URL: {config.identity_url}")
    logger.info(f"Agent card: {config.agent_card_url}")

    serve_agent(config)


if __name__ == "__main__":
    main()
