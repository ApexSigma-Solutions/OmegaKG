#!/usr/bin/env python
"""Omega_KG System Verification Script."""

import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from neo4j import GraphDatabase
from omega_kg.settings import settings


def main():
    """Run all verification checks."""
    print('\n' + '='*80)
    print('OMEGA_KG SYSTEM VERIFICATION')
    print('='*80 + '\n')

    checks_passed = 0
    checks_total = 6

    # Check 1: Settings loaded
    try:
        print('1️⃣  Settings loaded')
        print(f'   Neo4j URI: {settings.neo4j_uri}')
        print(f'   Obsidian Vault: {settings.obsidian_vault_path}\n')
        checks_passed += 1
    except Exception as e:
        print(f'❌ Check 1 failed: {e}\n')

    # Check 2: Neo4j connection
    try:
        print('2️⃣  Attempting Neo4j connection...')
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            session.run('RETURN 1')
        driver.close()
        print('✅ Neo4j connection successful\n')
        checks_passed += 1
    except Exception as e:
        print(f'❌ Check 2 failed: {e}\n')

    # Check 3: Data exists
    try:
        print('3️⃣  Checking for data in Neo4j...')
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            result = session.run('MATCH (n) RETURN count(n) as count')
            count = list(result)[0]['count']
        driver.close()

        if count > 0:
            print(f'✅ Found {count} nodes in database\n')
            checks_passed += 1
        else:
            print('⚠️  Check 3 warning: No data in Neo4j yet')
            print('   (Run Step 4 in GETTING_STARTED_BEGINNER.md)\n')
    except Exception as e:
        print(f'❌ Check 3 failed: {e}\n')

    # Check 4: Tasks queryable
    try:
        print('4️⃣  Checking if tasks can be queried...')
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        with driver.session() as session:
            result = session.run('MATCH (t:Task) RETURN count(t) as count')
            task_count = list(result)[0]['count']
        driver.close()

        if task_count > 0:
            print(f'✅ Tasks queryable: {task_count} found\n')
            checks_passed += 1
        else:
            print('⚠️  Check 4 warning: No tasks found yet\n')
    except Exception as e:
        print(f'❌ Check 4 failed: {e}\n')

    # Check 5: Obsidian vault structure
    try:
        print('5️⃣  Checking Obsidian vault structure...')
        vault_path = Path(settings.obsidian_vault_path)

        folders = {
            'Plans': 'Task plan notes',
            'Tasks': 'Task notes',
            'Archive': 'Completed plans and tasks',
            'AI_Conversations': 'Chat histories',
            'Daily': 'Daily thoughts and ideas',
            'Sessions': 'Terminal sessions'
        }

        ai_platforms = [
            'ChatGPT', 'Claude.ai', 'Gemini',
            'GitHub_Copilot', 'Perplexity', 'Qwen'
        ]

        if vault_path.exists():
            print('✅ Obsidian vault found')
            print(f'   Path: {vault_path}')

            all_exist = True

            for folder_name, description in folders.items():
                folder_path = vault_path / folder_name
                if folder_path.exists():
                    md_count = len(list(folder_path.glob('*.md')))
                    print(f'   ✅ {folder_name:20s} {md_count:3d} files')

                    if folder_name == 'AI_Conversations':
                        for platform in ai_platforms:
                            p_path = folder_path / platform
                            if p_path.exists():
                                p_count = len(list(p_path.glob('*.md')))
                                print(f'      • {platform:20s} {p_count:3d}')
                            else:
                                print(f'      • {platform:20s} (not yet)')
                else:
                    print(f'   ⚠️  {folder_name:20s} (not found)')
                    all_exist = False

            print()
            if all_exist:
                checks_passed += 1
        else:
            print('⚠️  Check 5 warning: Obsidian vault not found')
            print(f'   Expected at: {vault_path}\n')
    except Exception as e:
        print(f'❌ Check 5 failed: {e}\n')

    # Check 6: Markdown files
    try:
        print('6️⃣  Verifying markdown content...')
        vault_path = Path(settings.obsidian_vault_path)
        folders_to_check = ['Plans', 'Tasks', 'Sessions']

        total_files = 0
        folders_found = 0

        for folder_name in folders_to_check:
            folder_path = vault_path / folder_name
            if folder_path.exists():
                md_files = list(folder_path.glob('*.md'))
                total_files += len(md_files)
                if len(md_files) > 0:
                    folders_found += 1

        if total_files > 0:
            msg = f'✅ Found {total_files} markdown files in '
            print(msg + f'{folders_found} folders\n')
            checks_passed += 1
        else:
            print('⚠️  Check 6 warning: No markdown files found\n')
    except Exception as e:
        print(f'❌ Check 6 failed: {e}\n')

    # Summary
    print('='*80)
    print(f'RESULTS: {checks_passed}/{checks_total} checks passed')

    if checks_passed >= 4:
        print('✅ System is operational!')
    elif checks_passed >= 2:
        msg = '⚠️  System partially configured'
        print(f'{msg} - complete setup steps')
    else:
        msg = '❌ System needs configuration'
        print(f'{msg} - see GETTING_STARTED_BEGINNER.md')

    print('='*80 + '\n')


if __name__ == '__main__':
    main()
