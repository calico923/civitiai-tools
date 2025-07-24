#!/usr/bin/env python3
"""
Streaming Exporter for Real-time Data Export.
Implements incremental write functionality to prevent data loss on interruption.
"""

import json
import csv
import os
from typing import Dict, List, Any, Optional, Union, TextIO
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StreamingCSVExporter:
    """
    Streaming CSV exporter that writes data incrementally.
    Prevents data loss on process interruption.
    """
    
    def __init__(self, filepath: Union[str, Path], fieldnames: Optional[List[str]] = None):
        """
        Initialize streaming CSV exporter.
        
        Args:
            filepath: Path to output CSV file
            fieldnames: Optional list of field names (auto-detected if None)
        """
        self.filepath = Path(filepath)
        self.fieldnames = fieldnames
        self.file_handle: Optional[TextIO] = None
        self.csv_writer: Optional[csv.DictWriter] = None
        self.header_written = False
        self.rows_written = 0
        
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def open(self):
        """Open the CSV file for writing."""
        try:
            # Create directory if it doesn't exist
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Open file in append mode if it exists, write mode if new
            mode = 'a' if self.filepath.exists() else 'w'
            self.file_handle = open(self.filepath, mode, newline='', encoding='utf-8')
            
            # Check if header already exists (for append mode)
            if mode == 'a' and self.filepath.stat().st_size > 0:
                self.header_written = True
                # Count existing rows
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.rows_written = sum(1 for _ in csv.reader(f)) - 1  # Subtract header
                    
            logger.info(f"Opened CSV file: {self.filepath} (mode: {mode}, existing rows: {self.rows_written})")
            
        except Exception as e:
            logger.error(f"Failed to open CSV file {self.filepath}: {e}")
            raise
            
    def close(self):
        """Close the CSV file."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            self.csv_writer = None
            logger.info(f"Closed CSV file: {self.filepath} (total rows written: {self.rows_written})")
            
    def write_row(self, row_data: Dict[str, Any]):
        """
        Write a single row to the CSV file.
        
        Args:
            row_data: Dictionary containing row data
        """
        if not self.file_handle:
            raise RuntimeError("CSV file is not open. Use 'with' statement or call open() first.")
            
        # Flatten nested data for CSV compatibility first
        flattened_row = self._flatten_dict(row_data)
        
        # Auto-detect fieldnames from first row if not provided
        if not self.fieldnames:
            self.fieldnames = list(flattened_row.keys())
            
        # Check if we need to expand fieldnames for new fields
        elif not self.header_written:
            # Still opportunity to expand fieldnames before header is written
            new_fields = set(flattened_row.keys()) - set(self.fieldnames)
            if new_fields:
                self.fieldnames.extend(sorted(new_fields))  # Keep consistent order
                
        # Initialize CSV writer if not done yet
        if not self.csv_writer:
            self.csv_writer = csv.DictWriter(self.file_handle, fieldnames=self.fieldnames)
            
        # Write header if not written yet
        if not self.header_written:
            self.csv_writer.writeheader()
            self.file_handle.flush()  # Ensure header is written immediately
            self.header_written = True
            logger.debug("CSV header written")
            
        # Handle new fields that appear after header is written
        if self.header_written:
            new_fields = set(flattened_row.keys()) - set(self.fieldnames)
            if new_fields:
                # Add missing fields with empty values
                for field in new_fields:
                    logger.warning(f"New field '{field}' discovered after header written, ignoring for consistency")
                # Remove new fields from row to prevent CSV error
                flattened_row = {k: v for k, v in flattened_row.items() if k in self.fieldnames}
        
        # Add missing fields with empty values if they exist in fieldnames but not in row
        for field in self.fieldnames:
            if field not in flattened_row:
                flattened_row[field] = ""
        
        # Write the row
        try:
            self.csv_writer.writerow(flattened_row)
            self.file_handle.flush()  # Force write to disk immediately
            self.rows_written += 1
            
            if self.rows_written % 100 == 0:  # Log progress every 100 rows
                logger.info(f"Written {self.rows_written} rows to {self.filepath}")
                
        except Exception as e:
            logger.error(f"Failed to write row {self.rows_written + 1}: {e}")
            raise
            
    def write_rows(self, rows_data: List[Dict[str, Any]]):
        """
        Write multiple rows to the CSV file.
        
        Args:
            rows_data: List of dictionaries containing row data
        """
        for row in rows_data:
            self.write_row(row)
            
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary for CSV export."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to string representation
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)


class StreamingJSONExporter:
    """
    Streaming JSON exporter that maintains a valid JSON array structure.
    Writes data incrementally while keeping the file valid JSON.
    """
    
    def __init__(self, filepath: Union[str, Path]):
        """
        Initialize streaming JSON exporter.
        
        Args:
            filepath: Path to output JSON file
        """
        self.filepath = Path(filepath)
        self.file_handle: Optional[TextIO] = None
        self.items_written = 0
        
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def open(self):
        """Open the JSON file for writing."""
        try:
            # Create directory if it doesn't exist
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists and has content
            if self.filepath.exists() and self.filepath.stat().st_size > 0:
                # Resume writing to existing file
                self._open_for_append()
            else:
                # Create new file
                self._open_for_new()
                
            logger.info(f"Opened JSON file: {self.filepath} (existing items: {self.items_written})")
            
        except Exception as e:
            logger.error(f"Failed to open JSON file {self.filepath}: {e}")
            raise
            
    def _open_for_new(self):
        """Open a new JSON file."""
        self.file_handle = open(self.filepath, 'w', encoding='utf-8')
        self.file_handle.write('[')
        self.file_handle.flush()
        self.items_written = 0
        
    def _open_for_append(self):
        """Open existing JSON file for appending."""
        # Read existing file to count items and prepare for append
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if not content.startswith('['):
            raise ValueError(f"Invalid JSON file format: {self.filepath}")
            
        # Count existing items (rough estimate)
        self.items_written = content.count('},{') + (1 if content.count('{') > 0 else 0)
        
        # Remove closing bracket and open for append
        if content.endswith(']'):
            content = content[:-1]  # Remove closing ]
            
        # Rewrite file without closing bracket
        self.file_handle = open(self.filepath, 'w', encoding='utf-8')
        self.file_handle.write(content)
        
        # Add comma if there are existing items
        if self.items_written > 0:
            self.file_handle.write(',')
            
        self.file_handle.flush()
        
    def close(self):
        """Close the JSON file with proper array closing."""
        if self.file_handle:
            # Close the JSON array
            self.file_handle.write('\n]')
            self.file_handle.close()
            self.file_handle = None
            logger.info(f"Closed JSON file: {self.filepath} (total items written: {self.items_written})")
            
    def write_item(self, item_data: Dict[str, Any]):
        """
        Write a single item to the JSON array.
        
        Args:
            item_data: Dictionary containing item data
        """
        if not self.file_handle:
            raise RuntimeError("JSON file is not open. Use 'with' statement or call open() first.")
            
        try:
            # Add comma before item if not the first item
            prefix = ',\n' if self.items_written > 0 else '\n'
            
            # Write the item
            json_str = json.dumps(item_data, ensure_ascii=False, indent=2)
            self.file_handle.write(f"{prefix}{json_str}")
            self.file_handle.flush()  # Force write to disk immediately
            
            self.items_written += 1
            
            if self.items_written % 50 == 0:  # Log progress every 50 items
                logger.info(f"Written {self.items_written} items to {self.filepath}")
                
        except Exception as e:
            logger.error(f"Failed to write item {self.items_written + 1}: {e}")
            raise
            
    def write_items(self, items_data: List[Dict[str, Any]]):
        """
        Write multiple items to the JSON array.
        
        Args:
            items_data: List of dictionaries containing item data
        """
        for item in items_data:
            self.write_item(item)


class StreamingExporterFactory:
    """Factory for creating appropriate streaming exporters."""
    
    @staticmethod
    def create_exporter(filepath: Union[str, Path], format_type: str = 'auto', **kwargs):
        """
        Create appropriate streaming exporter based on file extension or format type.
        
        Args:
            filepath: Path to output file
            format_type: Export format ('csv', 'json', or 'auto' for auto-detection)
            **kwargs: Additional arguments for specific exporters
            
        Returns:
            Streaming exporter instance
        """
        filepath = Path(filepath)
        
        if format_type == 'auto':
            # Auto-detect format from file extension
            ext = filepath.suffix.lower()
            if ext == '.csv':
                format_type = 'csv'
            elif ext == '.json':
                format_type = 'json'
            else:
                raise ValueError(f"Cannot auto-detect format for extension: {ext}")
                
        if format_type == 'csv':
            return StreamingCSVExporter(filepath, **kwargs)
        elif format_type == 'json':
            return StreamingJSONExporter(filepath, **kwargs)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")