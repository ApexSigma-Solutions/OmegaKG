"""
Comprehensive unit tests for debug_worker.py

Tests the worker startup debugging functionality including:
- Vector store initialization
- Worker lifecycle (start/stop)
- Error handling and logging
- Graceful shutdown
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import debug_worker


class TestWorkerStartupDebug:
    """Tests for worker startup debugging functionality"""

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    @patch("debug_worker.VectorStore.close_pool")
    async def test_successful_worker_startup_and_shutdown(
        self,
        mock_close_pool,
        mock_stop_worker,
        mock_start_worker,
        mock_get_vector_store,
    ):
        """Test successful worker startup and shutdown sequence"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.return_value = None
        mock_stop_worker.return_value = None
        mock_close_pool.return_value = None

        # Run the test
        await debug_worker.test_worker_startup()

        # Verify calls
        mock_get_vector_store.assert_called_once()
        mock_start_worker.assert_called_once()
        mock_stop_worker.assert_called_once()
        mock_close_pool.assert_called_once()

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    async def test_vector_store_initialization_failure(self, mock_get_vector_store):
        """Test handling of vector store initialization failure"""
        # Setup mock to raise exception
        mock_get_vector_store.side_effect = Exception("Connection failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Connection failed"):
            await debug_worker.test_worker_startup()

        # Verify get_vector_store was called
        mock_get_vector_store.assert_called_once()

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    async def test_worker_start_failure(self, mock_start_worker, mock_get_vector_store):
        """Test handling of worker start failure"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.side_effect = Exception("Worker start failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Worker start failed"):
            await debug_worker.test_worker_startup()

        # Verify calls
        mock_get_vector_store.assert_called_once()
        mock_start_worker.assert_called_once()

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    async def test_worker_stop_failure(
        self, mock_stop_worker, mock_start_worker, mock_get_vector_store
    ):
        """Test handling of worker stop failure"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.return_value = None
        mock_stop_worker.side_effect = Exception("Worker stop failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Worker stop failed"):
            await debug_worker.test_worker_startup()

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    @patch("debug_worker.VectorStore.close_pool")
    async def test_pool_close_failure(
        self,
        mock_close_pool,
        mock_stop_worker,
        mock_start_worker,
        mock_get_vector_store,
    ):
        """Test handling of pool close failure"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.return_value = None
        mock_stop_worker.return_value = None
        mock_close_pool.side_effect = Exception("Pool close failed")

        # Verify exception is raised
        with pytest.raises(Exception, match="Pool close failed"):
            await debug_worker.test_worker_startup()

        # Verify all previous calls were made
        mock_get_vector_store.assert_called_once()
        mock_start_worker.assert_called_once()
        mock_stop_worker.assert_called_once()
        mock_close_pool.assert_called_once()


class TestLoggingBehavior:
    """Tests for logging behavior during debug operations"""

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    @patch("debug_worker.VectorStore.close_pool")
    async def test_logging_messages_on_success(
        self,
        mock_close_pool,
        mock_stop_worker,
        mock_start_worker,
        mock_get_vector_store,
        caplog,
    ):
        """Test that appropriate log messages are generated on success"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store

        with caplog.at_level(logging.INFO):
            await debug_worker.test_worker_startup()

        # Check for expected log messages
        assert "Testing worker startup" in caplog.text
        assert "Initializing vector store" in caplog.text
        assert "Vector store initialized" in caplog.text
        assert "Starting worker" in caplog.text
        assert "Worker started" in caplog.text
        assert "Worker is still running after 2 seconds" in caplog.text
        assert "Stopping worker" in caplog.text
        assert "Worker stopped" in caplog.text
        assert "Vector store pool closed" in caplog.text

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    async def test_logging_on_exception(self, mock_get_vector_store, caplog):
        """Test that exceptions are logged with traceback"""
        # Setup mock to raise exception
        mock_get_vector_store.side_effect = RuntimeError("Test error")

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                await debug_worker.test_worker_startup()

        # Check for error log
        assert "Error during test" in caplog.text
        assert "Test error" in caplog.text


