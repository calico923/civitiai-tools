#!/usr/bin/env python3
"""
HTML Cleaner Utility for CivitAI Model Descriptions.
Removes HTML tags and extracts clean text content.
"""

import re
from typing import Optional, Dict, Any
from html import unescape


class HTMLCleaner:
    """
    Utility class for cleaning HTML content from model descriptions.
    """
    
    @staticmethod
    def clean_html(html_content: Optional[str]) -> str:
        """
        Clean HTML content and extract plain text.
        
        Args:
            html_content: HTML string to clean (can be None or empty)
            
        Returns:
            Clean text string without HTML tags
        """
        if not html_content or not isinstance(html_content, str):
            return ""
        
        # Handle empty strings
        html_content = html_content.strip()
        if not html_content:
            return ""
        
        # First pass: Remove script and style elements completely
        html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Second pass: Convert common HTML elements to readable text
        # Convert <br>, <br/>, <br /> to newlines
        html_content = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        
        # Convert paragraph tags to double newlines
        html_content = re.sub(r'</?p[^>]*>', '\n\n', html_content, flags=re.IGNORECASE)
        
        # Convert list items to bullet points
        html_content = re.sub(r'<li[^>]*>', '• ', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</li>', '\n', html_content, flags=re.IGNORECASE)
        
        # Convert headings to uppercase with newlines
        html_content = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\1\n', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Convert links to text with URL (if useful)
        html_content = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'\2 (\1)', html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove all remaining HTML tags
        html_content = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        html_content = unescape(html_content)
        
        # Clean up whitespace
        # Replace multiple whitespaces with single space
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        
        # Replace multiple newlines with double newlines (paragraph breaks)
        html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in html_content.split('\n')]
        html_content = '\n'.join(lines)
        
        # Final cleanup: remove excessive whitespace
        html_content = html_content.strip()
        
        return html_content
    
    @staticmethod
    def clean_model_description(model_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean description fields in model data.
        
        Args:
            model_data: Model data dictionary
            
        Returns:
            Model data with cleaned description fields
        """
        # Clean main description
        if 'description' in model_data:
            model_data['description'] = HTMLCleaner.clean_html(model_data['description'])
        
        # Clean version descriptions if they exist
        if 'modelVersions' in model_data and isinstance(model_data['modelVersions'], list):
            for version in model_data['modelVersions']:
                if isinstance(version, dict) and 'description' in version:
                    version['description'] = HTMLCleaner.clean_html(version['description'])
        
        return model_data
    
    @staticmethod
    def extract_useful_info(html_content: Optional[str]) -> str:
        """
        Extract useful information from HTML content with focus on usage instructions.
        
        Args:
            html_content: HTML string to process
            
        Returns:
            Cleaned text with focus on useful information
        """
        if not html_content:
            return ""
        
        # Clean HTML first
        clean_text = HTMLCleaner.clean_html(html_content)
        
        # If text is too long, try to extract key information
        if len(clean_text) > 500:
            lines = clean_text.split('\n')
            useful_lines = []
            
            # Keywords that indicate useful information
            useful_keywords = [
                'trigger', 'prompt', 'use', 'weight', 'strength', 'setting',
                'recommendation', 'instruction', 'how to', 'example',
                'parameter', 'cfg', 'step', 'sampler', 'model'
            ]
            
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Ignore very short lines
                    # Check if line contains useful keywords
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in useful_keywords):
                        useful_lines.append(line)
                    # Include first few lines as they often contain important info
                    elif len(useful_lines) < 3:
                        useful_lines.append(line)
                
                # Limit to reasonable length
                if len(useful_lines) >= 10:
                    break
            
            if useful_lines:
                return '\n'.join(useful_lines)
        
        return clean_text