# CivitAI Downloader v2

A high-performance, enterprise-grade tool for downloading models from CivitAI with advanced features like bulk downloads, metadata management, and security scanning.

## Features

### Core Functionality
- **High-Performance Downloads**: Concurrent downloads with resume capability
- **Advanced Search**: Complex filtering and search strategies
- **Security Scanning**: Malware detection and file verification
- **Database Optimization**: SQLite with PostgreSQL migration path
- **Monitoring & Logging**: Structured logging with metrics and alerting
- **Configuration Management**: YAML files with environment variable overrides

### Advanced Features (Phase 4)
- **Bulk Download System**: Efficient batch processing for large model collections
- **Performance Optimization**: Adaptive resource management and network optimization
- **Analytics & Reporting**: Comprehensive usage analytics with interactive reports

## Quick Start

### 1. Environment Setup

Copy the example environment file and configure your API key:

```bash
cp .env.example .env
```

Edit `.env` and set your CivitAI API key:

```bash
CIVITAI_API_KEY=your_actual_civitai_api_key_here
```

### 2. Configuration

The system uses environment variables for configuration with the following precedence:

1. Existing environment variables (highest priority)
2. `.env.local` file (local overrides, not in git)
3. `.env` file (main configuration)
4. Default values (lowest priority)

Key configuration options:

```bash
# API Configuration
CIVITAI_API_KEY=your_api_key_here
CIVITAI_BASE_URL=https://civitai.com/api/v1
CIVITAI_TIMEOUT=30

# Download Configuration
CIVITAI_CONCURRENT_DOWNLOADS=3
CIVITAI_CHUNK_SIZE=8192

# Security Configuration
CIVITAI_VERIFY_SSL=true

# Logging Configuration
CIVITAI_LOG_LEVEL=INFO
```

### 3. Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Start downloading
python -m src.main
```

## Project Structure

```
├── src/
│   ├── api/                 # API client and authentication
│   ├── core/               # Core business logic
│   │   ├── config/         # Configuration management
│   │   └── error/          # Error handling
│   ├── data/               # Data models and database
│   ├── monitoring/         # Logging and monitoring
│   └── main.py            # Application entry point
├── tests/                  # Test suite
├── docs/                   # Documentation
├── .env.example           # Environment configuration template
└── .env                   # Your local configuration (ignored by git)
```

## Development

### Phase 1: Foundation Systems ✅

- [x] Database optimization with SQLite
- [x] Structured logging and monitoring
- [x] Configuration management
- [x] Error handling framework

### Phase 2: Core Infrastructure ✅

- [x] API client with authentication
- [x] Data models and validation
- [x] Web authentication framework
- [x] Streaming search capabilities

### Phase 3: Core Business Logic ✅

- [x] Search strategy implementation
- [x] Download manager with concurrency
- [x] Security scanner integration

### Phase 4: Advanced Features ✅

- [x] Bulk download operations
- [x] Performance optimization
- [x] Enhanced metadata management
- [x] Analytics and reporting

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CIVITAI_API_KEY` | Your CivitAI API key | None | Yes |
| `CIVITAI_BASE_URL` | API base URL | `https://civitai.com/api/v1` | No |
| `CIVITAI_TIMEOUT` | API timeout in seconds | `30` | No |
| `CIVITAI_MAX_RETRIES` | Maximum retry attempts | `3` | No |
| `CIVITAI_CONCURRENT_DOWNLOADS` | Concurrent download limit | `3` | No |
| `CIVITAI_CHUNK_SIZE` | Download chunk size in bytes | `8192` | No |
| `CIVITAI_VERIFY_SSL` | Enable SSL verification | `true` | No |
| `CIVITAI_LOG_LEVEL` | Logging level | `INFO` | No |

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python -m pytest tests/unit/test_database_optimization.py
python -m pytest tests/unit/test_logging_monitoring.py

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Advanced Usage Examples

### Bulk Download System

```python
from core.bulk import BulkDownloadManager, create_bulk_download_from_search
from core.search import search_checkpoints

# Search for models
results = search_checkpoints(query="anime character", limit=50)

# Create bulk download job
bulk_manager = BulkDownloadManager()
job_id = bulk_manager.create_bulk_job(
    search_results=results,
    name="Anime Character Collection",
    options={'batch_size': 10, 'priority': 'HIGH'}
)

# Monitor progress
def progress_callback(job_id, progress):
    print(f"Progress: {progress['downloaded_files']}/{progress['total_files']}")

bulk_manager.add_progress_callback(progress_callback)
```

### Performance Optimization

```python
from core.performance import create_optimized_download_manager, OptimizationMode

# Create performance-optimized download manager
manager = create_optimized_download_manager(mode="adaptive")

# Download with automatic optimization
task_id = manager.create_download_task(file_info)
await manager.start_download(task_id)

# Check performance report
report = manager.optimizer.get_performance_report()
print(f"Network condition: {report['metrics']['network_condition']}")
print(f"Recommendations: {report['recommendations']}")
```

### Analytics and Reporting

```python
from core.analytics import create_complete_analytics_system, quick_analytics_report

# Initialize analytics system
collector, analyzer, generator = create_complete_analytics_system()

# Generate quick report for the last 7 days
report_path = quick_analytics_report(period_days=7, output_format="html")
print(f"Report generated: {report_path}")

# Custom analytics
end_time = time.time()
start_time = end_time - (30 * 24 * 3600)  # 30 days
report = analyzer.generate_report(start_time, end_time)

print(f"Downloads: {report.summary['downloads']['total_downloads']}")
print(f"Success rate: {report.summary['downloads']['success_rate']:.1f}%")
print(f"Recommendations: {len(report.recommendations)}")
```

### Example: Complete Workflow

```python
# Complete workflow combining all Phase 4 features
import asyncio
from core.search import search_loras
from core.bulk import BulkDownloadManager
from core.performance import create_optimized_download_manager
from core.analytics import get_analytics_collector

async def advanced_download_workflow():
    # 1. Initialize analytics
    collector = get_analytics_collector()
    
    # 2. Search for models
    loras = search_loras(query="style", limit=20)
    
    # 3. Create optimized bulk download
    bulk_manager = BulkDownloadManager()
    bulk_manager.download_manager = create_optimized_download_manager(mode="adaptive")
    
    # 4. Start bulk download with analytics
    job_id = bulk_manager.create_bulk_job(
        search_results=loras,
        name="Style LoRA Collection"
    )
    
    # 5. Wait for completion
    while True:
        job = bulk_manager.get_job_status(job_id)
        if job.status in ["COMPLETED", "FAILED"]:
            break
        await asyncio.sleep(5)
    
    # 6. Generate analytics report
    from core.analytics import quick_analytics_report
    report_path = quick_analytics_report()
    print(f"Analytics report: {report_path}")

# Run the workflow
asyncio.run(advanced_download_workflow())
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Security

- Never commit your `.env` file to git
- Use strong API keys and rotate them regularly
- Enable SSL verification in production
- Review security scanner results before using downloaded models