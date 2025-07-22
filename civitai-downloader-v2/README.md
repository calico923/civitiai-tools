# 🚀 CivitAI Downloader v2

**Enterprise-Grade AI Model Management Platform**

A comprehensive, high-performance tool for discovering, downloading, and managing AI models from CivitAI with advanced features including bulk operations, security scanning, analytics, and enterprise-level reliability.

[![Tests](https://img.shields.io/badge/tests-112%20passed-brightgreen)]() [![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]() [![Quality](https://img.shields.io/badge/quality-production%20ready-blue)]()

## ✨ Key Features

### 🔍 **Advanced Search & Discovery**
- **Dual Search Strategy**: Direct tag search + base model filtering
- **85+ API Fields**: Complete model metadata collection  
- **15 Categories**: Comprehensive model classification
- **Smart Deduplication**: Intelligent duplicate removal

### 📥 **Enterprise Download Management**
- **Bulk Operations**: Process hundreds of models efficiently
- **Resume Capability**: Automatic download resumption
- **Security Scanning**: Malware detection and file verification
- **Performance Optimization**: Adaptive resource management

### 🛡️ **Security & Compliance**
- **Multi-layer Security**: Encryption, access control, audit trails
- **License Management**: Automated license compliance checking
- **Sandbox Execution**: Secure file processing environment
- **Privacy Protection**: Celebrity content filtering

### 📊 **Analytics & Intelligence**
- **Usage Analytics**: Comprehensive download and usage insights
- **Performance Metrics**: System optimization recommendations
- **Interactive Reports**: HTML/JSON/CSV export formats
- **Predictive Analytics**: Resource usage forecasting

### 🔧 **Reliability & Extensibility**  
- **Circuit Breakers**: Automatic failure isolation
- **Health Monitoring**: Real-time system status
- **Plugin Architecture**: Custom functionality extensions
- **API Change Detection**: Automatic adaptation to API updates

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/civitai-downloader-v2.git
cd civitai-downloader-v2

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp config/app_config.yml.example config/app_config.yml
```

### 2. Configuration

Create your configuration file:

```bash
# Edit configuration
nano config/app_config.yml
```

**Essential Settings:**
```yaml
api:
  civitai_api_key: "YOUR_API_KEY_HERE"
  base_url: "https://civitai.com/api/v1"
  rate_limit: 0.5  # requests per second

download:
  base_directory: "./downloads"
  concurrent_downloads: 3
  verify_checksums: true
  
security:
  enable_scanning: true
  require_confirmation: true
  allow_nsfw: false
```

### 3. Basic Usage

```bash
# Search and display models
python -m src.cli.main search "anime character" --limit 10

# Download a specific model
python -m src.cli.main download --model-id 12345

# Bulk download from search
python -m src.cli.main bulk-download "style lora" --limit 50 --format safetensors

# Generate analytics report
python -m src.cli.main analytics --period 7d --format html
```

## 📖 Complete Usage Guide

### 🔍 Search Operations

#### Basic Search
```bash
# Search by query
python -m src.cli.main search "cyberpunk style"

# Filter by model type  
python -m src.cli.main search "character" --types Checkpoint,LORA

# Filter by base model
python -m src.cli.main search "anime" --base-models "Illustrious,NoobAI"

# Advanced filtering
python -m src.cli.main search "portrait" \
    --categories character,style \
    --min-downloads 1000 \
    --period Month \
    --sort "Most Downloaded"
```

#### Export Search Results
```bash
# Export to different formats
python -m src.cli.main search "mecha" --export json --output mecha_models.json
python -m src.cli.main search "landscape" --export csv --output landscapes.csv
python -m src.cli.main search "fantasy" --export html --output fantasy_report.html
```

### 📥 Download Operations

#### Single Downloads
```bash
# Download by model ID
python -m src.cli.main download --model-id 123456

# Download specific version
python -m src.cli.main download --model-id 123456 --version-id 789

# Download to custom directory
python -m src.cli.main download --model-id 123456 --output-dir ./custom_models/
```

#### Bulk Downloads
```bash
# Bulk download from search
python -m src.cli.main bulk-download "anime character" \
    --limit 100 \
    --batch-size 10 \
    --priority HIGH

# Resume failed bulk download
python -m src.cli.main bulk-resume --job-id bulk_20250122_001

# Monitor bulk download progress
python -m src.cli.main bulk-status --job-id bulk_20250122_001
```

#### Advanced Download Options
```bash
# Security-focused download
python -m src.cli.main download --model-id 123456 \
    --scan-before-download \
    --verify-hashes \
    --require-safetensors

# Performance-optimized download
python -m src.cli.main download --model-id 123456 \
    --optimization-mode adaptive \
    --concurrent-chunks 8
```

### 📊 Analytics & Reporting

#### Generate Reports
```bash
# Quick analytics summary
python -m src.cli.main analytics

# Detailed report for specific period
python -m src.cli.main analytics --period 30d --format html --output monthly_report.html

# Performance analysis
python -m src.cli.main analytics --type performance --show-recommendations

# Usage statistics
python -m src.cli.main analytics --type usage --group-by model_type,base_model
```

#### System Monitoring
```bash
# System health check
python -m src.cli.main health-check

# Performance metrics
python -m src.cli.main metrics --live

# View logs
python -m src.cli.main logs --level ERROR --tail 100
```

### 🔧 Management Operations

#### Database Management
```bash
# Database status
python -m src.cli.main db-status

# Cleanup orphaned records
python -m src.cli.main db-cleanup

# Export/backup database
python -m src.cli.main db-export --output backup_20250122.sql
```

#### Security Operations
```bash
# Scan downloaded files
python -m src.cli.main security-scan --directory ./downloads/

# Audit recent downloads
python -m src.cli.main security-audit --days 7

# Update security signatures
python -m src.cli.main security-update
```

### ⚙️ Configuration Management

#### View Configuration
```bash
# Show current configuration
python -m src.cli.main config show

# Validate configuration
python -m src.cli.main config validate

# Test API connection
python -m src.cli.main config test-connection
```

#### Update Settings
```bash
# Update download directory
python -m src.cli.main config set download.base_directory ./new_downloads/

# Enable debug logging
python -m src.cli.main config set logging.level DEBUG

# Set rate limits
python -m src.cli.main config set api.rate_limit 0.2
```

## 🏗️ Advanced Usage

### Python API

#### Programmatic Search
```python
from src.core.search.advanced_search import AdvancedSearchEngine
from src.api.client import CivitAIClient
from src.data.database import DatabaseManager

# Initialize components
client = CivitAIClient()
db = DatabaseManager()
search_engine = AdvancedSearchEngine(client, db)

# Perform advanced search
results = await search_engine.search(
    query="cyberpunk style",
    filters={
        "types": ["LORA", "LoCon"],
        "base_models": ["SDXL 1.0", "Pony"],
        "min_downloads": 500,
        "categories": ["style", "concept"]
    },
    limit=100
)

print(f"Found {len(results)} models")
```

#### Bulk Operations
```python
from src.core.bulk.download_manager import BulkDownloadManager
from src.core.performance.optimizer import PerformanceOptimizer

# Create optimized bulk downloader
optimizer = PerformanceOptimizer()
bulk_manager = BulkDownloadManager(
    download_manager=download_manager,
    optimizer=optimizer,
    db_manager=db
)

# Create and start bulk job
job = await bulk_manager.create_bulk_job(
    name="Style Collection",
    items=search_results,
    options={
        "batch_size": 10,
        "priority": "HIGH",
        "verify_hashes": True
    }
)

# Monitor progress
async for progress in bulk_manager.monitor_job(job.id):
    print(f"Progress: {progress.completed}/{progress.total}")
```

#### Analytics Integration
```python
from src.core.analytics import AnalyticsCollector, AnalyticsAnalyzer

# Initialize analytics
collector = AnalyticsCollector(db_manager)
analyzer = AnalyticsAnalyzer(collector)

# Generate custom report
report = await analyzer.generate_report(
    start_time=time.time() - 2592000,  # 30 days ago
    end_time=time.time(),
    metrics=['downloads', 'performance', 'usage']
)

print(f"Total downloads: {report.summary['downloads']['total']}")
print(f"Success rate: {report.summary['downloads']['success_rate']:.1f}%")
```

## 📁 Project Architecture

```
civitai-downloader-v2/
├── src/                          # Source code
│   ├── api/                      # API client layer
│   │   ├── client.py            # Main CivitAI API client
│   │   ├── auth.py              # Authentication management
│   │   └── cache.py             # Response caching
│   ├── core/                    # Core business logic
│   │   ├── search/              # Search engine
│   │   ├── download/            # Download management
│   │   ├── bulk/                # Bulk operations
│   │   ├── analytics/           # Analytics system
│   │   ├── security/            # Security features
│   │   ├── performance/         # Performance optimization
│   │   └── config/              # Configuration management
│   ├── cli/                     # Command-line interface
│   │   └── main.py              # CLI entry point
│   ├── data/                    # Data layer
│   │   ├── database.py          # Database management
│   │   └── models/              # Data models
│   └── ui/                      # User interfaces
│       ├── dashboard.py         # Web dashboard
│       └── progress.py          # Progress displays
├── tests/                       # Test suite (112 tests)
├── config/                      # Configuration files
├── data/                        # Database files
├── docs/                        # Documentation
├── downloads/                   # Downloaded models
└── logs/                        # Log files
```

## 🧪 Testing

### Run Complete Test Suite
```bash
# All tests (112 tests)
python -m pytest tests/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# Specific component tests
python -m pytest tests/unit/test_advanced_search.py -v
python -m pytest tests/unit/test_bulk_download.py -v
python -m pytest tests/unit/test_analytics_comprehensive.py -v
```

### Test Coverage
```bash
# Generate coverage report
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html
```

## ⚙️ Configuration Reference

### Main Configuration File (`config/app_config.yml`)

```yaml
# API Settings
api:
  civitai_api_key: "${CIVITAI_API_KEY}"
  base_url: "https://civitai.com/api/v1"
  timeout: 30
  max_retries: 3
  rate_limit: 0.5  # requests per second

# Download Settings  
download:
  base_directory: "./downloads"
  concurrent_downloads: 3
  chunk_size: 8192
  verify_checksums: true
  organize_by_type: true

# Security Settings
security:
  enable_scanning: true
  max_file_size: 10737418240  # 10GB
  scan_timeout: 300
  require_confirmation: true
  allow_nsfw: false
  
# Database Settings
database:
  url: "sqlite:///data/civitai.db"
  connection_pool_size: 5
  enable_optimization: true

# Logging Settings
logging:
  level: "INFO"
  file: "logs/civitai-downloader.log"
  max_size_mb: 100
  backup_count: 5

# Analytics Settings
analytics:
  enable_collection: true
  retention_days: 90
  report_formats: ["html", "json"]
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CIVITAI_API_KEY` | Your CivitAI API key | *Required* |
| `CIVITAI_DOWNLOAD_DIR` | Download directory | `./downloads` |
| `CIVITAI_LOG_LEVEL` | Logging level | `INFO` |
| `CIVITAI_DATABASE_URL` | Database URL | `sqlite:///data/civitai.db` |

## 🔧 Troubleshooting

### Common Issues

#### API Connection Problems
```bash
# Test API connection
python -m src.cli.main config test-connection

# Check API key validity
python -m src.cli.main config validate
```

#### Download Issues
```bash
# Check disk space
python -m src.cli.main health-check

# Resume failed downloads
python -m src.cli.main download --model-id 123456 --resume

# Clear download cache
python -m src.cli.main cache clear
```

#### Performance Issues
```bash
# Get performance recommendations
python -m src.cli.main analytics --type performance --show-recommendations

# Optimize database
python -m src.cli.main db-optimize

# Clear old logs
python -m src.cli.main logs clean --older-than 30d
```

### Debug Mode
```bash
# Enable debug logging
python -m src.cli.main config set logging.level DEBUG

# Run with verbose output
python -m src.cli.main search "test" --verbose --debug
```

## 🔒 Security

### Security Features
- **File Scanning**: Automatic malware detection
- **Hash Verification**: SHA256/BLAKE3 integrity checking  
- **Access Control**: Role-based permissions
- **Audit Logging**: Complete activity tracking
- **Encryption**: Multi-level data protection

### Security Best Practices
```bash
# Enable all security features
python -m src.cli.main config set security.enable_scanning true
python -m src.cli.main config set security.verify_checksums true
python -m src.cli.main config set security.require_confirmation true

# Run security audit
python -m src.cli.main security-audit

# Update security definitions
python -m src.cli.main security-update
```

## 📊 Performance Optimization

### Automatic Optimization
```bash
# Enable adaptive optimization
python -m src.cli.main config set performance.optimization_mode adaptive

# Monitor performance
python -m src.cli.main metrics --component download --live
```

### Manual Tuning
```bash
# Adjust concurrent downloads based on your system
python -m src.cli.main config set download.concurrent_downloads 5

# Optimize for bandwidth
python -m src.cli.main config set download.chunk_size 16384

# Database optimization
python -m src.cli.main db-optimize
```

## 🚀 Enterprise Features

### Deployment
```bash
# Docker deployment
docker-compose up -d

# Kubernetes deployment  
kubectl apply -f deployment/k8s/
```

### Monitoring
```bash
# Health check endpoint
curl http://localhost:8080/health

# Metrics endpoint
curl http://localhost:8080/metrics
```

### Backup & Recovery
```bash
# Backup database
python -m src.cli.main backup --output civitai_backup_20250122.tar.gz

# Restore from backup
python -m src.cli.main restore --input civitai_backup_20250122.tar.gz
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Submit** a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Run tests before committing
python -m pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- CivitAI for providing the comprehensive API
- The open-source community for inspiration and tools
- All contributors who helped make this project better

## 📞 Support

- **Documentation**: [Full Documentation](docs/README.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/civitai-downloader-v2/issues)
- **Discord**: [Community Discord](https://discord.gg/your-server)

---

**Made with ❤️ for the AI Art Community**

*Last updated: January 2025*