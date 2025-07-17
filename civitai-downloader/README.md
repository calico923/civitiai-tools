# CivitAI Model Downloader

A cross-platform command-line tool for searching and downloading AI models from CivitAI.

## Features

- 🔍 Search models with advanced filtering (type, tags, base model)
- 📥 Download models with progress tracking and resume support
- 🖼️ Preview model images before downloading
- 📁 Automatic organization by model type and base model
- 💾 Metadata preservation and download history
- 🌍 Cross-platform support (Windows, macOS, Linux)
- ⚡ Asynchronous downloads for better performance

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Search for models
```bash
./civitai search "anime" --type LORA --base-model "SD 1.5"
```

### Show model details
```bash
./civitai show 123456 --images
```

### Download a model
```bash
./civitai download 123456 --version "v2.0"
```

### List download history
```bash
./civitai list --limit 20
```

### Configure settings
```bash
./civitai config set download_path "/path/to/models"
./civitai config set api_key "your-api-key"
./civitai config show
```

## Configuration

Configuration is stored in platform-specific locations:
- Windows: `%APPDATA%\civitai-downloader\config.json`
- macOS: `~/Library/Application Support/civitai-downloader/config.json`
- Linux: `~/.config/civitai-downloader/config.json`

## Development

### Project Structure
```
civitai-downloader/
├── src/
│   ├── __init__.py
│   ├── interfaces.py     # Core interfaces and data models
│   ├── config.py         # Configuration management
│   ├── utils.py          # Cross-platform utilities
│   ├── cli.py            # Command-line interface
│   ├── api_client.py     # CivitAI API client (TODO)
│   ├── search.py         # Search engine (TODO)
│   ├── preview.py        # Preview manager (TODO)
│   ├── download.py       # Download manager (TODO)
│   └── storage.py        # Storage manager (TODO)
├── tests/                # Unit tests
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
└── civitai              # CLI entry point
```

### Running Tests
```bash
python -m pytest tests/
```

## License

MIT License