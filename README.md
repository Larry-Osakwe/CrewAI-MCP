# CrewAI GitHub MCP Server - Phase 1

**Client-side AI agents with secure, auditable API access via MCP tools**

This repository demonstrates **Phase 1** of the Keycard + MCP + CrewAI integration: portable, client-side crews that use MCP tools for secure, per-call authenticated access to GitHub APIs.

## What This Is

An MCP server that exposes GitHub API tools secured by Keycard authentication. CrewAI agents run **client-side** and autonomously choose which tools to use, while Keycard handles all authentication transparently.

### Key Innovation

**Two-Layer Authentication Model:**

1. **Session-level auth** (upfront): User authenticates to establish MCP session
2. **Tool-level token exchange** (per-call): User token → GitHub token on each tool invocation

This architecture ensures:
- ✅ Agents never see or handle tokens
- ✅ Fresh tokens per API call
- ✅ Full audit trail (user → tool → API)
- ✅ Portable crews (run anywhere)

## Architecture

```
┌─────────────────────────────────────────────┐
│ Your Application (tests/test_crew_with_auth.py) │
│                                             │
│  CrewAI Crew (Client-Side)                 │
│    ├─ Agent 1: PR Overview Specialist      │
│    ├─ Agent 2: Code Reviewer               │
│    ├─ Agent 3: Community Analyst           │
│    └─ Agent 4: Summarizer                  │
│                                             │
│  Each agent has access to MCP tools        │
└─────────────────────────────────────────────┘
              ↓ calls tools via
┌─────────────────────────────────────────────┐
│ keycardai-mcp Client                        │
│  (MCPToolWrapper bridges CrewAI ↔ MCP)      │
└─────────────────────────────────────────────┘
              ↓ JSON-RPC over HTTP
┌─────────────────────────────────────────────┐
│ MCP Server (src/server.py)                  │
│                                             │
│  Tools:                                     │
│    • fetch_pr_simple (no auth)             │
│    • fetch_pr_authenticated (@grant)       │
│    • test_auth_state (@grant)              │
│                                             │
│  @auth_provider.grant() decorator:         │
│    - Intercepts tool call                  │
│    - Exchanges user token → GitHub token   │
│    - Injects into tool context             │
└─────────────────────────────────────────────┘
              ↓ per-call token exchange
┌─────────────────────────────────────────────┐
│ Keycard (Authentication Broker)             │
│  • User OAuth session                       │
│  • GitHub App token exchange                │
│  • Audit logging                            │
└─────────────────────────────────────────────┘
              ↓ delegated credentials
┌─────────────────────────────────────────────┐
│ GitHub API                                   │
│  • Authenticated as user                    │
│  • Scoped permissions                       │
└─────────────────────────────────────────────┘
```

## How It Works

### The Authentication Flow

**Step 1: Session Authentication (Upfront)**

When you run `async with create_client(mcp_client)`:
1. Client sends MCP `initialize` handshake
2. Server responds with `401 Unauthorized` (requires session auth)
3. Browser opens for OAuth consent
4. User authenticates via Keycard
5. Session established with user token cached

**Step 2: Tool-Level Token Exchange (Per-Call)**

When an agent calls `fetch_pr_authenticated(repo, pr_number)`:
1. MCPToolWrapper sends tool call to MCP server
2. `@auth_provider.grant("https://api.github.com")` decorator intercepts
3. Extracts user's session token from context
4. Calls Keycard to exchange user token → GitHub token
5. Injects GitHub token into tool execution context
6. Tool calls GitHub API with fresh token
7. Token discarded after call completes

### Agent Autonomy

The test output shows the agent **reasoning through authentication**:

```
Agent tries: fetch_pr_simple (unauthenticated)
    → 404 (private repo)

Agent decides: Let me check if auth is available
    → Calls test_auth_state
    → SUCCESS

Agent escalates: Now I'll use authenticated tool
    → Calls fetch_pr_authenticated
    → SUCCESS with full PR data
```

**No hardcoded logic** - the agent reads tool descriptions and adapts its strategy based on errors.

## Quick Start

### Prerequisites

- Python 3.10+
- Keycard account with GitHub App configured
- OpenAI API key (for agent LLM)

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

**Required variables:**
- `KEYCARD_ZONE_ID` - Your Keycard zone ID
- `KEYCARD_CLIENT_ID` - OAuth client ID for MCP server
- `KEYCARD_CLIENT_SECRET` - OAuth client secret
- `MCP_BASE_URL` - Public URL where MCP server is accessible (use Cloudflare tunnel for local dev)
- `OPENAI_API_KEY` - For CrewAI agent LLM

### 3. Run the MCP Server

```bash
./run_server_local.sh
```

This starts:
- MCP server on port 8000
- Cloudflare tunnel (exposes to public URL)
- Server logs visible

### 4. Run the Demo

In a new terminal:

```bash
source venv/bin/activate
python tests/test_crew_with_auth.py
```

**What happens:**
1. Browser opens for OAuth consent (session auth)
2. Authorize via Keycard
3. Agent autonomously chooses tools
4. Agent successfully fetches PR from private repo
5. Crew produces summary

