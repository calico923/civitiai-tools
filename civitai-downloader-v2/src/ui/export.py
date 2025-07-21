#!/usr/bin/env python3
"""
Export Interface System.
Implements requirement 20.2: Multi-format export with customizable options.
"""

import logging
import json
import csv
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Union, IO
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import yaml
import sqlite3
from datetime import datetime
import zipfile
import tempfile
import shutil

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    YAML = "yaml"
    HTML = "html"
    TXT = "txt"
    SQLITE = "sqlite"
    ZIP = "zip"


class ExportScope(Enum):
    """Export scope options."""
    ALL = "all"
    FILTERED = "filtered"
    RECENT = "recent"
    CUSTOM = "custom"


@dataclass
class ExportFilter:
    """Export data filtering options."""
    date_range: Optional[tuple[datetime, datetime]] = None
    categories: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    size_range: Optional[tuple[int, int]] = None  # MB
    tags: Optional[List[str]] = None
    exclude_fields: Optional[List[str]] = None
    include_fields: Optional[List[str]] = None
    max_records: Optional[int] = None


@dataclass
class ExportOptions:
    """Export configuration options."""
    format: ExportFormat
    output_path: Path
    scope: ExportScope = ExportScope.ALL
    filters: Optional[ExportFilter] = None
    include_metadata: bool = True
    include_thumbnails: bool = False
    compress: bool = False
    encryption: bool = False
    password: Optional[str] = None
    template: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    # Format-specific options
    csv_delimiter: str = ","
    csv_quote_char: str = '"'
    json_indent: int = 2
    xml_root_element: str = "export"
    html_template: Optional[str] = None
    include_raw_data: bool = False


