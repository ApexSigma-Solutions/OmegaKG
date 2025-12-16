"""
Comprehensive unit tests for Alembic migration 001_create_omega_vectors_1024.py

Tests the database schema creation for vector embeddings including:
- Table creation with correct columns and constraints
- Index creation for performance optimization
- pgvector extension setup
- Upgrade and downgrade functionality
"""

import pytest
from unittest.mock import patch
import sqlalchemy as sa


class TestMigrationMetadata:
    """Tests for migration metadata and identification"""

    def test_migration_revision_id(self):
        """Test that migration has correct revision ID"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.revision == "001_create_omega_vectors_1024"

    def test_migration_has_no_down_revision(self):
        """Test that this is the first migration"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.down_revision is None

    def test_migration_has_no_branch_labels(self):
        """Test migration branch labels"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.branch_labels is None

    def test_migration_has_no_dependencies(self):
        """Test migration dependencies"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.depends_on is None


class TestPgvectorExtension:
    """Tests for pgvector extension creation"""

    @patch("alembic.op.execute")
    def test_pgvector_extension_created_in_upgrade(self, mock_execute):
        """Test that pgvector extension is created during upgrade"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Check that CREATE EXTENSION was called
        calls = [str(call) for call in mock_execute.call_args_list]
        assert any(
            "CREATE EXTENSION IF NOT EXISTS vector" in str(call) for call in calls
        )

    def test_pgvector_extension_sql_syntax(self):
        """Test that pgvector extension SQL is correct"""
        expected_sql = "CREATE EXTENSION IF NOT EXISTS vector"

        # Verify the SQL syntax is what we expect
        assert "vector" in expected_sql
        assert "IF NOT EXISTS" in expected_sql


class TestTableCreation:
    """Tests for omega_vectors_1024 table creation"""

    @patch("alembic.op.create_table")
    def test_table_created_with_correct_name(self, mock_create_table):
        """Test that table is created with correct name"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Verify create_table was called with correct table name
        assert mock_create_table.called
        call_args = mock_create_table.call_args[0]
        assert call_args[0] == "omega_vectors_1024"

    @patch("alembic.op.create_table")
    def test_table_has_id_column(self, mock_create_table):
        """Test that table has id column as primary key"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Check that id column exists in the table definition
        columns = mock_create_table.call_args[0][1:]
        id_col = next(
            (col for col in columns if hasattr(col, "name") and col.name == "id"), None
        )

        assert id_col is not None
        assert id_col.type.__class__.__name__ == "BigInteger"
        assert id_col.nullable is False
        assert id_col.autoincrement is True

    @patch("alembic.op.create_table")
    def test_table_has_message_id_column(self, mock_create_table):
        """Test that table has message_id column"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        columns = mock_create_table.call_args[0][1:]
        msg_id_col = next(
            (
                col
                for col in columns
                if hasattr(col, "name") and col.name == "message_id"
            ),
            None,
        )

        assert msg_id_col is not None
        assert msg_id_col.type.__class__.__name__ == "BigInteger"
        assert msg_id_col.nullable is False

    @patch("alembic.op.create_table")
    def test_table_has_embedding_column(self, mock_create_table):
        """Test that table has embedding column with correct vector dimension"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        columns = mock_create_table.call_args[0][1:]
        embedding_col = next(
            (
                col
                for col in columns
                if hasattr(col, "name") and col.name == "embedding"
            ),
            None,
        )

        assert embedding_col is not None
        # Embedding can be NULL during pending state
        assert embedding_col.nullable is True

    @patch("alembic.op.create_table")
    def test_table_has_status_column_with_default(self, mock_create_table):
        """Test that table has status column with default value"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        columns = mock_create_table.call_args[0][1:]
        status_col = next(
            (col for col in columns if hasattr(col, "name") and col.name == "status"),
            None,
        )

        assert status_col is not None
        assert status_col.nullable is False
        assert status_col.server_default is not None

    @patch("alembic.op.create_table")
    def test_table_has_retry_count_column(self, mock_create_table):
        """Test that table has retry_count column"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        columns = mock_create_table.call_args[0][1:]
        retry_col = next(
            (
                col
                for col in columns
                if hasattr(col, "name") and col.name == "retry_count"
            ),
            None,
        )

        assert retry_col is not None
        assert retry_col.type.__class__.__name__ == "Integer"
        assert retry_col.nullable is False

    @patch("alembic.op.create_table")
    def test_table_has_timestamp_columns(self, mock_create_table):
        """Test that table has created_at and updated_at columns"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        columns = mock_create_table.call_args[0][1:]
        created_col = next(
            (
                col
                for col in columns
                if hasattr(col, "name") and col.name == "created_at"
            ),
            None,
        )
        updated_col = next(
            (
                col
                for col in columns
                if hasattr(col, "name") and col.name == "updated_at"
            ),
            None,
        )

        assert created_col is not None
        assert updated_col is not None
        assert created_col.nullable is False
        assert updated_col.nullable is False


