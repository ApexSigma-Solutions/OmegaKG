Title: E2E Schema Alignment - Implement Golden Schema

Summary: Full end-to-end migration of all OKG components to the "Golden Schema" (Tasks Issues & Notes Metadata Schema), addressing `BKR_LINEAR_SYNC` and enabling future features.

Objectives:
1. Migrate Neo4j: apply constraints and schema changes to match Golden Schema.
2. Fix Capture Server Pathing: correct file save path to prevent nested directories.
3. Fix Capture Server Schema: ensure `capture_server.py` ingests taskNOTE frontmatter as Golden Schema.
4. Build Linear Sync: implement scheduled job that syncs Neo4j tasks to Linear (missing currently).
5. Build Vault Watcher: background script to ingest Obsidian notes into Neo4j.
6. Cleanup Old Logic: deprecate/remove percolation logic conflicting with Golden Schema.

Task List:
- TN-SCHEMA-MIGRATE-001
- TN-CAPTURE-PATH-FIX-001 (New)
- TN-CAPTURE-FIX-001
- TN-LINEAR-SYNC-001
- TN-VAULT-WATCH-001
- TN-PERC-CLEANUP-001

Owner: SigmaDev11
Status: pending

Notes:
- Validate migration in a staging DB before applying to production.
- Use `poetry run pytest -m requires_neo4j` for integration tests that require Neo4j.
- Include migration rollback scripts and thorough testing of Linear sync to avoid duplicate states.