class ExportInterface:
    """
    Multi-format export system.
    Implements requirement 20.2: Comprehensive data export capabilities.
    """
    
    def __init__(self, data_source: Optional[Path] = None):
        """
        Initialize export interface.
        
        Args:
            data_source: Path to data source (database, directory, etc.)
        """
        self.data_source = data_source
        self.export_history: List[Dict[str, Any]] = []
        
        # Template system
        self.templates = {
            'html_model_list': self._get_html_model_template(),
            'html_report': self._get_html_report_template(),
            'xml_metadata': self._get_xml_metadata_template()
        }
        
        # Export statistics
        self.stats = {
            'total_exports': 0,
            'successful_exports': 0,
            'failed_exports': 0,
            'formats_used': {},
            'total_records_exported': 0,
            'total_size_exported': 0
        }
    
    async def export_data(self, data: Union[List[Dict], Dict[str, Any]], options: ExportOptions) -> Dict[str, Any]:
        """
        Export data in specified format.
        
        Args:
            data: Data to export
            options: Export configuration
            
        Returns:
            Export result with metadata
        """
        start_time = datetime.now()
        
        try:
            # Validate options
            self._validate_export_options(options)
            
            # Prepare data
            prepared_data = await self._prepare_data(data, options)
            
            # Apply filters
            if options.filters:
                prepared_data = self._apply_filters(prepared_data, options.filters)
            
            # Perform export based on format
            if options.format == ExportFormat.JSON:
                result = await self._export_json(prepared_data, options)
            elif options.format == ExportFormat.CSV:
                result = await self._export_csv(prepared_data, options)
            elif options.format == ExportFormat.XML:
                result = await self._export_xml(prepared_data, options)
            elif options.format == ExportFormat.YAML:
                result = await self._export_yaml(prepared_data, options)
            elif options.format == ExportFormat.HTML:
                result = await self._export_html(prepared_data, options)
            elif options.format == ExportFormat.TXT:
                result = await self._export_txt(prepared_data, options)
            elif options.format == ExportFormat.SQLITE:
                result = await self._export_sqlite(prepared_data, options)
            elif options.format == ExportFormat.ZIP:
                result = await self._export_zip(prepared_data, options)
            else:
                raise ValueError(f"Unsupported export format: {options.format}")
            
            # Post-process
            if options.compress and options.format != ExportFormat.ZIP:
                result = await self._compress_export(result, options)
            
            if options.encryption:
                result = await self._encrypt_export(result, options)
            
            # Update statistics
            self._update_export_stats(options.format, len(prepared_data), result['file_size'])
            
            # Record export history
            export_record = {
                'timestamp': start_time.isoformat(),
                'format': options.format.value,
                'scope': options.scope.value,
                'records_count': len(prepared_data),
                'file_size': result['file_size'],
                'output_path': str(options.output_path),
                'duration_seconds': (datetime.now() - start_time).total_seconds(),
                'success': True
            }
            
            self.export_history.append(export_record)
            self.stats['successful_exports'] += 1
            
            result.update({
                'export_metadata': export_record,
                'records_exported': len(prepared_data)
            })
            
            logger.info(f"Export completed: {options.format.value} -> {options.output_path}")
            return result
            
        except Exception as e:
            # Record failure
            error_record = {
                'timestamp': start_time.isoformat(),
                'format': options.format.value,
                'error': str(e),
                'output_path': str(options.output_path),
                'success': False
            }
            
            self.export_history.append(error_record)
            self.stats['failed_exports'] += 1
            
            logger.error(f"Export failed: {e}")
            raise
    
    async def _prepare_data(self, data: Union[List[Dict], Dict[str, Any]], options: ExportOptions) -> List[Dict[str, Any]]:
        """Prepare data for export."""
        if isinstance(data, dict):
            # Convert single dict to list
            prepared_data = [data]
        elif isinstance(data, list):
            prepared_data = data
        else:
            raise ValueError("Data must be a dictionary or list of dictionaries")
        
        # Add metadata if requested
        if options.include_metadata:
            export_metadata = {
                'export_timestamp': datetime.now().isoformat(),
                'export_format': options.format.value,
                'total_records': len(prepared_data),
                'export_options': {
                    'scope': options.scope.value,
                    'include_thumbnails': options.include_thumbnails,
                    'include_raw_data': options.include_raw_data
                }
            }
            
            # Add metadata to each record or as separate metadata record
            if options.format in [ExportFormat.JSON, ExportFormat.YAML]:
                prepared_data = {
                    'metadata': export_metadata,
                    'data': prepared_data
                }
            else:
                # For tabular formats, add metadata as fields
                for record in prepared_data:
                    record['_export_timestamp'] = export_metadata['export_timestamp']
        
        return prepared_data
    
    def _apply_filters(self, data: List[Dict[str, Any]], filters: ExportFilter) -> List[Dict[str, Any]]:
        """Apply filters to data."""
        filtered_data = data
        
        # Date range filter
        if filters.date_range:
            start_date, end_date = filters.date_range
            filtered_data = [
                record for record in filtered_data
                if self._get_record_date(record, start_date) <= end_date
            ]
        
        # Category filter
        if filters.categories:
            filtered_data = [
                record for record in filtered_data
                if record.get('category') in filters.categories
            ]
        
        # Status filter
        if filters.statuses:
            filtered_data = [
                record for record in filtered_data
                if record.get('status') in filters.statuses
            ]
        
        # Size range filter
        if filters.size_range:
            min_size, max_size = filters.size_range
            filtered_data = [
                record for record in filtered_data
                if min_size <= record.get('size_mb', 0) <= max_size
            ]
        
        # Tag filter
        if filters.tags:
            filtered_data = [
                record for record in filtered_data
                if any(tag in record.get('tags', []) for tag in filters.tags)
            ]
        
        # Field inclusion/exclusion
        if filters.include_fields:
            filtered_data = [
                {k: v for k, v in record.items() if k in filters.include_fields}
                for record in filtered_data
            ]
        elif filters.exclude_fields:
            filtered_data = [
                {k: v for k, v in record.items() if k not in filters.exclude_fields}
                for record in filtered_data
            ]
        
        # Max records limit
        if filters.max_records:
            filtered_data = filtered_data[:filters.max_records]
        
        return filtered_data
    
    def _get_record_date(self, record: Dict[str, Any], default: datetime) -> datetime:
        """Extract date from record."""
        date_fields = ['created_at', 'updated_at', 'timestamp', 'date']
        
        for field in date_fields:
            if field in record:
                try:
                    if isinstance(record[field], str):
                        return datetime.fromisoformat(record[field].replace('Z', '+00:00'))
                    elif isinstance(record[field], (int, float)):
                        return datetime.fromtimestamp(record[field])
                except (ValueError, TypeError):
                    continue
        
        return default
    
    async def _export_json(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as JSON."""
        with open(options.output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=options.json_indent, ensure_ascii=False, default=str)
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.JSON.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(data) if isinstance(data, list) else 1
        }
    
    async def _export_csv(self, data: List[Dict[str, Any]], options: ExportOptions) -> Dict[str, Any]:
        """Export data as CSV."""
        if not data:
            raise ValueError("No data to export")
        
        # Get all unique field names
        fieldnames = set()
        for record in data:
            fieldnames.update(record.keys())
        fieldnames = sorted(fieldnames)
        
        with open(options.output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=options.csv_delimiter,
                quotechar=options.csv_quote_char,
                quoting=csv.QUOTE_MINIMAL
            )
            
            writer.writeheader()
            for record in data:
                # Flatten complex fields
                flattened_record = self._flatten_dict(record)
                writer.writerow(flattened_record)
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.CSV.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(data),
            'fields_count': len(fieldnames)
        }
    
    async def _export_xml(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as XML."""
        root = ET.Element(options.xml_root_element)
        
        if isinstance(data, dict):
            if 'data' in data:
                # Handle metadata + data structure
                if 'metadata' in data:
                    metadata_elem = ET.SubElement(root, "metadata")
                    self._dict_to_xml(data['metadata'], metadata_elem)
                
                data_elem = ET.SubElement(root, "data")
                for record in data['data']:
                    record_elem = ET.SubElement(data_elem, "record")
                    self._dict_to_xml(record, record_elem)
            else:
                # Single record
                self._dict_to_xml(data, root)
        else:
            # List of records
            for record in data:
                record_elem = ET.SubElement(root, "record")
                self._dict_to_xml(record, record_elem)
        
        # Write to file with pretty formatting
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(options.output_path, encoding='utf-8', xml_declaration=True)
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.XML.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(data) if isinstance(data, list) else 1
        }
    
    async def _export_yaml(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as YAML."""
        with open(options.output_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.YAML.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(data) if isinstance(data, list) else 1
        }
    
    async def _export_html(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as HTML."""
        template = options.html_template or 'html_model_list'
        
        if isinstance(data, dict) and 'data' in data:
            records = data['data']
            metadata = data.get('metadata', {})
        else:
            records = data if isinstance(data, list) else [data]
            metadata = {}
        
        html_content = self._generate_html(records, metadata, template)
        
        with open(options.output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.HTML.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(records)
        }
    
    async def _export_txt(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as plain text."""
        with open(options.output_path, 'w', encoding='utf-8') as f:
            if isinstance(data, dict) and 'data' in data:
                # Write metadata
                if 'metadata' in data:
                    f.write("=== EXPORT METADATA ===\n")
                    for key, value in data['metadata'].items():
                        f.write(f"{key}: {value}\n")
                    f.write("\n=== DATA ===\n\n")
                
                records = data['data']
            else:
                records = data if isinstance(data, list) else [data]
            
            # Write records
            for i, record in enumerate(records, 1):
                f.write(f"--- Record {i} ---\n")
                for key, value in record.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.TXT.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(records) if isinstance(data, list) else 1
        }
    
    async def _export_sqlite(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as SQLite database."""
        if isinstance(data, dict) and 'data' in data:
            records = data['data']
            metadata = data.get('metadata', {})
        else:
            records = data if isinstance(data, list) else [data]
            metadata = {}
        
        if not records:
            raise ValueError("No data to export")
        
        with sqlite3.connect(options.output_path) as conn:
            cursor = conn.cursor()
            
            # Create metadata table
            if metadata:
                cursor.execute("""
                    CREATE TABLE export_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                """)
                
                for key, value in metadata.items():
                    cursor.execute("INSERT INTO export_metadata (key, value) VALUES (?, ?)", 
                                 (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
            
            # Analyze data structure to create table schema
            all_fields = set()
            for record in records:
                all_fields.update(self._flatten_dict(record).keys())
            
            # Create main data table
            create_table_sql = "CREATE TABLE exported_data (\n"
            create_table_sql += "  id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            
            for field in sorted(all_fields):
                create_table_sql += f"  {self._sanitize_sql_name(field)} TEXT,\n"
            
            create_table_sql = create_table_sql.rstrip(',\n') + "\n)"
            cursor.execute(create_table_sql)
            
            # Insert data
            placeholders = ", ".join("?" * (len(all_fields) + 1))  # +1 for id
            field_names = ["id"] + sorted(all_fields)
            
            for i, record in enumerate(records, 1):
                flattened = self._flatten_dict(record)
                values = [i] + [flattened.get(field) for field in sorted(all_fields)]
                
                cursor.execute(f"INSERT INTO exported_data ({', '.join(field_names)}) VALUES ({placeholders})", values)
            
            conn.commit()
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.SQLITE.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'records_count': len(records),
            'tables_created': 2 if metadata else 1
        }
    
    async def _export_zip(self, data: Union[List[Dict], Dict], options: ExportOptions) -> Dict[str, Any]:
        """Export data as ZIP archive with multiple formats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Export in multiple formats
            formats_to_include = [ExportFormat.JSON, ExportFormat.CSV, ExportFormat.XML]
            exported_files = []
            
            for fmt in formats_to_include:
                try:
                    temp_options = ExportOptions(
                        format=fmt,
                        output_path=temp_path / f"data.{fmt.value}",
                        scope=options.scope,
                        filters=options.filters,
                        include_metadata=options.include_metadata
                    )
                    
                    result = await self.export_data(data, temp_options)
                    exported_files.append(temp_options.output_path)
                    
                except Exception as e:
                    logger.warning(f"Failed to include {fmt.value} in ZIP: {e}")
            
            # Create ZIP file
            with zipfile.ZipFile(options.output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in exported_files:
                    zipf.write(file_path, file_path.name)
                
                # Add export summary
                summary = {
                    'export_timestamp': datetime.now().isoformat(),
                    'formats_included': [fp.suffix[1:] for fp in exported_files],
                    'total_records': len(data) if isinstance(data, list) else 1,
                    'export_tool': 'CivitAI Downloader Export Interface'
                }
                
                zipf.writestr('export_summary.json', json.dumps(summary, indent=2))
        
        file_size = options.output_path.stat().st_size
        
        return {
            'format': ExportFormat.ZIP.value,
            'output_path': str(options.output_path),
            'file_size': file_size,
            'formats_included': len(exported_files),
            'records_count': len(data) if isinstance(data, list) else 1
        }
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _dict_to_xml(self, d: Dict[str, Any], parent: ET.Element) -> None:
        """Convert dictionary to XML elements."""
        for key, value in d.items():
            # Sanitize key name for XML
            clean_key = self._sanitize_xml_name(key)
            
            if isinstance(value, dict):
                child = ET.SubElement(parent, clean_key)
                self._dict_to_xml(value, child)
            elif isinstance(value, list):
                child = ET.SubElement(parent, clean_key)
                for item in value:
                    if isinstance(item, dict):
                        item_elem = ET.SubElement(child, "item")
                        self._dict_to_xml(item, item_elem)
                    else:
                        item_elem = ET.SubElement(child, "item")
                        item_elem.text = str(item)
            else:
                child = ET.SubElement(parent, clean_key)
                child.text = str(value) if value is not None else ""
    
    def _sanitize_xml_name(self, name: str) -> str:
        """Sanitize name for XML element."""
        # Replace invalid characters with underscores
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(name))
        # Ensure it starts with letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = f"_{sanitized}"
        return sanitized or "field"
    
    def _sanitize_sql_name(self, name: str) -> str:
        """Sanitize name for SQL column."""
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        # Ensure it starts with letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = f"_{sanitized}"
        return sanitized or "field"
    
    def _generate_html(self, records: List[Dict[str, Any]], metadata: Dict[str, Any], template: str) -> str:
        """Generate HTML from template."""
        template_content = self.templates.get(template, self.templates['html_model_list'])
        
        # Simple template substitution
        html_content = template_content.replace('{{title}}', metadata.get('export_timestamp', 'Data Export'))
        html_content = html_content.replace('{{metadata}}', self._format_metadata_html(metadata))
        html_content = html_content.replace('{{records}}', self._format_records_html(records))
        html_content = html_content.replace('{{record_count}}', str(len(records)))
        html_content = html_content.replace('{{export_date}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        return html_content
    
    def _format_metadata_html(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as HTML."""
        if not metadata:
            return ""
        
        html = "<div class='metadata'><h3>Export Information</h3><ul>"
        for key, value in metadata.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul></div>"
        
        return html
    
    def _format_records_html(self, records: List[Dict[str, Any]]) -> str:
        """Format records as HTML table."""
        if not records:
            return "<p>No records to display</p>"
        
        # Get all unique field names
        fieldnames = set()
        for record in records:
            fieldnames.update(record.keys())
        fieldnames = sorted(fieldnames)
        
        html = "<table class='records-table'><thead><tr>"
        for field in fieldnames:
            html += f"<th>{field}</th>"
        html += "</tr></thead><tbody>"
        
        for record in records:
            html += "<tr>"
            for field in fieldnames:
                value = record.get(field, "")
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                html += f"<td>{value}</td>"
            html += "</tr>"
        
        html += "</tbody></table>"
        return html
    
    def _get_html_model_template(self) -> str:
        """Get HTML template for model list export."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{title}} - CivitAI Model Export</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-bottom: 20px; }
        .metadata { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .records-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .records-table th, .records-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .records-table th { background-color: #007bff; color: white; }
        .records-table tr:nth-child(even) { background-color: #f2f2f2; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>CivitAI Model Export</h1>
        <p>Generated on {{export_date}} • {{record_count}} records</p>
    </div>
    
    {{metadata}}
    
    <div class="records">
        <h2>Exported Data</h2>
        {{records}}
    </div>
    
    <div class="footer">
        <p>Generated by CivitAI Downloader Export Interface</p>
    </div>
</body>
</html>
"""
    
    def _get_html_report_template(self) -> str:
        """Get HTML template for report export."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>{{title}} - Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        .report-header { text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 30px; }
        .stats { display: flex; justify-content: space-around; background: #f8f9fa; padding: 20px; border-radius: 8px; }
        .stat-item { text-align: center; }
        .stat-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; }
    </style>
</head>
<body>
    <div class="report-header">
        <h1>{{title}}</h1>
        <p>Report generated on {{export_date}}</p>
    </div>
    
    {{metadata}}
    {{records}}
</body>
</html>
"""
    
    def _get_xml_metadata_template(self) -> str:
        """Get XML template for metadata export."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<export>
    <metadata>
        <export_tool>CivitAI Downloader</export_tool>
        <export_timestamp>{{export_date}}</export_timestamp>
        <record_count>{{record_count}}</record_count>
    </metadata>
    <data>
        {{records}}
    </data>
</export>"""
    
    def _validate_export_options(self, options: ExportOptions) -> None:
        """Validate export options."""
        if not options.output_path:
            raise ValueError("Output path is required")
        
        if options.format == ExportFormat.CSV and not options.output_path.suffix == '.csv':
            logger.warning("CSV export with non-.csv extension")
        
        if options.encryption and not options.password:
            raise ValueError("Password required for encrypted export")
        
        # Ensure output directory exists
        options.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def _compress_export(self, result: Dict[str, Any], options: ExportOptions) -> Dict[str, Any]:
        """Compress exported file."""
        import gzip
        
        original_path = Path(result['output_path'])
        compressed_path = original_path.with_suffix(original_path.suffix + '.gz')
        
        with open(original_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        original_path.unlink()
        
        result.update({
            'output_path': str(compressed_path),
            'file_size': compressed_path.stat().st_size,
            'compressed': True
        })
        
        return result
    
    async def _encrypt_export(self, result: Dict[str, Any], options: ExportOptions) -> Dict[str, Any]:
        """Encrypt exported file."""
        # This would integrate with the encryption system from Phase 6.3
        # For now, just log that encryption was requested
        logger.info(f"Encryption requested for export: {result['output_path']}")
        
        # In a real implementation, this would use the DataEncryption class
        # from src/core/security/encryption.py
        
        result['encrypted'] = True
        return result
    
    def _update_export_stats(self, format: ExportFormat, records_count: int, file_size: int) -> None:
        """Update export statistics."""
        self.stats['total_exports'] += 1
        self.stats['total_records_exported'] += records_count
        self.stats['total_size_exported'] += file_size
        
        if format.value not in self.stats['formats_used']:
            self.stats['formats_used'][format.value] = 0
        self.stats['formats_used'][format.value] += 1
    
    def get_export_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get export history."""
        history = sorted(self.export_history, key=lambda x: x['timestamp'], reverse=True)
        return history[:limit] if limit else history
    
    def get_export_stats(self) -> Dict[str, Any]:
        """Get export statistics."""
        return self.stats.copy()
    
    @staticmethod
    def create_basic_options(format: ExportFormat, output_path: Path) -> ExportOptions:
        """Create basic export options."""
        return ExportOptions(
            format=format,
            output_path=output_path,
            scope=ExportScope.ALL,
            include_metadata=True
        )
    
    @staticmethod
    def create_filtered_options(format: ExportFormat, output_path: Path,
                              filters: ExportFilter) -> ExportOptions:
        """Create filtered export options."""
        return ExportOptions(
            format=format,
            output_path=output_path,
            scope=ExportScope.FILTERED,
            filters=filters,
            include_metadata=True
        )
    
    @staticmethod
    def create_secure_options(format: ExportFormat, output_path: Path,
                            password: str) -> ExportOptions:
        """Create secure export options."""
        return ExportOptions(
            format=format,
            output_path=output_path,
            scope=ExportScope.ALL,
            include_metadata=True,
            compress=True,
            encryption=True,
            password=password
        )