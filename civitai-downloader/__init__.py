"""CivitAI Model Downloader

A cross-platform command-line tool for searching and downloading AI models from CivitAI.
"""

try:
    from importlib.metadata import version
    __version__ = version(__package__ or __name__)
except ImportError:
    # Fallback for Python < 3.8 or when package not installed
    __version__ = "0.1.0"