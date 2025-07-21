#!/usr/bin/env python3
"""
Multi-Format Exporter for CivitAI model data.
Implements requirement 2.2: Support multiple export formats (JSON, YAML, CSV, Markdown, HTML, Text).
"""

import json
import csv
import io
from typing import Dict, List, Any, Union, Optional
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


class MultiFormatExporter:
    """
    Multi-format exporter supporting 6 formats per requirement 2.2.
    
    Supports: JSON, YAML, CSV, Markdown, HTML, Text
    """
    
    def __init__(self):
        """Initialize the multi-format exporter."""
        self.supported_formats = ['json', 'yaml', 'csv', 'markdown', 'html', 'text']
    
    def export_json(self, data: Union[Dict, List], pretty: bool = True) -> str:
        """
        Export data to JSON format.
        
        Args:
            data: Data to export
            pretty: Whether to format JSON with indentation
            
        Returns:
            JSON string representation
        """
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False, default=self._json_serializer)
        else:
            return json.dumps(data, ensure_ascii=False, default=self._json_serializer)
    
    def export_yaml(self, data: Union[Dict, List]) -> str:
        """
        Export data to YAML format.
        
        Args:
            data: Data to export
            
        Returns:
            YAML string representation
            
        Raises:
            ImportError: If PyYAML is not installed
        """
        if yaml is None:
            raise ImportError("PyYAML is required for YAML export. Install with: pip install PyYAML")
        
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, 
                        default=self._yaml_serializer)
    
    def export_csv(self, data: Union[Dict, List[Dict]], filename: Optional[str] = None) -> str:
        """
        Export data to CSV format.
        
        Args:
            data: Data to export (must be list of dicts or single dict)
            filename: Optional filename for reference
            
        Returns:
            CSV string representation
        """
        output = io.StringIO()
        
        # Convert single dict to list
        if isinstance(data, dict):
            data = [data]
        
        if not data:
            return ""
        
        # Get fieldnames from first item
        fieldnames = list(data[0].keys())
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for item in data:
            # Flatten nested objects for CSV
            flattened_item = self._flatten_dict(item)
            writer.writerow(flattened_item)
        
        return output.getvalue()
    
    def export_markdown(self, data: Union[Dict, List], title: str = "CivitAI Model Data") -> str:
        """
        Export data to Markdown format.
        
        Args:
            data: Data to export
            title: Title for the markdown document
            
        Returns:
            Markdown string representation
        """
        md_lines = [f"# {title}", "", f"*Generated on {datetime.now().isoformat()}*", ""]
        
        if isinstance(data, dict):
            md_lines.extend(self._dict_to_markdown(data))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                md_lines.append(f"## Item {i + 1}")
                md_lines.append("")
                if isinstance(item, dict):
                    md_lines.extend(self._dict_to_markdown(item))
                else:
                    md_lines.append(f"- {str(item)}")
                md_lines.append("")
        else:
            md_lines.append(str(data))
        
        return "\\n".join(md_lines)
    
    def export_html(self, data: Union[Dict, List], title: str = "CivitAI Model Data") -> str:
        """
        Export data to HTML format.
        
        Args:
            data: Data to export
            title: Title for the HTML document
            
        Returns:
            HTML string representation
        """
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            f"    <title>{title}</title>",
            "    <meta charset='UTF-8'>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        .model-item { border: 1px solid #ccc; margin: 10px 0; padding: 15px; }",
            "        .field { margin: 5px 0; }",
            "        .field-name { font-weight: bold; color: #333; }",
            "        .field-value { color: #666; }",
            "        .generated { font-style: italic; color: #999; font-size: 0.9em; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>{title}</h1>",
            f"    <p class='generated'>Generated on {datetime.now().isoformat()}</p>",
        ]
        
        if isinstance(data, dict):
            html_parts.extend(self._dict_to_html(data, "model-item"))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                html_parts.append(f"    <div class='model-item'>")
                html_parts.append(f"        <h2>Item {i + 1}</h2>")
                if isinstance(item, dict):
                    html_parts.extend(self._dict_to_html(item, indent="        "))
                else:
                    html_parts.append(f"        <p>{str(item)}</p>")
                html_parts.append("    </div>")
        else:
            html_parts.append(f"    <p>{str(data)}</p>")
        
        html_parts.extend(["</body>", "</html>"])
        
        return "\\n".join(html_parts)
    
    def export_text(self, data: Union[Dict, List], title: str = "CivitAI Model Data") -> str:
        """
        Export data to plain text format.
        
        Args:
            data: Data to export
            title: Title for the text document
            
        Returns:
            Plain text string representation
        """
        lines = [
            title,
            "=" * len(title),
            "",
            f"Generated on: {datetime.now().isoformat()}",
            ""
        ]
        
        if isinstance(data, dict):
            lines.extend(self._dict_to_text(data))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                lines.append(f"Item {i + 1}:")
                lines.append("-" * 20)
                if isinstance(item, dict):
                    lines.extend(self._dict_to_text(item, indent="  "))
                else:
                    lines.append(f"  {str(item)}")
                lines.append("")
        else:
            lines.append(str(data))
        
        return "\\n".join(lines)
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for special objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def _yaml_serializer(self, obj):
        """Custom YAML serializer for special objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary for CSV export."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _dict_to_markdown(self, d: Dict, indent: str = "") -> List[str]:
        """Convert dictionary to markdown lines."""
        lines = []
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{indent}### {key}")
                lines.append("")
                lines.extend(self._dict_to_markdown(value, indent + "  "))
            elif isinstance(value, list):
                lines.append(f"{indent}**{key}:** {len(value)} items")
                for item in value[:3]:  # Show first 3 items
                    lines.append(f"{indent}- {str(item)}")
                if len(value) > 3:
                    lines.append(f"{indent}- ... ({len(value) - 3} more)")
            else:
                lines.append(f"{indent}**{key}:** {str(value)}")
        return lines
    
    def _dict_to_html(self, d: Dict, css_class: str = "", indent: str = "    ") -> List[str]:
        """Convert dictionary to HTML lines."""
        lines = []
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{indent}<div class='field'>")
                lines.append(f"{indent}    <span class='field-name'>{key}:</span>")
                lines.extend(self._dict_to_html(value, indent=indent + "    "))
                lines.append(f"{indent}</div>")
            elif isinstance(value, list):
                lines.append(f"{indent}<div class='field'>")
                lines.append(f"{indent}    <span class='field-name'>{key}:</span>")
                lines.append(f"{indent}    <span class='field-value'>{len(value)} items</span>")
                lines.append(f"{indent}</div>")
            else:
                lines.append(f"{indent}<div class='field'>")
                lines.append(f"{indent}    <span class='field-name'>{key}:</span>")
                lines.append(f"{indent}    <span class='field-value'>{str(value)}</span>")
                lines.append(f"{indent}</div>")
        return lines
    
    def _dict_to_text(self, d: Dict, indent: str = "") -> List[str]:
        """Convert dictionary to text lines."""
        lines = []
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{indent}{key}:")
                lines.extend(self._dict_to_text(value, indent + "  "))
            elif isinstance(value, list):
                lines.append(f"{indent}{key}: {len(value)} items")
                for item in value[:3]:  # Show first 3 items
                    lines.append(f"{indent}  - {str(item)}")
                if len(value) > 3:
                    lines.append(f"{indent}  ... ({len(value) - 3} more)")
            else:
                lines.append(f"{indent}{key}: {str(value)}")
        return lines