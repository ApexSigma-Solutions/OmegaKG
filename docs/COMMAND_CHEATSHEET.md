# Omega_KG Command Quick Reference

Copy-paste commands for common tasks

---

## Initial Setup

### 1. Clone and Install

```bash
cd C:\Users\YourName\OneDrive\ApexSigma
git clone https://github.com/ApexSigma-Solutions/omega_kg.git
cd omega_kg
poetry install --with dev
Copy-Item .env.example .env
notepad .env  # Edit with your settings
```

### 2. Start Neo4j

```bash
# Docker (recommended)
docker-compose up -d neo4j-db

# Then access browser at: http://localhost:7474
# Username: neo4j
# Password: (from .env)
```

### 3. Verify Setup

```bash
poetry run python -c "from omega_kg.settings import settings; print('✅ Connected to:', settings.neo4j_uri)"
```

---

## Data Operations

### Create Sample Data

```bash
poetry run python -m omega_kg.poc_okg
```

### Query: List All Tasks

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (t:Task) RETURN t.uid, t.title, t.status, t.created ORDER BY t.created DESC")
    print("\n📋 Tasks in Neo4j:\n")
    for record in result:
        print(f"  {record['t.uid']}: {record['t.title']} [{record['t.status']}]")
driver.close()
EOF
```

### Query: Count All Nodes

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (n) RETURN labels(n)[0] as type, count(*) as count")
    print("\n📊 Data in Neo4j:\n")
    for record in result:
        print(f"  {record['type']}: {record['count']} nodes")
driver.close()
EOF
```

### Query: Show Task → Decision Links

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (d:Decision)-[:IMPLEMENTS]->(t:Task) RETURN d.content, t.title, t.status")
    print("\n🔗 Decision → Task Links:\n")
    for record in result:
        print(f"  {record['d.content']}")
        print(f"    └→ {record['t.title']} [{record['t.status']}]\n")
driver.close()
EOF
```

---

## Task Management

### Create a New Task

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
    """, uid="TASK-001", title="My first task", status="draft", created=datetime.now().isoformat())
    print("✅ Task created: TASK-001")
driver.close()
EOF
```

### Update Task Status

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings
from datetime import datetime

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    session.run("""
        MATCH (t:Task {uid: $uid})
        SET t.status = $status, t.transitioned_at = $now
    """, uid="TASK-001", status="active", now=datetime.now().isoformat())
    print("✅ Task status updated")
driver.close()
EOF
```

### Pin a Task (Prevent Auto-Archive)

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    session.run("MATCH (t:Task {uid: $uid}) SET t.pinned = true", uid="TASK-001")
    print("✅ Task pinned")
driver.close()
EOF
```

### Delete a Task

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    session.run("MATCH (t:Task {uid: $uid}) DETACH DELETE t", uid="TASK-001")
    print("✅ Task deleted")
driver.close()
EOF
```

---

## Obsidian Sync

### Sync Markdown File to Neo4j

```bash
poetry run python << 'EOF'
import frontmatter
from pathlib import Path
from neo4j import GraphDatabase
from omega_kg.settings import settings

vault_path = settings.obsidian_vault_path
file_path = Path(vault_path) / "TASK-001.md"

with open(file_path, 'r', encoding='utf-8') as f:
    post = frontmatter.load(f)

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    session.run("""
        MERGE (t:Task {uid: $uid})
        SET t.title = $title, t.status = $status, t.filepath = $filepath
    """,
    uid=post.metadata.get('uid'),
    title=post.metadata.get('title'),
    status=post.metadata.get('status'),
    filepath=str(file_path))
    print("✅ File synced to Neo4j")
driver.close()
EOF
```

### Create Markdown from Neo4j Task

```bash
poetry run python << 'EOF'
from pathlib import Path
from neo4j import GraphDatabase
from omega_kg.settings import settings
import frontmatter

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (t:Task {uid: $uid}) RETURN t", uid="TASK-001")
    task = list(result)[0]['t']

driver.close()

# Create markdown file
metadata = {
    'uid': task['uid'],
    'title': task['title'],
    'status': task['status'],
    'created': task['created']
}
content = f"# {task['title']}\n\n## Status\n- Status: {task['status']}\n- Created: {task['created']}"
post = frontmatter.Post(content, **metadata)

vault_path = Path(settings.obsidian_vault_path)
file_path = vault_path / f"{task['uid']}.md"
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(frontmatter.dumps(post))

print(f"✅ Created: {file_path}")
EOF
```

---

## Lifecycle Management

### Check Current Task States

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    result = session.run("MATCH (t:Task) RETURN t.status, count(*) as count GROUP BY t.status ORDER BY count DESC")
    print("\n📈 Task States:\n")
    for record in result:
        print(f"  {record['t.status']}: {record['count']} tasks")
driver.close()
EOF
```

### Run Lifecycle (Dry-Run)

```bash
poetry run python -m omega_kg.lifecycle --dry-run
```

### Apply Lifecycle Changes

```bash
poetry run python -m omega_kg.lifecycle
```

---

## Neo4j Browser Queries

Paste these in Neo4j Browser at `http://localhost:7474`

### Count Nodes by Type

