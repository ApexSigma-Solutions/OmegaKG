"""
Omega_KG System Verification Script.
"""

import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    except AttributeError:
        # Python < 3.7 doesn't have reconfigure
        pass

from neo4j import GraphDatabase
from omega_kg.settings import settings


def main() -> None:
    """Run a six-step system verification for the Omega_KG setup and print
    a human-readable report."""
    print("\n" + "="*80)
    print("OMEGA_KG SYSTEM VERIFICATION")
    print("="*80 + "\n")

    checks_passed = 0
    checks_total = 6
    driver = None

    try:
        # Create Neo4j driver once for all checks
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

        # Check 1: Settings loaded
        try:
            print("1️⃣  Settings loaded")
            print(f"   Neo4j URI: {settings.neo4j_uri}")
            print(f"   Obsidian Vault: {settings.obsidian_vault_path}")
            checks_passed += 1
        except Exception as e:
            print(f"❌ Check 1 failed: {e}")

        print()

        # Check 2: Neo4j connection
        try:
            print("2️⃣  Attempting Neo4j connection...")
            with driver.session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j connection successful")
            checks_passed += 1
        except Exception as e:
            print(f"❌ Check 2 failed: {e}")

        print()

        # Check 3: Data exists in Neo4j
        try:
            print("3️⃣  Checking for data in Neo4j...")
            with driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = list(result)[0]['count']

            if count > 0:
                print(f"✅ Data found: {count} nodes in Neo4j")
                checks_passed += 1
            else:
                print("⚠️  Check 3 warning: No data in Neo4j yet")
                print("   (Run Step 4 in GETTING_STARTED_BEGINNER.md)")
        except Exception as e:
            print(f"❌ Check 3 failed: {e}")

        print()

        # Check 4: Tasks are queryable
        try:
            print("4️⃣  Checking if tasks can be queried...")
            with driver.session() as session:
                result = session.run("MATCH (t:Task) RETURN count(t) as count")
                task_count = list(result)[0]['count']

            if task_count > 0:
                print(f"✅ Tasks queryable: {task_count} found")
                checks_passed += 1
            else:
                print("⚠️  Check 4 warning: No tasks found yet")
        except Exception as e:
            print(f"❌ Check 4 failed: {e}")

        print()

        # Check 5: Obsidian vault structure
        try:
            print("5️⃣  Checking Obsidian vault structure...")
            vault_path = Path(settings.obsidian_vault_path)
            if vault_path.exists():
                # Use rglob for recursive counting of markdown files
                md_count = len(list(vault_path.rglob("*.md")))
                print("✅ Obsidian vault found")
                print(f"   Path: {vault_path}")
                print(f"   Markdown files: {md_count}")
                checks_passed += 1
            else:
                print("⚠️  Check 5 warning: Obsidian vault not found")
                print(f"   Expected at: {vault_path}")
        except Exception as e:
            print(f"❌ Check 5 failed: {e}")

        print()

        # Check 6: Markdown content verification
        try:
            print("6️⃣  Verifying markdown content...")
            vault_path = Path(settings.obsidian_vault_path)
            # Use rglob for recursive counting across all subdirectories
            md_file_list = list(vault_path.rglob("*.md"))

            if md_file_list:
                folder_count = len(set(f.parent for f in md_file_list))
                print(f"✅ Found {len(md_file_list)} markdown files in "
                      f"{folder_count} folders")
                checks_passed += 1
            else:
                print("⚠️  Check 6 warning: No markdown files found")
        except Exception as e:
            print(f"❌ Check 6 failed: {e}")

        print()

        # Summary
        print("="*80)
        print(f"RESULTS: {checks_passed}/{checks_total} checks passed")

        if checks_passed >= 4:
            print("✅ System is operational!")
        elif checks_passed >= 2:
            print("⚠️  System partially configured - complete setup steps")
        else:
            print("❌ System needs configuration - see "
                  "GETTING_STARTED_BEGINNER.md")

        print("="*80 + "\n")

        # Detailed node counts if data exists
        try:
            with driver.session() as session:  # type: ignore
                query = ("MATCH (n) RETURN labels(n)[0] as type, "
                         "count(*) as count ORDER BY type")
                result = session.run(query)
                records = list(result)

            if records:
                print("📊 Data breakdown in Neo4j:")
                print("-" * 40)
                for record in records:
                    type_name = record['type'] or 'Unlabeled'
                    count_val = record['count']
                    print(f"  {type_name}: {count_val} nodes")
                print("-" * 40 + "\n")
        except Exception:
            pass

    finally:
        # Ensure driver is always closed
        if driver:
            driver.close()


if __name__ == '__main__':
    main()
