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

@mcp.tool(name="test_github_token", description="Test GitHub token and permissions (diagnostic tool)")
@auth_provider.grant("https://api.github.com")
async def test_github_token(ctx: Context) -> str:
    """Diagnostic tool to test GitHub token permissions."""
    try:
        access_context = ctx.get_state("keycardai")

        if access_context.has_errors():
            return f"❌ Token exchange failed: {access_context.get_errors()}"

        token = access_context.access("https://api.github.com").access_token

        if not token:
            return "❌ No token received from Keycard"

        # Test token against GitHub API
        async with httpx.AsyncClient() as client:
            # Test 1: Get authenticated user
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )

            if user_response.status_code != 200:
                return f"❌ Token invalid: {user_response.status_code} - {user_response.text}"

            user_data = user_response.json()
            username = user_data.get("login")

            # Test 2: Check token scopes
            scopes = user_response.headers.get("X-OAuth-Scopes", "none")

            return f"""✅ GitHub token works!

Authenticated as: {username}
Token scopes: {scopes}
Token length: {len(token)} chars

To access private repos, you need the 'repo' scope.
Current scopes: {scopes}
"""
    except Exception as e:
        import traceback
        return f"❌ Error testing token: {str(e)}\n\n{traceback.format_exc()}"

@mcp.tool(name="summarize_pr", description="Summarize a GitHub PR using AI")
@auth_provider.grant("https://api.github.com")
async def summarize_pr_tool(ctx: Context, repo: str, pr_number: int) -> str:
    from .crews.pr_summarizer import run_pr_summary_crew

    try:
        # Get access context
        access_context = ctx.get_state("keycardai")

        # CHECK: Did token exchange fail?
        if access_context.has_errors():
            errors = access_context.get_errors()
            return f"❌ Token exchange failed: {errors}"

        # Get GitHub token
        github_access = access_context.access("https://api.github.com")
        github_token = github_access.access_token

        # CHECK: Did we actually get a token?
        if not github_token:
            return f"❌ No GitHub token received from Keycard. Provider may not be configured."

        # Log token info (first/last 4 chars only for security)
        token_preview = f"{github_token[:4]}...{github_token[-4:]}" if len(github_token) > 8 else "***"
        print(f"[DEBUG] Got GitHub token: {token_preview}, length: {len(github_token)}")

        # Call crew
        result = run_pr_summary_crew(repo, pr_number, github_token=github_token)
        return result

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error: {str(e)}\n\nDetails:\n{error_details}"

# ============================================================================
# CREATE APP
# ============================================================================

# Create ASGI app using FastMCP's standard method
# The auth was already passed to FastMCP constructor above
app = mcp.http_app()
