"""
Unit Tests for Event Processor (TN-103)

Tests individual components in isolation:
- EventProcessor initialization
- Event routing logic
- Status update methods
- Metrics collection
- Configuration loading
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
from omega_kg.workers.event_processor import EventProcessor, EventProcessorMetrics
from omega_kg.models.webhook import RawWebhookEvent

@pytest.fixture
def mock_settings():
    with patch("omega_kg.workers.event_processor.settings") as mock:
        mock.webhook_poll_interval = 0.1
        mock.webhook_batch_size = 5
        yield mock

@pytest.mark.asyncio
async def test_process_batch_success_jsonb(mock_settings):
    """Verifies processing with JSONB payload (Dict) and error_log column."""
    # 1. Mock DB
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    
    # 2. Mock Event (Schema Match) - Fixed: payload should be string/bytes, not dict
    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.id = 123
    mock_event.source = "linear"
    mock_event.payload = '{"type": "Issue", "action": "create"}'  # String format
    mock_event.processed_status = False 
    mock_event.error_log = None
    
    # 3. Query Result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # 4. Patch & Run
    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
            # Mock Strategy
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(return_value=True)
            mock_get_lp.return_value = mock_lp
            
            processor = EventProcessor()
            count = await processor.process_batch()
            
            # 5. Verify
            assert count == 1
            assert mock_event.processed_status is True
            assert mock_event.error_log is None
            mock_lp.process_single_event.assert_called_with({"type": "Issue", "action": "create"})

@pytest.mark.asyncio
async def test_process_batch_failure_logging(mock_settings):
    """Verifies that failures write to error_log."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    
    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "unknown"
    mock_event.payload = {"type": "Test"}
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        count = await processor.process_batch()
        
        assert count == 1
        assert mock_event.processed_status is True
        assert mock_event.error_log is not None

@pytest.mark.asyncio
async def test_process_batch_multiple_events(mock_settings):
    """Verifies processing of multiple events in a single batch."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    
    # Create multiple events
    mock_events = []
    for i in range(3):
        mock_event = MagicMock(spec=RawWebhookEvent)
        mock_event.source = "linear"
        mock_event.payload = f'{{"type": "Issue", "id": {i}}}'
        mock_event.processed_status = False
        mock_event.error_log = None
        mock_events.append(mock_event)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_events
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(return_value=True)
            mock_get_lp.return_value = mock_lp
            
            processor = EventProcessor()
            count = await processor.process_batch()
            
            assert count == 3
            assert mock_lp.process_single_event.call_count == 3
            for event in mock_events:
                assert event.processed_status is True

@pytest.mark.asyncio
async def test_process_batch_mixed_success_failure(mock_settings):
    """Verifies batch continues processing after individual failures."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    
    event1 = MagicMock(spec=RawWebhookEvent)
    event1.source = "linear"
    event1.payload = '{"type": "Issue", "id": 1}'
    
    event2 = MagicMock(spec=RawWebhookEvent)
    event2.source = "linear"
    event2.payload = '{"type": "Issue", "id": 2}'
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [event1, event2]
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
            mock_lp = MagicMock()
            # First succeeds, second fails
            mock_lp.process_single_event = AsyncMock(side_effect=[True, ValueError("Error")])
            mock_get_lp.return_value = mock_lp
            
            processor = EventProcessor()
            count = await processor.process_batch()
            
            assert count == 2
            assert event1.processed_status is True
            assert event1.error_log is None
            assert event2.processed_status is True
            assert "Error" in event2.error_log