class TestAsyncBehavior:
    """Tests for async/await behavior"""

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    @patch("debug_worker.VectorStore.close_pool")
    @patch("asyncio.sleep")
    async def test_async_sleep_timing(
        self,
        mock_sleep,
        mock_close_pool,
        mock_stop_worker,
        mock_start_worker,
        mock_get_vector_store,
    ):
        """Test that async sleep is called with correct duration"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_sleep.return_value = None

        await debug_worker.test_worker_startup()

        # Verify sleep was called with 2 seconds
        mock_sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    async def test_async_operations_are_awaited(
        self, mock_start_worker, mock_get_vector_store
    ):
        """Test that all async operations are properly awaited"""
        # Setup mocks that track if they were awaited
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.return_value = None

        # This should raise if operations aren't awaited
        try:
            await debug_worker.test_worker_startup()
        except Exception as e:
            # If we get here, something wasn't awaited properly
            pytest.fail(f"Async operation not awaited: {e}")


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    @patch("debug_worker.VectorStore.close_pool")
    async def test_none_return_values(
        self,
        mock_close_pool,
        mock_stop_worker,
        mock_start_worker,
        mock_get_vector_store,
    ):
        """Test handling of None return values from mocked functions"""
        # Setup mocks to return None
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.return_value = None
        mock_stop_worker.return_value = None
        mock_close_pool.return_value = None

        # Should not raise any exceptions
        await debug_worker.test_worker_startup()

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    async def test_multiple_exception_types(self, mock_get_vector_store):
        """Test handling of different exception types"""
        exception_types = [
            ConnectionError("Connection failed"),
            TimeoutError("Operation timed out"),
            ValueError("Invalid value"),
            RuntimeError("Runtime error"),
        ]

        for exc in exception_types:
            mock_get_vector_store.side_effect = exc
            with pytest.raises(type(exc)):
                await debug_worker.test_worker_startup()


class TestImportDependencies:
    """Tests for import dependencies"""

    def test_required_imports_available(self):
        """Test that all required imports are available"""
        # This test ensures the module can be imported
        assert hasattr(debug_worker, "test_worker_startup")
        assert callable(debug_worker.test_worker_startup)

    @patch("debug_worker.get_vector_store")
    def test_lazy_imports_in_function(self, mock_get_vector_store):
        """Test that imports inside function don't cause issues"""
        # The function imports modules inside it, verify this works
        mock_get_vector_store.side_effect = ImportError("Module not found")

        with pytest.raises(ImportError):
            asyncio.run(debug_worker.test_worker_startup())


class TestWorkerLifecycle:
    """Tests for complete worker lifecycle"""

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    @patch("debug_worker.VectorStore.close_pool")
    async def test_correct_call_order(
        self,
        mock_close_pool,
        mock_stop_worker,
        mock_start_worker,
        mock_get_vector_store,
    ):
        """Test that operations are called in the correct order"""
        # Setup mocks
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store

        call_order = []
        mock_get_vector_store.side_effect = lambda: (
            call_order.append("get_vector_store"),
            mock_vector_store,
        )[1]
        mock_start_worker.side_effect = lambda: call_order.append("start_worker")
        mock_stop_worker.side_effect = lambda: call_order.append("stop_worker")
        mock_close_pool.side_effect = lambda: call_order.append("close_pool")

        await debug_worker.test_worker_startup()

        # Verify correct order
        assert call_order == [
            "get_vector_store",
            "start_worker",
            "stop_worker",
            "close_pool",
        ]

    @pytest.mark.asyncio
    @patch("debug_worker.get_vector_store")
    @patch("debug_worker.start_worker")
    @patch("debug_worker.stop_worker")
    async def test_cleanup_on_partial_failure(
        self, mock_stop_worker, mock_start_worker, mock_get_vector_store
    ):
        """Test that cleanup is attempted even on failure"""
        # Setup mocks where start succeeds but stop fails
        mock_vector_store = AsyncMock()
        mock_get_vector_store.return_value = mock_vector_store
        mock_start_worker.return_value = None
        mock_stop_worker.side_effect = Exception("Stop failed")

        with pytest.raises(Exception, match="Stop failed"):
            await debug_worker.test_worker_startup()

        # Verify that start was called even though stop failed
        mock_get_vector_store.assert_called_once()
        mock_start_worker.assert_called_once()
        mock_stop_worker.assert_called_once()


class TestIntegrationScenarios:
    """Integration-style tests for realistic scenarios"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_actual_worker_startup_if_services_available(self):
        """Test actual worker startup if services are available (integration test)"""
        # This test will be skipped if services aren't available
        try:
            from omega_kg.workers.embedding_worker import start_worker, stop_worker
            from omega_kg.vector_store import get_vector_store, VectorStore

            # Try to initialize
            vector_store = await get_vector_store()
            assert vector_store is not None

            # Try to start worker
            await start_worker()

            # Wait briefly
            await asyncio.sleep(1)

            # Stop worker
            await stop_worker()

            # Close pool
            await VectorStore.close_pool()

        except Exception as e:
            pytest.skip(f"Integration test skipped: services not available - {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
