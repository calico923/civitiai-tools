#!/usr/bin/env python3
"""
Analytics Reporter for CivitAI Downloader.
Generates visual reports and dashboards from analytics data.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import base64
import io

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from .analyzer import AnalyticsAnalyzer, AnalyticsReport, TimeSeriesData
    from .collector import AnalyticsCollector
    from ...core.config.system_config import SystemConfig
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.analytics.analyzer import AnalyticsAnalyzer, AnalyticsReport, TimeSeriesData
    from core.analytics.collector import AnalyticsCollector
    from core.config.system_config import SystemConfig


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    include_charts: bool = True
    chart_style: str = "modern"  # "modern", "classic", "minimal"
    format: str = "html"  # "html", "pdf", "json"
    theme: str = "light"  # "light", "dark"
    language: str = "en"  # "en", "ja"
    logo_path: Optional[Path] = None
    custom_css: Optional[str] = None


class ReportGenerator:
    """Generates comprehensive analytics reports."""
    
    def __init__(self, analyzer: AnalyticsAnalyzer, config: Optional[SystemConfig] = None):
        """
        Initialize report generator.
        
        Args:
            analyzer: Analytics analyzer instance
            config: System configuration
        """
        self.analyzer = analyzer
        self.config = config or SystemConfig()
        self.output_dir = Path(self.config.get('analytics.report_dir', 'reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Capabilities check
        self.matplotlib_available = MATPLOTLIB_AVAILABLE
        self.plotly_available = PLOTLY_AVAILABLE
        self.pdf_available = WEASYPRINT_AVAILABLE
        
        # Chart configurations
        self.chart_colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'success': '#009639',
            'warning': '#F18F01',
            'danger': '#C73E1D',
            'info': '#5BC0EB'
        }
    
    def generate_report(self, report: AnalyticsReport, 
                       config: Optional[ReportConfig] = None) -> Path:
        """
        Generate a comprehensive analytics report.
        
        Args:
            report: Analytics report data
            config: Report configuration
            
        Returns:
            Path to generated report file
        """
        config = config or ReportConfig()
        
        if config.format == "html":
            return self._generate_html_report(report, config)
        elif config.format == "pdf":
            return self._generate_pdf_report(report, config)
        elif config.format == "json":
            return self._generate_json_report(report, config)
        else:
            raise ValueError(f"Unsupported report format: {config.format}")
    
    def _generate_html_report(self, report: AnalyticsReport, 
                             config: ReportConfig) -> Path:
        """Generate HTML report."""
        timestamp = datetime.fromtimestamp(report.generated_at).strftime("%Y%m%d_%H%M%S")
        filename = f"analytics_report_{timestamp}.html"
        output_path = self.output_dir / filename
        
        # Generate charts if requested
        charts_data = {}
        if config.include_charts and self.plotly_available:
            charts_data = self._generate_plotly_charts(report)
        
        # Generate HTML content
        html_content = self._build_html_content(report, charts_data, config)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def _generate_pdf_report(self, report: AnalyticsReport, 
                            config: ReportConfig) -> Path:
        """Generate PDF report."""
        if not self.pdf_available:
            raise RuntimeError("PDF generation requires weasyprint. Install with: pip install weasyprint")
        
        # First generate HTML
        html_config = ReportConfig(
            include_charts=config.include_charts,
            format="html",
            theme=config.theme,
            language=config.language
        )
        html_path = self._generate_html_report(report, html_config)
        
        # Convert to PDF
        timestamp = datetime.fromtimestamp(report.generated_at).strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"analytics_report_{timestamp}.pdf"
        pdf_path = self.output_dir / pdf_filename
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        HTML(string=html_content, base_url=str(self.output_dir)).write_pdf(str(pdf_path))
        
        # Clean up temporary HTML file
        html_path.unlink()
        
        return pdf_path
    
    def _generate_json_report(self, report: AnalyticsReport, 
                             config: ReportConfig) -> Path:
        """Generate JSON report."""
        timestamp = datetime.fromtimestamp(report.generated_at).strftime("%Y%m%d_%H%M%S")
        filename = f"analytics_report_{timestamp}.json"
        output_path = self.output_dir / filename
        
        # Convert report to JSON-serializable format
        report_data = {
            'report_id': report.report_id,
            'generated_at': report.generated_at,
            'time_period': {
                'start': report.time_period[0],
                'end': report.time_period[1],
                'start_iso': datetime.fromtimestamp(report.time_period[0]).isoformat(),
                'end_iso': datetime.fromtimestamp(report.time_period[1]).isoformat()
            },
            'summary': report.summary,
            'trends': [
                {
                    'metric_name': trend.metric_name,
                    'current_value': trend.current_value,
                    'previous_value': trend.previous_value,
                    'change_percent': trend.change_percent,
                    'trend_direction': trend.trend_direction,
                    'significance': trend.significance,
                    'is_improving': trend.is_improving
                }
                for trend in report.trends
            ],
            'patterns': [
                {
                    'pattern_type': pattern.pattern_type,
                    'description': pattern.description,
                    'frequency': pattern.frequency,
                    'confidence': pattern.confidence,
                    'examples': pattern.examples,
                    'recommendations': pattern.recommendations
                }
                for pattern in report.patterns
            ],
            'insights': [
                {
                    'category': insight.category,
                    'metric': insight.metric,
                    'current_value': insight.current_value,
                    'benchmark_value': insight.benchmark_value,
                    'impact': insight.impact,
                    'severity': insight.severity,
                    'recommendation': insight.recommendation,
                    'estimated_improvement': insight.estimated_improvement
                }
                for insight in report.insights
            ],
            'recommendations': report.recommendations,
            'charts_data': {
                chart_name: [
                    {
                        'timestamp': data.timestamp,
                        'value': data.value,
                        'label': data.label,
                        'datetime_iso': datetime.fromtimestamp(data.timestamp).isoformat()
                    }
                    for data in chart_data
                ]
                for chart_name, chart_data in report.charts_data.items()
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def _generate_plotly_charts(self, report: AnalyticsReport) -> Dict[str, str]:
        """Generate Plotly charts and return as HTML strings."""
        charts = {}
        
        # Download activity chart
        if 'download_activity' in report.charts_data:
            charts['download_activity'] = self._create_download_activity_chart(
                report.charts_data['download_activity']
            )
        
        # Performance metrics chart
        if 'performance_metrics' in report.charts_data:
            charts['performance_metrics'] = self._create_performance_chart(
                report.charts_data['performance_metrics']
            )
        
        # Success rate chart
        if 'success_rate' in report.charts_data:
            charts['success_rate'] = self._create_success_rate_chart(
                report.charts_data['success_rate']
            )
        
        # Summary metrics pie chart
        charts['summary_pie'] = self._create_summary_pie_chart(report.summary)
        
        # Trends chart
        if report.trends:
            charts['trends'] = self._create_trends_chart(report.trends)
        
        return charts
    
    def _create_download_activity_chart(self, data: List[TimeSeriesData]) -> str:
        """Create download activity time series chart."""
        if not data:
            return "<p>No download activity data available</p>"
        
        times = [datetime.fromtimestamp(d.timestamp) for d in data]
        values = [d.value for d in data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times, 
            y=values,
            mode='lines+markers',
            name='Downloads',
            line=dict(color=self.chart_colors['primary'], width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title='Download Activity Over Time',
            xaxis_title='Time',
            yaxis_title='Number of Downloads',
            hovermode='x unified',
            height=400
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    
    def _create_performance_chart(self, data: List[TimeSeriesData]) -> str:
        """Create performance metrics chart."""
        if not data:
            return "<p>No performance data available</p>"
        
        times = [datetime.fromtimestamp(d.timestamp) for d in data]
        values = [d.value for d in data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode='lines',
            name='CPU Usage (%)',
            line=dict(color=self.chart_colors['warning'], width=2)
        ))
        
        fig.update_layout(
            title='System Performance Over Time',
            xaxis_title='Time',
            yaxis_title='CPU Usage (%)',
            yaxis=dict(range=[0, 100]),
            height=400
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    
    def _create_success_rate_chart(self, data: List[TimeSeriesData]) -> str:
        """Create success rate chart."""
        if not data:
            return "<p>No success rate data available</p>"
        
        times = [datetime.fromtimestamp(d.timestamp) for d in data]
        values = [d.value for d in data]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode='lines+markers',
            name='Success Rate',
            line=dict(color=self.chart_colors['success'], width=2),
            marker=dict(size=6)
        ))
        
        fig.update_layout(
            title='Download Success Rate Over Time',
            xaxis_title='Time',
            yaxis_title='Success Rate (%)',
            yaxis=dict(range=[0, 100]),
            height=400
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    
    def _create_summary_pie_chart(self, summary: Dict[str, Any]) -> str:
        """Create summary metrics pie chart."""
        if 'downloads' not in summary:
            return "<p>No download summary data available</p>"
        
        downloads = summary['downloads']
        
        labels = ['Successful', 'Failed']
        values = [
            downloads.get('successful_downloads', 0),
            downloads.get('failed_downloads', 0)
        ]
        
        colors = [self.chart_colors['success'], self.chart_colors['danger']]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            hole=0.3
        )])
        
        fig.update_layout(
            title='Download Results Summary',
            height=400
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    
    def _create_trends_chart(self, trends) -> str:
        """Create trends comparison chart."""
        if not trends:
            return "<p>No trends data available</p>"
        
        metrics = [trend.metric_name for trend in trends]
        changes = [trend.change_percent for trend in trends]
        colors = [
            self.chart_colors['success'] if change > 0 else self.chart_colors['danger']
            for change in changes
        ]
        
        fig = go.Figure(data=[go.Bar(
            x=metrics,
            y=changes,
            marker_color=colors
        )])
        
        fig.update_layout(
            title='Metrics Trends (% Change)',
            xaxis_title='Metrics',
            yaxis_title='Change (%)',
            height=400
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
    
    def _build_html_content(self, report: AnalyticsReport, 
                           charts_data: Dict[str, str], 
                           config: ReportConfig) -> str:
        """Build complete HTML report content."""
        
        # Generate report sections
        summary_section = self._build_summary_section(report.summary)
        trends_section = self._build_trends_section(report.trends)
        patterns_section = self._build_patterns_section(report.patterns)
        insights_section = self._build_insights_section(report.insights)
        recommendations_section = self._build_recommendations_section(report.recommendations)
        charts_section = self._build_charts_section(charts_data) if charts_data else ""
        
        # Period info
        start_time = datetime.fromtimestamp(report.time_period[0]).strftime("%Y-%m-%d %H:%M")
        end_time = datetime.fromtimestamp(report.time_period[1]).strftime("%Y-%m-%d %H:%M")
        generated_time = datetime.fromtimestamp(report.generated_at).strftime("%Y-%m-%d %H:%M:%S")
        
        # Plotly.js inclusion
        plotly_js = """
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        """ if config.include_charts and charts_data else ""
        
        html_template = f"""