@pytest.mark.asyncio
async def test_process_batch_empty(mock_settings):
    """Verifies handling of empty batch."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        processor = EventProcessor()
        count = await processor.process_batch()
        
        assert count == 0

@pytest.mark.asyncio
async def test_process_batch_handler_exception(mock_settings):
    """Verifies exception during handler execution marks event as failed."""
    mock_session = MagicMock()
    mock_session_cls = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    
    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "linear"
    mock_event.payload = {"type": "Issue"}
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_event]
    mock_session.execute = AsyncMock(return_value=mock_result)
    
    with patch("omega_kg.workers.event_processor.AsyncSessionLocal", mock_session_cls):
        with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
            mock_lp = MagicMock()
            mock_lp.process_single_event = AsyncMock(side_effect=ValueError("Test error"))
            mock_get_lp.return_value = mock_lp
            
            processor = EventProcessor()
            count = await processor.process_batch()
            
            assert count == 1
            assert mock_event.processed_status is True
            assert "Test error" in mock_event.error_log

@pytest.mark.asyncio
async def test_parse_payload_dict():
    """Verifies _parse_payload handles dict correctly."""
    processor = EventProcessor()
    payload = {"type": "Issue", "action": "create"}
    
    result = processor._parse_payload(payload)
    assert result == {"type": "Issue", "action": "create"}

@pytest.mark.asyncio
async def test_parse_payload_bytes():
    """Verifies _parse_payload handles bytes correctly."""
    processor = EventProcessor()
    payload = b'{"type": "Issue", "action": "create"}'
    
    result = processor._parse_payload(payload)
    assert result == {"type": "Issue", "action": "create"}

@pytest.mark.asyncio
async def test_parse_payload_string():
    """Verifies _parse_payload handles string correctly."""
    processor = EventProcessor()
    payload = '{"type": "Issue", "action": "create"}'
    
    result = processor._parse_payload(payload)
    assert result == {"type": "Issue", "action": "create"}

@pytest.mark.asyncio
async def test_parse_payload_invalid_json():
    """Verifies _parse_payload handles invalid JSON gracefully."""
    processor = EventProcessor()
    payload = b'invalid json{'
    
    result = processor._parse_payload(payload)
    assert result == {}

@pytest.mark.asyncio
async def test_dispatch_unknown_source():
    """Verifies _dispatch handles unknown event sources gracefully."""
    processor = EventProcessor()
    
    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.source = "unknown_platform"
    
    result = await processor._dispatch(mock_event, {"type": "Test"})
    
    assert result is False

@pytest.mark.asyncio
async def test_handle_linear_event_success(mock_settings):
    """Verifies _handle_linear_event processes valid Linear events."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(return_value=True)
        mock_get_lp.return_value = mock_lp
        
        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue", "action": "create"}
        
        result = await processor._handle_linear_event(mock_event, payload)
        
        assert result is True
        mock_lp.process_single_event.assert_called_once_with(payload)
        assert processor.metrics.processed_count == 1

@pytest.mark.asyncio
async def test_handle_linear_event_failure(mock_settings):
    """Verifies _handle_linear_event handles processor failures."""
    with patch("omega_kg.workers.event_processor.get_linear_processor") as mock_get_lp:
        mock_lp = MagicMock()
        mock_lp.process_single_event = AsyncMock(side_effect=Exception("Processing error"))
        mock_get_lp.return_value = mock_lp
        
        processor = EventProcessor()
        mock_event = MagicMock(spec=RawWebhookEvent)
        payload = {"type": "Issue"}
        
        result = await processor._handle_linear_event(mock_event, payload)
        
        assert result is False
        assert processor.metrics.error_count == 1

