import click
from omega_kg.obsidian_sync import ObsidianNeo4jSync
from tabulate import tabulate  # type: ignore


@click.group()
def cli() -> None:
    """Omega_KG Knowledge Graph CLI"""
    pass


@cli.command()
def sync() -> None:
    """Sync Obsidian vault to Neo4j"""
    sync_engine = ObsidianNeo4jSync()
    sync_engine.sync_all_tasks()
    sync_engine.close()


@cli.command()
@click.option("--days", default=7, help="Days of inactivity threshold")
def stale(days: int) -> None:
    """Show stale tasks"""
    sync_engine = ObsidianNeo4jSync()
    tasks = sync_engine.get_stale_tasks(days)

    if tasks:
        table_data = [
            [t["t.uid"], t["t.title"], t["t.created"]]
            for t in tasks
        ]
        print(
            tabulate(
                table_data,
                headers=["UID", "Title", "Created"],
                tablefmt="grid",
            )
        )
    else:
        print(f"[OK] No stale tasks (>{days} days)")

    sync_engine.close()


@cli.command()
def stats() -> None:
    """Show knowledge graph statistics"""
    sync_engine = ObsidianNeo4jSync()

    if not sync_engine.driver:
        print("[ERROR] No database connection")
        sync_engine.close()
        return

    with sync_engine.driver.session() as session:
        result = session.run(
            """
            MATCH (t:Task)
            RETURN
                count(t) as total,
                count(CASE WHEN t.status = 'draft' THEN 1 END) as draft,
                count(CASE WHEN t.status = 'active' THEN 1 END) as active,
                count(
                    CASE WHEN t.status = 'completed' THEN 1 END
                ) as completed
        """
        )
        stats_record = result.single()

    if stats_record:
        print(
            f"""
📊 Knowledge Graph Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tasks:      {stats_record['total']}
Draft:            {stats_record['draft']}
Active:           {stats_record['active']}
Completed:        {stats_record['completed']}
        """
        )

    sync_engine.close()


if __name__ == "__main__":
    cli()
