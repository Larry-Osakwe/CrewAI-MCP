from fastmcp import FastMCP, Context
import httpx
import os
from dotenv import load_dotenv
from keycardai.mcp.integrations.fastmcp import AuthProvider, ClientSecret

# Load environment variables from .env file
load_dotenv()

# Create Keycard authentication provider
auth_provider = AuthProvider(
    zone_id=os.getenv("KEYCARD_ZONE_ID"),
    mcp_server_name="CrewAI GitHub MCP Server",
    mcp_base_url=os.getenv("MCP_BASE_URL", "http://localhost:8000/"),
    application_credential=ClientSecret((
        os.getenv("KEYCARD_CLIENT_ID"),
        os.getenv("KEYCARD_CLIENT_SECRET")
    ))
)

# Get RemoteAuthProvider for FastMCP
auth = auth_provider.get_remote_auth_provider()

# Initialize MCP server WITH auth passed to constructor
mcp = FastMCP("CrewAI GitHub Demo", auth=auth)

# ============================================================================
# UNAUTHENTICATED TOOL (just for testing server is running)
# ============================================================================

@mcp.tool(name="echo", description="Echo test tool")
async def echo_tool(ctx: Context, message: str) -> str:
    return f"Echo: {message}"

# ============================================================================
# EXISTING TOOLS (keeping them for now)
# ============================================================================

@mcp.tool(name="fetch_pr_simple", description="Fetch PR (no auth)")
async def fetch_pr_simple(ctx: Context, repo: str, pr_number: int) -> dict:
    # Use public GitHub API (no auth required for public repos)
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "title": data.get("title"),
                "state": data.get("state"),
                "user": data.get("user", {}).get("login")
            }
        return {"error": f"Status {response.status_code}"}

@mcp.tool(name="summarize_pr", description="Summarize a GitHub PR using AI")
@auth_provider.grant("https://api.github.com")
async def summarize_pr_tool(ctx: Context, repo: str, pr_number: int) -> str:
    from .crews.pr_summarizer import run_pr_summary_crew

    try:
        # Get delegated GitHub token from Keycard
        github_token = ctx.get_state("keycardai").access("https://api.github.com").access_token

        result = run_pr_summary_crew(repo, pr_number, github_token=github_token)
        return result
    except Exception as e:
        return f"Error: {str(e)}"

# ============================================================================
# CREATE APP
# ============================================================================

# Create ASGI app using FastMCP's standard method
# The auth was already passed to FastMCP constructor above
app = mcp.http_app()
