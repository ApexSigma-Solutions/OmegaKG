"""
Omega_KG Smart Parser (smart_parser.py)

This module is the "brains" (Orchestrator) for the Obsidian-to-Linear
task creation workflow.

It imports and uses:
1.  VaultUtils: To read/write frontmatter from/to Obsidian notes.
2.  linear_client: To create the issue in Linear.
3.  settings: To get the API keys, default Team ID, and the new JSON maps.
"""

import logging
import re
import json
import frontmatter
from pathlib import Path
from typing import List, Optional

# Import our "adapters" and "config"
from omega_kg.settings import settings
from omega_kg.vault_utils import VaultUtils
from omega_kg.linear_client import linear_client

# Set up logger
logger = logging.getLogger(__name__)

# --- REGEX PATTERNS (pre-compiled) ---
# Finds @assignee/username
ASSIGNEE_REGEX = re.compile(r"@assignee/(\S+)")
# Finds @label/label-name (Legacy)
LABEL_REGEX_LEGACY = re.compile(r"@label/(\S+)")
# Finds #Hashtags
HASHTAG_REGEX = re.compile(r"(?<=^|(?<=[^a-zA-Z0-9-_.]))#([a-zA-Z0-9-_]+)")
# Finds @priority/1
PRIORITY_REGEX = re.compile(r"@priority/([0-4])")
# Finds the first H1
TITLE_REGEX = re.compile(r"^#\s+(.*)", re.MULTILINE)
# -------------------------------------


