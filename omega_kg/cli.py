"""
Omega_KG Command Line Interface
Unified entry point for all operations
"""

import click

from omega_kg.lifecycle import TaskLifecycle
from omega_kg.neo4j_schema import KnowledgeGraphSchema


@click.group()
def cli():
    """Omega_KG Knowledge Graph CLI"""
    pass


@cli.command()
def init():
    """Initialize Neo4j schema"""
    click.echo("🔧 Initializing Neo4j schema...")
    schema = KnowledgeGraphSchema()
    schema.initialize_schema()
    schema.create_sample_relationships()
    schema.close()
    click.echo("✓ Schema initialized")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Preview changes")
@click.option("--no-email", is_flag=True, help="Skip email report")
def lifecycle(dry_run, no_email):
    """Enforce task lifecycle rules"""
    lc = TaskLifecycle()

    try:
        click.echo("🔄 Running lifecycle enforcement...")
        results = lc.enforce_lifecycle(dry_run=dry_run)

        report = lc.generate_report(results)
        click.echo(f"\n{report}")

        if not dry_run and not no_email:
            lc.send_email_report(report)

    finally:
        lc.close()


@cli.command()
def stats():
    """Show knowledge graph statistics"""
    from omega_kg.obsidian_sync import ObsidianNeo4jSync

    click.echo("\n✓ Neo4j connection established\n")
    click.echo("📊 Knowledge Graph Statistics")
    click.echo("━" * 35)

    sync = ObsidianNeo4jSync()
    status = sync.get_connection_status()

    if not status["connected"]:
        click.echo("[WARN] Running in mock mode (no connection)")
        sync.close()
        return

    try:
        from neo4j import GraphDatabase
        from omega_kg.settings import settings

        driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )

        with driver.session() as session:
            result = session.run("""
                MATCH (t:Task)
                RETURN count(t) as total,
                       count(CASE WHEN t.status = 'draft'
                             THEN 1 END) as draft,
                       count(CASE WHEN t.status = 'active'
                             THEN 1 END) as active,
                       count(CASE WHEN t.status = 'completed'
                             THEN 1 END) as completed,
                       count(CASE WHEN t.status = 'archived'
                             THEN 1 END) as archived
            """)
            record = result.single()

        driver.close()

        if record:
            click.echo(f"Total Tasks:      {record['total']}")
            click.echo(f"Draft:            {record['draft']}")
            click.echo(f"Active:           {record['active']}")
            click.echo(f"Completed:        {record['completed']}")
            click.echo(f"Archived:         {record['archived']}")
        else:
            click.echo("No tasks found")

    finally:
        sync.close()


@cli.command()
def stale():
    """Show stale tasks"""
    from omega_kg.obsidian_sync import ObsidianNeo4jSync

    sync = ObsidianNeo4jSync()
    stale = sync.get_stale_tasks(7)

    if stale:
        click.echo("\n--- Stale Tasks (>7 days) ---")
        for task in stale:
            click.echo(
                f"{task['t.uid']}: {task['t.title']} " f"(created: {task['t.created']})"
            )
    else:
        click.echo("(none)")

    sync.close()


if __name__ == "__main__":
    cli()
