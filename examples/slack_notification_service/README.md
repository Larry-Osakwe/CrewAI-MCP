# Slack Notification Service - Phase 2A Example

Agent service that posts notifications to Slack. Designed to be called by other services via A2A delegation.

## Architecture

```
PR Analysis Service → Slack Notification Service
                        ├─ Formats message
                        └─ Posts to Slack (via MCP tool) → Slack API
```

**Delegation Chain:** `pr_analyzer_service → slack_poster_service → slack_api`

## Features

- **Simple Crew**: Message Formatter + Slack Poster
- **MCP Tool Integration**: Secure Slack API access
- **Callable by Other Services**: Receives delegated tasks via `/invoke` endpoint
- **OAuth Token Flow**: Token scoped to this service, then exchanged for Slack API access

## Installation

```bash
# Install dependencies
pip install keycardai-agents[crewai] keycardai-mcp[crewai]

# Copy environment template
cp .env.example .env

# Edit .env with your Keycard credentials
```

## Configuration

### Keycard Setup

1. Create Application for Slack Service:
```yaml
applications:
  - client_id: slack_poster_service
    identity_url: https://slack-poster.example.com
    # Save client_secret for .env
```

2. Configure Dependencies:
```yaml
dependencies:
  - application: slack_poster_service
    resource: slack_mcp_server
    permissions: [write]
```

### Environment Variables

Edit `.env` with:
- `KEYCARD_ZONE_ID`: Your Keycard zone
- `KEYCARD_CLIENT_ID`: Application client ID
- `KEYCARD_CLIENT_SECRET`: Application client secret
- `SERVICE_IDENTITY_URL`: Public URL of this service
- `OPENAI_API_KEY`: OpenAI API key for CrewAI
- `SLACK_MCP_SERVER_URL`: Slack MCP server endpoint

## Running

```bash
python service.py
```

Service starts on `http://localhost:8001`

### Agent Card

Visit `http://localhost:8001/.well-known/agent-card.json`:

```json
{
  "name": "Slack Notification Service",
  "description": "Posts notifications to Slack channels with formatting",
  "capabilities": ["slack_posting", "message_formatting"],
  "endpoints": {
    "invoke": "https://slack-poster.example.com/invoke"
  }
}
```

### Invoke Endpoint (Called by Other Services)

```bash
curl -X POST http://localhost:8001/invoke \
  -H "Authorization: Bearer SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": {
      "message": "PR #588 has been reviewed and approved",
      "channel": "#engineering"
    }
  }'
```

## How It Works

1. **PR Analysis Service** wants to post to Slack
2. **Calls A2A delegation tool**: `delegate_to_slack_notification_service`
3. **Token exchange**:
   - PR Analyzer service has token (from user)
   - Keycard exchanges: `pr_analyzer_token` → `slack_service_token`
   - Token scoped to Slack Service (audience: `https://slack-poster.example.com`)
4. **Slack Service receives request**:
   - Validates token (audience check)
   - Extracts delegation chain
5. **Crew executes**:
   - Formatter agent formats message
   - Poster agent calls Slack MCP tool
   - Keycard exchanges: `slack_service_token` → `slack_api_token`
   - Posts to Slack
6. **Returns result** to PR Analysis Service

## Delegation Chain

When called from PR Analysis Service, the delegation chain is:
```
user@example.com → pr_analyzer_service → slack_poster_service
```

This is tracked in:
- Token claims (`delegation_chain`)
- Response payload
- Keycard audit logs

## Testing Locally

```bash
# Terminal 1: Start Slack MCP Server
cd ../../slack-mcp-server
python server.py

# Terminal 2: Start this service
python service.py

# Terminal 3: Test direct invocation
python test_service.py
```

## Testing with PR Analysis Service

```bash
# Terminal 1: Slack MCP Server (port 8002)
cd ../../slack-mcp-server
python server.py

# Terminal 2: Slack Service (port 8001)
python service.py

# Terminal 3: GitHub MCP Server (port 8000)
cd ../../
./run_server_local.sh

# Terminal 4: PR Analysis Service (port 8000 - different process)
cd ../pr_analysis_service
python service.py

# Terminal 5: Test end-to-end
python test_e2e.py
```

## Deployment

For production:

1. Deploy alongside Slack MCP server
2. Configure public URL in `SERVICE_IDENTITY_URL`
3. Update Keycard Application with identity URL
4. Configure Keycard dependencies for services that can call this one
5. PR Analysis Service will discover this via agent card

## Security

- **Token validation**: Checks audience matches identity URL
- **Delegation tracking**: Full chain preserved
- **Scoped access**: Service token only works for this service
- **MCP tool auth**: Fresh Slack token per API call
