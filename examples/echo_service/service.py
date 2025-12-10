"""Echo Service - Simple A2A Delegation Test Service.

This is a minimal agent service for testing Phase 2A service-to-service delegation.
It simply echoes back whatever task it receives, without any external dependencies.

Purpose:
- Test service identity and authentication
- Test token exchange (user → service)
- Test agent card discovery
- Test A2A delegation pattern

No MCP tools, no external APIs - pure delegation testing.
"""

import os
import logging

from keycardai.agents import AgentServiceConfig, serve_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def simple_echo_crew():
    """Factory function that returns a simple echo handler.

    For this test service, we don't need a full CrewAI crew.
    We'll use a simple function that echoes the input.

    Note: The agent service framework expects a crew, but for testing
    we can use a simple callable that matches the crew interface.
    """
    class SimpleEchoHandler:
        """Minimal crew-like object that echoes input."""

        def kickoff(self, inputs: dict) -> str:
            """Echo the task back to the caller.

            Args:
                inputs: Dictionary with 'task' key

            Returns:
                Echo response string
            """
            task = inputs.get("task", inputs)

            if isinstance(task, dict):
                task_str = str(task)
            else:
                task_str = str(task)

            logger.info(f"Echo Service received task: {task_str[:100]}...")

            # Simple echo response
            response = f"""Echo Service Response:

Received: {task_str}

This is a simple echo service for testing A2A delegation.
The task has been successfully received and is being echoed back.

Service: Echo Service
Status: Operational
Delegation: Working"""

            return response

    return SimpleEchoHandler()


def main():
    """Start Echo Service."""
    # Validate environment variables
    required_vars = [
        "KEYCARD_CLIENT_SECRET",
        "KEYCARD_ZONE_ID",
        "SERVICE_IDENTITY_URL",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please copy .env.example to .env and configure it")
        exit(1)

    # Service configuration
    config = AgentServiceConfig(
        service_name="Echo Service",
        client_id=os.getenv("KEYCARD_CLIENT_ID", "echo_service"),
        client_secret=os.getenv("KEYCARD_CLIENT_SECRET"),
        identity_url=os.getenv("SERVICE_IDENTITY_URL"),
        zone_id=os.getenv("KEYCARD_ZONE_ID"),
        port=int(os.getenv("PORT", "8002")),
        host=os.getenv("HOST", "0.0.0.0"),
        description="Simple echo service for testing A2A delegation",
        capabilities=["echo", "testing", "a2a_delegation"],
        crew_factory=simple_echo_crew,
    )

    # Start service (blocking)
    logger.info("=" * 60)
    logger.info("Starting Echo Service...")
    logger.info(f"Service URL: {config.identity_url}")
    logger.info(f"Agent card: {config.agent_card_url}")
    logger.info(f"Listening on {config.host}:{config.port}")
    logger.info("=" * 60)

    serve_agent(config)


if __name__ == "__main__":
    main()
