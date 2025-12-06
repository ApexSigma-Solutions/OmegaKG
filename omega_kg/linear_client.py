"""
Omega_KG Linear Client (linear_client.py)

This module acts as the "Linear Adapter" for the application.
It uses the 'settings' object from omega_kg.settings for credentials.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from omega_kg.settings import settings

# Set up logger
logger = logging.getLogger(__name__)


class LinearClient:
    """
    Async client for the Linear GraphQL API.
    """

    API_URL = "https://api.linear.app/graphql"

    def __init__(self):
        self.api_key = settings.linear_api_key
        if not self.api_key:
            logger.warning(
                "LINEAR_API_KEY is not set. Linear integration will not work."
            )

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.api_key}",
            "Content-Type": "application/json",
        }

    async def _execute_query(
        self, query: str, variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Executes a GraphQL query against the Linear API.
        """
        if not self.api_key:
            raise ValueError("Linear API key is missing.")

        payload = {"query": query, "variables": variables or {}}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.API_URL, headers=self._headers, json=payload, timeout=10.0
                )
                response.raise_for_status()

                data = response.json()

                if "errors" in data:
                    raise Exception(f"GraphQL Error: {data['errors']}")

                return data.get("data", {})

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP Error connecting to Linear: {e.response.status_code}"
                )
                raise
            except httpx.RequestError as e:
                logger.error(f"Network Error connecting to Linear: {e}")
                raise
            except Exception as e:
                logger.error(f"Linear API Query Failed: {e}")
                raise

    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: str,
        assignee_id: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        priority: int = 0,
        state_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new issue in Linear.
        """
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              identifier
              title
              url
            }
          }
        }
        """

        variables = {
            "input": {
                "title": title,
                "description": description,
                "teamId": team_id,
                "priority": priority,
            }
        }

        if assignee_id:
            variables["input"]["assigneeId"] = assignee_id
        if label_ids:
            variables["input"]["labelIds"] = label_ids
        if state_id:
            variables["input"]["stateId"] = state_id

        result = await self._execute_query(mutation, variables)
        return result.get("issueCreate", {}).get("issue", {})

    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """
        Retrieves an issue by ID or Identifier (e.g., "APX-123").
        """
        query = """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            description
            state {
              id
              name
              type
            }
            assignee {
              id
              name
            }
            priority
            url
          }
        }
        """
        result = await self._execute_query(query, {"id": issue_id})
        return result.get("issue", {})

    async def update_issue(
        self, issue_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Updates an existing issue.
        """
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              identifier
              title
              state {
                name
              }
            }
          }
        }
        """
        result = await self._execute_query(mutation, {"id": issue_id, "input": updates})
        return result.get("issueUpdate", {}).get("issue", {})


# Singleton instance for easy import
linear_client = LinearClient()


# Backwards compatibility wrapper (if needed by existing code)
async def create_linear_issue(*args, **kwargs):
    return await linear_client.create_issue(*args, **kwargs)