<!DOCTYPE html>
<html lang="{config.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CivitAI Downloader Analytics Report</title>
    {plotly_js}
    <style>
        {self._get_css_styles(config)}
    </style>
</head>
<body>
    <div class="container">
        <header class="report-header">
            <h1>📊 CivitAI Downloader Analytics Report</h1>
            <div class="report-meta">
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Period:</strong> {start_time} - {end_time}</p>
                <p><strong>Generated:</strong> {generated_time}</p>
            </div>
        </header>
        
        <div class="report-content">
            {summary_section}
            {charts_section}
            {trends_section}
            {patterns_section}
            {insights_section}
            {recommendations_section}
        </div>
        
        <footer class="report-footer">
            <p>Generated by CivitAI Downloader Analytics System</p>
        </footer>
    </div>
</body>
</html>
        """
        
        return html_template
    
    def _build_summary_section(self, summary: Dict[str, Any]) -> str:
        """Build summary statistics section."""
        downloads = summary.get('downloads', {})
        searches = summary.get('searches', {})
        security = summary.get('security', {})
        performance = summary.get('performance', {})
        
        return f"""
        <section class="summary-section">
            <h2>📈 Summary Statistics</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Downloads</h3>
                    <div class="metric-value">{downloads.get('total_downloads', 0)}</div>
                    <div class="metric-label">Total Downloads</div>
                    <div class="metric-detail">
                        Success Rate: {downloads.get('success_rate', 0):.1f}%<br>
                        Total Size: {downloads.get('total_size_gb', 0):.2f} GB
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Searches</h3>
                    <div class="metric-value">{searches.get('total_searches', 0)}</div>
                    <div class="metric-label">Total Searches</div>
                    <div class="metric-detail">
                        Avg Results: {searches.get('average_results_per_search', 0):.1f}<br>
                        Avg Response: {searches.get('average_response_time', 0):.2f}s
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Security</h3>
                    <div class="metric-value">{security.get('total_scans', 0)}</div>
                    <div class="metric-label">Files Scanned</div>
                    <div class="metric-detail">
                        Safe: {security.get('safe_files', 0)}<br>
                        Threats: {security.get('suspicious_files', 0) + security.get('malicious_files', 0)}
                    </div>
                </div>
                
                <div class="metric-card">
                    <h3>Performance</h3>
                    <div class="metric-value">{performance.get('average_download_speed', 0) / (1024*1024):.1f}</div>
                    <div class="metric-label">Avg Speed (MB/s)</div>
                    <div class="metric-detail">
                        CPU: {performance.get('average_cpu_usage', 0):.1f}%<br>
                        Memory: {performance.get('average_memory_usage', 0):.1f}%
                    </div>
                </div>
            </div>
        </section>
        """
    
    def _build_trends_section(self, trends) -> str:
        """Build trends analysis section."""
        if not trends:
            return ""
        
        trends_html = ""
        for trend in trends:
            trend_icon = "📈" if trend.trend_direction == "up" else "📉" if trend.trend_direction == "down" else "➡️"
            significance_class = f"significance-{trend.significance}"
            
            trends_html += f"""
            <div class="trend-item {significance_class}">
                <div class="trend-header">
                    <span class="trend-icon">{trend_icon}</span>
                    <span class="trend-name">{trend.metric_name}</span>
                    <span class="trend-change">{trend.change_percent:+.1f}%</span>
                </div>
                <div class="trend-details">
                    Current: {trend.current_value:.2f} | Previous: {trend.previous_value:.2f}
                </div>
            </div>
            """
        
        return f"""
        <section class="trends-section">
            <h2>📊 Trends Analysis</h2>
            <div class="trends-container">
                {trends_html}
            </div>
        </section>
        """
    
    def _build_patterns_section(self, patterns) -> str:
        """Build usage patterns section."""
        if not patterns:
            return ""
        
        patterns_html = ""
        for pattern in patterns:
            patterns_html += f"""
            <div class="pattern-item">
                <h4>{pattern.description}</h4>
                <div class="pattern-meta">
                    Type: {pattern.pattern_type} | Frequency: {pattern.frequency} | 
                    Confidence: {pattern.confidence:.1%}
                </div>
                <div class="pattern-recommendations">
                    <strong>Recommendations:</strong>
                    <ul>
                        {''.join(f"<li>{rec}</li>" for rec in pattern.recommendations)}
                    </ul>
                </div>
            </div>
            """
        
        return f"""
        <section class="patterns-section">
            <h2>🔍 Usage Patterns</h2>
            <div class="patterns-container">
                {patterns_html}
            </div>
        </section>
        """
    
    def _build_insights_section(self, insights) -> str:
        """Build performance insights section."""
        if not insights:
            return ""
        
        insights_html = ""
        for insight in insights:
            severity_icon = "🚨" if insight.severity == "critical" else "⚠️" if insight.severity == "warning" else "ℹ️"
            severity_class = f"insight-{insight.severity}"
            
            improvement_text = ""
            if insight.estimated_improvement:
                improvement_text = f" (Est. improvement: {insight.estimated_improvement:.1f}%)"
            
            insights_html += f"""
            <div class="insight-item {severity_class}">
                <div class="insight-header">
                    <span class="insight-icon">{severity_icon}</span>
                    <span class="insight-category">{insight.category}</span>
                    <span class="insight-metric">{insight.metric}</span>
                </div>
                <div class="insight-content">
                    <div class="insight-values">
                        Current: {insight.current_value:.2f} | 
                        Benchmark: {insight.benchmark_value:.2f}
                    </div>
                    <div class="insight-recommendation">
                        {insight.recommendation}{improvement_text}
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <section class="insights-section">
            <h2>💡 Performance Insights</h2>
            <div class="insights-container">
                {insights_html}
            </div>
        </section>
        """
    
    def _build_recommendations_section(self, recommendations: List[str]) -> str:
        """Build recommendations section."""
        if not recommendations:
            return ""
        
        recommendations_html = "".join(f"<li>{rec}</li>" for rec in recommendations)
        
        return f"""
        <section class="recommendations-section">
            <h2>🎯 Recommendations</h2>
            <ul class="recommendations-list">
                {recommendations_html}
            </ul>
        </section>
        """
    
    def _build_charts_section(self, charts_data: Dict[str, str]) -> str:
        """Build charts section."""
        if not charts_data:
            return ""
        
        charts_html = ""
        for chart_name, chart_html in charts_data.items():
            charts_html += f"""
            <div class="chart-container">
                {chart_html}
            </div>
            """
        
        return f"""
        <section class="charts-section">
            <h2>📊 Visual Analytics</h2>
            <div class="charts-grid">
                {charts_html}
            </div>
        </section>
        """
    
    def _get_css_styles(self, config: ReportConfig) -> str:
        """Get CSS styles for the report."""
        base_styles = """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .report-header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #2E86AB;
        }
        
        .report-header h1 {
            color: #2E86AB;
            margin-bottom: 10px;
        }
        
        .report-meta p {
            margin: 5px 0;
            color: #666;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2E86AB;
            text-align: center;
        }
        
        .metric-card h3 {
            color: #2E86AB;
            margin-bottom: 10px;
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
            margin: 10px 0;
        }
        
        .metric-label {
            font-weight: bold;
            color: #666;
            margin-bottom: 10px;
        }
        
        .metric-detail {
            font-size: 0.9em;
            color: #888;
        }
        
        section {
            margin: 30px 0;
            padding: 20px 0;
        }
        
        section h2 {
            color: #2E86AB;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        .trends-container {
            display: grid;
            gap: 15px;
        }
        
        .trend-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ddd;
        }
        
        .trend-item.significance-high {
            border-left-color: #C73E1D;
        }
        
        .trend-item.significance-medium {
            border-left-color: #F18F01;
        }
        
        .trend-item.significance-low {
            border-left-color: #009639;
        }
        
        .trend-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }
        
        .trend-icon {
            font-size: 1.2em;
        }
        
        .trend-change {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .patterns-container, .insights-container {
            display: grid;
            gap: 20px;
        }
        
        .pattern-item, .insight-item {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #2E86AB;
        }
        
        .insight-item.insight-critical {
            border-left-color: #C73E1D;
            background: #fff5f5;
        }
        
        .insight-item.insight-warning {
            border-left-color: #F18F01;
            background: #fffbf0;
        }
        
        .insight-item.insight-info {
            border-left-color: #5BC0EB;
            background: #f0f9ff;
        }
        
        .insight-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .insight-category {
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.8em;
            padding: 2px 8px;
            background: #2E86AB;
            color: white;
            border-radius: 12px;
        }
        
        .recommendations-list {
            list-style: none;
            counter-reset: recommendation;
        }
        
        .recommendations-list li {
            counter-increment: recommendation;
            padding: 10px 0;
            padding-left: 30px;
            position: relative;
        }
        
        .recommendations-list li::before {
            content: counter(recommendation);
            position: absolute;
            left: 0;
            top: 10px;
            background: #2E86AB;
            color: white;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .charts-grid {
            display: grid;
            gap: 30px;
        }
        
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .report-footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .trend-header {
                flex-direction: column;
                align-items: flex-start;
            }
        }
        
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
            .chart-container { break-inside: avoid; }
        }
        """
        
        if config.custom_css:
            base_styles += "\n" + config.custom_css
        
        return base_styles


def create_analytics_dashboard(collector: AnalyticsCollector, 
                             output_dir: Optional[Path] = None) -> Path:
    """
    Create a comprehensive analytics dashboard.
    
    Args:
        collector: Analytics collector instance
        output_dir: Output directory for dashboard
        
    Returns:
        Path to generated dashboard
    """
    analyzer = AnalyticsAnalyzer(collector)
    generator = ReportGenerator(analyzer)
    
    # Generate report for the last 7 days
    end_time = time.time()
    start_time = end_time - (7 * 24 * 3600)
    
    report = analyzer.generate_report(start_time, end_time)
    
    config = ReportConfig(
        include_charts=True,
        format="html",
        theme="light"
    )
    
    dashboard_path = generator.generate_report(report, config)
    return dashboard_path


if __name__ == "__main__":
    # Test report generator
    print("Testing Analytics Reporter...")
    
    from core.analytics.collector import AnalyticsCollector
    from core.analytics.analyzer import AnalyticsAnalyzer
    
    # Create test instances
    collector = AnalyticsCollector()
    analyzer = AnalyticsAnalyzer(collector)
    generator = ReportGenerator(analyzer)
    
    # Generate test report
    end_time = time.time()
    start_time = end_time - (24 * 3600)  # Last 24 hours
    
    report = analyzer.generate_report(start_time, end_time)
    
    # Generate HTML report
    config = ReportConfig(
        include_charts=generator.plotly_available,
        format="html"
    )
    
    output_path = generator.generate_report(report, config)
    print(f"Report generated: {output_path}")
    
    # Generate JSON report
    json_config = ReportConfig(format="json")
    json_path = generator.generate_report(report, json_config)
    print(f"JSON report generated: {json_path}")
    
    print(f"Chart capabilities: Plotly={generator.plotly_available}, PDF={generator.pdf_available}")
    
    collector.stop()
    print("Analytics Reporter test completed.")