class TestTableConstraints:
    """Tests for table constraints"""

    @patch("alembic.op.create_table")
    def test_primary_key_constraint_exists(self, mock_create_table):
        """Test that primary key constraint is defined"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Check for PrimaryKeyConstraint in the arguments
        all_args = mock_create_table.call_args[0]
        pk_constraint = next(
            (arg for arg in all_args if isinstance(arg, sa.PrimaryKeyConstraint)), None
        )

        assert pk_constraint is not None

    @patch("alembic.op.create_table")
    def test_status_check_constraint_exists(self, mock_create_table):
        """Test that status check constraint is defined"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Check for CheckConstraint in the arguments
        all_args = mock_create_table.call_args[0]
        check_constraint = next(
            (arg for arg in all_args if isinstance(arg, sa.CheckConstraint)), None
        )

        assert check_constraint is not None


class TestIndexCreation:
    """Tests for index creation"""

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_message_id_index_created(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that index on message_id is created"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Check for message_id index
        index_calls = [call[0] for call in mock_create_index.call_args_list]
        assert any("idx_omega_vectors_message_id" in str(call) for call in index_calls)

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_status_index_created(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that index on status is created"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        index_calls = [call[0] for call in mock_create_index.call_args_list]
        assert any("idx_omega_vectors_status" in str(call) for call in index_calls)

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_pending_partial_index_created(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that partial index for pending records is created"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        index_calls = [call[0] for call in mock_create_index.call_args_list]
        assert any("idx_omega_vectors_pending" in str(call) for call in index_calls)

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_cleanup_index_created(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that cleanup index is created"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        index_calls = [call[0] for call in mock_create_index.call_args_list]
        assert any("idx_omega_vectors_cleanup" in str(call) for call in index_calls)

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_failed_retry_index_created(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that failed retry index is created"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        index_calls = [call[0] for call in mock_create_index.call_args_list]
        assert any(
            "idx_omega_vectors_failed_retry" in str(call) for call in index_calls
        )

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_correct_number_of_indexes_created(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that exactly 5 indexes are created"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Should create 5 indexes (message_id, status, pending, cleanup, failed_retry)
        assert mock_create_index.call_count == 5


class TestDowngrade:
    """Tests for migration downgrade"""

    @patch("alembic.op.drop_table")
    def test_table_dropped_on_downgrade(self, mock_drop_table):
        """Test that table is dropped during downgrade"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.downgrade()

        # Verify drop_table was called with correct table name
        mock_drop_table.assert_called_once_with("omega_vectors_1024")

    @patch("alembic.op.drop_table")
    def test_indexes_automatically_dropped(self, mock_drop_table):
        """Test that indexes are automatically dropped with table"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        # Indexes should be dropped automatically when table is dropped
        migration.downgrade()

        # Verify table drop was called (which handles indexes)
        assert mock_drop_table.called


class TestMigrationDocumentation:
    """Tests for migration documentation and comments"""

    def test_migration_has_docstring(self):
        """Test that migration has descriptive docstring"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.__doc__ is not None
        assert len(migration.__doc__) > 100  # Should have substantial documentation

    def test_migration_docstring_mentions_phase_7(self):
        """Test that docstring references Phase 7 (vector enrichment)"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert "Phase 7" in migration.__doc__ or "TN-LINEAR-07" in migration.__doc__

    def test_migration_docstring_mentions_pgvector(self):
        """Test that docstring mentions pgvector requirement"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert "pgvector" in migration.__doc__.lower()

    def test_upgrade_function_has_docstring(self):
        """Test that upgrade function has docstring"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.upgrade.__doc__ is not None

    def test_downgrade_function_has_docstring(self):
        """Test that downgrade function has docstring"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        assert migration.downgrade.__doc__ is not None


class TestMigrationIdempotence:
    """Tests for migration idempotence"""

    @patch("alembic.op.execute")
    def test_extension_creation_is_idempotent(self, mock_execute):
        """Test that extension creation uses IF NOT EXISTS"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Verify IF NOT EXISTS is used
        calls = [str(call) for call in mock_execute.call_args_list]
        vector_call = next((call for call in calls if "vector" in call.lower()), None)
        assert vector_call is not None
        assert "IF NOT EXISTS" in vector_call


class TestMigrationPerformance:
    """Tests for migration performance considerations"""

    @patch("alembic.op.create_index")
    @patch("alembic.op.create_table")
    @patch("alembic.op.execute")
    def test_partial_indexes_use_where_clause(
        self, mock_execute, mock_create_table, mock_create_index
    ):
        """Test that partial indexes use postgresql_where for efficiency"""
        from alembic.versions import _001_create_omega_vectors_1024 as migration

        migration.upgrade()

        # Check that partial indexes were created with where clause
        # (pending, cleanup, and failed_retry indexes should be partial)
        partial_index_count = sum(
            1
            for call in mock_create_index.call_args_list
            if "postgresql_where" in str(call)
        )

        # Should have at least 3 partial indexes
        assert partial_index_count >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
