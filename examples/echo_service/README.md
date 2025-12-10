# Echo Service - A2A Delegation Test Service

Minimal agent service for testing Phase 2A service-to-service delegation without external dependencies.

## Purpose

This service is intentionally simple to isolate and test the core A2A delegation pattern:
- ✅ Service identity and authentication
- ✅ Token exchange (user → echo_service)
- ✅ Agent card discovery
- ✅ Service-to-service invocation
- ✅ Delegation chain tracking

**No MCP tools, no external APIs** - just pure delegation mechanics.

## Architecture

```
PR Analysis Service → Echo Service
  └─ Receives task
  └─ Returns "Echo: {task}"
```

**Delegation Chain:** `user → pr_analyzer_service → echo_service`

## Installation

```bash
# Install dependencies
pip install keycardai-agents

# Copy environment template
cp .env.example .env

# Edit .env with your Keycard credentials
```

## Configuration

### Keycard Setup

1. **Create Application for Echo Service:**
```
Name: Echo Service
Identifier: echo_service
Description: Simple echo service for A2A testing
URL: https://echo-service-[your-app].onrender.com
```

Save the `client_secret` for your `.env` file.

2. **Create Resource provided by Echo Service:**
```
Name: Echo Service API
Identifier: https://echo-service-[your-app].onrender.com
Provided by Application: Echo Service
Credential Provider: Zone Provider (Keycard STS)
Scopes: ["invoke"]
```

3. **Configure Dependency** (for PR Analysis Service to call this):
```
Application: PR Analysis Service
Resource: Echo Service API
Permissions: [invoke]
```

### Environment Variables

Edit `.env` with:
- `KEYCARD_ZONE_ID`: Your Keycard zone ID
- `KEYCARD_CLIENT_ID`: Application client ID (usually `echo_service`)
- `KEYCARD_CLIENT_SECRET`: Application client secret from Keycard
- `SERVICE_IDENTITY_URL`: Public URL where this service is accessible
- `PORT`: HTTP port (default: 8002)

## Running Locally

```bash
python service.py
```

Service starts on `http://localhost:8002`

### Test Endpoints

**Agent Card (public):**
```bash
curl http://localhost:8002/.well-known/agent-card.json
```

**Status Check (public):**
```bash
curl http://localhost:8002/status
```

**Invoke (protected - requires token):**
```bash
curl -X POST http://localhost:8002/invoke \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Test message from PR Analysis Service"
  }'
```

## Deployment

### Render Deployment

1. **Create Web Service** on Render
2. **Connect Repository:**
   - Repository: `keycard` (or your fork)
   - Root Directory: `crewai-github-mcp-server/examples/echo_service`
3. **Configure Build:**
   - Build Command: `pip install keycardai-agents`
   - Start Command: `python service.py`
4. **Set Environment Variables:**
   - Copy all variables from `.env.example`
   - Set `SERVICE_IDENTITY_URL` to your Render URL
   - Add `KEYCARD_CLIENT_SECRET` from Keycard
5. **Deploy**

After deployment, update Keycard:
- Application URL: `https://echo-service-[app-name].onrender.com`
- Resource Identifier: Same URL

### Railway/Vercel

Similar steps - ensure:
- Python 3.10+ runtime
- Install `keycardai-agents` package
- Set environment variables
- Use public URL as `SERVICE_IDENTITY_URL`

## How It Works

### 1. Service Initialization
```python
config = AgentServiceConfig(
    service_name="Echo Service",
    client_id="echo_service",
    client_secret=os.getenv("KEYCARD_CLIENT_SECRET"),
    identity_url="https://echo-service.example.com",
    zone_id="xr9r33ga15...",
    capabilities=["echo", "testing", "a2a_delegation"],
)

serve_agent(config)  # Starts FastAPI server
```

### 2. Agent Card Published
GET `/.well-known/agent-card.json` returns:
```json
{
  "name": "Echo Service",
  "description": "Simple echo service for testing A2A delegation",
  "capabilities": ["echo", "testing", "a2a_delegation"],
  "endpoints": {
    "invoke": "https://echo-service.example.com/invoke"
  },
  "auth": {
    "type": "oauth2",
    "token_url": "https://xr9r33ga15.keycard.cloud/oauth/token",
    "resource": "https://echo-service.example.com"
  }
}
```

### 3. Invocation Flow (from PR Analyzer)
```
PR Analysis Service wants to call Echo Service:

1. PR Analyzer calls: delegate_to_echo_service("Task summary")

2. A2A Client:
   - Discovers Echo Service (fetches agent card)
   - Gets delegation token from Keycard:
     * Input: pr_analyzer's token
     * Resource: https://echo-service.example.com
     * Output: Token scoped to Echo Service

3. HTTP POST to Echo Service:
   POST https://echo-service.example.com/invoke
   Authorization: Bearer {delegated_token}
   Body: {"task": "Task summary"}

4. Echo Service:
   - Validates token (audience = https://echo-service.example.com)
   - Extracts delegation chain from token
   - Executes: simple_echo_crew()
   - Returns: "Echo: Task summary"
   - Includes: delegation_chain in response

5. PR Analyzer receives result
```

## Testing with PR Analysis Service

**Complete Flow:**
```
User (Okta authenticated)
  ↓
POST /invoke to PR Analysis Service (port 8001)
  ├─ Fetches PR from GitHub (via MCP tool)
  ├─ Analyzes code
  ├─ Generates summary
  └─ Delegates to Echo Service (A2A)
      ↓
  Echo Service (port 8002)
      ├─ Validates token
      ├─ Returns echo response
      └─ Delegation chain: [pr_analyzer_service, echo_service]
```

### Run Both Services

```bash
# Terminal 1: GitHub MCP Server (port 8000)
cd /Users/larryosakwe/Dev/keycard/crewai-github-mcp-server
./run_server_local.sh

# Terminal 2: Echo Service (port 8002)
cd examples/echo_service
python service.py

# Terminal 3: PR Analysis Service (port 8001)
cd ../pr_analysis_service
python service.py

# Terminal 4: Test
curl -X POST http://localhost:8001/invoke \
  -H "Authorization: Bearer USER_TOKEN" \
  -d '{"task": {"repo": "anthropics/anthropic-sdk-python", "pr_number": 588}}'
```

## Debugging

**Check logs for:**
- Token validation: `Echo Service received task:`
- Delegation chain: Shows in response JSON
- OAuth errors: Check `KEYCARD_CLIENT_SECRET` is correct
- Audience errors: `SERVICE_IDENTITY_URL` must match Resource identifier in Keycard

**Common Issues:**
1. **401 Unauthorized**: Token missing or invalid
   - Check Authorization header
   - Verify token is scoped to this service

2. **403 Forbidden**: Token audience mismatch
   - `SERVICE_IDENTITY_URL` must exactly match Resource identifier
   - Check Keycard Resource configuration

3. **500 Error**: Service error
   - Check logs for Python exceptions
   - Verify `keycardai-agents` is installed

## What's Next

After Echo Service works:
1. ✅ Validates A2A delegation pattern
2. ✅ Confirms token exchange working
3. ✅ Proves service identity model
4. → Replace Echo with Slack Notification Service
5. → Add Slack MCP Server for real functionality

## Security

- **No tokens exposed**: Crew code never sees tokens
- **Token validation**: Audience check on every request
- **Delegation tracking**: Full chain in audit logs
- **Scoped tokens**: Each service gets token for itself only
