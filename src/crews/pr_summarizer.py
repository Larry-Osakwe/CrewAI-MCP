from crewai import Agent, Crew, Task

def run_pr_summary_crew(repo: str, pr_number: int, tools: list):
    """
    Run a single-agent crew to summarize a GitHub PR.

    Args:
        repo: GitHub repository (e.g., "owner/repo")
        pr_number: Pull request number
        tools: List of Keycard-secured tools from MCP client
    """
    # Create agent with provided tools (NO TOKEN!)
    fetcher = Agent(
        role="PR Researcher",
        goal="Fetch and summarize PR information",
        backstory="You are an expert at analyzing pull requests",
        tools=tools,  # Use Keycard-secured tools
        verbose=True,
        llm="gpt-4o-mini"  # Cheaper for testing
    )

    # Create task
    task = Task(
        description=f"Fetch PR #{pr_number} from {repo} and summarize it",
        expected_output="A brief summary of the PR",
        agent=fetcher
    )

    # Create crew
    crew = Crew(
        agents=[fetcher],
        tasks=[task],
        verbose=True
    )

    # Run synchronously - tools will create their own event loops as needed
    result = crew.kickoff()
    return str(result)