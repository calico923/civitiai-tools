#!/usr/bin/env python3
"""
Analytics reporting system.
Implements requirement 13.5: Daily, weekly, monthly reports in multiple formats.
"""

import json
import time
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .analyzer import AnalyticsAnalyzer, AnalysisReport


class ReportFormat(Enum):
    """Report output formats."""
    JSON = "json"
    HTML = "html"
    CSV = "csv"
    MARKDOWN = "md"
    TEXT = "text"


class ReportPeriod(Enum):
    """Report time periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class ReportConfig:
    """Report generation configuration."""
    format: ReportFormat = ReportFormat.JSON
    period: ReportPeriod = ReportPeriod.DAILY
    include_charts: bool = False
    include_raw_data: bool = False
    output_dir: Optional[Path] = None
    template_path: Optional[Path] = None


class ReportGenerator:
    """
    Analytics report generator.
    Generates comprehensive reports per requirement 13.5.
    """
    
    def __init__(self, analyzer: AnalyticsAnalyzer):
        """Initialize report generator."""
        self.analyzer = analyzer
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_report(self, report: AnalysisReport, 
                       config: ReportConfig) -> Path:
        """Generate report in specified format."""
        timestamp = datetime.fromtimestamp(report.period_end).strftime("%Y%m%d_%H%M%S")
        
        if config.output_dir:
            output_dir = config.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = self.output_dir
        
        filename = f"analytics_report_{config.period.value}_{timestamp}.{config.format.value}"
        output_path = output_dir / filename
        
        if config.format == ReportFormat.JSON:
            self._generate_json_report(report, output_path, config)
        elif config.format == ReportFormat.HTML:
            self._generate_html_report(report, output_path, config)
        elif config.format == ReportFormat.CSV:
            self._generate_csv_report(report, output_path, config)
        elif config.format == ReportFormat.MARKDOWN:
            self._generate_markdown_report(report, output_path, config)
        elif config.format == ReportFormat.TEXT:
            self._generate_text_report(report, output_path, config)
        
        return output_path
    
    def generate_daily_report(self, days_back: int = 0, 
                             format: ReportFormat = ReportFormat.JSON) -> Path:
        """Generate daily report."""
        end_time = time.time() - (days_back * 24 * 3600)
        start_time = end_time - (24 * 3600)
        
        report = self.analyzer.generate_report(start_time, end_time)
        config = ReportConfig(format=format, period=ReportPeriod.DAILY)
        
        return self.generate_report(report, config)
    
    def generate_weekly_report(self, weeks_back: int = 0,
                              format: ReportFormat = ReportFormat.HTML) -> Path:
        """Generate weekly report."""
        end_time = time.time() - (weeks_back * 7 * 24 * 3600)
        start_time = end_time - (7 * 24 * 3600)
        
        report = self.analyzer.generate_report(start_time, end_time)
        config = ReportConfig(
            format=format, 
            period=ReportPeriod.WEEKLY,
            include_charts=True
        )
        
        return self.generate_report(report, config)
    
    def generate_monthly_report(self, months_back: int = 0,
                               format: ReportFormat = ReportFormat.HTML) -> Path:
        """Generate monthly report."""
        # Approximate month as 30 days
        end_time = time.time() - (months_back * 30 * 24 * 3600)
        start_time = end_time - (30 * 24 * 3600)
        
        report = self.analyzer.generate_report(start_time, end_time)
        config = ReportConfig(
            format=format,
            period=ReportPeriod.MONTHLY,
            include_charts=True,
            include_raw_data=True
        )
        
        return self.generate_report(report, config)
    
    def _generate_json_report(self, report: AnalysisReport, 
                             output_path: Path, config: ReportConfig) -> None:
        """Generate JSON format report."""
        report_data = {
            'report_metadata': {
                'generated_at': time.time(),
                'generated_by': 'CivitAI Downloader Analytics',
                'period': {
                    'start': report.period_start,
                    'end': report.period_end,
                    'start_date': datetime.fromtimestamp(report.period_start).isoformat(),
                    'end_date': datetime.fromtimestamp(report.period_end).isoformat()
                },
                'format': config.format.value
            },
            'summary': report.summary,
            'api_statistics': report.api_statistics,
            'download_statistics': report.download_statistics,
            'search_statistics': report.search_statistics,
            'cache_statistics': report.cache_statistics,
            'performance_metrics': report.performance_metrics,
            'error_analysis': report.error_analysis,
            'recommendations': report.recommendations
        }
        
        if config.include_raw_data:
            # Add raw events for detailed analysis
            events = self.analyzer.collector.get_events(
                start_time=report.period_start,
                end_time=report.period_end,
                limit=1000  # Limit to prevent huge files
            )
            report_data['raw_events'] = events
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
    
    def _generate_html_report(self, report: AnalysisReport,
                             output_path: Path, config: ReportConfig) -> None:
        """Generate HTML format report."""
        start_date = datetime.fromtimestamp(report.period_start).strftime("%Y-%m-%d %H:%M")
        end_date = datetime.fromtimestamp(report.period_end).strftime("%Y-%m-%d %H:%M")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CivitAI Downloader Analytics Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 1px solid #ecf0f1; padding-bottom: 5px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #3498db; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ color: #7f8c8d; text-transform: uppercase; font-size: 0.9em; }}
        .recommendations {{ background: #e8f5e8; padding: 15px; border-radius: 6px; border-left: 4px solid #27ae60; }}
        .error-section {{ background: #fdf2f2; padding: 15px; border-radius: 6px; border-left: 4px solid #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: 600; }}
        .progress-bar {{ width: 100%; height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #3498db; transition: width 0.3s ease; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CivitAI Downloader Analytics Report</h1>
        
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-label">Report Period</div>
                <div>{start_date}<br>to<br>{end_date}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Events</div>
                <div class="metric-value">{report.summary.get('total_events', 0):,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Unique Sessions</div>
                <div class="metric-value">{report.summary.get('unique_sessions', 0)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Events per Hour</div>
                <div class="metric-value">{report.summary.get('events_per_hour', 0):.1f}</div>
            </div>
        </div>

        <h2>API Statistics</h2>
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value">{report.api_statistics.get('success_rate', 0):.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.api_statistics.get('success_rate', 0):.1f}%"></div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value">{report.api_statistics.get('total_requests', 0):,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Response Time</div>
                <div class="metric-value">{report.api_statistics.get('avg_response_time', 0):.2f}s</div>
            </div>
        </div>

        <h2>Download Statistics</h2>
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-label">Download Success Rate</div>
                <div class="metric-value">{report.download_statistics.get('success_rate', 0):.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.download_statistics.get('success_rate', 0):.1f}%"></div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Downloads</div>
                <div class="metric-value">{report.download_statistics.get('total_downloads', 0):,}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Data Downloaded</div>
                <div class="metric-value">{report.download_statistics.get('total_downloaded_gb', 0):.1f} GB</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Speed</div>
                <div class="metric-value">{report.download_statistics.get('avg_download_speed_mbps', 0):.1f} MB/s</div>
            </div>
        </div>

        <h2>Cache Performance</h2>
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-label">Cache Hit Rate</div>
                <div class="metric-value">{report.cache_statistics.get('hit_rate_percent', 0):.1f}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {report.cache_statistics.get('hit_rate_percent', 0):.1f}%"></div>
                </div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Cache Requests</div>
                <div class="metric-value">{report.cache_statistics.get('total_cache_requests', 0):,}</div>
            </div>
        </div>"""
        
        # Add error analysis if there are errors
        if report.error_analysis.get('total_errors', 0) > 0:
            html_content += f"""
        <h2>Error Analysis</h2>
        <div class="error-section">
            <div class="summary-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Errors</div>
                    <div class="metric-value">{report.error_analysis.get('total_errors', 0)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">API Errors</div>
                    <div class="metric-value">{report.error_analysis.get('api_errors', 0)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Download Errors</div>
                    <div class="metric-value">{report.error_analysis.get('download_errors', 0)}</div>
                </div>
            </div>
        </div>"""
        
        # Add recommendations
        if report.recommendations:
            html_content += f"""
        <h2>Recommendations</h2>
        <div class="recommendations">
            <ul>
                {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
            </ul>
        </div>"""
        
        html_content += """
    </div>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_csv_report(self, report: AnalysisReport,
                            output_path: Path, config: ReportConfig) -> None:
        """Generate CSV format report."""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow(['CivitAI Downloader Analytics Report'])
            writer.writerow(['Generated at', datetime.now().isoformat()])
            writer.writerow(['Period', f"{datetime.fromtimestamp(report.period_start)} to {datetime.fromtimestamp(report.period_end)}"])
            writer.writerow([])  # Empty row
            
            # Summary metrics
            writer.writerow(['Summary Metrics'])
            writer.writerow(['Metric', 'Value'])
            for key, value in report.summary.items():
                if isinstance(value, dict):
                    continue
                writer.writerow([key.replace('_', ' ').title(), value])
            
            writer.writerow([])  # Empty row
            
            # API Statistics
            writer.writerow(['API Statistics'])
            writer.writerow(['Metric', 'Value'])
            for key, value in report.api_statistics.items():
                if isinstance(value, dict):
                    continue
                writer.writerow([key.replace('_', ' ').title(), value])
            
            writer.writerow([])  # Empty row
            
            # Download Statistics
            writer.writerow(['Download Statistics'])
            writer.writerow(['Metric', 'Value'])
            for key, value in report.download_statistics.items():
                if isinstance(value, dict):
                    continue
                writer.writerow([key.replace('_', ' ').title(), value])
    
    def _generate_markdown_report(self, report: AnalysisReport,
                                 output_path: Path, config: ReportConfig) -> None:
        """Generate Markdown format report."""
        start_date = datetime.fromtimestamp(report.period_start).strftime("%Y-%m-%d %H:%M")
        end_date = datetime.fromtimestamp(report.period_end).strftime("%Y-%m-%d %H:%M")
        
        md_content = f"""# CivitAI Downloader Analytics Report

