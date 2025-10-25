"""
percolation.py

Provides functions for extracting and linking commit and task data from markdown content into the database.

This module is part of the Omega_KG package.
"""

import re
from pathlib import Path
from typing import Dict


def _percolate_session(self, path: Path, metadata: Dict, content: str):
    """Extract session with commits and link to tasks"""

    # Parse commits from markdown
    commit_pattern = r"#### Git Commit \[(.+?)\]: `(.+?)`\n(?:\*\*Linear:\*\* \[\[(.+?)\]\]\n)?```\n(.+?)\n```"
    commits = re.finditer(commit_pattern, content, re.DOTALL)

    with self.driver.session() as session:
        for commit_match in commits:
            repo, commit_hash, linear_id, message = commit_match.groups()

            # Create commit node
            session.run(
                """
                MERGE (c:Commit {hash: $hash})
                SET c.message = $message,
                    c.repo = $repo,
                    c.timestamp = datetime()

                // Link to session
                WITH c
                MATCH (s:Session {date: $date})
                MERGE (s)-[:CONTAINS_COMMIT]->(c)

                // Link to Linear task if present
                WITH c
                MATCH (t:Task {linear_id: $linear_id})
                MERGE (c)-[:IMPLEMENTS]->(t)
            """,
                hash=commit_hash,
                message=message,
                repo=repo,
                date=metadata["date"],
                linear_id=linear_id,
            )
