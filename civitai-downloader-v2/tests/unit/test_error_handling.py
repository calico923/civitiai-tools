#!/usr/bin/env python3
"""
Unified error handling system tests.
Tests for comprehensive error handling with fallback mechanisms and context tracking.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import importlib.util
from typing import Dict, Any, Optional
import sys


class TestUnifiedErrorHandling:
    """Test unified error handling system functionality."""
    
    @property
    def error_dir(self) -> Path:
        """Get the error handling directory."""
        return Path(__file__).parent.parent.parent / "src" / "core" / "error"
    
    def test_api_error_is_wrapped_in_unified_exception(self):
        """Test that API errors are wrapped in unified exception format."""
        # Import unified error handler
        unified_handler_path = self.error_dir / "unified_error_handler.py"
        assert unified_handler_path.exists(), "unified_error_handler.py must exist"
        
        spec = importlib.util.spec_from_file_location("unified_error_handler", unified_handler_path)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        # Test UnifiedErrorHandler class exists
        assert hasattr(handler_module, 'UnifiedErrorHandler'), "UnifiedErrorHandler class must exist"
        UnifiedErrorHandler = handler_module.UnifiedErrorHandler
        
        error_handler = UnifiedErrorHandler()
        
        # Simulate API error
        original_error = ConnectionError("API connection failed")
        context = {
            'operation': 'api_call',
            'endpoint': '/api/v1/models',
            'retry_count': 0
        }
        
        # Test error wrapping
        wrapped_error = error_handler.wrap_error(original_error, context)
        
        # Validate wrapped error structure
        assert hasattr(wrapped_error, 'original_error'), "Wrapped error must contain original error"
        assert hasattr(wrapped_error, 'error_context'), "Wrapped error must contain context"
        assert hasattr(wrapped_error, 'error_category'), "Wrapped error must have category"
        assert hasattr(wrapped_error, 'suggested_action'), "Wrapped error must have suggested action"
        
        # Validate error categorization (check the value of the enum)
        assert wrapped_error.error_category.value in ['NETWORK', 'API', 'VALIDATION', 'SYSTEM'], \
            "Error must be categorized properly"
        
        # Validate context preservation
        assert wrapped_error.error_context.operation == 'api_call'
        assert wrapped_error.error_context.endpoint == '/api/v1/models'
    
    def test_fallback_is_triggered_on_primary_service_failure(self):
        """Test that fallback mechanisms are triggered when primary service fails."""
        unified_handler_path = self.error_dir / "unified_error_handler.py"
        spec = importlib.util.spec_from_file_location("unified_error_handler", unified_handler_path)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        UnifiedErrorHandler = handler_module.UnifiedErrorHandler
        error_handler = UnifiedErrorHandler()
        
        # Mock primary and fallback services
        primary_service = Mock()
        fallback_service = Mock()
        
        # Configure primary to fail, fallback to succeed
        primary_service.execute.side_effect = Exception("Primary service failed")
        fallback_service.execute.return_value = "fallback_result"
        
        # Register fallback
        error_handler.register_fallback('api_service', primary_service, fallback_service)
        
        # Test fallback execution
        result = error_handler.execute_with_fallback('api_service', 'execute')
        
        # Validate fallback was used
        assert result['status'] == 'success'
        assert result['data'] == 'fallback_result'
        assert result['used_fallback'] == True
        
        # Verify call patterns
        primary_service.execute.assert_called_once()
        fallback_service.execute.assert_called_once()
    
    def test_error_context_captures_request_details(self):
        """Test that error context captures comprehensive request details."""
        error_context_path = self.error_dir / "error_context.py"
        assert error_context_path.exists(), "error_context.py must exist"
        
        spec = importlib.util.spec_from_file_location("error_context", error_context_path)
        context_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(context_module)
        
        # Test ErrorContext class exists
        assert hasattr(context_module, 'ErrorContext'), "ErrorContext class must exist"
        ErrorContext = context_module.ErrorContext
        
        # Create error context with comprehensive details
        context = ErrorContext(
            operation='model_search',
            component='api_client',
            endpoint='/api/v1/models',
            parameters={'query': 'anime', 'type': 'Checkpoint'},
            user_agent='CivitAI-Downloader/2.0',
            request_id='req_123456',
            timestamp=1234567890.0
        )
        
        # Validate context structure
        assert context.operation == 'model_search'
        assert context.component == 'api_client'
        assert context.endpoint == '/api/v1/models'
        assert context.parameters['query'] == 'anime'
        assert context.request_id == 'req_123456'
        
        # Test context serialization
        context_dict = context.to_dict()
        assert isinstance(context_dict, dict)
        assert 'operation' in context_dict
        assert 'timestamp' in context_dict
        assert 'parameters' in context_dict
        
        # Test context from dict reconstruction
        reconstructed = ErrorContext.from_dict(context_dict)
        assert reconstructed.operation == context.operation
        assert reconstructed.request_id == context.request_id
    
    def test_error_categorization_accuracy(self):
        """Test that errors are categorized accurately for appropriate handling."""
        unified_handler_path = self.error_dir / "unified_error_handler.py"
        spec = importlib.util.spec_from_file_location("unified_error_handler", unified_handler_path)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        UnifiedErrorHandler = handler_module.UnifiedErrorHandler
        error_handler = UnifiedErrorHandler()
        
        # Test network error categorization
        network_error = ConnectionError("Connection timeout")
        category = error_handler.categorize_error(network_error)
        assert category.value == 'NETWORK', "Connection errors should be categorized as NETWORK"
        
        # Test validation error categorization
        validation_error = ValueError("Invalid parameter: query cannot be empty")
        category = error_handler.categorize_error(validation_error)
        assert category.value == 'VALIDATION', "Value errors should be categorized as VALIDATION"
        
        # Test API error categorization (using imported exception from the handler module)
        if hasattr(handler_module, 'APIRateLimitError'):
            APIRateLimitError = handler_module.APIRateLimitError
            rate_limit_error = APIRateLimitError("Rate limit exceeded")
            category = error_handler.categorize_error(rate_limit_error)
            assert category.value == 'RATE_LIMIT', "Rate limit errors should be categorized correctly"
    
    def test_error_recovery_strategies(self):
        """Test different error recovery strategies."""
        unified_handler_path = self.error_dir / "unified_error_handler.py"
        spec = importlib.util.spec_from_file_location("unified_error_handler", unified_handler_path)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        UnifiedErrorHandler = handler_module.UnifiedErrorHandler
        error_handler = UnifiedErrorHandler()
        
        # Test retry strategy for transient errors
        transient_error = ConnectionError("Temporary network issue")
        strategy = error_handler.get_recovery_strategy(transient_error)
        
        assert strategy['type'] in ['RETRY', 'FALLBACK', 'ABORT'], \
            "Recovery strategy must be one of the defined types"
        assert 'max_retries' in strategy, "Retry strategy must specify max retries"
        assert 'backoff_multiplier' in strategy, "Retry strategy must specify backoff"
        
        # Test abort strategy for fatal errors
        fatal_error = PermissionError("API key invalid")
        strategy = error_handler.get_recovery_strategy(fatal_error)
        assert strategy['type'] == 'ABORT', "Fatal errors should trigger abort strategy"
    
    def test_error_statistics_tracking(self):
        """Test that error statistics are tracked for monitoring."""
        error_stats_path = self.error_dir / "error_statistics.py"
        assert error_stats_path.exists(), "error_statistics.py must exist"
        
        spec = importlib.util.spec_from_file_location("error_statistics", error_stats_path)
        stats_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stats_module)
        
        # Test ErrorStatistics class exists
        assert hasattr(stats_module, 'ErrorStatistics'), "ErrorStatistics class must exist"
        ErrorStatistics = stats_module.ErrorStatistics
        
        error_stats = ErrorStatistics()
        
        # Record various error events
        error_stats.record_error('NETWORK', 'ConnectionError', 'api_call')
        error_stats.record_error('VALIDATION', 'ValueError', 'parameter_check')
        error_stats.record_error('NETWORK', 'TimeoutError', 'api_call')
        
        # Test statistics aggregation
        stats = error_stats.get_statistics()
        
        assert 'total_errors' in stats, "Statistics must include total error count"
        assert 'error_categories' in stats, "Statistics must break down by category"
        assert 'error_types' in stats, "Statistics must break down by type"
        assert 'components' in stats, "Statistics must break down by component"
        
        # Validate specific counts
        assert stats['total_errors'] == 3
        assert stats['error_categories']['NETWORK'] == 2
        assert stats['error_categories']['VALIDATION'] == 1
        assert stats['components']['api_call'] == 2
    
    def test_async_error_handling(self):
        """Test error handling in async contexts."""
        unified_handler_path = self.error_dir / "unified_error_handler.py"
        spec = importlib.util.spec_from_file_location("unified_error_handler", unified_handler_path)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        UnifiedErrorHandler = handler_module.UnifiedErrorHandler
        error_handler = UnifiedErrorHandler()
        
        async def test_async_operation():
            # Mock async operation that fails
            async def failing_operation():
                await asyncio.sleep(0.1)
                raise ConnectionError("Async operation failed")
            
            # Test async error handling
            try:
                result = await error_handler.handle_async_error(
                    failing_operation(),
                    context={'operation': 'async_api_call'}
                )
                # Should not reach here if error is properly handled
                assert False, "Expected exception was not raised"
            except Exception as e:
                # Verify error was properly wrapped
                assert hasattr(e, 'error_context'), "Async errors should be wrapped with context"
                assert e.error_context.operation == 'async_api_call'
        
        # Run async test
        asyncio.run(test_async_operation())
    
    def test_error_reporting_format(self):
        """Test that errors are formatted consistently for logging and user display."""
        unified_handler_path = self.error_dir / "unified_error_handler.py"
        spec = importlib.util.spec_from_file_location("unified_error_handler", unified_handler_path)
        handler_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handler_module)
        
        UnifiedErrorHandler = handler_module.UnifiedErrorHandler
        error_handler = UnifiedErrorHandler()
        
        # Test error formatting for different audiences
        original_error = ConnectionError("Connection failed")
        context = {'operation': 'model_download', 'model_id': '12345'}
        
        wrapped_error = error_handler.wrap_error(original_error, context)
        
        # Test user-friendly message
        user_message = error_handler.format_user_message(wrapped_error)
        assert isinstance(user_message, str), "User message must be string"
        assert len(user_message) > 0, "User message cannot be empty"
        assert "technical details" not in user_message.lower(), \
            "User message should not contain technical jargon"
        
        # Test detailed log message
        log_message = error_handler.format_log_message(wrapped_error)
        assert isinstance(log_message, str), "Log message must be string"
        assert "model_download" in log_message, "Log message should contain operation context"
        assert "12345" in log_message, "Log message should contain relevant context data"
        
        # Test structured error data
        error_data = error_handler.format_structured_data(wrapped_error)
        assert isinstance(error_data, dict), "Structured data must be dictionary"
        assert 'error_id' in error_data, "Structured data must have error ID"
        assert 'timestamp' in error_data, "Structured data must have timestamp"
        assert 'context' in error_data, "Structured data must have context"