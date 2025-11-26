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
        headers = {}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        response = httpx.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return f"PR: {data['title']} by {data['user']['login']}"
        return f"Error: {response.status_code}"