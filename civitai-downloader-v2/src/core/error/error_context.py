"""
ErrorContext - Comprehensive error context tracking.

This module provides detailed context information for error handling,
including request details, operation context, and debugging information.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ErrorContext:
    """
    Comprehensive error context for detailed error tracking and debugging.
    
    This class captures all relevant information about the operation context
    when an error occurs, enabling better debugging and error analysis.
    """
    
    operation: str
    component: str
    endpoint: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: float = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()
        
        if self.parameters is None:
            self.parameters = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ErrorContext to dictionary for serialization.
        
        Returns:
            Dictionary representation of the error context
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ErrorContext':
        """
        Create ErrorContext from dictionary.
        
        Args:
            data: Dictionary containing error context data
            
        Returns:
            ErrorContext instance
        """
        return cls(**data)
    
    def add_parameter(self, key: str, value: Any) -> None:
        """
        Add a parameter to the context.
        
        Args:
            key: Parameter name
            value: Parameter value
        """
        if self.parameters is None:
            self.parameters = {}
        self.parameters[key] = value
    
    def get_human_readable_time(self) -> str:
        """
        Get human-readable timestamp.
        
        Returns:
            Formatted timestamp string
        """
        if self.timestamp:
            return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        return "Unknown"
    
    def get_summary(self) -> str:
        """
        Get a summary string of the error context.
        
        Returns:
            Summary string for logging
        """
        parts = [
            f"Operation: {self.operation}",
            f"Component: {self.component}"
        ]
        
        if self.endpoint:
            parts.append(f"Endpoint: {self.endpoint}")
        
        if self.request_id:
            parts.append(f"Request ID: {self.request_id}")
        
        if self.parameters:
            # Only show non-sensitive parameters
            safe_params = {k: v for k, v in self.parameters.items() 
                          if not any(sensitive in k.lower() 
                                   for sensitive in ['password', 'token', 'key', 'secret'])}
            if safe_params:
                parts.append(f"Parameters: {safe_params}")
        
        # Add other context data
        for key, value in self.__dict__.items():
            if key not in ['operation', 'component', 'endpoint', 'parameters', 'timestamp'] and value is not None:
                if not any(sensitive in key.lower() for sensitive in ['password', 'token', 'key', 'secret']):
                    parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return " | ".join(parts)
    
    def is_api_operation(self) -> bool:
        """
        Check if this is an API-related operation.
        
        Returns:
            True if this is an API operation
        """
        return (self.endpoint is not None or 
                'api' in self.operation.lower() or 
                'api' in self.component.lower())
    
    def is_user_facing(self) -> bool:
        """
        Check if this is a user-facing operation.
        
        Returns:
            True if this operation directly impacts user experience
        """
        user_facing_operations = [
            'search', 'download', 'export', 'display', 'cli', 'ui'
        ]
        return any(op in self.operation.lower() for op in user_facing_operations)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debugging information excluding sensitive data.
        
        Returns:
            Debug information dictionary
        """
        debug_info = {
            'operation': self.operation,
            'component': self.component,
            'timestamp': self.get_human_readable_time(),
            'is_api_operation': self.is_api_operation(),
            'is_user_facing': self.is_user_facing()
        }
        
        if self.endpoint:
            debug_info['endpoint'] = self.endpoint
        
        if self.request_id:
            debug_info['request_id'] = self.request_id
        
        if self.correlation_id:
            debug_info['correlation_id'] = self.correlation_id
        
        # Add safe parameters only
        if self.parameters:
            safe_params = {k: v for k, v in self.parameters.items() 
                          if not any(sensitive in k.lower() 
                                   for sensitive in ['password', 'token', 'key', 'secret'])}
            if safe_params:
                debug_info['parameters'] = safe_params
        
        return debug_info