## Key Files

### Core Implementation

- **[src/server.py](src/server.py)** - MCP server with Keycard-secured tools
  - Uses FastMCP framework
  - `@auth_provider.grant()` decorator for tool-level auth
  - Mix of authenticated and unauthenticated tools

- **[src/crews/pr_analyzer.py](src/crews/pr_analyzer.py)** - Multi-agent crew
  - 4 agents with different personas
  - All agents can independently call GitHub API
  - Demonstrates parallel authenticated tool usage

### Tests & Examples

- **[tests/test_crew_with_auth.py](tests/test_crew_with_auth.py)** - Main demo
  - Shows agent autonomy (choosing tools, handling failures)
  - Validates end-to-end auth flow
  - Best reference for integration pattern

- **[tests/test_with_local_server.py](tests/test_with_local_server.py)** - Basic connectivity
  - Tests MCP server connection
  - Validates tool listing
  - Useful for debugging server issues

- **[tests/test_auth_scenarios.py](tests/test_auth_scenarios.py)** - Auth architecture docs
  - Explains session-level vs tool-level auth
  - Code examples of both patterns
  - Reference for understanding auth flow

## Testing

### Run the Full Integration Test

```bash
# Terminal 1: Start server
./run_server_local.sh

# Terminal 2: Run test
source venv/bin/activate
python tests/test_crew_with_auth.py
```

**Expected output:**
1. Connection to MCP server succeeds
2. Browser opens for Keycard OAuth
3. After authorization, agent starts
4. Agent tries unauthenticated tool → 404
5. Agent tests auth state → SUCCESS
6. Agent uses authenticated tool → Full PR data
7. Crew produces summary

### Test Individual Components

```bash
# Test server connectivity only
python tests/test_with_local_server.py

# Review auth architecture patterns
python tests/test_auth_scenarios.py
```

## Phase Comparison

### Phase 0 (Monolithic, on `main` branch)

```
MCP Server contains entire crew
  ↓
Token passed to crew on startup
  ↓
All agents share same token
  ↓
Crew logic tied to server deployment
```

**Problems:**
- Crew not portable (embedded in server)
- Token shared across all agents
- Poor audit trail (session-level only)
- Can't reuse crew elsewhere

### Phase 1 (Current, this branch)

```
Crew runs client-side
  ↓
Crew uses MCP tools (no tokens!)
  ↓
Fresh token per tool call
  ↓
Portable, reusable agents
```

**Improvements:**
- ✅ Crews are portable Python code
- ✅ No tokens passed to agents
- ✅ Per-call authorization & audit
- ✅ Framework agnostic (works with LangChain, AutoGPT, etc.)

## Security Model

### What Agents Can't Do

- ❌ See or cache tokens
- ❌ Call APIs directly (must use MCP tools)
- ❌ Bypass authorization checks
- ❌ Access resources without user consent

### What Keycard Provides

- ✅ User attribution (every call tied to user identity)
- ✅ Audit trail (who, what, when, where)
- ✅ Token exchange (user token → resource tokens)
- ✅ OAuth consent flow management
- ✅ Fresh tokens per call (no staleness)

### Audit Trail

Every tool call is logged:
- **User**: Identity from OAuth session
- **Tool**: `fetch_pr_authenticated`
- **Arguments**: `{"repo": "owner/repo", "pr_number": 1}`
- **Resource**: `https://api.github.com`
- **Result**: Success/failure
- **Timestamp**: When it occurred

## Troubleshooting

### "Authorization timed out after 300s"

**Cause:** You didn't complete OAuth consent within 5 minutes.

**Solution:** Re-run the test and complete authorization promptly.

### "No authentication token available"

**Cause:** Session-level auth not configured or failed.

**Solution:**
1. Check that `auth=auth` is passed to `FastMCP()` constructor
2. Verify `KEYCARD_*` environment variables are set
3. Check server logs for token exchange errors

### Tools return 404 for private repos

**Cause:** Using unauthenticated tool (`fetch_pr_simple`) for private repo.

**Solution:** The agent should automatically escalate to `fetch_pr_authenticated`. If not, check tool descriptions and agent prompts.

### "Connection refused" or server not reachable

**Cause:** MCP server not running or wrong URL.

**Solution:**
1. Start server: `./run_server_local.sh`
2. Check `MCP_BASE_URL` in `.env` matches tunnel URL
3. Verify tunnel is active (look for Cloudflare URL in server logs)

## Contributing

This is Phase 1 of the Keycard agent integration roadmap. Phase 2 will add:
- Service-to-service delegation (crews calling crews)
- Agent identity (not just user attribution)
- Cross-service auth chains

## License

MIT

## Related Projects

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [CrewAI](https://github.com/joaomdmoura/crewAI) - Multi-agent orchestration
- [Keycard](https://keycard.com) - Authentication broker for AI agents
- [MCP Specification](https://spec.modelcontextprotocol.io/) - Model Context Protocol

---

**Questions?** Open an issue or check [tests/test_auth_scenarios.py](tests/test_auth_scenarios.py) for detailed auth flow documentation.
