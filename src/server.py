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

@mcp.tool(name="fetch_pr_simple", description="Fetch PR from GitHub (no auth required). Parameters: repo (string, e.g. 'owner/repo'), pr_number (integer)")
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

@mcp.tool(
    name="fetch_pr_authenticated",
    description="Fetch PR from GitHub with authentication (works for private repos). Parameters: repo (string, e.g. 'owner/repo'), pr_number (integer)"
)
@auth_provider.grant("https://api.github.com")
async def fetch_pr_authenticated(ctx: Context, repo: str, pr_number: int) -> dict:
    """Fetch PR details using user's GitHub token (supports private repos)."""
    # Get the exchanged GitHub token
    access_context = ctx.get_state("keycardai")

    # Check if context was set at all
    if access_context is None:
        return {
            "error": "Authentication context not available",
            "details": "The grant decorator did not inject the auth context. Check: 1) User is authenticated, 2) KEYCARD_* env vars are set, 3) Enable KEYCARD_LOG_LEVEL=DEBUG for more info",
            "isError": True
        }

    # Check if there were errors during token exchange
    if access_context.has_errors():
        return {
            "error": "Authentication failed",
            "details": access_context.get_errors(),
            "isError": True
        }

    # Wrap token access in try-catch
    try:
        token = access_context.access("https://api.github.com").access_token
    except Exception as e:
        return {
            "error": "Failed to access GitHub token",
            "details": str(e),
            "isError": True
        }

    # Use authenticated GitHub API
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Safely extract nested fields (handle null values)
            user = data.get("user") or {}
            base = data.get("base") or {}
            repo = base.get("repo") or {}

            return {
                "title": data.get("title"),
                "state": data.get("state"),
                "user": user.get("login"),
                "body": (data.get("body") or "")[:500],  # First 500 chars of description
                "private": repo.get("private", False),
                "url": data.get("html_url"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at")
            }
    except httpx.HTTPStatusError as e:
        error_body = e.response.text if hasattr(e.response, 'text') else str(e)
        return {
            "error": f"GitHub API error: {e.response.status_code}",
            "message": (error_body or "")[:200],  # First 200 chars of error
            "isError": True
        }
    except Exception as e:
        return {"error": str(e), "isError": True}

@mcp.tool(
    name="test_auth_state",
    description="Diagnostic tool to test if authentication state is working"
)
@auth_provider.grant("https://api.github.com")
async def test_auth_state(ctx: Context) -> dict:
    """Diagnostic tool to verify auth context injection and token retrieval."""
    access_context = ctx.get_state("keycardai")

    # Check 1: Is context set at all?
    if access_context is None:
        return {
            "status": "FAIL",
            "message": "AccessContext is None - decorator did not inject state",
            "possible_causes": [
                "User not authenticated with Keycard",
                "KEYCARD_ZONE_ID, KEYCARD_CLIENT_ID, or KEYCARD_CLIENT_SECRET not set",
                "Token exchange failed silently"
            ],
            "debug_tip": "Set KEYCARD_LOG_LEVEL=DEBUG in environment and restart server"
        }

    # Check 2: Were there errors during token exchange?
    if access_context.has_errors():
        return {
            "status": "ERROR",
            "message": "Token exchange failed",
            "errors": access_context.get_errors()
        }

    # Check 3: Can we access the GitHub token?
    try:
        token_response = access_context.access("https://api.github.com")
        token = token_response.access_token

        return {
            "status": "SUCCESS",
            "message": "Auth context working correctly!",
            "token_length": len(token),
            "token_type": token_response.token_type,
            "token_preview": f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "***"
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Failed to access token: {e}",
            "exception_type": type(e).__name__
        }

@mcp.tool(name="test_github_token", description="Test GitHub token and permissions (works for OAuth and GitHub Apps)")
@auth_provider.grant("https://api.github.com")
async def test_github_token(ctx: Context) -> str:
    """Diagnostic tool to test GitHub token permissions for both OAuth Apps and GitHub Apps."""
    try:
        access_context = ctx.get_state("keycardai")

        if access_context.has_errors():
            return f"❌ Token exchange failed: {access_context.get_errors()}"

        token = access_context.access("https://api.github.com").access_token

        if not token:
            return "❌ No token received from Keycard"

        async with httpx.AsyncClient() as client:
            # Test 1: Get authenticated user/app
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

            # Test 2: Check if this is a GitHub App token
            is_bot = user_data.get("type") == "Bot"
            oauth_scopes = user_response.headers.get("X-OAuth-Scopes", "")

            # Test 3: Check accessible repositories
            # Use different endpoint based on token type
            if not oauth_scopes:
                # GitHub App token (user access token or installation token)
                if is_bot:
                    # Installation token: use /installation/repositories
                    repos_response = await client.get(
                        "https://api.github.com/installation/repositories",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json"
                        }
                    )
                    token_type = "Installation Access Token"
                else:
                    # User access token: use /user/repos
                    repos_response = await client.get(
                        "https://api.github.com/user/repos",
                        params={
                            "affiliation": "owner,collaborator,organization_member",
                            "per_page": 100
                        },
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github+json"
                        }
                    )
                    token_type = "User Access Token"

                if repos_response.status_code == 200:
                    repos_data = repos_response.json()

                    # Handle different response formats
                    if isinstance(repos_data, dict) and "total_count" in repos_data:
                        # /installation/repositories format
                        repo_count = repos_data["total_count"]
                        repo_names = [r["full_name"] for r in repos_data.get("repositories", [])[:5]]
                    else:
                        # /user/repos format (array)
                        repo_count = len(repos_data)
                        repo_names = [r["full_name"] for r in repos_data[:5]]

                    return f"""✅ GitHub App token works!

Token Type: GitHub App {token_type}
Authenticated as: {username}{"  (Bot)" if is_bot else ""}
Token length: {len(token)} chars
Accessible repositories: {repo_count}

Sample repos:
{chr(10).join(f"  - {name}" for name in repo_names) if repo_names else "  (none)"}

Note: GitHub Apps use permissions (not OAuth scopes).
Empty X-OAuth-Scopes header is EXPECTED for GitHub Apps.

{"This is a user access token - it acts on your behalf with the intersection of your permissions and the app's permissions." if not is_bot else "This is an installation token - it acts as the app itself."}
"""
                else:
                    return f"""⚠️ GitHub App token valid but can't list repositories

Authenticated as: {username}
Token Type: {token_type}
Error: {repos_response.status_code} - {repos_response.text}

This usually means:
1. GitHub App doesn't have required permissions configured
2. GitHub App isn't installed on any repositories
3. Token doesn't have access to any repos

Fix:
- Verify app has 'Contents: Read' permission in GitHub App settings
- Ensure app is installed on your repositories
- Check installation configuration includes target repositories
"""

            # OAuth App token (has X-OAuth-Scopes)
            return f"""✅ OAuth App token works!

Token Type: OAuth App Token
Authenticated as: {username}
Token scopes: {oauth_scopes}
Token length: {len(token)} chars

To access private repos, you need the 'repo' scope.
Current scopes: {oauth_scopes}
"""

    except Exception as e:
        import traceback
        return f"❌ Error testing token: {str(e)}\n\n{traceback.format_exc()}"

# ============================================================================
# NOTE: Crew-wrapping tools removed - crews should run client-side!
# ============================================================================
#
# The analyze_pr and summarize_pr tools have been removed because they:
# 1. Passed tokens directly to agents (security concern)
# 2. Mixed concerns (MCP server should provide tools, not run agents)
# 3. Prevented proper Keycard authorization on each tool call
#
# To run crews with Keycard-secured tools, use:
#   python test_with_keycard.py
#
# Or integrate with keycardai-agents package:
#   from keycardai.agents.crewai_agents import create_client
#   async with create_client(mcp_client) as client:
#       tools = await client.get_tools()
#       result = run_pr_analysis_crew(repo, pr, tools)
#
# ============================================================================

# ============================================================================
# CREATE APP
# ============================================================================

# Create ASGI app using FastMCP's standard method
# The auth was already passed to FastMCP constructor above
app = mcp.http_app()
