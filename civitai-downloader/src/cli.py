"""Command-line interface for CivitAI downloader."""

import click
import asyncio
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .utils import get_platform_info, ensure_app_dirs
from .api_client import CivitAIAPIClient
from .search import ModelSearchEngine
from .interfaces import SearchParams, ModelType, SortOrder


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
    
    async def _search():
        async with CivitAIAPIClient(config) as api_client:
            search_engine = ModelSearchEngine(api_client=api_client)
            
            # Convert CLI arguments to search parameters
            types = [ModelType(t.upper()) for t in type] if type else None
            sort_order = SortOrder(sort.replace(' ', '_').upper()) if sort else SortOrder.HIGHEST_RATED
            
            search_params = SearchParams(
                query=query,
                types=types,
                tags=list(tag) if tag else None,
                base_models=list(base_model) if base_model else None,
                sort=sort_order,
                limit=limit or 20,
                nsfw=nsfw
            )
            
            try:
                results = await search_engine.search(search_params)
                
                click.echo(f"Found {len(results)} models")
                click.echo("=" * 50)
                
                for i, model in enumerate(results, 1):
                    click.echo(f"{i}. {model.name} (ID: {model.id})")
                    click.echo(f"   Type: {model.type.value}")
                    click.echo(f"   Creator: {model.creator}")
                    if model.tags:
                        click.echo(f"   Tags: {', '.join(model.tags[:5])}")
                    click.echo()
                    
            except Exception as e:
                click.echo(f"Search failed: {e}", err=True)
    
    asyncio.run(_search())


@cli.command()
@click.argument('model_id', type=int)
@click.option('--version', '-v', help='Specific version to show')
@click.option('--images', '-i', is_flag=True, help='Show preview images')
@click.pass_context
def show(ctx, model_id: int, version: Optional[str], images: bool):
    """Show detailed information about a model."""
    config = ctx.obj['config']
    
    async def _show():
        async with CivitAIAPIClient(config) as api_client:
            try:
                model = await api_client.get_model_details(model_id)
                
                click.echo(f"Model: {model.name}")
                click.echo(f"ID: {model.id}")
                click.echo(f"Type: {model.type.value}")
                click.echo(f"Creator: {model.creator}")
                click.echo(f"Description: {model.description}")
                click.echo(f"Tags: {', '.join(model.tags) if model.tags else 'None'}")
                click.echo(f"Created: {model.created_at}")
                click.echo(f"Updated: {model.updated_at}")
                click.echo()
                
                # Get versions
                versions = await api_client.get_model_versions(model_id)
                click.echo(f"Versions ({len(versions)}):")
                for v in versions:
                    click.echo(f"  - {v.name} (ID: {v.id})")
                    click.echo(f"    Base Model: {v.base_model}")
                    if v.files:
                        click.echo(f"    Files: {len(v.files)}")
                        for file in v.files[:3]:  # Show first 3 files
                            size_mb = file.size_bytes / (1024 * 1024)
                            click.echo(f"      - {file.name} ({size_mb:.1f}MB)")
                    click.echo()
                    
            except Exception as e:
                click.echo(f"Failed to get model details: {e}", err=True)
    
    asyncio.run(_show())


@cli.command()
@click.argument('model_id', type=int)
@click.option('--version', '-v', help='Specific version to download')
@click.option('--path', '-p', type=click.Path(), help='Download path')
@click.option('--no-metadata', is_flag=True, help='Skip metadata saving')
@click.pass_context
def download(ctx, model_id: int, version: Optional[str], path: Optional[str], no_metadata: bool):
    """Download a model from CivitAI."""
    config = ctx.obj['config']
    
    async def _download():
        async with CivitAIAPIClient(config) as api_client:
            try:
                # Get model details
                model = await api_client.get_model_details(model_id)
                click.echo(f"Model: {model.name}")
                
                # Get versions
                versions = await api_client.get_model_versions(model_id)
                if not versions:
                    click.echo("No versions available", err=True)
                    return
                
                # Select version
                if version:
                    selected_version = next((v for v in versions if v.name == version), None)
                    if not selected_version:
                        click.echo(f"Version '{version}' not found", err=True)
                        return
                else:
                    selected_version = versions[0]  # Latest version
                
                click.echo(f"Version: {selected_version.name}")
                
                # Show files
                if not selected_version.files:
                    click.echo("No files available for download", err=True)
                    return
                
                download_path = Path(path or config.config.download_path)
                download_path.mkdir(parents=True, exist_ok=True)
                
                click.echo(f"Download path: {download_path}")
                click.echo(f"Files to download: {len(selected_version.files)}")
                
                for file in selected_version.files:
                    file_path = download_path / file.name
                    size_mb = file.size_bytes / (1024 * 1024)
                    click.echo(f"  - {file.name} ({size_mb:.1f}MB)")
                    # TODO: Implement actual file download
                    click.echo(f"    Would download to: {file_path}")
                
                if not no_metadata:
                    # TODO: Save metadata
                    click.echo("Metadata would be saved")
                    
            except Exception as e:
                click.echo(f"Download failed: {e}", err=True)
    
    asyncio.run(_download())


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