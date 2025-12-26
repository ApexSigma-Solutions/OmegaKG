"""
GitHub API Client

Async HTTP client for GitHub REST API, following the pattern from
omega_kg.linear_client.LinearClient.

Provides methods for fetching PR details and commits from GitHub
to enable PR → Linear issue automation.
"""
import logging
from typing import Dict, Any, List, Optional

import httpx

from omega_kg.settings import settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Async HTTP client for GitHub REST API v3.

    This client handles authentication and provides methods to fetch
    repository data, pull requests, and commits.

    Example:
        client = GitHubClient()
        pr = await client.get_pull_request("owner", "repo", 123)
        commits = await client.get_pull_request_commits("owner", "repo", 123)
    """

    API_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token. If None, uses settings.github_token.
        """
        self.token = token or settings.github_token

        if not self.token:
            raise ValueError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable "
                "or pass token to GitHubClient()."
            )

        self._headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OmegaKG-Webhook/1.0",
        }

    async def get_pull_request(
        self, owner: str, repo: str, pr_number: int
    ) -> Dict[str, Any]:
        """
        Fetch pull request details from GitHub.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            pr_number: Pull request number

        Returns:
            GitHub PR data as dictionary

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.API_URL}/repos/{owner}/{repo}/pulls/{pr_number}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.debug(f"Fetching PR: {owner}/{repo}#{pr_number}")
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def get_pull_request_commits(
        self, owner: str, repo: str, pr_number: int
    ) -> List[Dict[str, Any]]:
        """
        Fetch all commits for a pull request.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of commit dictionaries

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/commits"

        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.debug(f"Fetching commits for PR: {owner}/{repo}#{pr_number}")
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def get_repository(
        self, owner: str, repo: str
    ) -> Dict[str, Any]:
        """
        Fetch repository details from GitHub.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name

        Returns:
            Repository data as dictionary

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{self.API_URL}/repos/{owner}/{repo}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.debug(f"Fetching repository: {owner}/{repo}")
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def close(self) -> None:
        """
        Close the HTTP client.

        This method is provided for compatibility with other clients
        that use async context managers.
        """
        # httpx.AsyncClient is used as context manager,
        # so no explicit close needed
        pass