```cypher
MATCH (n) RETURN labels(n)[0] as type, count(*) as count
```

### List All Tasks

```cypher
MATCH (t:Task) RETURN t.uid, t.title, t.status, t.created ORDER BY t.created DESC
```

### Show All Relationships

```cypher
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50
```

### Tasks and Their Decisions

```cypher
MATCH (d:Decision)-[:IMPLEMENTS]->(t:Task)
RETURN d.content, t.title, t.status
```

### Find Tasks by Status

```cypher
MATCH (t:Task {status: 'active'})
RETURN t.uid, t.title, t.created ORDER BY t.created DESC
```

### Show Recent Changes

```cypher
MATCH (t:Task)
WHERE t.transitioned_at IS NOT NULL
RETURN t.uid, t.title, t.status, t.transitioned_at
ORDER BY t.transitioned_at DESC
LIMIT 20
```

---

## Verification

### Full System Check (Recommended)

```bash
poetry run python verify_system.py
```

**Output example:**

```text
================================================================================
OMEGA_KG SYSTEM VERIFICATION
================================================================================

1️⃣  Settings loaded
   Neo4j URI: bolt://localhost:7687
   Obsidian Vault: C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as

2️⃣  Attempting Neo4j connection...
✅ Neo4j connection successful

3️⃣  Checking for data in Neo4j...
⚠️  Check 3 warning: No data in Neo4j yet

4️⃣  Checking if tasks can be queried...
⚠️  Check 4 warning: No tasks found yet

5️⃣  Checking Obsidian vault structure...
✅ Obsidian vault found
   Path: C:\Users\steyn\OneDrive\ApexSigma\omegavault.as\omegavault.as
   ✅ Plans                 13 files
   ✅ Tasks                  5 files
   ✅ Archive                0 files
   ✅ AI_Conversations       0 files
   ✅ Daily                  0 files
   ✅ Sessions               2 files

6️⃣  Verifying markdown content...
✅ Found 20 markdown files in 3 folders

================================================================================
RESULTS: 4/6 checks passed
✅ System is operational!
================================================================================
```

### Quick Checks

```bash
# Check settings
poetry run python -c "from omega_kg.settings import settings; print(f'✅ Neo4j: {settings.neo4j_uri}')"

# Check Neo4j connection
poetry run python -c "from neo4j import GraphDatabase; from omega_kg.settings import settings; d = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)); print('✅ Connected'); d.close()"

# Count nodes
poetry run python -c "from neo4j import GraphDatabase; from omega_kg.settings import settings; d = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)); c = list(d.session().run('MATCH (n) RETURN count(n)') )[0][0]; print(f'📊 Total nodes: {c}')"
```

---

## Troubleshooting Commands

### Check Neo4j Status

```bash
docker-compose ps neo4j-db
docker-compose logs neo4j-db | tail -20
```

### Restart Neo4j

```bash
docker-compose restart neo4j-db
```

### Test Connection

```bash
poetry run python << 'EOF'
from omega_kg.settings import settings
print(f"URI: {settings.neo4j_uri}")
print(f"User: {settings.neo4j_user}")

from neo4j import GraphDatabase
driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
try:
    with driver.session() as session:
        session.run("RETURN 1")
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
finally:
    driver.close()
EOF
```

### Clear All Data (⚠️ DESTRUCTIVE)

```bash
poetry run python << 'EOF'
from neo4j import GraphDatabase
from omega_kg.settings import settings

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
with driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")
    print("⚠️  All data deleted")
driver.close()
EOF
```

---

## Development Commands

### Run Tests

```bash
poetry run pytest -v
```

### Run Specific Test

```bash
poetry run pytest tests/test_neo4j.py -v
```

### Check Code Quality

```bash
poetry run ruff check omega_kg/
poetry run mypy omega_kg/
```

### Format Code

```bash
poetry run ruff check omega_kg/ --fix
```

### Build Documentation

```bash
poetry run mkdocs build
poetry run mkdocs serve
```

---

## Environment Variables

Key variables in `.env`:

```bash
# Required
APP_ENV=development
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
OBSIDIAN_VAULT_PATH=C:\Users\YourName\Obsidian\MyVault

# Optional
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
LINEAR_API_KEY=lin_xxx
GITHUB_TOKEN=ghp_xxx
```

---

## Helpful Links

| Resource              | Link                                                                                               |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| Neo4j Browser         | [http://localhost:7474](http://localhost:7474)                                                     |
| Neo4j Documentation   | [https://neo4j.com/docs/](https://neo4j.com/docs/)                                                 |
| Cypher Query Language | [https://neo4j.com/docs/cypher-manual/current/](https://neo4j.com/docs/cypher-manual/current/)     |
| Obsidian              | [https://obsidian.md](https://obsidian.md)                                                         |
| Python Neo4j Driver   | [https://neo4j.com/docs/python-manual/current/](https://neo4j.com/docs/python-manual/current/)     |
| Project Repo          | [https://github.com/ApexSigma-Solutions/omega_kg](https://github.com/ApexSigma-Solutions/omega_kg) |

---

**Version**: 1.0  
**Last Updated**: October 28, 2025