**Report Period:** {start_date} to {end_date}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

| Metric | Value |
|--------|-------|
| Total Events | {report.summary.get('total_events', 0):,} |
| Unique Sessions | {report.summary.get('unique_sessions', 0)} |
| Events per Hour | {report.summary.get('events_per_hour', 0):.1f} |
| Duration | {report.summary.get('analysis_period', {}).get('duration_hours', 0):.1f} hours |

## API Statistics

| Metric | Value |
|--------|-------|
| Success Rate | {report.api_statistics.get('success_rate', 0):.1f}% |
| Total Requests | {report.api_statistics.get('total_requests', 0):,} |
| Total Responses | {report.api_statistics.get('total_responses', 0):,} |
| Total Errors | {report.api_statistics.get('total_errors', 0):,} |
| Avg Response Time | {report.api_statistics.get('avg_response_time', 0):.3f}s |
| Max Response Time | {report.api_statistics.get('max_response_time', 0):.3f}s |

## Download Statistics

| Metric | Value |
|--------|-------|
| Success Rate | {report.download_statistics.get('success_rate', 0):.1f}% |
| Total Downloads | {report.download_statistics.get('total_downloads', 0):,} |
| Successful Downloads | {report.download_statistics.get('successful_downloads', 0):,} |
| Failed Downloads | {report.download_statistics.get('failed_downloads', 0):,} |
| Total Downloaded | {report.download_statistics.get('total_downloaded_gb', 0):.1f} GB |
| Avg Download Speed | {report.download_statistics.get('avg_download_speed_mbps', 0):.1f} MB/s |

