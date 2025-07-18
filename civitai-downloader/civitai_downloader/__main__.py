"""Entry point for the CivitAI downloader CLI."""

import sys
from .cli import cli

def main():
    """Main entry point for console script."""
    # Fix the program name for proper Click parsing
    sys.argv[0] = 'civitai'
    cli()

if __name__ == '__main__':
    main()