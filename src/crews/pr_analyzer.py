from crewai import Agent, Crew, Task
from ..tools.github_tools import create_github_tools

def run_pr_analysis_crew(repo: str, pr_number: int, github_token: str):
    """
    Multi-agent crew where MULTIPLE agents can independently call GitHub API.

    All agents share the same set of GitHub tools with the delegated token.
    This allows each agent to fetch the specific data they need.

    Workflow:
    1. Overview Agent: Gets high-level PR info
    2. Code Reviewer: Deep dives into file changes
    3. Community Analyst: Analyzes comments/discussion
    4. Summarizer: Synthesizes everything into executive summary

    All agents 1-3 can make independent GitHub API calls!
    """

    # Create tools once, share across all agents
    github_tools = create_github_tools(github_token)

    # Agent 1: PR Overview Specialist
    overview_agent = Agent(
        role="PR Overview Specialist",
        goal="Fetch and summarize high-level PR information",
        backstory="Expert at quickly understanding PR scope, purpose, and overall structure",
        tools=github_tools,  # Has access to ALL GitHub tools
        verbose=True,
        llm="gpt-4o-mini"
    )

    # Agent 2: Senior Code Reviewer
    code_reviewer = Agent(
        role="Senior Code Reviewer",
        goal="Analyze code changes in detail, focusing on quality, security, and best practices",
        backstory="Senior engineer with 10+ years experience in code review. Knows common pitfalls and anti-patterns.",
        tools=github_tools,  # Has access to ALL GitHub tools
        verbose=True,
        llm="gpt-4o"  # More powerful for deep analysis
    )

    # Agent 3: Community Engagement Analyst
    community_analyst = Agent(
        role="Community Engagement Analyst",
        goal="Analyze PR comments, review feedback, and community discussion",
        backstory="Expert at understanding team dynamics, identifying consensus, and surfacing concerns from code reviews",
        tools=github_tools,  # Has access to ALL GitHub tools
        verbose=True,
        llm="gpt-4o-mini"
    )

    # Agent 4: Executive Summarizer
    summarizer = Agent(
        role="Technical Writer",
        goal="Create clear executive summary from all analyses",
        backstory="Skilled technical writer who distills complex technical information into actionable insights for stakeholders",
        tools=[],  # Doesn't need GitHub tools, works from other agents' outputs
        verbose=True,
        llm="gpt-4o-mini"
    )

    # Task 1: Get PR Overview
    overview_task = Task(
        description=f"""Fetch PR #{pr_number} from repository {repo} and provide a comprehensive overview.

Use the fetch_pr tool to get:
- Title and description
- Author and state
- Statistics (files, additions, deletions, commits)
- Overall purpose and scope
""",
        expected_output="Complete PR overview with title, description, author, state, and statistics",
        agent=overview_agent
    )

    # Task 2: Analyze Code Changes
    code_review_task = Task(
        description=f"""Perform a detailed code review of PR #{pr_number} from repository {repo}.

Repository: {repo}
PR Number: {pr_number}

Use fetch_pr_files to examine:
- What files changed
- Code diffs and modifications
- Patterns in the changes

Identify:
1. Key technical changes and their purpose
2. Code quality observations
3. Potential bugs or issues
4. Security considerations
5. Best practice violations

Provide specific, actionable feedback.""",
        expected_output="Technical code review with specific concerns, observations, and recommendations",
        agent=code_reviewer,
        context=[]  # No context needed! Agent calls GitHub API directly
    )

    # Task 3: Analyze Community Discussion
    community_task = Task(
        description=f"""Analyze the discussion and feedback on PR #{pr_number} from repository {repo}.

Repository: {repo}
PR Number: {pr_number}

Use fetch_pr_comments to examine:
- Review comments
- Discussion threads
- Feedback from team members

Identify:
1. Main concerns raised by reviewers
2. Points of consensus
3. Unresolved questions or debates
4. Overall community sentiment

Summarize the discussion dynamics.""",
        expected_output="Summary of community feedback, concerns raised, and discussion sentiment",
        agent=community_analyst,
        context=[]  # No context needed! Agent calls GitHub API directly
    )

    # Task 4: Create Executive Summary
    summary_task = Task(
        description="""Synthesize all analyses into a comprehensive executive summary.

Combine insights from:
- PR overview (scope and purpose)
- Code review (technical quality)
- Community discussion (team feedback)

Create a summary that includes:
1. What changed and why (2-3 sentences)
2. Code quality assessment
3. Key concerns or risks identified
4. Community sentiment
5. Clear recommendation: Approve / Request Changes / Needs Discussion
6. Reasoning for recommendation

Make it suitable for non-technical stakeholders.""",
        expected_output="Executive summary (3-5 paragraphs) with clear recommendation and reasoning",
        agent=summarizer,
        context=[overview_task, code_review_task, community_task]  # Gets all outputs
    )

    # Create crew
    crew = Crew(
        agents=[overview_agent, code_reviewer, community_analyst, summarizer],
        tasks=[overview_task, code_review_task, community_task, summary_task],
        verbose=True
    )

    result = crew.kickoff()
    return str(result)
