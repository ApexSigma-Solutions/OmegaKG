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
import asyncio
import frontmatter
from typing import Mapping

# Import our "adapters" and "config"
from omega_kg.settings import settings
from omega_kg.vault_utils import VaultUtils
from omega_kg.linear_client import create_linear_issue

# Set up logger
logger = logging.getLogger(__name__)

# --- REGEX PATTERNS (pre-compiled) ---
# Finds @assignee/username
ASSIGNEE_REGEX = re.compile(r"@assignee/(\S+)")
# Finds @label/label-name
LABEL_REGEX = re.compile(r"@label/(\S+)")
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
            # Expected format for both settings.linear_user_map_json and settings.linear_label_map_json:
            # '{"obsidian_tag_or_username": "linear_user_or_label_id", ...}'
            # Example:
            # settings.linear_user_map_json = '{"your_user": "linearUserId123"}'
            # settings.linear_label_map_json = '{"YourLabel": "linearLabelId456"}'
            self.user_map: dict[str, str] = json.loads(
                settings.linear_user_map_json or "{}"
            )
            self.label_map: dict[str, str] = json.loads(
                settings.linear_label_map_json or "{}"
            )
            
            self.default_team_id = settings.linear_team_id
            
            if not self.default_team_id:
                raise ValueError("LINEAR_TEAM_ID is not set in .env")
            if not self.user_map:
                logger.warning("LINEAR_USER_MAP_JSON is empty. Assignee parsing will be disabled.")
            if not self.label_map:
                logger.warning("LINEAR_LABEL_MAP_JSON is empty. Label parsing will be disabled.")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON maps from settings: {e}")
            raise ValueError("Invalid JSON in LINEAR_USER_MAP_JSON or LINEAR_LABEL_MAP_JSON")
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

    def _parse_tag(self, content: str, pattern: re.Pattern, mapping: dict) -> str | None:
        """Finds the first match for a pattern and maps it."""
        match = pattern.search(content)
        if match:
            key = match.group(1)
            if key in mapping:
                return mapping[key]
            logger.warning(f"Found tag '@.../{key}' but it has no mapping in settings.")
        return None

    def _parse_all_tags(self, content: str, pattern: re.Pattern, mapping: dict) -> list[str]:
        """Finds all matches for a pattern and maps them."""
        matches = pattern.findall(content)
        mapped_ids = []
        for key in matches:
            if key in mapping:
                mapped_ids.append(mapping[key])
            else:
                logger.warning(f"Found tag '@.../{key}' but it has no mapping in settings.")
        return mapped_ids

    def _parse_priority(self, content: str) -> int:
        """Finds the priority tag."""
        match = PRIORITY_REGEX.search(content)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, TypeError):
                pass
        return 0  # Default: No Priority

    async def parse_and_create_task(self, note_path: str | Path) -> dict | None:
        """
        Main orchestration method.
        
        1.  Reads a note's frontmatter and content.
        2.  Checks if it's already been processed.
        3.  Parses the content for tags.
        4.  Calls the linear_client to create the issue.
        5.  Calls vault_utils to write the new ID back to the note.
        
        Args:
            note_path: The path to the note (relative or absolute).
            
        Returns:
            A dict with the new Linear issue info, or None if skipped/failed.
        """
        logger.info(f"--- SmartParser starting for: {note_path} ---")
        
        # 1. Read frontmatter and check for duplicates
        try:
            metadata = self.vault.read_note_frontmatter(note_path)
            if metadata.get("linear_id") or metadata.get("linear_identifier"):
                logger.warning(f"Skipping: Note already has Linear ID. ({metadata.get('linear_identifier')})")
                return None

            # 2. Read full content (this is inefficient, but avoids
            #    modifying vault_utils to return content)
            full_path = self.vault._resolve_path(note_path) # Use the (now known) internal method
            if not full_path.is_file():
                logger.error(f"File not found at resolved path: {full_path}")
                return None
                
            with full_path.open('r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                content = post.content
                
        except Exception as e:
            logger.error(f"Failed to read note {note_path}: {e}")
            return None
        
        # 3. Parse all tags
        title = self._parse_title(content, metadata)
        assignee_id = self._parse_tag(content, ASSIGNEE_REGEX, self.user_map)
        label_ids = self._parse_all_tags(content, LABEL_REGEX, self.label_map)
        priority = self._parse_priority(content)
        
        logger.info(f"Parsed note: Title='{title}', Assignee='{assignee_id}', Labels={label_ids}, Priority={priority}")

        # 4. Call Linear API
        try:
            new_issue = await create_linear_issue(
                title=title,
                description=content, # Send the full markdown content
                team_id=self.default_team_id,
                assignee_id=assignee_id,
                label_ids=label_ids,
                priority=priority
            )
            logger.info(f"Successfully created Linear issue: {new_issue['identifier']}")
            
        except Exception as e:
            logger.error(f"Failed to create Linear issue: {e}")
            return None

        # 5. Write back to note
        updates = {
            "linear_id": new_issue["id"],
            "linear_identifier": new_issue["identifier"]
        }
        
        if not self.vault.update_note_frontmatter(note_path, updates):
            logger.error(f"CRITICAL: Created Linear issue {new_issue['identifier']} but FAILED to write back to {note_path}!")
            # TODO: Add to a retry queue?
        
        logger.info(f"--- SmartParser finished for: {note_path} ---")
        return new_issue


# -----------------------------------------------------------------------------
# TEST HARNESS
#
# To run this test:
# 1.  Update settings.py and .env.example (see other files)
# 2.  Fill out your .env file with your real API key, Team ID,
#     and at least one user/label in the JSON maps.
# 3.  Create a test note in your vault at 'Tasks/my_smart_task.md'
#     with content like:
#
#     ---
#     status: draft
#     ---
#     # This is a smart parser test
#     This task will be assigned to @assignee/your_user
#     and get a @label/YourLabel
#     @priority/1
#
# 4.  Run: poetry run python omega_kg/smart_parser.py
# -----------------------------------------------------------------------------
# Test harness code has been moved to tests/test_smart_parser.py to keep production code clean.

