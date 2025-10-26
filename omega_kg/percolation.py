"""
percolation.py

Provides functions for extracting and linking commit and task data from markdown content into the database.

This module is part of the Omega_KG package and handles the percolation of knowledge
from Obsidian notes into the Neo4j knowledge graph through commit and task extraction.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from neo4j import GraphDatabase, Driver


class PercolationEngine:
    """Engine for extracting and linking commit and task data from markdown content."""

    def __init__(self, driver: Driver):
        """
        Initialize the percolation engine.

        Args:
            driver: Neo4j driver instance for database operations
        """
        self.driver = driver

    def percolate_from_vault(self, vault_path: Path) -> Dict[str, int]:
        """
        Extract and percolate all tasks and commits from an Obsidian vault.

        Args:
            vault_path: Path to the Obsidian vault root directory

        Returns:
            Dictionary with counts of extracted items (tasks, commits, links)
        """
        stats = {"tasks": 0, "commits": 0, "links": 0}

        # Find all markdown files in the vault
        for md_file in vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                metadata = self._extract_frontmatter(content)

                if metadata:
                    # Extract and percolate tasks
                    task_count = self._percolate_task(md_file, metadata, content)
                    stats["tasks"] += task_count

                    # Extract and percolate commits
                    commit_count = self._percolate_commits(md_file, metadata, content)
                    stats["commits"] += commit_count

                    # Extract and percolate session data
                    session_count = self._percolate_session(md_file, metadata, content)
                    stats["links"] += session_count

            except Exception as e:
                print(f"Error percolating {md_file}: {e}")

        return stats

    def _extract_frontmatter(self, content: str) -> Optional[Dict]:
        """
        Extract YAML frontmatter from markdown content.

        Args:
            content: Markdown file content

        Returns:
            Dictionary of frontmatter metadata or None if not found
        """
        if not content.startswith("---"):
            return None

        try:
            _, frontmatter, _ = content.split("---", 2)
            metadata = {}

            for line in frontmatter.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip()

            return metadata
        except Exception:
            return None

    def _percolate_task(self, path: Path, metadata: Dict, content: str) -> int:
        """
        Extract task information and link to decisions.

        Args:
            path: Path to the markdown file
            metadata: Extracted metadata from frontmatter
            content: Full content of the markdown file

        Returns:
            Number of tasks extracted
        """
        task_count = 0

        # Look for task references (e.g., [[DRAFT-001]])
        task_pattern = r"\[\[([A-Z]+-\d+)\]\]"
        tasks = re.findall(task_pattern, content)

        with self.driver.session() as session:
            for task_uid in tasks:
                # Create or update task node
                session.run(
                    """
                    MERGE (t:Task {uid: $uid})
                    SET t.filepath = $filepath,
                        t.created = $created,
                        t.pinned = false
                    RETURN t
                    """,
                    uid=task_uid,
                    filepath=str(path),
                    created=metadata.get("date", datetime.now().isoformat()),
                )
                task_count += 1

                # Link task to decision if in a decision context
                decision_id = metadata.get("decision_id")
                if decision_id:
                    session.run(
                        """
                        MATCH (t:Task {uid: $uid})
                        MATCH (d:Decision {id: $decision_id})
                        MERGE (t)-[:IMPLEMENTS]->(d)
                        """,
                        uid=task_uid,
                        decision_id=decision_id,
                    )

        return task_count

    def _percolate_commits(self, path: Path, metadata: Dict, content: str) -> int:
        """
        Extract commit information from markdown content.

        Args:
            path: Path to the markdown file
            metadata: Extracted metadata from frontmatter
            content: Full content of the markdown file

        Returns:
            Number of commits extracted
        """
        commit_count = 0

        # Parse commits from markdown (format: #### Git Commit [repo]: `hash`)
        commit_pattern = r"#### Git Commit \[(.+?)\]: `(.+?)`\n(?:\*\*Linear:\*\* \[\[(.+?)\]\])?\n?(?:\*\*Message:\*\*\n)?```\n(.+?)\n```"
        commits = re.finditer(commit_pattern, content, re.DOTALL)

        with self.driver.session() as session:
            for commit_match in commits:
                repo, commit_hash, linear_id, message = commit_match.groups()
                commit_count += 1

                # Create commit node
                session.run(
                    """
                    MERGE (c:Commit {hash: $hash})
                    SET c.message = $message,
                        c.repo = $repo,
                        c.timestamp = $timestamp
                    RETURN c
                    """,
                    hash=commit_hash,
                    message=message.strip(),
                    repo=repo.strip(),
                    timestamp=datetime.now().isoformat(),
                )

                # Link to task if linear_id provided
                if linear_id:
                    session.run(
                        """
                        MATCH (c:Commit {hash: $hash})
                        MATCH (t:Task {linear_id: $linear_id})
                        MERGE (c)-[:IMPLEMENTS]->(t)
                        """,
                        hash=commit_hash,
                        linear_id=linear_id.strip(),
                    )

        return commit_count

    def _percolate_session(self, path: Path, metadata: Dict, content: str) -> int:
        """
        Extract session and decision information from markdown.

        Args:
            path: Path to the markdown file
            metadata: Extracted metadata from frontmatter
            content: Full content of the markdown file

        Returns:
            Number of session/decision links created
        """
        link_count = 0
        session_date = metadata.get("date")

        if not session_date:
            return link_count

        with self.driver.session() as session:
            # Create or match session node
            session.run(
                """
                MERGE (s:ChatSession {date: $date})
                SET s.topic = $topic
                RETURN s
                """,
                date=session_date,
                topic=metadata.get("topic", "Unknown"),
            )

            # Extract decisions (look for ## Decision markers)
            decision_pattern = r"## Decision\n\n(.+?)(?=\n##|\Z)"
            decisions = re.finditer(decision_pattern, content, re.DOTALL)

            for decision_match in decisions:
                decision_text = decision_match.group(1).strip()
                decision_id = self._generate_decision_id(decision_text)

                # Create decision node
                session.run(
                    """
                    MERGE (d:Decision {id: $id})
                    SET d.content = $content,
                        d.created = $created
                    RETURN d
                    """,
                    id=decision_id,
                    content=decision_text[:500],  # Store first 500 chars
                    created=session_date,
                )

                # Link decision to session
                session.run(
                    """
                    MATCH (s:ChatSession {date: $date})
                    MATCH (d:Decision {id: $id})
                    MERGE (s)-[:CONTAINS]->(d)
                    """,
                    date=session_date,
                    id=decision_id,
                )
                link_count += 1

        return link_count

    @staticmethod
    def _generate_decision_id(content: str) -> str:
        """
        Generate a unique ID for a decision based on its content.

        Args:
            content: Decision content text

        Returns:
            Generated decision ID
        """
        # Create a simple hash from the first words
        words = content.split()[:3]
        hash_input = "-".join(words).lower()[:20]
        return f"DEC-{hash(hash_input) % 10000:04d}"

    def detect_stale_tasks(self, days_threshold: int = 30) -> List[Dict]:
        """
        Find tasks that haven't been updated in a specified number of days.

        Args:
            days_threshold: Number of days to consider a task stale

        Returns:
            List of stale task information
        """
        stale_tasks = []

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task)
                WHERE t.status IN ['active', 'ready']
                  AND duration.between(
                    datetime(t.created),
                    datetime()
                  ).days > $threshold
                RETURN t.uid, t.title, t.status, t.created
                ORDER BY t.created ASC
                """,
                threshold=days_threshold,
            )

            for record in result:
                stale_tasks.append(
                    {
                        "uid": record["t.uid"],
                        "title": record["t.title"],
                        "status": record["t.status"],
                        "created": record["t.created"],
                    }
                )

        return stale_tasks


def create_percolation_engine(uri: str, user: str, password: str) -> PercolationEngine:
    """
    Factory function to create a PercolationEngine with a Neo4j connection.

    Args:
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password

    Returns:
        Configured PercolationEngine instance
    """
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return PercolationEngine(driver)
