"""
Omega_KG Linear Client (linear_client.py)

This module acts as the "Linear Adapter" for the application.
Its only responsibility is to communicate with the Linear GraphQL API.
It uses the 'settings' object from omega_kg.settings for credentials.
"""

# Test harness for this module is located in tests/test_linear_client.py
# for better separation of concerns.

import httpx
import asyncio
import logging
import json
from typing import Optional
from omega_kg.settings import settings

# Set up logger
logger = logging.getLogger(__name__)
LINEAR_API_URL = "https://api.linear.app/graphql"

async def create_linear_issue(
    title: str,
    description: str,
    team_id: str,
    assignee_id: str | None = None,
    label_ids: list[str] | None = None,
    priority: int = 0
) -> dict:
    """
    Creates a new issue in Linear with the specified details.

    Args:
        title (str): The title of the issue.
        description (str): The description of the issue.
        team_id (str): The Linear team ID where the issue will be created.
        assignee_id (str | None, optional): The user ID to assign the issue to.
        label_ids (list[str] | None, optional): List of label IDs to apply to the issue.
        priority (int, optional): Priority of the issue.
            Mapping:
                0 = No priority
                1 = Urgent
                2 = High
                3 = Normal
                4 = Low
            Defaults to 0.

    Returns:
        dict: A dictionary containing the new issue's ID and identifier (e.g., "APX-123").

    Raises:
        Exception: If the API call fails or returns an error.
        httpx.HTTPStatusError: If the HTTP response status is an error (4xx, 5xx).
        httpx.RequestError: If a network error occurs while making the request.
    """
    
    headers = {
        "Authorization": f"Bearer {settings.linear_api_key}",
        "Content-Type": "application/json",
    }
    
    # GraphQL mutation
    # We dynamically build the 'createIssue' input
    mutation = """
    mutation CreateIssue($title: String!, $description: String, $teamId: String!, $assigneeId: String, $labelIds: [String!], $priority: Int) {
      issueCreate(
        input: {
          title: $title
          description: $description
          teamId: $teamId
          assigneeId: $assigneeId
          labelIds: $labelIds
          priority: $priority
        }
      ) {
        success
        issue {
          id
          identifier
          title
        }
        error
      }
    }
    """
    
    variables = {
        "title": title,
        "description": description,
        "teamId": team_id,
        "assigneeId": assignee_id,
        "priority": priority,
    }
    
    # Conditionally add labelIds only if provided
    if label_ids is not None:
        variables["labelIds"] = label_ids
    
    query = {
        "query": mutation,
        "variables": variables,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(LINEAR_API_URL, headers=headers, json=query, timeout=10.0)
            
            # Raise an exception for HTTP errors (4xx, 5xx)
            response.raise_for_status() 
            
            # .json() is synchronous after the await on client.post()
            data = response.json()
            
            # Check for GraphQL-level errors
            if "errors" in data:
                raise Exception(
                    f"GraphQL Error: {data['errors']}\n"
                    f"Query: {mutation}\n"
                    f"Variables: {json.dumps(variables, indent=2)}"
                )

            create_payload = data.get("data", {}).get("issueCreate", {})
            
            if create_payload.get("success") and create_payload.get("issue"):
                issue = create_payload["issue"]
                return {
                    "id": issue.get("id"),
                    "identifier": issue.get("identifier"),
                    "title": issue.get("title")
                }
            else:
                error_msg = create_payload.get('error', 'Unknown error')
                raise Exception(
                    f"Linear API failed to create issue: {error_msg}. "
                    f"Full response: {json.dumps(create_payload, indent=2)}"
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error connecting to Linear: {e.response.status_code} [response text redacted for security]")
            raise
        except httpx.RequestError as e:
            logger.error(f"Network Error connecting to Linear: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Linear issue: {e}")
            raise

