# Omega_KG Beginner's Guide

**Getting Started with Knowledge Graph Management**

Welcome! This guide walks you through setting up and using Omega_KG for the first time. By the end, you'll have data flowing into Neo4j and syncing with Obsidian.

---

## Table of Contents

1. [What is Omega_KG?](#what-is-omega_kg)
2. [Prerequisites & Installation](#prerequisites--installation)
3. [Step 1: Initial Setup](#step-1-initial-setup)
4. [Step 2: Start Neo4j](#step-2-start-neo4j)
5. [Step 3: Verify Database Connection](#step-3-verify-database-connection)
6. [Step 4: Populate Test Data](#step-4-populate-test-data)
7. [Step 5: Query Data in Neo4j](#step-5-query-data-in-neo4j)
8. [Step 6: Set Up Obsidian Sync](#step-6-set-up-obsidian-sync)
9. [Step 7: Run Lifecycle Management](#step-7-run-lifecycle-management)
10. [Verification Checklist](#verification-checklist)
11. [Common Tasks](#common-tasks)
12. [Troubleshooting](#troubleshooting)

---

## What is Omega_KG?

Omega_KG is a **knowledge management system** that:

- **Captures** information from conversations and documents
- **Stores** everything in a Neo4j graph database
- **Syncs** tasks and decisions with Obsidian markdown files
- **Manages** task lifecycles automatically (draft → ready → active → completed → archived)
- **Integrates** with Linear for team task management

**Key Concepts:**

| Term | Meaning |
|------|---------|
| **Neo4j** | Graph database that stores all your data (conversations, tasks, commits, decisions) |
| **Obsidian** | Note-taking app where markdown files sync with Neo4j |
| **Task** | An item to do, with status (draft, ready, active, completed) |
| **Session** | A conversation or meeting where decisions are made |
| **Decision** | A conclusion or plan captured in a session |

---

## Prerequisites & Installation

### System Requirements

Before starting, ensure you have:

```bash
# Check Python version (3.14+ required)
python --version

# Check Git is installed
git --version

# Check Poetry is installed
poetry --version
```

If anything is missing:

```bash
# Install Python 3.14+
# Download from https://www.python.org/downloads/

# Install Poetry
# See: https://python-poetry.org/docs/#installation

# Install Git
# Download from https://git-scm.com/download/win
```

### 1. Clone the Repository

```bash
cd C:\Users\YourName\OneDrive\ApexSigma
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg
```

### 2. Install Dependencies

```bash
poetry install --with dev
```

This creates a virtual environment with all required packages.

### 3. Create Environment Configuration

```bash
# Copy the template
Copy-Item .env.example .env

# Edit .env with your values
notepad .env
```

**Example .env file (for local development):**

```bash
APP_ENV=development
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me-to-your-password
OBSIDIAN_VAULT_PATH=C:\Users\YourName\Obsidian\MyVault
```

**Important fields:**

- `NEO4J_URI`: Connection to Neo4j (use `bolt://` for local or cloud)
- `OBSIDIAN_VAULT_PATH`: Full path to your Obsidian vault folder
- All other fields are optional for basic setup

---

## Step 1: Initial Setup

### Verify Installation

```bash
# Activate the virtual environment
poetry shell

# Verify imports work
poetry run python -c "from omega_kg.settings import settings; print('✅ Import successful')"

# Check settings loaded
poetry run python -c "from omega_kg.settings import settings; print(f'Neo4j URI: {settings.neo4j_uri}')"
```

Expected output:

```
✅ Import successful
Neo4j URI: bolt://localhost:7687
```

### View Project Structure

```bash
# See the main modules
ls omega_kg/

# Expected files:
# - settings.py          (Configuration)
# - lifecycle.py         (Task automation)
# - linear_sync.py       (Obsidian sync)
# - percolation.py       (Data extraction)
# - poc_okg.py           (Proof of concept)
# - neo4j_schema.py      (Database schema)
```

---

## Step 2: Start Neo4j

Neo4j is your database. You need to start it before running Omega_KG.

### Option A: Docker (Recommended for Beginners)

```bash
# Start Neo4j container
docker-compose up -d neo4j-db

# Verify it's running
docker ps | findstr neo4j

# Wait 30 seconds for startup
Start-Sleep -Seconds 30
```

### Option B: Neo4j Desktop (GUI)

1. Download Neo4j Desktop from https://neo4j.com/download/
2. Create a new database (use password from .env)
3. Start the database
4. Browser will open at http://localhost:7474

### Option C: Neo4j Cloud

If using cloud Neo4j:

```bash
# Update .env with cloud credentials
NEO4J_URI=neo4j+s://abc123.databases.neo4j.io:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-cloud-password
```

---

## Step 3: Verify Database Connection

### Test Connection

```bash
# Run the connection test script
poetry run python -c "
from neo4j import GraphDatabase
from omega_kg.settings import settings

try:
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    with driver.session() as session:
        result = session.run('RETURN \"Neo4j is running!\" as message')
        for record in result:
            print(f'✅ {record[\"message\"]}')
    driver.close()
except Exception as e:
    print(f'❌ Connection failed: {e}')
"
```

Expected output:

```
✅ Neo4j is running!
```

### Access Neo4j Browser

**Local Neo4j:**

1. Open http://localhost:7474
2. Username: `neo4j`
3. Password: (your password from .env)

**First time login:**

- You'll be asked to change the default password
- Use the password from your `.env` file

---

## Step 4: Populate Test Data

Now let's add some sample data to Neo4j so you can see how it works.

### Method 1: Using the Proof of Concept Script

```bash
# Run the POC script to create sample data
poetry run python -m omega_kg.poc_okg
```

This creates:

- 1 ChatSession with topic "Product Strategy"
- 2 Decisions within that session
- 3 Tasks linked to those decisions
- 2 Commits showing implementation

### Method 2: Manual Data Creation

If the POC script doesn't work, create data manually:

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings
from datetime import datetime

# Connect to Neo4j
driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    # Create a ChatSession
    session.run("""
        CREATE (s:ChatSession {
            date: $date,
            topic: $topic
        })
    """, date=datetime.now().isoformat(), topic="Getting Started Demo")
    
    # Create a Decision
    session.run("""
        CREATE (d:Decision {
            content: $content
        })
    """, content="Use Neo4j as the primary data store")
    
    # Create a Task
    session.run("""
        CREATE (t:Task {
            uid: $uid,
            title: $title,
            status: $status,
            created: $created
        })
    """, uid="DEMO-001", title="Set up Neo4j database", status="completed", created=datetime.now().isoformat())
    
    print("✅ Sample data created successfully")

driver.close()
EOF
```

Expected output:

```
✅ Sample data created successfully
```

---

## Step 5: Query Data in Neo4j

Now let's verify the data was stored and learn how to query it.

### Query 1: Count All Nodes

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(*) as count")
    
    print("\n📊 Data in Neo4j:")
    print("-" * 40)
    for record in result:
        print(f"  {record['type']}: {record['count']} nodes")
    print("-" * 40 + "\n")

driver.close()
EOF
```

Expected output:

```
📊 Data in Neo4j:
----------------------------------------
  ChatSession: 1 nodes
  Decision: 1 nodes
  Task: 1 nodes
  Commit: 0 nodes
----------------------------------------
```

### Query 2: Find All Tasks and Their Status

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    result = session.run("""
        MATCH (t:Task)
        RETURN t.uid, t.title, t.status, t.created
        ORDER BY t.created DESC
    """)
    
    print("\n📋 All Tasks:")
    print("-" * 60)
    for record in result:
        print(f"  ID: {record['t.uid']}")
        print(f"  Title: {record['t.title']}")
        print(f"  Status: {record['t.status']}")
        print(f"  Created: {record['t.created']}")
        print("-" * 60)

driver.close()
EOF
```

Expected output:

```
📋 All Tasks:
------------------------------------------------------------
  ID: DEMO-001
  Title: Set up Neo4j database
  Status: completed
  Created: 2025-10-28T10:30:45.123456
------------------------------------------------------------
```

### Query 3: Show Decision → Task Links

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    result = session.run("""
        MATCH (d:Decision)-[:IMPLEMENTS]->(t:Task)
        RETURN d.content as decision, t.title as task, t.status as status
    """)
    
    print("\n🔗 Decisions linked to Tasks:")
    print("-" * 70)
    count = 0
    for record in result:
        print(f"  Decision: {record['decision']}")
        print(f"    └→ Task: {record['task']} [{record['status']}]")
        print()
        count += 1
    
    if count == 0:
        print("  (No links found - create some data first!)")
    print("-" * 70 + "\n")

driver.close()
EOF
```

### Query 4: Using Neo4j Browser (GUI)

You can also use the Neo4j Browser for visual queries:

```cypher
# Paste these in Neo4j Browser at http://localhost:7474

# See all nodes and relationships
MATCH (n) RETURN n LIMIT 25

# Count nodes by type
MATCH (n) RETURN labels(n)[0] as type, count(*) as count

# Show all tasks with their status
MATCH (t:Task) RETURN t.uid, t.title, t.status

# Show relationships
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 10
```

---

## Step 6: Set Up Obsidian Sync

Obsidian Sync automatically keeps your markdown files in sync with Neo4j.

### Prerequisites

- Obsidian installed (https://obsidian.md)
- An Obsidian vault created
- Path to vault set in `.env` (OBSIDIAN_VAULT_PATH)

### Create Test Markdown Files

Create a test task file in your Obsidian vault:

```bash
# Create a markdown file
$vaultPath = (Select-String -Path .env -Pattern 'OBSIDIAN_VAULT_PATH=(.+)' | % { $_.Matches.Groups[1].Value })
$testFile = "$vaultPath/TASK-TEST-001.md"

@"
---
uid: TASK-TEST-001
title: Complete Omega_KG setup
status: ready
linear_id: 
created: 2025-10-28
---

# Complete Omega_KG Setup

## Overview
This is a test task created in Obsidian to verify sync with Neo4j.

## Steps
- [ ] Install Omega_KG
- [ ] Configure Neo4j
- [ ] Test data creation
- [ ] Verify Obsidian sync

## Related Decisions
- Use Neo4j as primary database
- Implement markdown-first workflow
"@ | Out-File -FilePath $testFile -Encoding UTF8

Write-Host "✅ Created test file: $testFile"
```

### Sync File to Neo4j

```bash
# Extract frontmatter and create Neo4j node
poetry run python << 'EOF'
import frontmatter
from pathlib import Path
from neo4j import GraphDatabase
from omega_kg.settings import settings

# Path to the markdown file
vault_path = settings.obsidian_vault_path
test_file = Path(vault_path) / "TASK-TEST-001.md"

# Read frontmatter
with open(test_file, 'r', encoding='utf-8') as f:
    post = frontmatter.load(f)

metadata = post.metadata
content = post.content

# Create/update in Neo4j
driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    session.run("""
        MERGE (t:Task {uid: $uid})
        SET t.title = $title,
            t.status = $status,
            t.filepath = $filepath,
            t.created = $created,
            t.content = $content
    """,
    uid=metadata.get('uid'),
    title=metadata.get('title'),
    status=metadata.get('status'),
    filepath=str(test_file),
    created=metadata.get('created'),
    content=content)
    
    print("✅ Task synced from Obsidian to Neo4j")

driver.close()
EOF
```

### Verify Sync

Query Neo4j to confirm the file was synced:

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    result = session.run("""
        MATCH (t:Task {uid: 'TASK-TEST-001'})
        RETURN t.uid, t.title, t.status, t.filepath
    """)
    
    records = list(result)
    if records:
        r = records[0]
        print(f"\n✅ Obsidian Sync Verified:")
        print(f"   UID: {r['t.uid']}")
        print(f"   Title: {r['t.title']}")
        print(f"   Status: {r['t.status']}")
        print(f"   File: {r['t.filepath']}\n")
    else:
        print("\n❌ Task not found in Neo4j\n")

driver.close()
EOF
```

---

## Step 7: Run Lifecycle Management

Task lifecycle automatically transitions tasks between states based on time and conditions.

### Understand Task States

```
draft (new task)
   ↓ (after 14 days if not pinned) OR (manual transition)
ready (ready to work on)
   ↓ (manual start)
active (currently being worked)
   ↓ (after 30 days without commits OR manual)
blocked (waiting on something)
   ↓ (resolved, manual restart)
active (back to work)
   ↓ (manual completion)
completed (done!)
   ↓ (cleanup, manual)
archived (old completed tasks)
```

### Check Current Task States

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    result = session.run("""
        MATCH (t:Task)
        RETURN t.uid, t.title, t.status, t.created, t.transitioned_at
        ORDER BY t.status, t.created DESC
    """)
    
    print("\n📈 Task Lifecycle Status:")
    print("-" * 80)
    
    by_status = {}
    for record in result:
        status = record['t.status']
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(record)
    
    for status in ['draft', 'ready', 'active', 'blocked', 'completed', 'archived']:
        tasks = by_status.get(status, [])
        print(f"\n{status.upper()} ({len(tasks)} tasks):")
        for t in tasks:
            print(f"  • {t['t.uid']}: {t['t.title']}")
    
    print("\n" + "-" * 80 + "\n")

driver.close()
EOF
```

### Run Lifecycle Enforcement (Dry-Run)

Dry-run shows what WOULD happen without making changes:

```bash
poetry run python -m omega_kg.lifecycle --dry-run
```

Expected output:

```
INFO - Loading task lifecycle rules...
INFO - Connecting to Neo4j...
INFO - Running in DRY-RUN mode (no changes will be made)
INFO - Checking 5 tasks for lifecycle transitions...
INFO - Task DEMO-001: draft → archive (age: 15 days, pinned: false)
INFO - 1 task(s) would transition
INFO - Lifecycle enforcement complete (dry-run)
```

### Apply Lifecycle Changes

**Warning: This makes real changes to the database!**

```bash
poetry run python -m omega_kg.lifecycle
```

This will:
- Archive draft tasks older than 14 days (if not pinned)
- Warn about tasks about to expire
- Move active tasks to blocked after 30 days without commits
- Send email notifications (if configured)

---

## Verification Checklist

Use this checklist to verify everything is working:

```bash
# Run all verification checks
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings
from pathlib import Path

print("\n" + "="*80)
print("OMEGA_KG VERIFICATION CHECKLIST")
print("="*80 + "\n")

checks_passed = 0
checks_total = 6

# Check 1: Settings loaded
try:
    print("✓ Check 1: Settings loaded")
    print(f"  Neo4j URI: {settings.neo4j_uri}")
    print(f"  Obsidian Vault: {settings.obsidian_vault_path}")
    checks_passed += 1
except Exception as e:
    print(f"✗ Check 1 failed: {e}")

# Check 2: Neo4j connection
try:
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    with driver.session() as session:
        session.run("RETURN 1")
    driver.close()
    print("✓ Check 2: Neo4j connection successful")
    checks_passed += 1
except Exception as e:
    print(f"✗ Check 2 failed: {e}")

# Check 3: Data exists
try:
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as count")
        count = list(result)[0]['count']
    driver.close()
    if count > 0:
        print(f"✓ Check 3: Data exists in Neo4j ({count} nodes)")
        checks_passed += 1
    else:
        print("✗ Check 3 failed: No data in Neo4j (run Step 4)")
except Exception as e:
    print(f"✗ Check 3 failed: {e}")

# Check 4: Tasks can be queried
try:
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    with driver.session() as session:
        result = session.run("MATCH (t:Task) RETURN count(t) as count")
        count = list(result)[0]['count']
    driver.close()
    if count > 0:
        print(f"✓ Check 4: Tasks are queryable ({count} tasks)")
        checks_passed += 1
    else:
        print("✗ Check 4 failed: No tasks found (run Step 4)")
except Exception as e:
    print(f"✗ Check 4 failed: {e}")

# Check 5: Obsidian vault exists
try:
    vault_path = Path(settings.obsidian_vault_path)
    if vault_path.exists():
        print(f"✓ Check 5: Obsidian vault exists")
        print(f"  Path: {vault_path}")
        checks_passed += 1
    else:
        print(f"✗ Check 5 failed: Obsidian vault not found at {vault_path}")
except Exception as e:
    print(f"✗ Check 5 failed: {e}")

# Check 6: Can read markdown
try:
    import frontmatter
    vault_path = Path(settings.obsidian_vault_path)
    md_files = list(vault_path.glob("*.md"))
    if len(md_files) > 0:
        print(f"✓ Check 6: Markdown files found ({len(md_files)} files)")
        checks_passed += 1
    else:
        print("✗ Check 6 failed: No markdown files in vault")
except Exception as e:
    print(f"✗ Check 6 failed: {e}")

# Summary
print("\n" + "-"*80)
print(f"RESULTS: {checks_passed}/{checks_total} checks passed")
if checks_passed == checks_total:
    print("✅ All systems operational!")
else:
    print(f"⚠️  {checks_total - checks_passed} checks failed - see above for details")
print("-"*80 + "\n")
EOF
```

---

## Common Tasks

### Task 1: Create a New Task in Neo4j

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings
from datetime import datetime

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    session.run("""
        CREATE (t:Task {
            uid: $uid,
            title: $title,
            status: $status,
            created: $created,
            pinned: false
        })
    """,
    uid="TASK-20251028-001",
    title="Example: Create a new task",
    status="draft",
    created=datetime.now().isoformat())
    
    print("✅ Task created: TASK-20251028-001")

driver.close()
EOF
```

### Task 2: Update a Task Status

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings
from datetime import datetime

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    session.run("""
        MATCH (t:Task {uid: $uid})
        SET t.status = $status,
            t.transitioned_at = $now
    """,
    uid="TASK-20251028-001",
    status="active",
    now=datetime.now().isoformat())
    
    print("✅ Task TASK-20251028-001 status changed to 'active'")

driver.close()
EOF
```

### Task 3: Link a Task to a Decision

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    # First, ensure both nodes exist
    session.run("""
        MERGE (d:Decision {content: $decision_content})
        MERGE (t:Task {uid: $task_uid})
        MERGE (d)-[:IMPLEMENTS]->(t)
    """,
    decision_content="Implement knowledge graph system",
    task_uid="TASK-20251028-001")
    
    print("✅ Linked Decision → Task")

driver.close()
EOF
```

### Task 4: Pin a Task (Prevent Auto-Archive)

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    session.run("""
        MATCH (t:Task {uid: $uid})
        SET t.pinned = true
    """, uid="TASK-20251028-001")
    
    print("✅ Task pinned (will not auto-archive)")

driver.close()
EOF
```

### Task 5: Export All Tasks to CSV

```bash
poetry run python << 'EOF'
import csv
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))

with driver.session() as session:
    result = session.run("""
        MATCH (t:Task)
        RETURN t.uid, t.title, t.status, t.created, t.filepath
        ORDER BY t.created DESC
    """)
    
    # Write to CSV
    with open('tasks_export.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['UID', 'Title', 'Status', 'Created', 'File Path'])
        for record in result:
            writer.writerow([
                record['t.uid'],
                record['t.title'],
                record['t.status'],
                record['t.created'],
                record['t.filepath']
            ])
    
    print("✅ Tasks exported to tasks_export.csv")

driver.close()
EOF
```

---

## Troubleshooting

### Problem: "Connection refused" when connecting to Neo4j

**Causes:**
- Neo4j is not running
- Wrong URI in .env
- Neo4j crashed

**Solutions:**

```bash
# Check if Neo4j is running
docker ps | findstr neo4j

# Start Neo4j if stopped
docker-compose up -d neo4j-db

# View Neo4j logs
docker-compose logs neo4j-db

# Verify correct URI
cat .env | findstr NEO4J_URI
```

### Problem: "Authentication failed" when connecting

**Causes:**
- Wrong password in .env
- Neo4j default password still in use

**Solutions:**

```bash
# Verify password in .env
cat .env | findstr NEO4J_PASSWORD

# Reset Neo4j password (requires stopping container)
docker-compose down
docker volume rm apexsigma.neo4j.data  # ⚠️ Deletes data
docker-compose up -d neo4j-db
```

### Problem: "No such file or directory" for Obsidian vault

**Causes:**
- Wrong path in .env
- Path doesn't exist

**Solutions:**

```bash
# Check vault path
cat .env | findstr OBSIDIAN_VAULT_PATH

# Verify path exists
Test-Path C:\Users\YourName\Obsidian\MyVault

# Create vault if missing
mkdir C:\Users\YourName\Obsidian\MyVault
```

### Problem: Markdown files not syncing to Neo4j

**Causes:**
- Frontmatter format incorrect
- File encoding is not UTF-8
- Module not running

**Solutions:**

```bash
# Check file has correct frontmatter
head -n 10 $vaultPath/TASK-001.md

# Ensure UTF-8 encoding
# In notepad: File → Save As → Encoding: UTF-8

# Test sync script manually
poetry run python << 'EOF'
import frontmatter
from pathlib import Path

file_path = Path(r"C:\path\to\file.md")
with open(file_path, 'r', encoding='utf-8') as f:
    post = frontmatter.load(f)
    print(f"Metadata: {post.metadata}")
    print(f"Content length: {len(post.content)}")
EOF
```

### Problem: "Module not found" errors

**Causes:**
- Poetry environment not activated
- Dependencies not installed

**Solutions:**

```bash
# Enter poetry environment
poetry shell

# Reinstall dependencies
poetry install --with dev

# Check import works
poetry run python -c "from omega_kg.settings import settings"
```

### Problem: Queries in Neo4j return no results

**Causes:**
- Data hasn't been created yet
- Query syntax is wrong
- Nodes don't have expected properties

**Solutions:**

```bash
# Create sample data first
poetry run python -m omega_kg.poc_okg

# Run simple query to verify data exists
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (n) RETURN n LIMIT 5")
    for record in result:
        print(record)
driver.close()
EOF
```

---

## Next Steps

Once you've completed this guide:

1. **Create real data** - Add your actual tasks and decisions
2. **Explore relationships** - Build connections between tasks and decisions
3. **Set up Linear** - Integrate with Linear for team sync
4. **Configure lifecycle** - Set up email notifications and custom rules
5. **Automate percolation** - Schedule periodic syncs
6. **Build queries** - Create custom Neo4j queries for your workflow

**Continue with:**

- [DEVELOPMENT_STANDARDS.md](DEVELOPMENT_STANDARDS.md) - Advanced setup and configuration
- [NEO4J_SETUP.md](NEO4J_SETUP.md) - Deep dive into Neo4j configuration
- [reference.md](reference.md) - Complete API reference

---

## Quick Reference

### Essential Commands

```bash
# Enter environment
poetry shell

# Create test data
poetry run python -m omega_kg.poc_okg

# Run lifecycle (dry-run)
poetry run python -m omega_kg.lifecycle --dry-run

# Query tasks
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings
driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (t:Task) RETURN t.uid, t.title, t.status")
    for record in result:
        print(f"{record['t.uid']}: {record['t.title']} [{record['t.status']}]")
driver.close()
EOF

# Run tests
poetry run pytest

# Check code quality
poetry run ruff check omega_kg/
poetry run mypy omega_kg/
```

### Important URLs

| Service | URL | Login |
|---------|-----|-------|
| Neo4j Browser | http://localhost:7474 | neo4j / password |
| Obsidian | localhost or app | Your vault |
| GitHub | https://github.com/ApexSigma-Solutions/omega_kg | Your GitHub account |

### Key Files

| File | Purpose |
|------|---------|
| `.env` | Configuration (never commit) |
| `.env.example` | Template (commit this) |
| `omega_kg/settings.py` | Load .env variables |
| `omega_kg/lifecycle.py` | Task automation |
| `omega_kg/linear_sync.py` | Obsidian sync |
| `omega_kg/poc_okg.py` | Create test data |

---

**Questions?** Check the [Troubleshooting](#troubleshooting) section or see [DEVELOPMENT_STANDARDS.md](DEVELOPMENT_STANDARDS.md).

**Last Updated**: October 28, 2025  
**Version**: 1.0
