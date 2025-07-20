# CivitAI Downloader v2

A high-performance, enterprise-grade tool for downloading models from CivitAI with advanced features like bulk downloads, metadata management, and security scanning.

## Features

- **High-Performance Downloads**: Concurrent downloads with resume capability
- **Advanced Search**: Complex filtering and search strategies
- **Security Scanning**: Malware detection and file verification
- **Database Optimization**: SQLite with PostgreSQL migration path
- **Monitoring & Logging**: Structured logging with metrics and alerting
- **Configuration Management**: YAML files with environment variable overrides

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

### Phase 3: Core Business Logic (In Progress)

- [ ] Search strategy implementation
- [ ] Download manager with concurrency
- [ ] Security scanner integration

### Phase 4: Advanced Features (Planned)

- [ ] Bulk download operations
- [ ] Performance optimization
- [ ] Enhanced metadata management
- [ ] Analytics and reporting

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