class SmartParser:
    """
    Orchestrates the parsing of an Obsidian note and creation of a
    corresponding Linear issue.
    """

    def __init__(self):
        """
        Initializes the parser, loading utilities and parsing mappings
        from the settings.
        """
        try:
            self.vault = VaultUtils()

            # Load and parse the JSON maps from settings
            self.user_map: dict[str, str] = json.loads(
                settings.linear_user_map_json or "{}"
            )
            self.label_map: dict[str, str] = json.loads(
                settings.linear_label_map_json or "{}"
            )
            self.status_map: dict[str, str] = json.loads(
                settings.linear_status_map_json or "{}"
            )

            self.default_team_id = settings.linear_team_id

            if not self.default_team_id:
                # We don't raise here to allow instantiation, but we'll check before creating issues
                logger.warning("LINEAR_TEAM_ID is not set. Issue creation will fail.")

            if not self.user_map:
                logger.warning(
                    "LINEAR_USER_MAP_JSON is empty. Assignee parsing will be disabled."
                )
            if not self.label_map:
                logger.warning(
                    "LINEAR_LABEL_MAP_JSON is empty. Label parsing will be disabled."
                )
            if not self.status_map:
                logger.warning(
                    "LINEAR_STATUS_MAP_JSON is empty. Status parsing will be disabled."
                )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON maps from settings: {e}")
            raise ValueError(
                "Invalid JSON in LINEAR_USER_MAP_JSON, LINEAR_LABEL_MAP_JSON, or LINEAR_STATUS_MAP_JSON"
            )
        except Exception as e:
            logger.error(f"Failed to initialize SmartParser: {e}")
            raise

    def _parse_title(self, content: str, metadata: dict) -> str:
        """Finds the best title for the issue."""
        # 1. Try H1
        title_match = TITLE_REGEX.search(content)
        if title_match:
            return title_match.group(1).strip()

        # 2. Try metadata 'title'
        if metadata.get("title"):
            return metadata["title"]

        # 3. Fallback
        return "New Task from Obsidian"

    def _parse_tag(
        self, content: str, pattern: re.Pattern, mapping: dict
    ) -> str | None:
        """Finds the first match for a pattern and maps it."""
        match = pattern.search(content)
        if match:
            key = match.group(1)
            if key in mapping:
                return mapping[key]
            logger.warning(f"Found tag '{key}' but it has no mapping in settings.")
        return None

    def _parse_labels(self, content: str, metadata: dict) -> List[str]:
        """
        Parses labels from:
        1. Frontmatter 'labels' list (raw strings, mapped).
        2. Body hashtags (mapped).
        3. Legacy @label/ tags (mapped).
        """
        found_labels = set()

        # 1. Frontmatter
        fm_labels = metadata.get("labels", [])
        if isinstance(fm_labels, list):
            for label in fm_labels:
                if label in self.label_map:
                    found_labels.add(self.label_map[label])
                else:
                    logger.warning(f"Frontmatter label '{label}' has no mapping.")

        # 2. Body Hashtags
        hashtags = HASHTAG_REGEX.findall(content)
        for tag in hashtags:
            if tag in self.label_map:
                found_labels.add(self.label_map[tag])
            # We don't warn for every hashtag as many are just normal tags

        # 3. Legacy @label/ tags
        legacy_tags = LABEL_REGEX_LEGACY.findall(content)
        for tag in legacy_tags:
            if tag in self.label_map:
                found_labels.add(self.label_map[tag])
            else:
                logger.warning(f"Legacy tag '@label/{tag}' has no mapping.")

        return list(found_labels)

    def _parse_status(self, metadata: dict) -> Optional[str]:
        """
        Parses status from frontmatter 'status' field and maps to Linear state ID.
        """
        status = metadata.get("status")
        if status:
            # Normalize status (lowercase, replace spaces with dashes)
            # This allows "In Progress" to match "in-progress" key
            normalized_status = str(status).lower().replace(" ", "-")

            if normalized_status in self.status_map:
                return self.status_map[normalized_status]

            # Also try exact match
            if str(status) in self.status_map:
                return self.status_map[str(status)]

            logger.warning(
                f"Status '{status}' has no mapping in LINEAR_STATUS_MAP_JSON."
            )
        return None

    def _parse_priority(self, content: str) -> int:
        """Finds the priority tag."""
        match = PRIORITY_REGEX.search(content)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, TypeError):
                pass
        return 0  # Default: No Priority

    async def sync_note_to_linear(self, note_path: str | Path) -> dict | None:
        """
        Main orchestration method.

        1.  Reads a note's frontmatter and content.
        2.  Parses the content for tags.
        3.  If 'linear_id' exists, UPDATES the Linear issue.
        4.  If not, CREATES a new Linear issue.
        5.  Updates the note's frontmatter with the result.

        Args:
            note_path: The path to the note (relative or absolute).

        Returns:
            A dict with the Linear issue info, or None if skipped/failed.
        """
        logger.info(f"--- SmartParser syncing: {note_path} ---")

        if not self.default_team_id:
            logger.error("Cannot sync task: LINEAR_TEAM_ID is not set.")
            return None

        # 1. Read frontmatter and content
        try:
            metadata = self.vault.read_note_frontmatter(note_path)
            linear_id = metadata.get("linear_id")

            full_path = self.vault.resolve_path(note_path)
            if not full_path.is_file():
                logger.error(f"File not found at resolved path: {full_path}")
                return None

            with full_path.open("r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                content = post.content

        except Exception as e:
            logger.error(f"Failed to read note {note_path}: {e}")
            return None

        # 2. Parse all tags
        title = self._parse_title(content, metadata)
        assignee_id = self._parse_tag(content, ASSIGNEE_REGEX, self.user_map)
        label_ids = self._parse_labels(content, metadata)
        priority = self._parse_priority(content)
        state_id = self._parse_status(metadata)

        logger.info(
            f"Parsed note: Title='{title}', Assignee='{assignee_id}', Labels={label_ids}, Priority={priority}, State={state_id}"
        )

        # 3. Update or Create
        try:
            if linear_id:
                # UPDATE
                logger.info(f"Found existing Linear ID: {linear_id}. Updating...")
                updates = {
                    "title": title,
                    "description": content,
                    "priority": priority,
                }
                if assignee_id:
                    updates["assigneeId"] = assignee_id
                if label_ids:
                    updates["labelIds"] = label_ids
                if state_id:
                    updates["stateId"] = state_id

                updated_issue = await linear_client.update_issue(
                    str(linear_id), updates
                )
                logger.info(
                    f"Successfully updated Linear issue: {updated_issue.get('identifier')}"
                )
                return updated_issue

            else:
                # CREATE
                logger.info("No Linear ID found. Creating new issue...")
                new_issue = await linear_client.create_issue(
                    title=title,
                    description=content,
                    team_id=self.default_team_id,
                    assignee_id=assignee_id,
                    label_ids=label_ids,
                    priority=priority,
                    state_id=state_id,
                )
                logger.info(
                    f"Successfully created Linear issue: {new_issue['identifier']}"
                )

                # Write back ID to note
                updates = {
                    "linear_id": new_issue["id"],
                    "linear_identifier": new_issue["identifier"],
                    "linear_url": new_issue.get("url"),
                }

                if not self.vault.update_note_frontmatter(note_path, updates):
                    logger.error(
                        f"CRITICAL: Created Linear issue {new_issue['identifier']} but FAILED to write back to {note_path}!"
                    )

                return new_issue

        except Exception as e:
            logger.error(f"Failed to sync with Linear: {e}")
            return None