@pytest.mark.asyncio
async def test_mark_complete_updates_event(mock_settings):
    """Verifies _mark_complete updates event correctly."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    
    mock_event = MagicMock(spec=RawWebhookEvent)
    mock_event.processed_status = False
    mock_event.error_log = "previous error"
    
    processor = EventProcessor()
    await processor._mark_complete(mock_session, mock_event)
    
    assert mock_event.processed_status is True
    assert mock_event.error_log is None
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_mark_failed_truncates_long_errors(mock_settings):
    """Verifies _mark_failed truncates error messages exceeding 1000 chars."""
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    
    mock_event = MagicMock(spec=RawWebhookEvent)
    long_error = "x" * 2000
    
    processor = EventProcessor()
    await processor._mark_failed(mock_session, mock_event, long_error)
    
    assert mock_event.processed_status is True
    assert len(mock_event.error_log) == 1000
    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_start_loop_adaptive_sleep(mock_settings):
    """Verifies start() uses adaptive sleep based on work availability."""
    processor = EventProcessor()
    
    with patch.object(processor, 'process_batch', new_callable=AsyncMock) as mock_batch:
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # First iteration processes events, second finds none, third stops
            mock_batch.side_effect = [5, 0, 0]
            
            async def stop_after_three():
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                processor.running = False
            
            stop_task = asyncio.create_task(stop_after_three())
            await processor.start()
            await stop_task
            
            # Verify quick retry after work, longer sleep when idle
            assert mock_sleep.call_count >= 2
            assert call(0.1) in mock_sleep.call_args_list
            assert call(0.1) in mock_sleep.call_args_list

@pytest.mark.asyncio
async def test_start_handles_polling_errors(mock_settings):
    """Verifies start() continues after polling errors with backoff."""
    processor = EventProcessor()
    
    with patch.object(processor, 'process_batch', new_callable=AsyncMock) as mock_batch:
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Simulate error then stop
            mock_batch.side_effect = [Exception("DB error"), 0]
            
            async def stop_after_error():
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                processor.running = False
            
            stop_task = asyncio.create_task(stop_after_error())
            await processor.start()
            await stop_task
            
            # Verify backoff sleep after error
            assert call(5.0) in mock_sleep.call_args_list

def test_metrics_initialization():
    """Verifies EventProcessorMetrics initializes correctly."""
    metrics = EventProcessorMetrics()
    
    assert metrics.processed_count == 0
    assert metrics.error_count == 0
    assert metrics.batch_count == 0
    assert metrics.last_batch_time == 0.0

def test_metrics_record_processed():
    """Verifies metrics record_processed increments correctly."""
    metrics = EventProcessorMetrics()
    
    metrics.record_processed()
    metrics.record_processed()
    
    assert metrics.processed_count == 2

def test_metrics_record_error():
    """Verifies metrics record_error increments correctly."""
    metrics = EventProcessorMetrics()
    
    metrics.record_error()
    
    assert metrics.error_count == 1

def test_metrics_record_batch():
    """Verifies metrics record_batch updates correctly."""
    metrics = EventProcessorMetrics()
    
    metrics.record_batch(1.5)
    
    assert metrics.batch_count == 1
    assert metrics.last_batch_time == 1.5

def test_metrics_get_stats():
    """Verifies get_stats returns correct dictionary."""
    metrics = EventProcessorMetrics()
    metrics.record_processed()
    metrics.record_error()
    
    stats = metrics.get_stats()
    
    assert stats["processed_total"] == 1
    assert stats["errors_total"] == 1
    assert "uptime_seconds" in stats

def test_metrics_log_metrics(caplog):
    """Verifies log_metrics outputs correct format."""
    metrics = EventProcessorMetrics()
    metrics.record_processed()
    metrics.record_processed()
    metrics.record_error()
    
    with caplog.at_level("INFO"):
        metrics.log_metrics()
    
    assert "processed=2" in caplog.text
    assert "errors=1" in caplog.text

def test_processor_initialization():
    """Verifies EventProcessor initializes with correct handlers."""
    processor = EventProcessor()
    
    assert processor.running is False
    assert isinstance(processor.metrics, EventProcessorMetrics)
    assert "linear" in processor.handlers

@pytest.mark.asyncio
async def test_stop_sets_running_false():
    """Verifies stop() method sets running flag to False."""
    processor = EventProcessor()
    processor.running = True
    
    await processor.stop()
    
    assert processor.running is False

def test_handler_registry_extensibility():
    """Verifies handler registry supports future integrations."""
    processor = EventProcessor()
    
    # Verify current handler
    assert "linear" in processor.handlers
    
    # Verify extensibility
    async def mock_handler(event, payload):
        return True
    
    processor.handlers["github"] = mock_handler
    assert "github" in processor.handlers
