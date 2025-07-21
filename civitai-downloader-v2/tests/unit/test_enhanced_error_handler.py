#!/usr/bin/env python3
"""
Tests for Enhanced Error Handler (Requirement 8).
Comprehensive testing for intelligent backoff, multi-level logging, and performance tracking.
"""

import asyncio
import json
import logging
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import statistics

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.error.enhanced_error_handler import (
    EnhancedErrorHandler, LogLevel, BackoffStrategy, RetryMetrics, ErrorMetrics
)
from core.error.error_context import ErrorContext
from core.error.api_errors import (
    APIError, APIRateLimitError, APIAuthenticationError, APINotFoundError
)


class TestEnhancedErrorHandlerIntegration(unittest.TestCase):
    """Test enhanced error handler implementation per requirement 8."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Mock analytics collector
        self.mock_analytics = Mock()
        self.mock_analytics.record_api_error = Mock()
        self.mock_analytics.record_api_response = Mock()
        
        # Initialize enhanced error handler
        self.handler = EnhancedErrorHandler(
            log_level=LogLevel.DEBUG,
            enable_detailed_logging=True,
            analytics_collector=self.mock_analytics
        )
        
        # Patch log directory
        self.original_log_dir = None
        if hasattr(self.handler.logger, 'handlers'):
            for handler in self.handler.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    # Update file handler to use temp directory
                    handler.baseFilename = str(self.log_dir / "error_handler.log")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirement_8_1_contextual_error_messages(self):
        """Test contextual detailed error messages per requirement 8.1."""
        # Test with comprehensive context
        context = {
            "operation": "download_model",
            "component": "api_client", 
            "endpoint": "/api/v1/models/123",
            "parameters": {"model_id": 123, "format": "safetensors"},
            "request_id": "req_001",
            "user_id": "user123"
        }
        
        # Create test error
        original_error = ConnectionError("Connection refused by server")
        unified_error = self.handler.wrap_error(original_error, context)
        
        # Verify contextual information is preserved
        self.assertEqual(unified_error.error_context.operation, "download_model")
        self.assertEqual(unified_error.error_context.component, "api_client")
        self.assertEqual(unified_error.error_context.endpoint, "/api/v1/models/123")
        self.assertEqual(unified_error.error_context.parameters["model_id"], 123)
        self.assertEqual(unified_error.error_context.request_id, "req_001")
        
        # Verify detailed error messages
        self.assertIn("Connection problem", unified_error.user_message)
        self.assertIn("download_model", unified_error.log_message)
        self.assertIn("api_client", unified_error.log_message)
        self.assertIn("NETWORK", unified_error.log_message)
        
        # Verify structured data format
        structured_data = self.handler.format_structured_data(unified_error)
        self.assertIn("error_id", structured_data)
        self.assertIn("context", structured_data)
        self.assertIn("suggested_action", structured_data)
        self.assertEqual(structured_data["category"], "NETWORK")
    
    def test_requirement_8_2_intelligent_backoff_retry(self):
        """Test intelligent backoff and retry logic per requirement 8.2."""
        
        # Test exponential backoff
        async def failing_operation_exponential():
            raise ConnectionError("Network timeout")
        
        async def test_exponential_backoff():
            context = {
                "operation": "test_exponential",
                "component": "test_client"
            }
            
            start_time = time.time()
            try:
                await self.handler.execute_with_intelligent_retry(
                    failing_operation_exponential,
                    context,
                    max_retries=3,
                    backoff_strategy=BackoffStrategy.EXPONENTIAL
                )
            except Exception:
                pass
            
            # Verify retry attempts were made
            operation_key = "test_client.test_exponential"
            self.assertIn(operation_key, self.handler.retry_history)
            
            retry_history = self.handler.retry_history[operation_key]
            # Should have 3 attempts that failed (no more attempts after max retries)
            failed_attempts = len(retry_history)
            self.assertEqual(failed_attempts, 3)
            
            # Verify exponential backoff pattern
            self.assertGreater(retry_history[1].delay_seconds, retry_history[0].delay_seconds)
            self.assertGreater(retry_history[2].delay_seconds, retry_history[1].delay_seconds)
            
            # Verify all attempts failed
            self.assertTrue(all(not metric.success for metric in retry_history))
        
        asyncio.run(test_exponential_backoff())
        
        # Test adaptive backoff
        call_count = 0
        async def partially_failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise APIError("Temporary API issue")
            return {"status": "success", "data": "test_data"}
        
        async def test_adaptive_backoff():
            context = {
                "operation": "test_adaptive",
                "component": "api_client"
            }
            
            result = await self.handler.execute_with_intelligent_retry(
                partially_failing_operation,
                context,
                max_retries=5,
                backoff_strategy=BackoffStrategy.ADAPTIVE
            )
            
            # Verify successful result
            self.assertEqual(result["status"], "success")
            
            # Verify retry metrics were recorded
            operation_key = "api_client.test_adaptive"
            self.assertIn(operation_key, self.handler.retry_history)
            
            retry_history = self.handler.retry_history[operation_key]
            # Should have 2 failures and 1 success
            failed_attempts = [m for m in retry_history if not m.success]
            successful_attempts = [m for m in retry_history if m.success]
            
            self.assertEqual(len(failed_attempts), 2)
            self.assertEqual(len(successful_attempts), 1)
        
        asyncio.run(test_adaptive_backoff())
    
    def test_requirement_8_3_multi_level_logging(self):
        """Test comprehensive multi-level logging per requirement 8.3."""
        # Test different log levels
        test_cases = [
            (LogLevel.DEBUG, logging.DEBUG),
            (LogLevel.INFO, logging.INFO), 
            (LogLevel.WARNING, logging.WARNING),
            (LogLevel.ERROR, logging.ERROR),
            (LogLevel.CRITICAL, logging.CRITICAL)
        ]
        
        for log_level, expected_level in test_cases:
            handler = EnhancedErrorHandler(
                log_level=log_level,
                enable_detailed_logging=True
            )
            
            # Verify logging level is set correctly
            self.assertEqual(handler.logger.level, expected_level)
        
        # Test detailed logging capability
        context = {
            "operation": "test_logging",
            "component": "test_component",
            "endpoint": "/api/test"
        }
        
        # Test error logging
        test_error = ValueError("Test validation error")
        unified_error = self.handler.wrap_error(test_error, context)
        
        # Verify log message format includes all required information
        log_message = self.handler.format_log_message(unified_error)
        self.assertIn("test_logging", log_message)
        self.assertIn("test_component", log_message)
        self.assertIn("VALIDATION", log_message)
        self.assertIn("ValueError", log_message)
    
    def test_requirement_8_4_specialized_error_handling(self):
        """Test proper handling of network, auth, parsing errors per requirement 8.4."""
        
        # Test network error handling
        network_error = ConnectionError("Network unreachable")
        context = {"operation": "fetch_data", "component": "network_client"}
        
        async def test_network_handling():
            unified_error = self.handler.wrap_error(network_error, context)
            recovery_info = await self.handler._handle_network_error(unified_error, context)
            
            self.assertEqual(recovery_info["strategy"], "retry_with_backoff")
            self.assertEqual(recovery_info["max_retries"], 5)
            self.assertEqual(recovery_info["backoff_strategy"], BackoffStrategy.EXPONENTIAL)
        
        asyncio.run(test_network_handling())
        
        # Test authentication error handling
        auth_error = APIAuthenticationError("Invalid API key", status_code=401)
        
        async def test_auth_handling():
            unified_error = self.handler.wrap_error(auth_error, context)
            recovery_info = await self.handler._handle_authentication_error(unified_error, context)
            
            self.assertEqual(recovery_info["strategy"], "user_intervention")
            self.assertEqual(recovery_info["max_retries"], 0)
            self.assertIn("Authentication failed", recovery_info["user_message"])
        
        asyncio.run(test_auth_handling())
        
        # Test rate limit error handling
        rate_limit_error = APIRateLimitError("Rate limit exceeded", status_code=429, retry_after=60)
        
        async def test_rate_limit_handling():
            unified_error = self.handler.wrap_error(rate_limit_error, context)
            recovery_info = await self.handler._handle_rate_limit_error(unified_error, context)
            
            self.assertEqual(recovery_info["strategy"], "extended_backoff")
            self.assertEqual(recovery_info["max_retries"], 10)
            self.assertEqual(recovery_info["backoff_strategy"], BackoffStrategy.JITTERED)
        
        asyncio.run(test_rate_limit_handling())
        
        # Test not found error handling
        not_found_error = APINotFoundError("Model not found", status_code=404)
        
        async def test_not_found_handling():
            unified_error = self.handler.wrap_error(not_found_error, context)
            recovery_info = await self.handler._handle_not_found_error(unified_error, context)
            
            self.assertEqual(recovery_info["strategy"], "fallback_or_abort")
            self.assertEqual(recovery_info["max_retries"], 1)
        
        asyncio.run(test_not_found_handling())
    
    def test_requirement_8_5_request_response_logging(self):
        """Test detailed request/response logging per requirement 8.5."""
        
        async def test_successful_request_logging():
            request_data = {
                "method": "GET",
                "endpoint": "/api/v1/models",
                "parameters": {"limit": 20, "query": "anime"},
                "headers": {"Authorization": "Bearer token123"},
                "size": 256
            }
            
            response_data = {
                "status_code": 200,
                "size": 4096,
                "response_time": 1.25,
                "headers": {"Content-Type": "application/json"},
                "data": {"items": [{"id": 1, "name": "test_model"}]}
            }
            
            context = {
                "request_id": "req_test_001",
                "operation": "search_models",
                "component": "api_client"
            }
            
            # Log successful request/response
            await self.handler.log_request_response(
                request_data=request_data,
                response_data=response_data,
                context=context
            )
            
            # Verify analytics collector was called
            self.mock_analytics.record_api_response.assert_called_once_with(
                request_id="req_test_001",
                status_code=200,
                response_time=1.25,
                response_size=4096
            )
        
        asyncio.run(test_successful_request_logging())
        
        async def test_error_request_logging():
            request_data = {
                "method": "POST",
                "endpoint": "/api/v1/models/download",
                "parameters": {"model_id": 123}
            }
            
            error = APIError("Service unavailable", status_code=503)
            context = {
                "request_id": "req_test_002",
                "operation": "download_model",
                "component": "download_client"
            }
            
            # Log error request
            await self.handler.log_request_response(
                request_data=request_data,
                error=error,
                context=context
            )
            
            # Verify analytics collector was called for error
            self.mock_analytics.record_api_error.assert_called_once_with(
                request_id="req_test_002",
                error_type="APIError",
                error_message="Service unavailable"
            )
        
        asyncio.run(test_error_request_logging())
    
    def test_requirement_8_6_performance_tracking(self):
        """Test API usage, timing, success rate tracking per requirement 8.6."""
        
        # Simulate multiple operations with different outcomes
        async def simulate_operations():
            # Successful operations
            for i in range(10):
                async def successful_op():
                    await asyncio.sleep(0.01)  # Simulate work
                    return f"result_{i}"
                
                context = {
                    "operation": "test_operation",
                    "component": "test_client"
                }
                
                result = await self.handler.execute_with_intelligent_retry(
                    successful_op, context, max_retries=3
                )
                self.assertEqual(result, f"result_{i}")
            
            # Some failing operations
            failure_count = 0
            for i in range(5):
                async def failing_op():
                    nonlocal failure_count
                    failure_count += 1
                    if failure_count <= 3:
                        raise ConnectionError("Network error")
                    return f"success_after_retry_{i}"
                
                context = {
                    "operation": "test_failing_operation", 
                    "component": "test_client"
                }
                
                try:
                    result = await self.handler.execute_with_intelligent_retry(
                        failing_op, context, max_retries=2
                    )
                except Exception:
                    pass  # Some operations will fail completely
        
        asyncio.run(simulate_operations())
        
        # Generate performance report
        report = self.handler.get_performance_report()
        
        # Verify report structure
        required_sections = [
            "api_usage_stats",
            "success_rates", 
            "error_patterns",
            "performance_impact",
            "timing_statistics",
            "retry_effectiveness",
            "recommendations"
        ]
        
        for section in required_sections:
            self.assertIn(section, report)
        
        # Verify API usage tracking
        self.assertIn("test_client.test_operation", report["api_usage_stats"])
        self.assertGreater(report["api_usage_stats"]["test_client.test_operation"], 0)
        
        # Verify success rates
        if "test_client.test_operation" in report["success_rates"]:
            success_rate = report["success_rates"]["test_client.test_operation"]
            self.assertGreaterEqual(success_rate, 0.0)
            self.assertLessEqual(success_rate, 1.0)
        
        # Verify timing statistics
        if "test_client.test_operation" in report["timing_statistics"]:
            timing_stats = report["timing_statistics"]["test_client.test_operation"]
            required_timing_fields = [
                "avg_response_time", "min_response_time", 
                "max_response_time", "median_response_time", "total_calls"
            ]
            for field in required_timing_fields:
                self.assertIn(field, timing_stats)
                self.assertIsInstance(timing_stats[field], (int, float))
        
        # Verify recommendations are generated
        self.assertIsInstance(report["recommendations"], list)
    
    def test_backoff_strategy_calculations(self):
        """Test different backoff strategy calculations."""
        from core.error.unified_error_handler import RecoveryConfig
        
        # Create test unified error
        test_error = ConnectionError("Test error")
        context = {"operation": "test", "component": "test"}
        unified_error = self.handler.wrap_error(test_error, context)
        unified_error.recovery_config = RecoveryConfig(
            strategy=None,  # Will be set per test
            max_retries=5,
            backoff_multiplier=2.0,
            initial_delay=1.0,
            max_delay=60.0
        )
        
        operation_key = "test.test"
        
        # Test exponential backoff
        delays = []
        for attempt in range(1, 4):
            delay = self.handler._calculate_backoff_delay(
                unified_error, attempt, BackoffStrategy.EXPONENTIAL, operation_key
            )
            delays.append(delay)
        
        # Verify exponential pattern (each delay should be larger)
        self.assertLess(delays[0], delays[1])
        self.assertLess(delays[1], delays[2])
        
        # Test linear backoff
        delays = []
        for attempt in range(1, 4):
            delay = self.handler._calculate_backoff_delay(
                unified_error, attempt, BackoffStrategy.LINEAR, operation_key
            )
            delays.append(delay)
        
        # Verify linear pattern
        self.assertEqual(delays[0], 1.0)  # 1 * 1
        self.assertEqual(delays[1], 2.0)  # 1 * 2  
        self.assertEqual(delays[2], 3.0)  # 1 * 3
        
        # Test jittered backoff (should have some randomness)
        delays = []
        for attempt in range(1, 10):
            delay = self.handler._calculate_backoff_delay(
                unified_error, attempt, BackoffStrategy.JITTERED, operation_key
            )
            delays.append(delay)
        
        # Verify jittered delays are not exactly the same (randomness)
        unique_delays = set(delays)
        self.assertGreater(len(unique_delays), 1, "Jittered backoff should produce varied delays")
        
        # Test max delay limitation
        unified_error.recovery_config.max_delay = 5.0
        large_attempt = 20
        delay = self.handler._calculate_backoff_delay(
            unified_error, large_attempt, BackoffStrategy.EXPONENTIAL, operation_key
        )
        self.assertLessEqual(delay, 5.0, "Delay should not exceed max_delay")
    
    def test_metrics_data_integrity(self):
        """Test integrity and accuracy of metrics data."""
        # Clear any existing metrics
        self.handler.metrics = ErrorMetrics(
            api_usage={},
            timing_data={},
            success_rates={},
            error_patterns={},
            backoff_effectiveness={},
            recovery_success_rates={},
            performance_impact={}
        )
        
        operation_key = "test_client.integrity_test"
        
        # Simulate known operations
        for i in range(5):
            # Successful operations
            self.handler._update_success_metrics(operation_key, True, 1.0 + i * 0.1)
            self.handler._record_retry_metrics(
                operation_key, 1, 0.0, "success", True, 1.0 + i * 0.1, "exponential"
            )
        
        # Simulate some errors - create separate error instances to avoid tracking prevention
        context = {"operation": "integrity_test", "component": "test_client"}
        for i in range(2):
            test_error = ValueError(f"Test error {i}")  # Different error instances
            unified_error = self.handler.wrap_error(test_error, context)
            # Don't call _update_error_metrics directly as wrap_error already does this
        
        # Verify metrics accuracy
        self.assertEqual(self.handler.metrics.api_usage[operation_key], 5)
        self.assertEqual(len(self.handler.metrics.timing_data[operation_key]), 5)
        
        # Verify timing data accuracy
        expected_times = [1.0, 1.1, 1.2, 1.3, 1.4]
        actual_times = self.handler.metrics.timing_data[operation_key]
        for expected, actual in zip(expected_times, actual_times):
            self.assertAlmostEqual(expected, actual, places=2)
        
        # Verify retry history
        retry_history = self.handler.retry_history[operation_key]
        self.assertEqual(len(retry_history), 5)
        self.assertTrue(all(metric.success for metric in retry_history))
        
        # Verify error patterns
        error_pattern_key = f"{operation_key}.ValueError"
        self.assertEqual(self.handler.metrics.error_patterns[error_pattern_key], 2)


class TestErrorHandlerPerformance(unittest.TestCase):
    """Test error handler performance under load."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.handler = EnhancedErrorHandler(
            log_level=LogLevel.WARNING,  # Reduce logging for performance
            enable_detailed_logging=False
        )
    
    def test_high_volume_error_processing(self):
        """Test error handler performance with high volume."""
        start_time = time.time()
        
        # Process 1000 errors quickly
        for i in range(1000):
            error = ConnectionError(f"Error {i}")
            context = {
                "operation": f"operation_{i % 10}",
                "component": "test_client",
                "request_id": f"req_{i}"
            }
            
            unified_error = self.handler.wrap_error(error, context)
            self.assertIsNotNone(unified_error.error_id)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time
        self.assertLess(processing_time, 5.0, 
                       f"High volume error processing took {processing_time:.2f}s")
        
        # Verify metrics were collected
        self.assertGreater(len(self.handler.metrics.error_patterns), 0)
    
    def test_concurrent_error_handling(self):
        """Test concurrent error handling."""
        import threading
        
        errors_processed = []
        
        def error_producer(thread_id):
            for i in range(50):
                error = APIError(f"Thread {thread_id} error {i}")
                context = {
                    "operation": f"thread_{thread_id}_op_{i}",
                    "component": "concurrent_test"
                }
                
                unified_error = self.handler.wrap_error(error, context)
                errors_processed.append(unified_error.error_id)
        
        # Start multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=error_producer, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all errors were processed
        self.assertEqual(len(errors_processed), 250)  # 5 threads * 50 errors
        
        # Verify all error IDs are unique
        unique_ids = set(errors_processed)
        self.assertEqual(len(unique_ids), 250)


if __name__ == '__main__':
    unittest.main(verbosity=2)