from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx

class FetchPRSchema(BaseModel):
    repo: str = Field(description="Repository (owner/name)")
    pr_number: int = Field(description="PR number")

class FetchPRTool(BaseTool):
    name: str = "fetch_pr"
    description: str = "Fetch PR details from GitHub"
    args_schema: type[BaseModel] = FetchPRSchema
    github_token: str | None = None

    def _run(self, repo: str, pr_number: int) -> str:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        response = httpx.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"

        data = response.json()

        # Extract comprehensive PR information
        pr_info = {
            "title": data.get("title", "No title"),
            "number": data.get("number"),
            "author": data.get("user", {}).get("login", "Unknown"),
            "state": data.get("state", "unknown"),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "body": data.get("body", "No description provided"),
            "html_url": data.get("html_url", ""),
            "additions": data.get("additions", 0),
            "deletions": data.get("deletions", 0),
            "changed_files": data.get("changed_files", 0),
            "commits": data.get("commits", 0),
            "mergeable_state": data.get("mergeable_state", "unknown"),
            "draft": data.get("draft", False),
        }

        # Format as readable text for the AI agent
        return f"""Pull Request #{pr_info['number']}: {pr_info['title']}

Author: {pr_info['author']}
State: {pr_info['state']} {'(Draft)' if pr_info['draft'] else ''}
Created: {pr_info['created_at']}
Updated: {pr_info['updated_at']}

Description:
{pr_info['body'][:1000] if pr_info['body'] else 'No description provided'}

Changes:
- Files changed: {pr_info['changed_files']}
- Additions: +{pr_info['additions']}
- Deletions: -{pr_info['deletions']}
- Commits: {pr_info['commits']}
- Mergeable: {pr_info['mergeable_state']}

URL: {pr_info['html_url']}
"""