## Cache Performance

| Metric | Value |
|--------|-------|
| Hit Rate | {report.cache_statistics.get('hit_rate_percent', 0):.1f}% |
| Total Requests | {report.cache_statistics.get('total_cache_requests', 0):,} |
| Cache Hits | {report.cache_statistics.get('cache_hits', 0):,} |
| Cache Misses | {report.cache_statistics.get('cache_misses', 0):,} |
"""
        
        # Add error analysis if there are errors
        if report.error_analysis.get('total_errors', 0) > 0:
            md_content += f"""
## Error Analysis

| Metric | Value |
|--------|-------|
| Total Errors | {report.error_analysis.get('total_errors', 0):,} |
| API Errors | {report.error_analysis.get('api_errors', 0):,} |
| Download Errors | {report.error_analysis.get('download_errors', 0):,} |
"""
        
        # Add recommendations
        if report.recommendations:
            md_content += "\n## Recommendations\n\n"
            for i, rec in enumerate(report.recommendations, 1):
                md_content += f"{i}. {rec}\n"
        
        md_content += f"\n---\n*Report generated by CivitAI Downloader Analytics System*\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    def _generate_text_report(self, report: AnalysisReport,
                             output_path: Path, config: ReportConfig) -> None:
        """Generate plain text format report."""
        start_date = datetime.fromtimestamp(report.period_start).strftime("%Y-%m-%d %H:%M")
        end_date = datetime.fromtimestamp(report.period_end).strftime("%Y-%m-%d %H:%M")
        
        content = f"""CivitAI Downloader Analytics Report
{'=' * 50}

Report Period: {start_date} to {end_date}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

SUMMARY
{'-' * 20}
Total Events: {report.summary.get('total_events', 0):,}
Unique Sessions: {report.summary.get('unique_sessions', 0)}
Events per Hour: {report.summary.get('events_per_hour', 0):.1f}

API STATISTICS  
{'-' * 20}
Success Rate: {report.api_statistics.get('success_rate', 0):.1f}%
Total Requests: {report.api_statistics.get('total_requests', 0):,}
Average Response Time: {report.api_statistics.get('avg_response_time', 0):.3f}s

DOWNLOAD STATISTICS
{'-' * 20}
Success Rate: {report.download_statistics.get('success_rate', 0):.1f}%
Total Downloads: {report.download_statistics.get('total_downloads', 0):,}
Data Downloaded: {report.download_statistics.get('total_downloaded_gb', 0):.1f} GB
Average Speed: {report.download_statistics.get('avg_download_speed_mbps', 0):.1f} MB/s

CACHE PERFORMANCE
{'-' * 20}
Hit Rate: {report.cache_statistics.get('hit_rate_percent', 0):.1f}%
Total Requests: {report.cache_statistics.get('total_cache_requests', 0):,}
"""
        
        # Add error analysis
        if report.error_analysis.get('total_errors', 0) > 0:
            content += f"""
ERROR ANALYSIS
{'-' * 20}
Total Errors: {report.error_analysis.get('total_errors', 0):,}
API Errors: {report.error_analysis.get('api_errors', 0):,}
Download Errors: {report.error_analysis.get('download_errors', 0):,}
"""
        
        # Add recommendations
        if report.recommendations:
            content += f"\nRECOMMENDATIONS\n{'-' * 20}\n"
            for i, rec in enumerate(report.recommendations, 1):
                content += f"{i}. {rec}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)