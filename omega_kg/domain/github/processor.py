"""
GitHub Event Processor

Processes GitHub webhook events and integrates with Linear issue tracking.
Handles PR merge events, extracts "Fixes [TEAM-ID]" patterns from commit
messages, and updates corresponding Linear issues to "Done" status.

 TN-103: The Refinery - GitHub Domain Processor
 TN-202: Inbound - GitHub to Linear (Implementation)
"""
import re
import logging
from typing import Dict, Any, List, Optional

from omega_kg.github_client import GitHubClient
from omega_kg.linear_client import LinearClient
from omega_kg.settings import settings
from omega_kg.domain.github.models import ParsedIssueReference

logger = logging.getLogger(__name__)

# Regex pattern to match issue references in commit messages
# Supports: Fixes [PROJ-123], Closes [LIN-456], Resolves [TEAM-789]
ISSUE_REFERENCE_PATTERN = re.compile(
    r"\b(?:fixes|closes|resolves)\s+\[([A-Z]+-\d+)\]",
    re.IGNORECASE,
)


class GitHubProcessor:
    """
    Domain processor for GitHub webhook events.

    This processor is decoupled from database and HTTP layers,
    making it testable and reusable. It accepts parsed JSON payloads
    directly rather than querying the database.

    Attributes:
        github_client: GitHubClient for fetching PR and commit data
        linear_client: LinearClient for updating issues
    """

    def __init__(self):
        """Initialize GitHub processor with API clients."""
        self.github_client = GitHubClient()
        self.linear_client = LinearClient()

    async def process_single_event(self, payload: Dict[str, Any]) -> bool:
        """
        Process a single GitHub webhook payload.

        This is the main entry point for the event processor. It validates
        the payload, detects PR merge events, extracts issue references,
        and updates corresponding Linear issues.

        Args:
            payload: Parsed JSON dictionary from webhook

        Returns:
            bool: True if processed successfully, False otherwise
        """
        try:
            # Validate payload structure
            action = payload.get("action")
            pr = payload.get("pull_request", {})
            repo = payload.get("repository", {})

            if not action:
                logger.debug("GitHub event has no action, skipping")
                return True

            # Handle PR merge events only
            if action == "closed" and pr.get("merged"):
                logger.info(
                    f"Processing PR merge: {repo.get('full_name', 'unknown')}#{pr.get('number', '?')}"
                )
                return await self._handle_pr_merged(payload)

            # Log ignored events for debugging
            logger.debug(
                f"Ignoring GitHub event action '{action}' (merged={pr.get('merged', False)})"
            )
            return True

        except KeyError as e:
            logger.error(f"GitHub event missing required field: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"GitHub event processing failed: {e}", exc_info=True)
            return False

    async def _handle_pr_merged(self, payload: Dict[str, Any]) -> bool:
        """
        Handle pull request merge event.

        Extracts issue references from commit messages and updates
        corresponding Linear issues.

        Args:
            payload: GitHub webhook payload for merged PR

        Returns:
            bool: True if processed successfully
        """
        try:
            pr = payload["pull_request"]
            repo = payload["repository"]
            pr_number = pr["number"]
            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            # Extract issue references from PR commit messages
            issue_refs = await self._extract_issue_references(
                owner, repo_name, pr_number
            )

            if not issue_refs:
                logger.info(
                    f"No issue references found in PR {owner}/{repo_name}#{pr_number}"
                )
                return True

            # Log found references
            identifiers = [ref.identifier for ref in issue_refs]
            logger.info(
                f"Found {len(issue_refs)} issue reference(s) in PR "
                f"{owner}/{repo_name}#{pr_number}: {', '.join(identifiers)}"
            )

            # Update each referenced Linear issue
            success_count = 0
            for ref in issue_refs:
                if await self._update_linear_issue(ref.identifier):
                    success_count += 1
                else:
                    logger.warning(
                        f"Failed to update Linear issue: {ref.identifier}"
                    )

            logger.info(
                f"Successfully updated {success_count}/{len(issue_refs)} "
                f"Linear issue(s) for PR {owner}/{repo_name}#{pr_number}"
            )

            return success_count > 0

        except Exception as e:
            logger.error(f"Failed to handle PR merge: {e}", exc_info=True)
            return False

    async def _extract_issue_references(
        self, owner: str, repo_name: str, pr_number: int
    ) -> List["ParsedIssueReference"]:
        """
        Extract [TEAM-ID] references from PR commit messages.

        Parses commit messages for patterns like:
        - Fixes [PROJ-123]
        - Closes [LIN-456]
        - Resolves [TEAM-789]

        Args:
            owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number

        Returns:
            List of parsed issue references
        """
        try:
            # Fetch commits from GitHub API
            commits = await self.github_client.get_pull_request_commits(
                owner, repo_name, pr_number
            )

            issue_refs = []

            # Parse each commit message
            for commit_data in commits:
                message = commit_data.get("commit", {}).get("message", "")
                sha = commit_data.get("sha", "")

                # Find all issue references in commit message
                matches = ISSUE_REFERENCE_PATTERN.findall(message)

                for identifier in matches:
                    issue_refs.append(
                        ParsedIssueReference(
                            identifier=identifier,
                            pattern=self._extract_pattern_keyword(message, identifier),
                            commit_sha=sha[:8] if sha else None,
                        )
                    )

            return issue_refs

        except Exception as e:
            logger.error(
                f"Failed to extract issue references from PR {owner}/{repo_name}#{pr_number}: {e}",
                exc_info=True,
            )
            return []

    def _extract_pattern_keyword(self, message: str, identifier: str) -> str:
        """
        Extract the keyword (fixes/closes/resolves) used for an identifier.

        Args:
            message: Commit message
            identifier: Issue identifier (e.g., "PROJ-123")

        Returns:
            Keyword used: "fixes", "closes", or "resolves"
        """
        # Find the pattern that matched this identifier
        pattern = rf"\b(fixes|closes|resolves)\s+\[{re.escape(identifier)}\]"
        match = re.search(pattern, message, re.IGNORECASE)

        return match.group(1).lower() if match else "fixes"

    async def _update_linear_issue(self, identifier: str) -> bool:
        """
        Update Linear issue to "Done" status.

        Args:
            identifier: Linear issue identifier (e.g., "PROJ-123")

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Check if done state ID is configured
            if not settings.linear_done_state_id:
                logger.error(
                    f"LINEAR_DONE_STATE_ID not configured. "
                    f"Cannot update issue {identifier}"
                )
                return False

            # Get issue details from Linear
            issue = await self.linear_client.get_issue(identifier)

            if not issue:
                logger.warning(f"Linear issue not found: {identifier}")
                return False

            issue_id = issue["id"]
            current_state_id = issue.get("state", {}).get("id")

            # Skip if already in done state
            if current_state_id == settings.linear_done_state_id:
                logger.debug(f"Issue {identifier} already in done state")
                return True

            # Update issue state to "Done"
            logger.info(f"Updating Linear issue {identifier} to done state")

            await self.linear_client.update_issue(
                issue_id=issue_id,
                updates={"stateId": settings.linear_done_state_id},
            )

            logger.info(f"✓ Successfully updated {identifier} to done state")
            return True

        except Exception as e:
            logger.error(f"Failed to update Linear issue {identifier}: {e}", exc_info=True)
            return False

    async def close(self) -> None:
        """Close HTTP clients."""
        await self.github_client.close()
        await self.linear_client.close()


# Singleton instance for GitHubProcessor
_github_processor_instance: Optional[GitHubProcessor] = None


def get_github_processor() -> GitHubProcessor:
    """
    Get singleton instance of GitHubProcessor.

    Returns:
        GitHubProcessor: Singleton instance
    """
    global _github_processor_instance
    if _github_processor_instance is None:
        _github_processor_instance = GitHubProcessor()
    return _github_processor_instance
