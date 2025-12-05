"""
Test script to understand session-level vs tool-level auth in FastMCP.

This script creates two server configurations:
1. WITH session-level auth (auth=auth passed to FastMCP constructor)
2. WITHOUT session-level auth (no auth passed to FastMCP constructor)

Both have the same tool decorated with @auth_provider.grant()
"""

from fastmcp import FastMCP, Context
from keycardai.mcp.integrations.fastmcp import AuthProvider, ClientSecret
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# SCENARIO 1: WITH SESSION-LEVEL AUTH
# ============================================================================

print("\n" + "="*80)
print("SCENARIO 1: WITH SESSION-LEVEL AUTH")
print("="*80)

auth_provider_1 = AuthProvider(
    zone_id=os.getenv("KEYCARD_ZONE_ID"),
    mcp_server_name="Test Server With Session Auth",
    mcp_base_url=os.getenv("MCP_BASE_URL", "http://localhost:8000/"),
    application_credential=ClientSecret((
        os.getenv("KEYCARD_CLIENT_ID"),
        os.getenv("KEYCARD_CLIENT_SECRET")
    ))
)

# Get RemoteAuthProvider and pass to FastMCP
auth = auth_provider_1.get_remote_auth_provider()
mcp_with_session_auth = FastMCP("Server With Session Auth", auth=auth)

@mcp_with_session_auth.tool(name="secure_tool_1")
@auth_provider_1.grant("https://api.github.com")
async def secure_tool_1(ctx: Context) -> dict:
    """Tool with @grant decorator on server WITH session auth."""
    access_context = ctx.get_state("keycardai")
    if access_context is None:
        return {"error": "No auth context"}
    if access_context.has_errors():
        return {"error": access_context.get_errors()}
    token = access_context.access("https://api.github.com").access_token
    return {"status": "success", "has_token": bool(token)}

print("✓ Created server WITH session-level auth")
print(f"  - FastMCP constructor received: auth={auth}")
print(f"  - Tool decorated with: @auth_provider.grant()")
print(f"  - Expected behavior: 401 on initialize if not authenticated")

# ============================================================================
# SCENARIO 2: WITHOUT SESSION-LEVEL AUTH
# ============================================================================

print("\n" + "="*80)
print("SCENARIO 2: WITHOUT SESSION-LEVEL AUTH")
print("="*80)

auth_provider_2 = AuthProvider(
    zone_id=os.getenv("KEYCARD_ZONE_ID"),
    mcp_server_name="Test Server Without Session Auth",
    mcp_base_url=os.getenv("MCP_BASE_URL", "http://localhost:8001/"),  # Different port
    application_credential=ClientSecret((
        os.getenv("KEYCARD_CLIENT_ID"),
        os.getenv("KEYCARD_CLIENT_SECRET")
    ))
)

# DO NOT pass auth to FastMCP
mcp_without_session_auth = FastMCP("Server Without Session Auth")  # No auth parameter!

@mcp_without_session_auth.tool(name="secure_tool_2")
@auth_provider_2.grant("https://api.github.com")
async def secure_tool_2(ctx: Context) -> dict:
    """Tool with @grant decorator on server WITHOUT session auth."""
    access_context = ctx.get_state("keycardai")
    if access_context is None:
        return {"error": "No auth context"}
    if access_context.has_errors():
        return {"error": access_context.get_errors()}
    token = access_context.access("https://api.github.com").access_token
    return {"status": "success", "has_token": bool(token)}

print("✓ Created server WITHOUT session-level auth")
print(f"  - FastMCP constructor received: auth=None (not passed)")
print(f"  - Tool decorated with: @auth_provider.grant()")
print(f"  - Expected behavior: ??? (this is what we're testing!)")

# ============================================================================
# COMPARISON
# ============================================================================

print("\n" + "="*80)
print("KEY DIFFERENCES")
print("="*80)

print("""
SCENARIO 1 (WITH session auth):
  FastMCP.__init__(..., auth=auth)
  ├─ MCP server requires authentication on initialize
  ├─ Returns 401 if no token provided
  ├─ WWW-Authenticate header points to resource metadata
  ├─ @auth_provider.grant() can perform token exchange
  └─ ctx.get_state("keycardai") will have access_context

SCENARIO 2 (WITHOUT session auth):
  FastMCP.__init__(...)  # No auth parameter
  ├─ MCP server does NOT require authentication on initialize
  ├─ Returns 200 OK on initialize (no 401)
  ├─ No WWW-Authenticate header
  ├─ @auth_provider.grant() decorator still present on tool
  └─ QUESTION: Will ctx.get_state("keycardai") work?

THE QUESTION:
  Can @auth_provider.grant() establish a security layer
  even if the MCP session itself is unauthenticated?

  In other words:
  - Session-level auth = Required authentication BEFORE any tools can be called
  - Tool-level auth = Required authentication WHEN that specific tool is called

  Can you have tool-level auth without session-level auth?
""")

print("\n" + "="*80)
print("HYPOTHESIS")
print("="*80)

print("""
HYPOTHESIS 1: @auth_provider.grant() REQUIRES session-level auth
  - The grant decorator relies on the session's auth context
  - Without auth=auth in FastMCP(), there's no auth context
  - ctx.get_state("keycardai") will return None
  - Tool will fail with "No auth context" error

HYPOTHESIS 2: @auth_provider.grant() WORKS INDEPENDENTLY
  - The grant decorator creates its own auth flow
  - It can work even without session-level auth
  - When tool is called, decorator initiates token exchange
  - ctx.get_state("keycardai") will have access_context

HYPOTHESIS 3: Mixed Mode - Lazy Authentication
  - Without session auth, server accepts all connections
  - Tools with @grant decorator require auth when called
  - First call to decorated tool triggers auth flow
  - Subsequent calls use cached token

To test this, we need to:
1. Start both servers
2. Try to call tools without authentication
3. Observe what happens in each scenario
""")

print("\n" + "="*80)
print("TO TEST THIS:")
print("="*80)
print("""
1. Run scenario 1 server:
   uvicorn test_auth_scenarios:mcp_with_session_auth --port 8000

2. Run scenario 2 server:
   uvicorn test_auth_scenarios:mcp_without_session_auth --port 8001

3. Try to connect with MCP client to both

4. Observe:
   - Does server 1 return 401 on initialize?
   - Does server 2 return 200 on initialize?
   - Can you call tools on server 2 without auth?
   - What happens when you call secure_tool_2 without auth?
""")
