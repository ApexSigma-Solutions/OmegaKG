"""
Omega_KG Task Lifecycle Enforcement
Implements time-based state transitions with email notifications
"""

from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from neo4j import GraphDatabase
import frontmatter

from omega_kg.settings import settings


class TaskStatus(Enum):
    """Task lifecycle states"""

    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class LifecycleRule:
    """Defines a lifecycle transition rule"""

    from_status: TaskStatus
    to_status: TaskStatus
    days_threshold: int
    condition: Optional[str] = None  # Cypher WHERE clause
    action: str = "auto"  # auto, warn, manual


class TaskLifecycle:
    """Enforces task lifecycle rules and generates reports"""

    # Lifecycle rules (the thermodynamics)
    RULES = [
        # Draft tasks decay to archive
        LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=14,
            condition="NOT t.pinned = true",
            action="auto",
        ),
        # Draft tasks warn before archival
        LifecycleRule(
            from_status=TaskStatus.DRAFT,
            to_status=TaskStatus.DRAFT,  # No transition, just warn
            days_threshold=10,
            condition="NOT t.pinned = true AND NOT t.warned = true",
            action="warn",
        ),
        # Active tasks stale after 30 days without commits
        LifecycleRule(
            from_status=TaskStatus.ACTIVE,
            to_status=TaskStatus.BLOCKED,  # Flag as blocked
            days_threshold=30,
            condition="NOT EXISTS((t)<-[:IMPLEMENTS]-(:Commit))",
            action="warn",
        ),
        # Completed tasks archive after 90 days
        LifecycleRule(
            from_status=TaskStatus.COMPLETED,
            to_status=TaskStatus.ARCHIVED,
            days_threshold=90,
            action="auto",
        ),
    ]

    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.vault_path = Path(settings.obsidian_vault_path)

    def enforce_lifecycle(self, dry_run: bool = False) -> Dict[str, List]:
        """
        Apply all lifecycle rules

        Returns:
            Dictionary of violations by action type
        """
        results: Dict[str, List] = {
            "archived": [],
            "warned": [],
            "blocked": [],
            "failed": [],
        }

        with self.driver.session() as session:
            for rule in self.RULES:
                violations = self._find_violations(session, rule)

                for task in violations:
                    try:
                        if dry_run:
                            print(f"[DRY RUN] Would {rule.action}: {task['t.uid']}")
                            continue

                        if rule.action == "auto":
                            self._transition_task(session, task["t.uid"], rule)
                            results[rule.to_status.value].append(task)
                        elif rule.action == "warn":
                            self._warn_task(session, task["t.uid"], rule)
                            results["warned"].append(task)

                    except Exception as e:
                        print(f"✗ Failed to process {task['t.uid']}: {e}")
                        results["failed"].append({"task": task, "error": str(e)})

        return results

    def _find_violations(self, session, rule: LifecycleRule) -> List[Dict]:
        """Find tasks violating a lifecycle rule"""

        # Build Cypher query
        query = f"""
            MATCH (t:Task)
            WHERE t.status = $from_status
              AND duration.between(t.created, datetime()).days > $days_threshold
              {f"AND ({rule.condition})" if rule.condition else ""}
            RETURN t.uid, t.title, t.filepath, t.status,
                   duration.between(t.created, datetime()).days as days_old
            ORDER BY days_old DESC
        """

        result = session.run(
            query,
            from_status=rule.from_status.value,
            days_threshold=rule.days_threshold,
        )

        return [dict(record) for record in result]

    def _transition_task(self, session, uid: str, rule: LifecycleRule):
        """Execute task status transition"""

        # Update Neo4j
        session.run(
            """
            MATCH (t:Task {uid: $uid})
            SET t.status = $new_status,
                t.transitioned_at = datetime(),
                t.transition_reason = $reason
        """,
            uid=uid,
            new_status=rule.to_status.value,
            reason=f"Lifecycle rule: {rule.from_status.value} -> {rule.to_status.value} after {rule.days_threshold} days",
        )

        # Update Obsidian file
        self._update_task_file(uid, rule.to_status.value, rule)

        print(
            f"✓ Transitioned {uid}: {rule.from_status.value} → {rule.to_status.value}"
        )

    def _warn_task(self, session, uid: str, rule: LifecycleRule):
        """Mark task as warned (prevents duplicate warnings)"""

        session.run(
            """
            MATCH (t:Task {uid: $uid})
            SET t.warned = true,
                t.warned_at = datetime()
        """,
            uid=uid,
        )

        print(f"⚠ Warned {uid}: approaching {rule.to_status.value}")

    def _update_task_file(self, uid: str, new_status: str, rule: LifecycleRule):
        """Update task note in Obsidian vault"""

        # Find task file
        task_files = list(self.vault_path.glob(f"Tasks/**/{uid}*.md"))
        if not task_files:
            print(f"  ⚠ Task file not found for {uid}")
            return

        task_path = task_files[0]

        # Update frontmatter
        with open(task_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)

        post.metadata["status"] = new_status
        post.metadata["lifecycle_transition"] = {
            "from": rule.from_status.value,
            "to": rule.to_status.value,
            "reason": f"Auto-transitioned after {rule.days_threshold} days",
            "date": datetime.now().isoformat(),
        }

        # Append notice to content
        notice = f"""

---

**🤖 Lifecycle Transition:** {rule.from_status.value} → **{new_status}**
*Reason:* Automatic transition after {rule.days_threshold} days of inactivity.
*Date:* {datetime.now().strftime('%Y-%m-%d %H:%M')}

"""
        post.content += notice

        # Write back
        with open(task_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

    def generate_report(self, results: Dict[str, List]) -> str:
        """Generate human-readable lifecycle report"""

        report_lines = [
            "🔄 Task Lifecycle Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
            "",
        ]

        # Auto-archived tasks
        if results.get("archived"):
            report_lines.append("🗄️  AUTO-ARCHIVED (14+ days draft):")
            for task in results["archived"][:10]:  # Limit to 10
                report_lines.append(
                    f"  • {task['t.uid']}: {task['t.title']} ({task['days_old']} days)"
                )
            if len(results["archived"]) > 10:
                report_lines.append(f"  ... and {len(results['archived']) - 10} more")
            report_lines.append("")

        # Warnings
        if results.get("warned"):
            report_lines.append("⚠️  WARNINGS (approaching expiry):")
            for task in results["warned"][:10]:
                days_remaining = 14 - task["days_old"]
                report_lines.append(
                    f"  • {task['t.uid']}: {task['t.title']} ({days_remaining} days until auto-archive)"
                )
            report_lines.append("")

        # Stale active tasks
        stale_active = self._get_stale_active_tasks()
        if stale_active:
            report_lines.append("🐌 STALE ACTIVE (30+ days, no commits):")
            for task in stale_active[:5]:
                report_lines.append(
                    f"  • {task['t.linear_id'] or task['t.uid']}: {task['t.title']}"
                )
            report_lines.append("")

        # Summary
        report_lines.extend(
            [
                "=" * 50,
                "SUMMARY:",
                f"  Archived: {len(results.get('archived', []))}",
                f"  Warned: {len(results.get('warned', []))}",
                f"  Stale Active: {len(stale_active)}",
                f"  Failed: {len(results.get('failed', []))}",
            ]
        )

        return "\n".join(report_lines)

    def _get_stale_active_tasks(self) -> List[Dict]:
        """Get active tasks with no recent commits"""

        with self.driver.session() as session:
            result = session.run("""
                MATCH (t:Task)
                WHERE t.status = 'active'
                  AND duration.between(t.created, datetime()).days > 30
                  AND NOT EXISTS {
                      MATCH (t)<-[:IMPLEMENTS]-(c:Commit)
                      WHERE duration.between(c.timestamp, datetime()).days < 7
                  }
                RETURN t.uid, t.title, t.linear_id,
                       duration.between(t.created, datetime()).days as days_stale
                ORDER BY days_stale DESC
                LIMIT 10
            """)

            return [dict(record) for record in result]

    def send_email_report(self, report: str):
        """Send lifecycle report via email"""

        if not all([settings.smtp_host, settings.smtp_user, settings.email_to]):
            print("⚠ Email not configured, skipping")
            return

        msg = MIMEMultipart()
        msg["From"] = settings.smtp_user
        msg["To"] = settings.email_to
        msg["Subject"] = (
            f"Omega_KG Lifecycle Report - {datetime.now().strftime('%Y-%m-%d')}"
        )

        msg.attach(MIMEText(report, "plain"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

            print("✓ Email report sent")
        except Exception as e:
            print(f"✗ Failed to send email: {e}")

    def close(self):
        self.driver.close()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Enforce Omega_KG task lifecycle")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    parser.add_argument("--no-email", action="store_true", help="Skip email report")
    args = parser.parse_args()

    lifecycle = TaskLifecycle()

    try:
        print("🔄 Running lifecycle enforcement...")
        results = lifecycle.enforce_lifecycle(dry_run=args.dry_run)

        report = lifecycle.generate_report(results)
        print(f"\n{report}")

        if not args.dry_run and not args.no_email:
            lifecycle.send_email_report(report)

    finally:
        lifecycle.close()


if __name__ == "__main__":
    main()
