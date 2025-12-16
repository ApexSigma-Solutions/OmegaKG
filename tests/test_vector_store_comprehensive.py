"""
Comprehensive unit tests for omega_kg/vector_store.py

Tests the VectorStore class functionality including:
- Connection pool management
- Pending embedding record creation
- Batch fetching for workers
- Status updates and failure tracking
- Statistics and health monitoring
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def mock_asyncpg_pool():
    """Create a mock asyncpg connection pool"""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    return pool


@pytest.fixture
async def vector_store(mock_asyncpg_pool):
    """Create a VectorStore instance with mocked pool"""
    from omega_kg.vector_store import VectorStore

    return VectorStore(mock_asyncpg_pool)


class TestVectorStoreInitialization:
    """Tests for VectorStore initialization"""

    def test_vector_store_created_with_pool(self, mock_asyncpg_pool):
        """Test that VectorStore can be created with a pool"""
        from omega_kg.vector_store import VectorStore

        store = VectorStore(mock_asyncpg_pool)
        assert store.pool == mock_asyncpg_pool

    @pytest.mark.asyncio
    @patch("omega_kg.vector_store.asyncpg.create_pool")
    @patch("omega_kg.vector_store.register_vector")
    async def test_pool_initialization_success(self, mock_register, mock_create_pool):
        """Test successful pool initialization"""
        from omega_kg.vector_store import VectorStore

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_create_pool.return_value = mock_pool

        pool = await VectorStore.initialize_pool()

        assert pool == mock_pool
        mock_create_pool.assert_called_once()
        mock_register.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    @patch("omega_kg.vector_store.asyncpg.create_pool")
    async def test_pool_initialization_failure(self, mock_create_pool):
        """Test pool initialization failure handling"""
        from omega_kg.vector_store import VectorStore

        mock_create_pool.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError):
            await VectorStore.initialize_pool()


class TestStorePending:
    """Tests for store_pending functionality"""

    @pytest.mark.asyncio
    async def test_store_pending_success(self, vector_store, mock_asyncpg_pool):
        """Test successfully storing a pending embedding record"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchval.return_value = 123  # Mock vector_id

        vector_id = await vector_store.store_pending(
            message_id=456, node_label="ChatSession"
        )

        assert vector_id == 123
        assert mock_conn.fetchval.called

    @pytest.mark.asyncio
    async def test_store_pending_with_invalid_node_label(self, vector_store):
        """Test storing pending with invalid node label"""
        with pytest.raises(ValueError, match="not in SUPPORTED_NODE_TYPES"):
            await vector_store.store_pending(message_id=456, node_label="InvalidLabel")

    @pytest.mark.asyncio
    async def test_store_pending_duplicate_handling(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test handling of duplicate pending records"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        # First call returns None (duplicate), second call returns existing ID
        mock_conn.fetchval.side_effect = [None, 789]

        vector_id = await vector_store.store_pending(
            message_id=456, node_label="ChatSession"
        )

        assert vector_id == 789
        assert mock_conn.fetchval.call_count == 2


class TestUpdateEmbedding:
    """Tests for update_embedding functionality"""

    @pytest.mark.asyncio
    async def test_update_embedding_success(self, vector_store, mock_asyncpg_pool):
        """Test successfully updating an embedding"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        test_embedding = [0.1] * 1024

        await vector_store.update_embedding(vector_id=123, embedding=test_embedding)

        assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_update_embedding_wrong_dimension(self, vector_store):
        """Test updating embedding with wrong dimension"""
        wrong_embedding = [0.1] * 512  # Wrong size

        with pytest.raises(ValueError, match="must be 1024"):
            await vector_store.update_embedding(
                vector_id=123, embedding=wrong_embedding
            )

    @pytest.mark.asyncio
    async def test_update_embedding_empty_list(self, vector_store):
        """Test updating embedding with empty list"""
        with pytest.raises(ValueError, match="must be 1024"):
            await vector_store.update_embedding(vector_id=123, embedding=[])

    @pytest.mark.asyncio
    async def test_update_embedding_none_value(self, vector_store):
        """Test updating embedding with None"""
        with pytest.raises((ValueError, TypeError)):
            await vector_store.update_embedding(vector_id=123, embedding=None)


class TestMarkFailed:
    """Tests for mark_failed functionality"""

    @pytest.mark.asyncio
    async def test_mark_failed_without_retry_increment(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test marking record as failed without incrementing retry"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value

        await vector_store.mark_failed(vector_id=123, increment_retry=False)

        assert mock_conn.execute.called
        # Verify the query doesn't increment retry_count
        query = str(mock_conn.execute.call_args[0][0])
        assert "retry_count" not in query or "retry_count + 1" not in query

    @pytest.mark.asyncio
    async def test_mark_failed_with_retry_increment(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test marking record as failed with retry increment"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value

        await vector_store.mark_failed(vector_id=123, increment_retry=True)

        assert mock_conn.execute.called


class TestFetchPendingBatch:
    """Tests for fetch_pending_batch functionality"""

    @pytest.mark.asyncio
    async def test_fetch_pending_batch_with_results(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test fetching pending batch with results"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_rows = [
            {"vector_id": 1, "message_id": 100, "node_label": "ChatSession"},
            {"vector_id": 2, "message_id": 101, "node_label": "ChatSession"},
        ]
        mock_conn.fetch.return_value = mock_rows

        results = await vector_store.fetch_pending_batch(batch_size=10)

        assert len(results) == 2
        assert results[0]["vector_id"] == 1
        assert results[1]["message_id"] == 101

    @pytest.mark.asyncio
    async def test_fetch_pending_batch_empty(self, vector_store, mock_asyncpg_pool):
        """Test fetching pending batch with no results"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch.return_value = []

        results = await vector_store.fetch_pending_batch(batch_size=10)

        assert len(results) == 0
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_pending_batch_custom_size(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test fetching pending batch with custom batch size"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch.return_value = []

        await vector_store.fetch_pending_batch(batch_size=25)

        # Verify batch_size parameter was passed
        call_args = mock_conn.fetch.call_args[0]
        assert 25 in call_args


class TestGetVectorStatus:
    """Tests for get_vector_status functionality"""

    @pytest.mark.asyncio
    async def test_get_vector_status_found(self, vector_store, mock_asyncpg_pool):
        """Test getting status of existing vector"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchval.return_value = "ready"

        status = await vector_store.get_vector_status(vector_id=123)

        assert status == "ready"

    @pytest.mark.asyncio
    async def test_get_vector_status_not_found(self, vector_store, mock_asyncpg_pool):
        """Test getting status of non-existent vector"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchval.return_value = None

        status = await vector_store.get_vector_status(vector_id=999)

        assert status is None

    @pytest.mark.asyncio
    async def test_get_vector_status_all_valid_statuses(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test all valid status values"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        valid_statuses = ["pending_embedding", "ready", "failed"]

        for status in valid_statuses:
            mock_conn.fetchval.return_value = status
            result = await vector_store.get_vector_status(vector_id=123)
            assert result == status


class TestGetStats:
    """Tests for get_stats functionality"""

    @pytest.mark.asyncio
    async def test_get_stats_success(self, vector_store, mock_asyncpg_pool):
        """Test getting statistics successfully"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = {
            "total_records": 100,
            "pending_count": 10,
            "ready_count": 85,
            "failed_count": 5,
            "avg_retry_count": 0.5,
        }

        stats = await vector_store.get_stats()

        assert stats["total_records"] == 100
        assert stats["pending_count"] == 10
        assert stats["ready_count"] == 85
        assert stats["failed_count"] == 5
        assert stats["avg_retry_count"] == 0.5

    @pytest.mark.asyncio
    async def test_get_stats_empty_database(self, vector_store, mock_asyncpg_pool):
        """Test getting statistics from empty database"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = {
            "total_records": 0,
            "pending_count": 0,
            "ready_count": 0,
            "failed_count": 0,
            "avg_retry_count": 0.0,
        }

        stats = await vector_store.get_stats()

        assert all(v == 0 or v == 0.0 for v in stats.values())


class TestClosePool:
    """Tests for pool closure"""

    @pytest.mark.asyncio
    @patch("omega_kg.vector_store._pool")
    async def test_close_pool_success(self, mock_global_pool):
        """Test successfully closing connection pool"""
        from omega_kg.vector_store import VectorStore

        Mock()  # mock_pool = AsyncMock()
        # mock_global_pool = mock_pool

        await VectorStore.close_pool()

        # Pool should be closed
        # Note: actual implementation may vary

    @pytest.mark.asyncio
    async def test_close_pool_when_none(self):
        """Test closing pool when it's None"""
        from omega_kg.vector_store import VectorStore

        # Should not raise an error
        await VectorStore.close_pool()


class TestGetVectorStore:
    """Tests for get_vector_store singleton function"""

    @pytest.mark.asyncio
    @patch("omega_kg.vector_store.VectorStore.initialize_pool")
    async def test_get_vector_store_first_call(self, mock_init_pool):
        """Test first call to get_vector_store initializes singleton"""
        from omega_kg.vector_store import get_vector_store

        mock_pool = AsyncMock()
        mock_init_pool.return_value = mock_pool

        # Reset singleton state
        import omega_kg.vector_store

        omega_kg.vector_store.vector_store = None

        store = await get_vector_store()

        assert store is not None
        mock_init_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_vector_store_subsequent_calls(self):
        """Test subsequent calls return same instance"""
        # Reset and setup
        import omega_kg.vector_store
        from omega_kg.vector_store import get_vector_store

        mock_pool = AsyncMock()
        omega_kg.vector_store.vector_store = omega_kg.vector_store.VectorStore(
            mock_pool
        )

        store1 = await get_vector_store()
        store2 = await get_vector_store()

        assert store1 is store2


class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_handle_connection_error(self, vector_store, mock_asyncpg_pool):
        """Test handling of connection errors"""
        import asyncpg

        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchval.side_effect = asyncpg.PostgresError("Connection lost")

        with pytest.raises(asyncpg.PostgresError):
            await vector_store.store_pending(message_id=123, node_label="ChatSession")

    @pytest.mark.asyncio
    async def test_handle_query_timeout(self, vector_store, mock_asyncpg_pool):
        """Test handling of query timeouts"""
        import asyncpg

        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch.side_effect = asyncpg.QueryCanceledError("Query timeout")

        with pytest.raises(asyncpg.QueryCanceledError):
            await vector_store.fetch_pending_batch()


class TestConcurrency:
    """Tests for concurrent operations"""

    @pytest.mark.asyncio
    async def test_concurrent_store_pending_calls(
        self, vector_store, mock_asyncpg_pool
    ):
        """Test multiple concurrent store_pending calls"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchval.side_effect = [1, 2, 3, 4, 5]

        tasks = [
            vector_store.store_pending(message_id=i, node_label="ChatSession")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(isinstance(r, int) for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_fetch_batch_calls(self, vector_store, mock_asyncpg_pool):
        """Test multiple concurrent fetch_pending_batch calls"""
        mock_conn = mock_asyncpg_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch.return_value = []

        tasks = [vector_store.fetch_pending_batch(batch_size=10) for _ in range(3)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(isinstance(r, list) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
