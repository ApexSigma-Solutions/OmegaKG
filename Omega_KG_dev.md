Omega_KG_dev
├── AGENTS.md
├── CLAUDE.md
├── FORENSIC_GRAPH_POML.xml
├── Omega_KG_dev.code-workspace
├── Omega_KG_stable.code-workspace
├── README.md
├── alembic
├── alembic.ini
│   ├── __pycache__
│   │   ├── env.cpython-312.pyc
│   │   └── env.cpython-313.pyc
│   ├── env.py
│   └── versions
│       ├── 001_create_omega_vectors_1024.py
│       ├── __pycache__
│       │   ├── 001_create_omega_vectors_1024.cpython-312.pyc
│       │   ├── b0221ebe33a0_add_linear_raw_events.cpython-312.pyc
│       │   └── b0222cbe34b1_add_processed_received_at_index.cpython-312.pyc
│       └── b0222cbe34b1_add_processed_received_at_index.py
├── chrome-extension
│   ├── RELOAD_EXTENSION.md
│   ├── background.js
│   ├── chrome-extension
│   │   ├── RELOAD_EXTENSION.md
│   │   ├── background.js
│   │   ├── config.js
│   │   ├── content.js
│   │   ├── manifest.json
│   │   ├── options.html
│   │   ├── options.js
│   │   ├── popup.html
│   │   └── popup.js
│   ├── config.js
│   ├── content.js
│   ├── manifest.json
│   ├── options.html
│   ├── options.js
│   ├── popup.html
│   └── popup.js
├── docker-compose.yml
├── docker_backups
│   ├── neo4j_backup_20251101_062438.tar.gz
│   └── server_id
├── dockerfile
├── docs
│   ├── 20251130
│   │   ├── AUTO_START_IMPLEMENTATION_SUMMARY.md
│   │   ├── CAPTURE_SERVER_AUTO_START.md
│   │   ├── COVERAGE.md
│   │   ├── COVERAGE_QUICKSTART.md
│   │   ├── DEVELOPER_QUICKSTART.md
│   │   ├── DEVELOPMENT_SUMMARY.md
│   │   ├── E2E_COMPLETION_SUMMARY.md
│   │   ├── E2E_TEST_REPORT_20251130.md
│   │   ├── E2E_WORKFLOW_COMPLETE.md
│   │   ├── ENVIRONMENT_ISOLATION_COMPLETE.md
│   │   ├── EXTENSION_FIXES_APPLIED.md
│   │   ├── EXTENSION_IMPROVEMENTS.md
│   │   ├── EXTENSION_LOADING_RESOLUTION.md
│   │   ├── EXTENSION_LOADING_TROUBLESHOOTING.md
│   │   ├── EXTENSION_LOADING_VERIFICATION.md
│   │   ├── EXTENSION_RELOAD_REQUIRED.md
│   │   ├── IMPLEMENTATION_NOTES.md
│   │   ├── OMEGA_KG_SETUP_GUIDE.md
│   │   ├── P0_FIXES_MANUAL_GUIDE.md
│   │   ├── PORT_MAPPING.md
│   │   ├── QUICK_REFERENCE_EXTENSION.md
│   │   ├── SESSION_CHECKLIST.md
│   │   ├── TEST_FIXES_SUMMARY.md
│   │   ├── TROUBLESHOOTING_SESSION_20251031_063959.md
│   │   ├── TROUBLESHOOTING_SESSION_20251130_141541.md
│   │   ├── VENV_AUTOMATION_SETUP.md
│   │   ├── ZERO_TRUST_CONFIRMATION.md
│   │   ├── ZERO_TRUST_QUICK_REFERENCE.md
│   │   └── ZERO_TRUST_SECURITY_VERIFICATION.md
│   ├── CAPTURE_SERVER_STATUS.md
│   ├── COMPLETION_REPORT.md
│   ├── CONNECTION_RECOVERY.md
│   ├── DELIVERY_SUMMARY.md
│   ├── FINAL_VERIFICATION.md
│   ├── Find Gemini Messages Output.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── NEO4J_SETUP.md
│   ├── OLLAMA_HEADLESS_SETUP.md
│   ├── Omega_KG.tree.md
│   ├── P0_FIXES_MANUAL_GUIDE.md
│   ├── PHASE_3_SUMMARY.md
│   ├── PORT_MAPPING.md
│   ├── QUICK_FIX_EXTENSION_NOT_LOADING.md
│   ├── SETTINGS_FIX.md
│   ├── TESTING_SETUP.md
│   ├── TEST_REPORT.md
│   ├── TEST_REPORT_SUMMARY.md
│   ├── TROUBLESHOOTING_SESSION_20251130_141541.md
│   ├── VENV_AUTOMATION_SETUP.md
│   ├── index.md
│   └── reference.md
├── hooks
│   ├── Omega_KG.code-workspace
│   ├── installed-repos.txt
│   └── post-commit.ps1
├── mkdocs.yml
├── monitoring
│   └── prometheus
│       ├── alert.rules
│       └── prometheus.yml
├── nul
├── omega_kg
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   ├── __init__.cpython-313.pyc
│   │   ├── __init__.cpython-314.pyc
│   │   ├── ai_import.cpython-312.pyc
│   │   ├── ai_import.cpython-313.pyc
│   │   ├── ai_import.cpython-314.pyc
│   │   ├── auth_utils.cpython-312.pyc
│   │   ├── auth_utils.cpython-313.pyc
│   │   ├── auth_utils.cpython-314.pyc
│   │   ├── capture_server.cpython-312.pyc
│   │   ├── capture_server.cpython-313.pyc
│   │   ├── capture_server.cpython-314.pyc
│   │   ├── check_nodes.cpython-312.pyc
│   │   ├── check_nodes.cpython-314.pyc
│   │   ├── cli.cpython-312.pyc
│   │   ├── cli.cpython-313.pyc
│   │   ├── cli.cpython-314.pyc
│   │   ├── config.cpython-312.pyc
│   │   ├── lifecycle.cpython-312.pyc
│   │   ├── lifecycle.cpython-313.pyc
│   │   ├── lifecycle.cpython-314.pyc
│   │   ├── linear_client.cpython-312.pyc
│   │   ├── linear_client.cpython-313.pyc
│   │   ├── linear_client.cpython-314.pyc
│   │   ├── linear_sync.cpython-312.pyc
│   │   ├── linear_sync.cpython-313.pyc
│   │   ├── linear_sync.cpython-314.pyc
│   │   ├── neo4j_schema.cpython-312.pyc
│   │   ├── neo4j_schema.cpython-313.pyc
│   │   ├── neo4j_schema.cpython-314.pyc
│   │   ├── obsidian_sync.cpython-312.pyc
│   │   ├── obsidian_sync.cpython-313.pyc
│   │   ├── obsidian_sync.cpython-314.pyc
│   │   ├── parsers.cpython-312.pyc
│   │   ├── parsers.cpython-313.pyc
│   │   ├── percolation.cpython-312.pyc
│   │   ├── percolation.cpython-313.pyc
│   │   ├── percolation.cpython-314.pyc
│   │   ├── poc_okg.cpython-312.pyc
│   │   ├── poc_okg.cpython-314.pyc
│   │   ├── quipu_ollama_heartbeat.cpython-312.pyc
│   │   ├── settings.cpython-312.pyc
│   │   ├── settings.cpython-313.pyc
│   │   ├── settings.cpython-314.pyc
│   │   ├── smart_parser.cpython-312.pyc
│   │   ├── smart_parser.cpython-313.pyc
│   │   ├── smart_parser.cpython-314.pyc
│   │   ├── vault_utils.cpython-312.pyc
│   │   ├── vault_utils.cpython-313.pyc
│   │   ├── vault_utils.cpython-314.pyc
│   │   └── vector_store.cpython-312.pyc
│   ├── ai_import.py
│   ├── auth_utils.py
│   ├── capture_server.py
│   ├── check_nodes.py
│   ├── cli.py
│   ├── config.py
│   ├── database
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-312.pyc
│   │   │   ├── base.cpython-312.pyc
│   │   │   ├── graph.cpython-312.pyc
│   │   │   ├── quipu.cpython-312.pyc
│   │   │   └── session.cpython-312.pyc
│   │   ├── base.py
│   │   ├── graph.py
│   │   ├── quipu.py
│   │   └── session.py
│   ├── domain
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   └── __init__.cpython-312.pyc
│   │   ├── common
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__
│   │   │   │   ├── __init__.cpython-312.pyc
│   │   │   │   └── embedding_service.cpython-312.pyc
│   │   │   └── embedding_service.py
│   │   └── linear
│   │       ├── __init__.py
│   │       ├── __pycache__
│   │       │   ├── __init__.cpython-312.pyc
│   │       │   ├── graph_writer.cpython-312.pyc
│   │       │   ├── mapper.cpython-312.pyc
│   │       │   ├── models.cpython-312.pyc
│   │       │   └── processor.cpython-312.pyc
│   │       ├── graph_writer.py
│   │       ├── mapper.py
│   │       ├── models.py
│   │       └── processor.py
│   ├── lifecycle.py
│   ├── linear_client.py
│   ├── linear_sync.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-312.pyc
│   │   │   ├── conversation.cpython-312.pyc
│   │   │   └── linear.cpython-312.pyc
│   │   └── linear.py
│   ├── neo4j_schema.py
│   ├── obsidian_sync.py
│   ├── parsers.py
│   ├── percolation.py
│   ├── poc_okg.py
│   ├── quipu_ollama_heartbeat.py
│   ├── routers
│   │   ├── __pycache__
│   │   │   ├── conversations.cpython-312.pyc
│   │   │   └── linear_receiver.cpython-312.pyc
│   │   └── linear_receiver.py
│   ├── scripts
│   │   ├── __pycache__
│   │   │   └── init_vector_index.cpython-312.pyc
│   │   └── init_vector_index.py
│   ├── settings.py
│   ├── smart_parser.py
│   ├── vault_utils.py
│   ├── vector_store.py
│   └── workers
│       ├── __init__.py
│       ├── __pycache__
│       │   ├── __init__.cpython-312.pyc
│       │   └── embedding_worker.cpython-312.pyc
│       └── embedding_worker.py
├── poetry.lock
├── pyproject.toml
├── scripts
│   ├── P0_FIXES_MANUAL_GUIDE.md
│   ├── Start-OmegaKGDev.ps1
│   ├── Start-OmegaServer.ps1
│   ├── VENV_SETUP.md
│   ├── __pycache__
│   │   ├── smoke_test.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_bitwarden_config.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_capture.cpython-312-pytest-9.0.1.pyc
│   │   ├── validate_env_example.cpython-312.pyc
│   │   ├── validate_env_example.cpython-313.pyc
│   │   └── validate_env_example.cpython-314.pyc
│   ├── backup-and-restart.ps1
│   ├── check_frontmatter.py
│   ├── copy-extension-local.ps1
│   ├── curl_test.ps1
│   ├── debug_import.py
│   ├── diagnose-capture-issue.ps1
│   ├── diagnose-extension.ps1
│   ├── dump-chatgpt-dom.js
│   ├── e2e_test_capture.py
│   ├── find-chatgpt-messages.js
│   ├── find-chatgpt-turns.js
│   ├── find-gemini-messages.js
│   ├── graceful-shutdown.ps1
│   ├── install-hooks.ps1
│   ├── load-extension.ps1
│   ├── migrations
│   │   ├── 001_create_omega_vectors_1024.sql
│   │   ├── 002_add_node_label_column.sql
│   │   ├── apply_migration.sql
│   │   └── monitoring_queries.sql
│   ├── ollama-heartbeat-monitor.ps1
│   ├── omega-venv.ps1
│   ├── p0_fixes.patch
│   ├── percolate-conversations.ps1
│   ├── pre-commit-full.ps1
│   ├── register-capture-monitor.ps1
│   ├── register_heartbeat.ps1
│   ├── reload-extension-tabs.ps1
│   ├── schedule-lifecycle.ps1
│   ├── setup-ollama-headless.ps1
│   ├── smoke-test-capture-server.py
│   ├── smoke_test.py
│   ├── start-capture-server.ps1
│   ├── start-dev.ps1
│   ├── start-stable.ps1
│   ├── start-tunnel.ps1
│   ├── startup-with-recovery.ps1
│   ├── sync_dev_environment.ps1
│   ├── sync_linear.py
│   ├── task-capture-server.ps1
│   ├── test-gemini-selectors.js
│   ├── test-selectors.js
│   ├── test_bitwarden_config.py
│   ├── test_capture.py
│   ├── test_capture_auth.ps1
│   ├── validate_env_example.py
│   ├── verify-ollama-service.ps1
│   ├── verify_settings.py
│   ├── verify_tn103.py
│   ├── verify_ztp_dev.py
│   └── verify_ztp_stable.py
├── start-server.sh
├── test_vault
├── tests
│   ├── README.md
│   ├── __pycache__
│   │   ├── conftest.cpython-312-pytest-9.0.1.pyc
│   │   ├── conftest.cpython-313-pytest-9.0.1.pyc
│   │   ├── conftest.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_ai_import.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_ai_import.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_ai_import.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_capture.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_capture.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_capture.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_capture_server.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_capture_server.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_capture_server.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_capture_server_dual_write.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_capture_server_dual_write.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_check_nodes.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_check_nodes.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_check_nodes.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_cli.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_cli.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_cli.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_config.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_config.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_config.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_config_drift.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_config_drift.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_frontmatter.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_frontmatter.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_frontmatter.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_heartbeat.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_html_parsing.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_html_parsing.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_html_parsing.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_jwt_e2e.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_jwt_e2e.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_jwt_e2e.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_lifecycle.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_lifecycle.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_lifecycle.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_linear_sync.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_linear_sync.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_linear_sync.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_models_conversation.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_models_conversation.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_neo4j.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_neo4j.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_neo4j.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_neo4j_schema_migration.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_neo4j_schema_migration.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_neo4j_schema_migration.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_neo4j_schema_recovery.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_neo4j_schema_recovery.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_neo4j_schema_recovery.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_obsidian_sync_recovery.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_obsidian_sync_recovery.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_obsidian_sync_recovery.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_percolation.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_percolation.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_percolation.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_percolation_archive_exclusion.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_percolation_archive_exclusion.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_poc.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_poc.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_poc.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_query.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_query.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_query.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_routers_conversations.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_routers_conversations.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_scripts_migrate_conversations.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_scripts_migrate_conversations.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_settings.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_settings.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_settings.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_troubleshoot_extension.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_troubleshoot_extension.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_troubleshoot_extension.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_uids.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_uids.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_uids.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_validate_env_example.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_validate_env_example.cpython-313-pytest-9.0.1.pyc
│   │   ├── test_validate_env_example.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_verify_system.cpython-312-pytest-9.0.1.pyc
│   │   ├── test_verify_system.cpython-313-pytest-9.0.1.pyc
│   │   └── test_verify_system.cpython-314-pytest-8.4.2.pyc
│   ├── conftest.py
│   ├── integration
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-312.pyc
│   │   │   ├── __init__.cpython-314.pyc
│   │   │   ├── test_embedding_sync.cpython-312-pytest-9.0.1.pyc
│   │   │   ├── test_embedding_sync.cpython-312.pyc
│   │   │   ├── test_embedding_sync.cpython-314-pytest-8.4.2.pyc
│   │   │   ├── test_graph_sync.cpython-312-pytest-9.0.1.pyc
│   │   │   ├── test_graph_sync.cpython-314-pytest-8.4.2.pyc
│   │   │   ├── test_parsers_integration.cpython-312-pytest-9.0.1.pyc
│   │   │   ├── test_refinery.cpython-312-pytest-9.0.1.pyc
│   │   │   └── test_refinery.cpython-314-pytest-8.4.2.pyc
│   │   ├── test_embedding_sync.py
│   │   ├── test_graph_sync.py
│   │   ├── test_parsers_integration.py
│   │   └── test_refinery.py
│   ├── pytest.ini
│   ├── test_ai_import.py
│   ├── test_capture.py
│   ├── test_capture_server.py
│   ├── test_check_nodes.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_config_drift.py
│   ├── test_frontmatter.py
│   ├── test_heartbeat.py
│   ├── test_jwt_e2e.py
│   ├── test_lifecycle.py
│   ├── test_linear_sync.py
│   ├── test_neo4j.py
│   ├── test_neo4j_schema_migration.py
│   ├── test_neo4j_schema_recovery.py
│   ├── test_obsidian_sync_recovery.py
│   ├── test_percolation.py
│   ├── test_poc.py
│   ├── test_query.py
│   ├── test_settings.py
│   ├── test_troubleshoot_extension.py
│   ├── test_uids.py
│   ├── test_validate_env_example.py
│   └── test_verify_system.py
└── vault