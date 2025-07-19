"""
ExportFormat - Abstract interface for export format implementations.

This module defines the abstract base class for implementing different export formats
for model data. Supports various output formats like JSON, CSV, YAML, Markdown, etc.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import io


class ExportFormat(ABC):
    """
    Abstract base class for export format implementations.
    
    This interface defines the contract for implementing different export formats
    to output model data in various formats (JSON, CSV, YAML, Markdown, HTML, etc.).
    """
    
    @abstractmethod
    def export(self, models: List[Dict[str, Any]], output_path: Union[str, Path, io.StringIO]) -> bool:
        """
        Export models to the specified format.
        
        Args:
            models: List of model data dictionaries to export
            output_path: Path to output file or StringIO object for in-memory export
            
        Returns:
            True if export was successful
            
        Raises:
            ExportError: If export operation fails
            ValidationError: If model data is invalid for this format
        """
        pass
    
    @abstractmethod
    def get_extension(self) -> str:
        """
        Get the file extension for this export format.
        
        Returns:
            File extension including the dot (e.g., '.json', '.csv')
        """
        pass
    
    @abstractmethod
    def get_mime_type(self) -> str:
        """
        Get the MIME type for this export format.
        
        Returns:
            MIME type string (e.g., 'application/json', 'text/csv')
        """
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """
        Check if this format supports streaming export for large datasets.
        
        Returns:
            True if format can stream data to avoid memory issues
        """
        pass
    
    @abstractmethod
    def validate_data(self, models: List[Dict[str, Any]]) -> bool:
        """
        Validate that model data is suitable for this export format.
        
        Args:
            models: Model data to validate
            
        Returns:
            True if data is valid for this format
            
        Raises:
            ValidationError: If data is not suitable for this format
        """
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get the human-readable name of this export format.
        
        Returns:
            Format name (e.g., 'JSON', 'CSV', 'YAML')
        """
        pass
    
    def export_metadata(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate metadata about the export operation.
        
        Args:
            models: Models being exported
            
        Returns:
            Metadata dictionary with export information
        """
        return {
            'format': self.get_format_name(),
            'extension': self.get_extension(),
            'mime_type': self.get_mime_type(),
            'model_count': len(models),
            'supports_streaming': self.supports_streaming()
        }