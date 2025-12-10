# PR Analysis Service - Phase 2A Example

Agent service that analyzes GitHub pull requests and delegates to Slack Notification Service.

## Architecture

```
User → PR Analysis Service
  ├─ Fetches PR data (via MCP GitHub tools)
  ├─ Analyzes code quality
  ├─ Generates summary
  └─ Delegates to Slack Service (via A2A) → Posts to Slack
```

**Delegation Chain:** `user → pr_analyzer_service → slack_notification_service → slack_api`

## Features

- **Multi-Agent Crew**: PR Fetcher, Code Reviewer, Orchestrator
- **MCP Tool Integration**: Secure GitHub API access via Phase 1 tools
- **Service-to-Service Delegation**: Orchestrator delegates to Slack Service
- **OAuth Token Flow**: Full RFC 8693 token exchange with delegation chains

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

1. Create Application for PR Analysis Service:
```yaml
applications:
  - client_id: pr_analyzer_service
    identity_url: https://pr-analyzer.example.com
    # Save client_secret for .env
```

2. Configure Dependencies:
```yaml
dependencies:
  - application: pr_analyzer_service
    resource: github_mcp_server
    permissions: [read]
  - application: pr_analyzer_service
    resource: slack_notification_service
    permissions: [invoke]
```

### Environment Variables

Edit `.env` with:
- `KEYCARD_ZONE_ID`: Your Keycard zone
- `KEYCARD_CLIENT_ID`: Application client ID
- `KEYCARD_CLIENT_SECRET`: Application client secret
- `SERVICE_IDENTITY_URL`: Public URL of this service
- `OPENAI_API_KEY`: OpenAI API key for CrewAI
- `GITHUB_MCP_SERVER_URL`: GitHub MCP server endpoint
- `SLACK_SERVICE_URL`: Slack Notification Service URL

## Running

```bash
python service.py
```

Service starts on `http://localhost:8000`

### Agent Card

Visit `http://localhost:8000/.well-known/agent-card.json` to see service capabilities.

### Invoke Endpoint

```bash
curl -X POST http://localhost:8000/invoke \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task": {
      "repo": "anthropics/anthropic-sdk-python",
      "pr_number": 588
    }
  }'
```

## How It Works

1. **User authenticates** via Keycard → receives user token
2. **User calls /invoke** with PR details + user token
3. **PR Fetcher agent**:
   - Calls `fetch_pr_authenticated` MCP tool
   - Keycard exchanges user token → GitHub token
   - Fetches PR data from GitHub API
4. **Code Reviewer agent**:
   - Analyzes PR changes
   - Identifies issues
5. **Orchestrator agent**:
   - Generates summary
   - Calls `delegate_to_slack_notification_service` A2A tool
   - Keycard exchanges service token → Slack service token
   - Slack Service posts to Slack

## Audit Trail

Full delegation chain captured in Keycard:
```
user@example.com
  → pr_analyzer_service (fetch_pr_authenticated)
    → github_api (read PR #588)
  → pr_analyzer_service (delegate_to_slack_notification_service)
    → slack_notification_service (post_to_slack)
      → slack_api (post message)
```

## Testing

```bash
# Start GitHub MCP server (terminal 1)
cd ../../
./run_server_local.sh

# Start Slack Notification Service (terminal 2)
cd ../slack_notification_service
python service.py

# Start PR Analysis Service (terminal 3)
python service.py

# Test invocation (terminal 4)
python test_service.py
```

## Deployment

For production deployment:

1. Deploy to hosting platform (Render, Railway, Vercel, etc.)
2. Configure public URL in `SERVICE_IDENTITY_URL`
3. Update Keycard Application with actual identity URL
4. Configure dependencies in Keycard
5. Set up OAuth callbacks if needed

## Security

- **No tokens in crew code**: All auth via Keycard
- **Per-call token exchange**: Fresh tokens for each API call
- **Service-level identity**: Each service has Keycard Application identity
- **Delegation tracking**: Full audit trail of service-to-service calls
