#!/usr/bin/env python
"""Omega_KG System Verification Script."""

from neo4j import GraphDatabase
from omega_kg.settings import settings
from pathlib import Path

print("\n" + "="*80)
print("OMEGA_KG SYSTEM VERIFICATION")
print("="*80 + "\n")

checks_passed = 0
checks_total = 6

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
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    with driver.session() as session:
        session.run("RETURN 1")
    driver.close()
    print("✅ Neo4j connection successful")
    checks_passed += 1
except Exception as e:
    print(f"❌ Check 2 failed: {e}")

print()

# Check 3: Data exists in Neo4j
try:
    print("3️⃣  Checking for data in Neo4j...")
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    with driver.session() as session:
        result = session.run(
            "MATCH (n) RETURN count(n) as count"
        )
        count = list(result)[0]['count']
    driver.close()

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
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    with driver.session() as session:
        result = session.run(
            "MATCH (t:Task) RETURN count(t) as count"
        )
        task_count = list(result)[0]['count']
    driver.close()

    if task_count > 0:
        print(f"✅ Tasks queryable: {task_count} found")
        checks_passed += 1
    else:
        print("⚠️  Check 4 warning: No tasks found yet")
except Exception as e:
    print(f"❌ Check 4 failed: {e}")

print()

# Check 5: Obsidian vault exists
try:
    print("5️⃣  Checking Obsidian vault...")
    vault_path = Path(settings.obsidian_vault_path)
    if vault_path.exists():
        md_files = len(list(vault_path.glob("*.md")))
        print("✅ Obsidian vault found")
        print(f"   Path: {vault_path}")
        print(f"   Markdown files: {md_files}")
        checks_passed += 1
    else:
        print("⚠️  Check 5 warning: Obsidian vault not found")
        print(f"   Expected at: {vault_path}")
except Exception as e:
    print(f"❌ Check 5 failed: {e}")

print()

# Check 6: Can read markdown files
try:
    print("6️⃣  Checking markdown files...")
    vault_path = Path(settings.obsidian_vault_path)
    md_files = list(vault_path.glob("*.md"))

    if md_files:
        print(f"✅ Markdown files readable: {len(md_files)}")
        checks_passed += 1
    else:
        msg = "⚠️  Check 6 warning: No markdown files"
        print(msg)
except Exception as e:
    print(f"❌ Check 6 failed: {e}")

print()

# Summary
print("="*80)
print(f"RESULTS: {checks_passed}/{checks_total} checks passed")

if checks_passed >= 4:
    print("✅ System is operational!")
elif checks_passed >= 2:
    msg = "⚠️  System partially configured"
    print(f"{msg} - complete setup steps")
else:
    msg = "❌ System needs configuration"
    print(f"{msg} - see GETTING_STARTED_BEGINNER.md")

print("="*80 + "\n")

# Detailed node counts if data exists
try:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    with driver.session() as session:
        query = ("MATCH (n) RETURN labels(n)[0] as type, "
                 "count(*) as count ORDER BY type")
        result = session.run(query)
        records = list(result)
    driver.close()

    if records:
        print("📊 Data breakdown in Neo4j:")
        print("-" * 40)
        for record in records:
            type_name = record['type']
            count_val = record['count']
            print(f"  {type_name}: {count_val} nodes")
        print("-" * 40 + "\n")
except Exception:
    pass
