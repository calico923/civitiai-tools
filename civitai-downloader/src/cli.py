"""Command-line interface for CivitAI downloader."""

import click
import asyncio
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .utils import get_platform_info, ensure_app_dirs


@click.group()
@click.pass_context
def cli(ctx):
    """CivitAI Model Downloader - Search and download AI models from CivitAI."""
    # Initialize configuration
    ctx.ensure_object(dict)
    ctx.obj['config'] = ConfigManager()
    ensure_app_dirs()


@cli.command()
@click.argument('query', required=False)
@click.option('--type', '-t', multiple=True, help='Filter by model type')
@click.option('--tag', multiple=True, help='Filter by tags')
@click.option('--base-model', '-b', multiple=True, help='Filter by base model')
@click.option('--sort', '-s', help='Sort order')
@click.option('--limit', '-l', type=int, help='Number of results')
@click.option('--nsfw', is_flag=True, help='Include NSFW content')
@click.pass_context
def search(ctx, query: Optional[str], type, tag, base_model, sort, limit, nsfw):
    """Search for models on CivitAI."""
    config = ctx.obj['config']
    
    # TODO: Implement search functionality
    click.echo(f"Searching for: {query or 'all models'}")
    if type:
        click.echo(f"Types: {', '.join(type)}")
    if tag:
        click.echo(f"Tags: {', '.join(tag)}")
    if base_model:
        click.echo(f"Base models: {', '.join(base_model)}")


@cli.command()
@click.argument('model_id', type=int)
@click.option('--version', '-v', help='Specific version to show')
@click.option('--images', '-i', is_flag=True, help='Show preview images')
@click.pass_context
def show(ctx, model_id: int, version: Optional[str], images: bool):
    """Show detailed information about a model."""
    config = ctx.obj['config']
    
    # TODO: Implement show functionality
    click.echo(f"Showing model {model_id}")
    if version:
        click.echo(f"Version: {version}")
    if images:
        click.echo("Showing preview images...")


@cli.command()
@click.argument('model_id', type=int)
@click.option('--version', '-v', help='Specific version to download')
@click.option('--path', '-p', type=click.Path(), help='Download path')
@click.option('--no-metadata', is_flag=True, help='Skip metadata saving')
@click.pass_context
def download(ctx, model_id: int, version: Optional[str], path: Optional[str], no_metadata: bool):
    """Download a model from CivitAI."""
    config = ctx.obj['config']
    
    # TODO: Implement download functionality
    click.echo(f"Downloading model {model_id}")
    if version:
        click.echo(f"Version: {version}")
    download_path = path or config.config.download_path
    click.echo(f"Download path: {download_path}")


@cli.command()
@click.option('--limit', '-l', type=int, default=10, help='Number of items to show')
@click.pass_context
def list(ctx, limit: int):
    """List download history."""
    config = ctx.obj['config']
    
    # TODO: Implement list functionality
    click.echo(f"Showing last {limit} downloads")


@cli.group()
@click.pass_context
def config(ctx):
    """Manage configuration settings."""
    pass


@config.command()
@click.pass_context
def show(ctx):
    """Show current configuration."""
    config_manager = ctx.obj['config']
    
    click.echo("Current configuration:")
    for key, value in config_manager.config.__dict__.items():
        if key == 'api_key' and value:
            # Mask API key
            value = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
        click.echo(f"  {key}: {value}")


@config.command()
@click.argument('key')
@click.argument('value')
@click.pass_context
def set(ctx, key: str, value: str):
    """Set a configuration value."""
    config_manager = ctx.obj['config']
    
    # Convert boolean strings
    if value.lower() in ['true', 'false']:
        value = value.lower() == 'true'
    # Try to convert numeric strings
    elif value.isdigit():
        value = int(value)
    
    try:
        config_manager.update(**{key: value})
        click.echo(f"Set {key} = {value}")
    except AttributeError:
        click.echo(f"Unknown configuration key: {key}", err=True)


@config.command()
@click.pass_context
def reset(ctx):
    """Reset configuration to defaults."""
    if click.confirm("Are you sure you want to reset all settings?"):
        config_manager = ctx.obj['config']
        config_manager.reset()
        click.echo("Configuration reset to defaults")


@cli.command()
def version():
    """Show version and system information."""
    from .. import __version__
    
    click.echo(f"CivitAI Downloader v{__version__}")
    click.echo("\nSystem information:")
    info = get_platform_info()
    for key, value in info.items():
        click.echo(f"  {key}: {value}")


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise


if __name__ == '__main__':
    main()