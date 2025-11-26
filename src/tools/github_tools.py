from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx

# ============================================================================
# TOOL 1: Fetch PR Details
# ============================================================================

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

# ============================================================================
# TOOL 2: Fetch PR Files
# ============================================================================

class FetchPRFilesSchema(BaseModel):
    repo: str = Field(description="Repository (owner/name)")
    pr_number: int = Field(description="PR number")

class FetchPRFilesTool(BaseTool):
    name: str = "fetch_pr_files"
    description: str = "Fetch list of files changed in a PR with diffs"
    args_schema: type[BaseModel] = FetchPRFilesSchema
    github_token: str | None = None

    def _run(self, repo: str, pr_number: int) -> str:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        response = httpx.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"

        files = response.json()

        output = f"Files changed in PR: {len(files)}\n\n"
        for file in files[:20]:  # Limit to first 20 files
            output += f"""File: {file['filename']}
Status: {file['status']}
Changes: +{file['additions']} -{file['deletions']}
Patch preview:
{file.get('patch', 'No patch available')[:500]}

---
"""
        return output

# ============================================================================
# TOOL 3: Fetch PR Comments
# ============================================================================

class FetchPRCommentsSchema(BaseModel):
    repo: str = Field(description="Repository (owner/name)")
    pr_number: int = Field(description="PR number")

class FetchPRCommentsTool(BaseTool):
    name: str = "fetch_pr_comments"
    description: str = "Fetch review comments and discussions on a PR"
    args_schema: type[BaseModel] = FetchPRCommentsSchema
    github_token: str | None = None

    def _run(self, repo: str, pr_number: int) -> str:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        response = httpx.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"

        comments = response.json()

        if not comments:
            return "No review comments on this PR."

        output = f"Review Comments ({len(comments)} total):\n\n"
        for comment in comments[:10]:  # Limit to first 10
            output += f"""Comment by {comment['user']['login']}:
File: {comment.get('path', 'General')}
Line: {comment.get('line', 'N/A')}
Comment: {comment['body']}

---
"""
        return output

# ============================================================================
# TOOL 4: Fetch PR Commits
# ============================================================================

class FetchPRCommitsSchema(BaseModel):
    repo: str = Field(description="Repository (owner/name)")
    pr_number: int = Field(description="PR number")

class FetchPRCommitsTool(BaseTool):
    name: str = "fetch_pr_commits"
    description: str = "Fetch list of commits in a PR"
    args_schema: type[BaseModel] = FetchPRCommitsSchema
    github_token: str | None = None

    def _run(self, repo: str, pr_number: int) -> str:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        response = httpx.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"

        commits = response.json()

        output = f"Commits in PR: {len(commits)}\n\n"
        for commit in commits:
            output += f"""Commit: {commit['sha'][:7]}
Author: {commit['commit']['author']['name']}
Date: {commit['commit']['author']['date']}
Message: {commit['commit']['message']}

---
"""
        return output

# ============================================================================
# TOOL FACTORY: Create all tools with shared token
# ============================================================================

def create_github_tools(github_token: str):
    """
    Create all GitHub tools with the delegated token.

    Returns a list of tools that can be shared across multiple agents.
    All tools use the same token, so all API calls are attributed to the user.
    """
    return [
        FetchPRTool(github_token=github_token),
        FetchPRFilesTool(github_token=github_token),
        FetchPRCommentsTool(github_token=github_token),
        FetchPRCommitsTool(github_token=github_token),
    ]