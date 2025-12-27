# Neo4j Schema Visualization (TN-301)

This document describes the Neo4j schema for the Omega Knowledge Graph, including the high-fidelity context extraction nodes and relationships added in TN-301.

## Node Labels and Constraints

### Core Entities

#### Task
- **Constraint**: `task_id` - `id` property must be unique
- **Indexes**:
  - `task_status` - on `status` property
  - `task_created` - on `created` property
  - `task_created_at` - on `created_at` property

#### TaskPlan
- **Constraint**: `taskplan_id` - `id` property must be unique

#### ADR (Architecture Decision Record)
- **Constraint**: `adr_id` - `id` property must be unique

#### BacklogPlan
- **Constraint**: `backlogplan_id` - `id` property must be unique

#### Plan
- **Constraint**: `plan_id` - `id` property must be unique

### Intelligence Layer

#### Constraint
- **Constraint**: `constraint_id` - `id` property must be unique

#### Context
- **Constraint**: `context_name` - `name` property must be unique

#### Incident
- **Constraint**: `incident_id` - `id` property must be unique

### High-Fidelity Context Extraction Nodes (TN-301)

#### CodeBlock
- **Constraint**: `codeblock_hash` - `hash` property must be unique
- **Properties**:
  - `hash`: Unique hash for deduplication
  - `content`: The actual code content
  - `language`: Programming language (e.g., "python", "javascript")
  - `start_line`: Starting line number in the source file
  - `end_line`: Ending line number in the source file

#### ErrorLog
- **Constraint**: `errorlog_id` - `id` property must be unique
- **Indexes**:
  - `errorlog_error_type` - on `error_type` property
  - `errorlog_timestamp` - on `timestamp` property
- **Properties**:
  - `id`: Unique identifier (application should construct from error_type + timestamp combination)
  - `error_type`: Type/category of error (e.g., "RuntimeError", "SyntaxError")
  - `timestamp`: When the error occurred
  - `message`: Error message content
- **Note**: The `id` constraint enforces uniqueness but does not automatically composite error_type and timestamp. Applications creating ErrorLog nodes should construct the `id` property from these fields (e.g., `f"{error_type}-{timestamp}"`) to ensure proper deduplication.

#### Concept
- **Constraint**: `concept_name` - `name` property must be unique
- **Properties**:
  - `name`: Normalized concept name

#### File
- **Constraint**: `file_path` - `path` property must be unique
- **Properties**:
  - `path`: Full file path
  - `name`: File name
  - `extension`: File extension

#### LinearIssue
- **Constraint**: `linearissue_id` - `id` property must be unique
- **Properties**:
  - `id`: Linear issue identifier
  - `title`: Issue title
  - `description`: Issue description

## Key Relationships

### Core Relationships
- `(:Task)-[:RELATED_TO]->(:ADR)` - Tasks related to architecture decisions

### High-Fidelity Context Relationships (TN-301)

#### (:LinearIssue)-[:TRIGGERS]->(:ErrorLog)
Links Linear issues to error logs they trigger or are related to. This relationship enables:
- Root cause analysis: Track which issues are associated with specific errors
- Error pattern detection: Identify recurring errors across multiple issues
- Impact assessment: Understand the error impact of issue changes

**Example Cypher**:
```cypher
MATCH (li:LinearIssue {id: 'ISSUE-123'})-[:TRIGGERS]->(el:ErrorLog)
RETURN li.title, el.error_type, el.message, el.timestamp
ORDER BY el.timestamp DESC
```

#### (:CodeBlock)-[:BELONGS_TO]->(:File)
Associates code blocks with their source files. This relationship enables:
- Code context preservation: Maintain the relationship between code snippets and their origins
- File-level analysis: Aggregate code blocks by file
- Blame tracking: Identify which files contain specific code patterns

**Example Cypher**:
```cypher
MATCH (cb:CodeBlock)-[:BELONGS_TO]->(f:File)
WHERE f.extension = 'py'
RETURN f.path, count(cb) as block_count
ORDER BY block_count DESC
```

## Schema Migration

The schema is initialized and migrated using the `KnowledgeGraphSchema` class in `omega_kg/neo4j_schema.py`.

To initialize the schema:
```bash
python scripts/init_neo4j_schema.py
```

To create sample relationships demonstrating the new schema:
```python
from omega_kg.neo4j_schema import KnowledgeGraphSchema

schema = KnowledgeGraphSchema()
schema.initialize_schema()
schema.create_sample_relationships()
schema.close()
```

## Verification Queries

### Check All Constraints
```cypher
SHOW CONSTRAINTS
```

### Check All Indexes
```cypher
SHOW INDEXES
```

### Verify TN-301 Nodes Exist
```cypher
MATCH (cb:CodeBlock) RETURN count(cb) as code_blocks;
MATCH (el:ErrorLog) RETURN count(el) as error_logs;
MATCH (c:Concept) RETURN count(c) as concepts;
MATCH (f:File) RETURN count(f) as files;
MATCH (li:LinearIssue) RETURN count(li) as linear_issues;
```

### Verify TN-301 Relationships Exist
```cypher
MATCH ()-[r:TRIGGERS]->() RETURN count(r) as triggers_count;
MATCH ()-[r:BELONGS_TO]->() RETURN count(r) as belongs_to_count;
```

## Schema Evolution Notes

- **TN-301**: Added high-fidelity context extraction nodes (`CodeBlock`, `ErrorLog`, `Concept`, `File`, `LinearIssue`) with corresponding constraints and relationships
- All constraints use `IF NOT EXISTS` to support idempotent schema updates
- The schema supports both legacy `created` and new `created_at` timestamp fields during migration period
