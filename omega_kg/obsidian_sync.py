import frontmatter
from pathlib import Path
from neo4j import GraphDatabase
from datetime import datetime
from omega_kg.settings import settings


class ObsidianNeo4jSync:
    def __init__(self):
        self.vault_path = Path(settings.obsidian_vault_path)
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def sync_task_note(self, task_file: Path):
        """Sync a single task note to Neo4j"""
        with open(task_file, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        metadata = post.metadata
        content = post.content

        with self.driver.session() as session:
            session.run(
                """
                MERGE (t:Task {uid: $uid})
                SET t.title = $title,
                    t.status = $status,
                    t.created = datetime($created),
                    t.last_modified = datetime($modified),
                    t.filepath = $filepath,
                    t.content = $content,
                    t.parent_plan = $parent
                RETURN t
            """,
                uid=metadata.get("uid"),
                title=metadata.get("title", task_file.stem),
                status=metadata.get("status", "draft"),
                created=metadata.get("created", datetime.now().isoformat()),
                modified=datetime.fromtimestamp(task_file.stat().st_mtime).isoformat(),
                filepath=str(task_file.relative_to(self.vault_path)),
                content=content,
                parent=metadata.get("parent", None),
            )

    def sync_all_tasks(self):
        """Sync all task notes from vault to Neo4j"""
        task_files = self.vault_path.glob("Tasks/*.md")

        count = 0
        for task_file in task_files:
            try:
                self.sync_task_note(task_file)
                count += 1
                print(f"✓ Synced: {task_file.name}")
            except Exception as e:
                print(f"✗ Failed: {task_file.name} - {e}")

        print(f"\n✓ Synced {count} tasks to Neo4j")

    def get_stale_tasks(self, days_idle: int = 7):
        """Query Neo4j for tasks idle longer than N days"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task)
                WHERE t.status = 'draft'
                  AND duration.between(t.last_modified, datetime()).days > $days
                RETURN t.uid, t.title,
                       duration.between(t.last_modified, datetime()).days as idle_days
                ORDER BY idle_days DESC
            """,
                days=days_idle,
            )

            return [dict(record) for record in result]

    def close(self):
        self.driver.close()


if __name__ == "__main__":
    sync = ObsidianNeo4jSync()
    sync.sync_all_tasks()

    print("\n--- Stale Tasks (>7 days) ---")
    stale = sync.get_stale_tasks(7)
    for task in stale:
        print(f"{task['t.uid']}: {task['t.title']} ({task['idle_days']} days)")

    sync.close()
