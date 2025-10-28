#!/usr/bin/env python#!/usr/bin/env python

"""Omega_KG System Verification Script.# -*- coding: utf-8 -*-

"""Omega_KG System Verification Script."""

Performs comprehensive checks on system configuration, Neo4j connection,import sys

Obsidian vault structure, and data availability.

"""# Set UTF-8 encoding for proper emoji display on Windows

if sys.platform == "win32":

import sys    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path

from neo4j import GraphDatabase

# Ensure UTF-8 encoding for emoji support on Windowsfrom omega_kg.settings import settings

if sys.stdout.encoding != "utf-8":from pathlib import Path

    sys.stdout.reconfigure(encoding="utf-8")

print("\n - verify_system.py:14" + "="*80)

from neo4j import GraphDatabaseprint("OMEGA_KG SYSTEM VERIFICATION - verify_system.py:15")

print("= - verify_system.py:16"*80 + "\n")

from omega_kg.settings import settings

checks_passed = 0

checks_total = 6

def main() -> None:

    """Run all verification checks."""# Check 1: Settings loaded

    print("\n" + "=" * 80)try:

    print("OMEGA_KG SYSTEM VERIFICATION")    print("1️⃣  Settings loaded - verify_system.py:23")

    print("=" * 80 + "\n")    print(f"Neo4j URI: {settings.neo4j_uri} - verify_system.py:24")

    print(f"Obsidian Vault: {settings.obsidian_vault_path} - verify_system.py:25")

    checks_passed = 0    checks_passed += 1

    checks_total = 6except Exception as e:

    print(f"❌ Check 1 failed: {e} - verify_system.py:28")

    # Check 1: Settings loaded

    try:print()

        print("1️⃣  Settings loaded")

        print(f"   Neo4j URI: {settings.neo4j_uri}")# Check 2: Neo4j connection

        print(f"   Obsidian Vault: {settings.obsidian_vault_path}\n")try:

        checks_passed += 1    print("2️⃣  Attempting Neo4j connection... - verify_system.py:34")

    except Exception as e:    driver = GraphDatabase.driver(

        print(f"❌ Check 1 failed: {e}\n")        settings.neo4j_uri,

        auth=(settings.neo4j_user, settings.neo4j_password)

    # Check 2: Neo4j connection    )

    try:    with driver.session() as session:

        print("2️⃣  Attempting Neo4j connection...")        session.run("RETURN 1")

        driver = GraphDatabase.driver(    driver.close()

            settings.neo4j_uri,    print("✅ Neo4j connection successful - verify_system.py:42")

            auth=(settings.neo4j_user, settings.neo4j_password)    checks_passed += 1

        )except Exception as e:

        with driver.session() as session:    print(f"❌ Check 2 failed: {e} - verify_system.py:45")

            session.run("RETURN 1")

        driver.close()print()

        print("✅ Neo4j connection successful\n")

        checks_passed += 1# Check 3: Data exists in Neo4j

    except Exception as e:try:

        print(f"❌ Check 2 failed: {e}\n")    print("3️⃣  Checking for data in Neo4j... - verify_system.py:51")

    driver = GraphDatabase.driver(

    # Check 3: Data exists        settings.neo4j_uri,

    try:        auth=(settings.neo4j_user, settings.neo4j_password)

        print("3️⃣  Checking for data in Neo4j...")    )

        driver = GraphDatabase.driver(    with driver.session() as session:

            settings.neo4j_uri,        result = session.run(

            auth=(settings.neo4j_user, settings.neo4j_password)            "MATCH (n) RETURN count(n) as count"

        )        )

        with driver.session() as session:        count = list(result)[0]['count']

            result = session.run("MATCH (n) RETURN count(n) as count")    driver.close()

            count = list(result)[0]["count"]

        driver.close()    if count > 0:

        print(f"✅ Data found: {count} nodes in Neo4j - verify_system.py:64")

        if count > 0:        checks_passed += 1

            print(f"✅ Found {count} nodes in database\n")    else:

            checks_passed += 1        print("⚠️  Check 3 warning: No data in Neo4j yet - verify_system.py:67")

        else:        print("(Run Step 4 in GETTING_STARTED_BEGINNER.md) - verify_system.py:68")

            print("⚠️  Check 3 warning: No data in Neo4j yet")except Exception as e:

            print("   (Run Step 4 in GETTING_STARTED_BEGINNER.md)\n")    print(f"❌ Check 3 failed: {e} - verify_system.py:70")

    except Exception as e:

        print(f"❌ Check 3 failed: {e}\n")print()



    # Check 4: Tasks queryable# Check 4: Tasks are queryable

    try:try:

        print("4️⃣  Checking if tasks can be queried...")    print("4️⃣  Checking if tasks can be queried... - verify_system.py:76")

        driver = GraphDatabase.driver(    driver = GraphDatabase.driver(

            settings.neo4j_uri,        settings.neo4j_uri,

            auth=(settings.neo4j_user, settings.neo4j_password)        auth=(settings.neo4j_user, settings.neo4j_password)

        )    )

        with driver.session() as session:    with driver.session() as session:

            result = session.run("MATCH (t:Task) RETURN count(t) as count")        result = session.run(

            task_count = list(result)[0]["count"]            "MATCH (t:Task) RETURN count(t) as count"

        driver.close()        )

        task_count = list(result)[0]['count']

        if task_count > 0:    driver.close()

            print(f"✅ Tasks queryable: {task_count} found\n")

            checks_passed += 1    if task_count > 0:

        else:        print(f"✅ Tasks queryable: {task_count} found - verify_system.py:89")

            print("⚠️  Check 4 warning: No tasks found yet\n")        checks_passed += 1

    except Exception as e:    else:

        print(f"❌ Check 4 failed: {e}\n")        print("⚠️  Check 4 warning: No tasks found yet - verify_system.py:92")

except Exception as e:

    # Check 5: Obsidian vault structure    print(f"❌ Check 4 failed: {e} - verify_system.py:94")

    try:

        print("5️⃣  Checking Obsidian vault structure...")print()

        vault_path = Path(settings.obsidian_vault_path)

# Check 5: Obsidian vault structure

        # Define expected folder structuretry:

        folders = {    print("5️⃣  Checking Obsidian vault structure... - verify_system.py:100")

            "Plans": "Task plan notes",    vault_path = Path(settings.obsidian_vault_path)

            "Tasks": "Task notes",

            "Archive": "Completed plans and tasks",    # Define expected folder structure

            "AI_Conversations": "Chat histories",    folders = {

            "Daily": "Daily thoughts and ideas",        "Plans": "Task plan notes",

            "Sessions": "Terminal sessions"        "Tasks": "Task notes",

        }        "Archive": "Completed plans and tasks",

        "AI_Conversations": "Chat histories",

        # AI platforms within AI_Conversations        "Daily": "Daily thoughts and ideas",

        ai_platforms = [        "Sessions": "Terminal sessions"

            "ChatGPT",    }

            "Claude.ai",

            "Gemini",    # AI platforms within AI_Conversations

            "GitHub_Copilot",    ai_platforms = [

            "Perplexity",        "ChatGPT",

            "Qwen"        "Claude.ai",

        ]        "Gemini",

        "GitHub_Copilot",

        if vault_path.exists():        "Perplexity",

            print("✅ Obsidian vault found")        "Qwen"

            print(f"   Path: {vault_path}")    ]



            # Check folder structure    if vault_path.exists():

            all_exist = True        print("✅ Obsidian vault found - verify_system.py:124")

        print(f"Path: {vault_path} - verify_system.py:125")

            for folder_name, description in folders.items():

                folder_path = vault_path / folder_name        # Check folder structure

                if folder_path.exists():        all_exist = True

                    md_count = len(list(folder_path.glob("*.md")))        folder_info = {}

                    print(f"   ✅ {folder_name:20s} {md_count:3d} files")

        for folder_name, description in folders.items():

                    # For AI_Conversations, check platform subdirectories            folder_path = vault_path / folder_name

                    if folder_name == "AI_Conversations":            if folder_path.exists():

                        for platform in ai_platforms:                md_count = len(list(folder_path.glob("*.md")))

                            platform_path = folder_path / platform                folder_info[folder_name] = md_count

                            if platform_path.exists():                print(f"✅ {folder_name:20s} {md_count:3d} files - verify_system.py:136")

                                p_md_count = len(

                                    list(platform_path.glob("*.md"))                # For AI_Conversations, check platform subdirectories

                                )                if folder_name == "AI_Conversations":

                                print(f"      • {platform:20s} {p_md_count:3d}")                    for platform in ai_platforms:

                            else:                        platform_path = folder_path / platform

                                print(f"      • {platform:20s} (not yet)")                        if platform_path.exists():

                else:                            p_md_count = len(

                    print(f"   ⚠️  {folder_name:20s} (not found)")                                list(platform_path.glob("*.md"))

                    all_exist = False                            )

                            print(f"• {platform:20s} {p_md_count:3d} - verify_system.py:146")

            print()                        else:

            if all_exist:                            print(f"• {platform:20s} (not yet) - verify_system.py:148")

                checks_passed += 1            else:

        else:                print(f"⚠️  {folder_name:20s} (not found) - verify_system.py:150")

            print("⚠️  Check 5 warning: Obsidian vault not found")                all_exist = False

            print(f"   Expected at: {vault_path}\n")

    except Exception as e:        if all_exist:

        print(f"❌ Check 5 failed: {e}\n")            checks_passed += 1

    else:

    # Check 6: Markdown files readable        print("⚠️  Check 5 warning: Obsidian vault not found - verify_system.py:156")

    try:        print(f"Expected at: {vault_path} - verify_system.py:157")

        print("6️⃣  Verifying markdown content...")except Exception as e:

        vault_path = Path(settings.obsidian_vault_path)    print(f"❌ Check 5 failed: {e} - verify_system.py:159")

        folders_to_check = ["Plans", "Tasks", "Sessions"]

print()

        total_files = 0

        folders_found = 0# Check 6: Markdown content verification

try:

        for folder_name in folders_to_check:    print("6️⃣  Verifying markdown content... - verify_system.py:165")

            folder_path = vault_path / folder_name    vault_path = Path(settings.obsidian_vault_path)

            if folder_path.exists():

                md_files = list(folder_path.glob("*.md"))    # Define folders to check

                total_files += len(md_files)    folders_to_check = [

                if len(md_files) > 0:        "Plans", "Tasks", "Archive",

                    folders_found += 1        "AI_Conversations", "Daily", "Sessions"

    ]

        if total_files > 0:

            print(f"✅ Found {total_files} markdown files in "    total_md_files = 0

                  f"{folders_found} folders\n")    folders_with_content = 0

            checks_passed += 1

        else:    for folder_name in folders_to_check:

            print("⚠️  Check 6 warning: No markdown files found\n")        folder_path = vault_path / folder_name

    except Exception as e:        if folder_path.exists():

        print(f"❌ Check 6 failed: {e}\n")            md_files = list(folder_path.glob("*.md"))

            total_md_files += len(md_files)

    # Summary            if len(md_files) > 0:

    print("=" * 80)                folders_with_content += 1

    print(f"RESULTS: {checks_passed}/{checks_total} checks passed")

    if total_md_files > 0:

    if checks_passed >= 4:        print(

        print("✅ System is operational!")            f"✅ Found {total_md_files} markdown files "

    elif checks_passed >= 2:            f"in {folders_with_content} folders"

        msg = "⚠️  System partially configured"        )

        print(f"{msg} - complete setup steps")        checks_passed += 1

    else:    else:

        msg = "❌ System needs configuration"        msg = "⚠️  Check 6 warning: No markdown files in folders"

        print(f"{msg} - see GETTING_STARTED_BEGINNER.md")        print(msg)

except Exception as e:

    print("=" * 80 + "\n")    print(f"❌ Check 6 failed: {e} - verify_system.py:195")



    # Detailed node counts if data existsprint()

    try:

        driver = GraphDatabase.driver(# Summary

            settings.neo4j_uri,print("= - verify_system.py:200" * 80)

            auth=(settings.neo4j_user, settings.neo4j_password)print(f"RESULTS: {checks_passed}/{checks_total} checks passed - verify_system.py:201")

        )

        with driver.session() as session:if checks_passed >= 4:

            query = ("MATCH (n) RETURN labels(n)[0] as type, "    print("✅ System is operational! - verify_system.py:204")

                     "count(*) as count ORDER BY type")elif checks_passed >= 2:

            result = session.run(query)    msg = "⚠️  System partially configured"

            records = list(result)    print(f"{msg}  complete setup steps - verify_system.py:207")

        driver.close()else:

    msg = "❌ System needs configuration"

        if records:    print(f"{msg}  see GETTING_STARTED_BEGINNER.md - verify_system.py:210")

            print("📊 Data breakdown in Neo4j:")

            print("-" * 40)print("= - verify_system.py:212" * 80 + "\n")

            for record in records:

                type_name = record["type"]# Detailed node counts if data exists

                count_val = record["count"]try:

                print(f"  {type_name}: {count_val} nodes")    driver = GraphDatabase.driver(

            print("-" * 40 + "\n")        settings.neo4j_uri,

    except Exception:        auth=(settings.neo4j_user, settings.neo4j_password)

        pass    )

    with driver.session() as session:

        query = ("MATCH (n) RETURN labels(n)[0] as type, "

if __name__ == "__main__":                 "count(*) as count ORDER BY type")

    main()        result = session.run(query)

        records = list(result)
    driver.close()

    if records:
        print("📊 Data breakdown in Neo4j: - verify_system.py:228")
        print("" * 40)
        for record in records:
            type_name = record['type']
            count_val = record['count']
            print(f"{type_name}: {count_val} nodes - verify_system.py:233")
        print("" * 40 + "\n")
except Exception:
    pass
