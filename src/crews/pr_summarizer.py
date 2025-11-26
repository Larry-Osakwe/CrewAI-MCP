from crewai import Agent, Crew, Task
from tools.github_tools import FetchPRTool

def run_pr_summary_crew(repo: str, pr_number: int, github_token: str | None = None):
    # Create tool
    fetch_tool = FetchPRTool(github_token=github_token)

    # Create agent
    fetcher = Agent(
        role="PR Researcher",
        goal="Fetch and summarize PR information",
        backstory="You are an expert at analyzing pull requests",
        tools=[fetch_tool],
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

    # Run
    result = crew.kickoff()
    return str(result)