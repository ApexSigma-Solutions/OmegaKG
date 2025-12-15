# Omega_KG Core Hardening Context

## Active Roadmap
**Strategy:** [Omega_KG_Core_Implementation_Strategy.md](../../../omegavault.as/Workflow/Plans/004_InProgress/Omega_KG_Core_Implementation_Strategy.md)
**Roadmap:** [Omega_KG Core - Hardening & Stabilization Roadmap.md](../../../omegavault.as/Workflow/Plans/004_InProgress/Omega_KG%20Core%20-%20Hardening%20&%20Stabilization%20Roadmap.md)

## Current Focus: "Secure the Core"
The project is currently in a **Hardening & Stabilization** phase.
- **Goal:** Validate `capture_server` pipeline (Chrome Extension -> Graph).
- **Constraint:** Remove all `memOS` and `Ingest-LLM` dependencies.
- **Key Tech:** Testcontainers (for clean tests), Postgres (pgvector), Neo4j.

## Immediate Tasks
1. **Audit:** Run `scripts/analyze_repository.py` to find ghost tests.
2. **Smoke Test:** Verify `docker-compose` stability.
3. **Clean Room:** Implement `testcontainers` for integration tests.
