"""Command-line interface for CivitAI downloader."""

import click
import asyncio
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from .utils import get_platform_info, ensure_app_dirs, format_file_size
from .api_client import CivitAIAPIClient
from .search import ModelSearchEngine
from .preview import PreviewManager
from .download import DownloadManager, ProgressDisplay
from .storage import StorageManager, BackupManager
from .interfaces import SearchParams, ModelType, SortOrder, ModelCategory, PeriodFilter, DownloadProgress


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
@click.option('--category', '-c', multiple=True, help='Filter by categories')
@click.option('--base-model', '-b', multiple=True, help='Filter by base model')
@click.option('--sort', '-s', help='Sort order')
@click.option('--sort-by', help='Custom sort field')
@click.option('--period', '-p', help='Time period (AllTime, Year, Month, Week, Day)')
@click.option('--limit', '-l', type=int, help='Number of results')
@click.option('--nsfw', is_flag=True, help='Include NSFW content')
@click.option('--featured', is_flag=True, help='Only featured models')
@click.option('--verified', is_flag=True, help='Only verified models')
@click.option('--commercial', is_flag=True, help='Only commercial-use models')
@click.pass_context
def search(ctx, query: Optional[str], type, tag, category, base_model, sort, sort_by, period, limit, nsfw, featured, verified, commercial):
    """Search for models on CivitAI."""
    config = ctx.obj['config']
    
    async def _search():
        async with CivitAIAPIClient(config) as api_client:
            search_engine = ModelSearchEngine(api_client=api_client)
            
            # Convert CLI arguments to search parameters
            types = [ModelType(t.upper()) for t in type] if type else None
            categories = [ModelCategory(c.upper()) for c in category] if category else None
            sort_order = SortOrder(sort.replace(' ', '_').upper()) if sort else SortOrder.HIGHEST_RATED
            period_filter = PeriodFilter(period.upper()) if period else PeriodFilter.ALL_TIME
            
            search_params = SearchParams(
                query=query,
                types=types,
                tags=list(tag) if tag else None,
                categories=categories,
                base_models=list(base_model) if base_model else None,
                sort=sort_order,
                sort_by=sort_by,
                period=period_filter,
                limit=limit or 20,
                nsfw=nsfw,
                featured=featured,
                verified=verified,
                commercial=commercial
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
@click.option('--images', '-i', is_flag=True, help='Show preview images with metadata')
@click.option('--license', '-l', is_flag=True, help='Show license information')
@click.option('--download-images', is_flag=True, help='Download preview images')
@click.option('--image-size', type=int, default=512, help='Preview image size (256, 512, 1024)')
@click.pass_context
def show(ctx, model_id: int, version: Optional[str], images: bool, license: bool, download_images: bool, image_size: int):
    """Show detailed information about a model."""
    config = ctx.obj['config']
    
    async def _show():
        async with CivitAIAPIClient(config) as api_client:
            async with PreviewManager(api_client, config) as preview_manager:
                try:
                    # Get comprehensive model details
                    model, versions = await preview_manager.get_model_details_with_versions(model_id)
                    
                    # Find specific version if requested
                    selected_version = None
                    if version:
                        for v in versions:
                            if v.name == version or str(v.id) == version:
                                selected_version = v
                                break
                        if not selected_version:
                            click.echo(f"Version '{version}' not found", err=True)
                            return
                    else:
                        selected_version = versions[0] if versions else None
                    
                    # Display model information
                    preview_manager.display_model_info(model, selected_version)
                    
                    # Show license information if requested
                    if license:
                        preview_manager.display_license_info(model, selected_version)
                    
                    # Show preview images if requested
                    if images:
                        click.echo(f"\n🖼️  Fetching preview images...")
                        preview_images = await preview_manager.get_preview_images(model, image_size)
                        
                        if preview_images:
                            click.echo(f"Found {len(preview_images)} preview images:")
                            for i, img in enumerate(preview_images, 1):
                                click.echo(f"  {i}. {img.width}x{img.height} - {img.url}")
                                if img.meta:
                                    # Show basic metadata
                                    meta = img.meta
                                    if 'prompt' in meta:
                                        prompt = meta['prompt'][:100] + "..." if len(meta['prompt']) > 100 else meta['prompt']
                                        click.echo(f"     Prompt: {prompt}")
                                    if 'seed' in meta:
                                        click.echo(f"     Seed: {meta['seed']}")
                        else:
                            click.echo("No preview images found.")
                    
                    # Download preview images if requested
                    if download_images:
                        click.echo(f"\n📥 Downloading preview images...")
                        preview_images = await preview_manager.get_preview_images(model, image_size)
                        
                        if preview_images:
                            download_dir = Path(config.config.download_path) / "previews" / str(model.id)
                            download_dir.mkdir(parents=True, exist_ok=True)
                            
                            for i, img in enumerate(preview_images, 1):
                                image_path = download_dir / f"preview_{i}.png"
                                try:
                                    await preview_manager.download_image(img, image_path, image_size)
                                    click.echo(f"  ✅ Downloaded: {image_path}")
                                except Exception as e:
                                    click.echo(f"  ❌ Failed to download image {i}: {e}")
                            
                            # Save metadata
                            metadata_path = download_dir / "metadata.json"
                            await preview_manager.save_model_metadata(model, versions, metadata_path)
                            click.echo(f"  📄 Metadata saved: {metadata_path}")
                        else:
                            click.echo("No preview images to download.")
                    
                except Exception as e:
                    click.echo(f"Failed to get model details: {e}", err=True)
    
    asyncio.run(_show())


@cli.command()
@click.argument('model_ids', nargs=-1, type=int, required=True)
@click.option('--version', '-v', multiple=True, help='Specific versions to compare (format: model_id:version)')
@click.pass_context
def compare(ctx, model_ids: tuple, version: tuple):
    """Compare multiple models side by side."""
    config = ctx.obj['config']
    
    async def _compare():
        async with CivitAIAPIClient(config) as api_client:
            async with PreviewManager(api_client, config) as preview_manager:
                try:
                    models_data = []
                    
                    # Parse version specifications
                    version_map = {}
                    for v in version:
                        if ':' in v:
                            model_id_str, version_name = v.split(':', 1)
                            version_map[int(model_id_str)] = version_name
                    
                    # Fetch all models
                    for model_id in model_ids:
                        try:
                            model, versions = await preview_manager.get_model_details_with_versions(model_id)
                            
                            # Find specific version if requested
                            selected_version = None
                            if model_id in version_map:
                                version_name = version_map[model_id]
                                for v in versions:
                                    if v.name == version_name or str(v.id) == version_name:
                                        selected_version = v
                                        break
                            else:
                                selected_version = versions[0] if versions else None
                            
                            models_data.append((model, selected_version))
                            
                        except Exception as e:
                            click.echo(f"Failed to fetch model {model_id}: {e}", err=True)
                    
                    if models_data:
                        preview_manager.display_model_comparison(models_data)
                    else:
                        click.echo("No models could be fetched for comparison.", err=True)
                    
                except Exception as e:
                    click.echo(f"Comparison failed: {e}", err=True)
    
    asyncio.run(_compare())


@cli.command()
@click.argument('model_id', type=int)
@click.option('--version', '-v', help='Specific version to download')
@click.option('--path', '-p', type=click.Path(), help='Download path')
@click.option('--file-index', '-f', type=int, help='Download specific file by index (0-based)')
@click.option('--all-files', is_flag=True, help='Download all files for the version')
@click.option('--no-metadata', is_flag=True, help='Skip metadata saving')
@click.option('--no-progress', is_flag=True, help='Disable progress display')
@click.pass_context
def download(ctx, model_id: int, version: Optional[str], path: Optional[str], file_index: Optional[int], all_files: bool, no_metadata: bool, no_progress: bool):
    """Download a model from CivitAI."""
    config = ctx.obj['config']
    
    async def _download():
        async with CivitAIAPIClient(config) as api_client:
            async with DownloadManager(config) as download_manager:
                try:
                    # Get model details
                    model = await api_client.get_model_details(model_id)
                    click.echo(f"📦 Model: {model.name}")
                    
                    # Get versions
                    versions = await api_client.get_model_versions(model_id)
                    if not versions:
                        click.echo("❌ No versions available", err=True)
                        return
                    
                    # Select version
                    if version:
                        selected_version = next((v for v in versions if v.name == version or str(v.id) == version), None)
                        if not selected_version:
                            click.echo(f"❌ Version '{version}' not found", err=True)
                            return
                    else:
                        selected_version = versions[0]  # Latest version
                    
                    click.echo(f"📋 Version: {selected_version.name}")
                    
                    # Show files
                    if not selected_version.files:
                        click.echo("❌ No files available for download", err=True)
                        return
                    
                    download_path = Path(path or config.config.download_path)
                    download_path.mkdir(parents=True, exist_ok=True)
                    
                    click.echo(f"📁 Download path: {download_path}")
                    click.echo(f"📄 Files available: {len(selected_version.files)}")
                    
                    # List files
                    for i, file in enumerate(selected_version.files):
                        size_mb = file.size_bytes / (1024 * 1024)
                        click.echo(f"  {i}. {file.name} ({size_mb:.1f}MB)")
                    
                    # Set up progress display
                    progress_display = ProgressDisplay() if not no_progress else None
                    
                    def progress_callback(progress: DownloadProgress):
                        if progress_display:
                            progress_display.update_progress(progress)
                    
                    # Download files
                    if all_files:
                        click.echo(f"⬇️  Downloading all files...")
                        
                        def multi_file_progress_callback(file_desc: str, progress: DownloadProgress):
                            click.echo(f"📥 {file_desc}: {progress.file_name}")
                            if progress_display:
                                progress_display.update_progress(progress)
                        
                        await download_manager.download_all_model_files(
                            version=selected_version,
                            path=download_path,
                            progress_callback=multi_file_progress_callback
                        )
                        
                    elif file_index is not None:
                        if file_index < 0 or file_index >= len(selected_version.files):
                            click.echo(f"❌ File index {file_index} out of range (0-{len(selected_version.files)-1})", err=True)
                            return
                        
                        file_to_download = selected_version.files[file_index]
                        click.echo(f"⬇️  Downloading: {file_to_download.name}")
                        
                        await download_manager.download_model(
                            version=selected_version,
                            path=download_path,
                            file_index=file_index,
                            progress_callback=progress_callback
                        )
                        
                    else:
                        # Download first file by default
                        click.echo(f"⬇️  Downloading primary file: {selected_version.files[0].name}")
                        
                        await download_manager.download_model(
                            version=selected_version,
                            path=download_path,
                            file_index=0,
                            progress_callback=progress_callback
                        )
                    
                    # Clean up progress display
                    if progress_display:
                        progress_display.close_all()
                    
                    # Save metadata if requested
                    if not no_metadata:
                        storage_manager = StorageManager(config)
                        model_path = storage_manager.get_model_path(model, selected_version)
                        storage_manager.save_metadata(model, selected_version, model_path)
                        storage_manager.add_to_history(model, selected_version, model_path)
                        click.echo(f"  📄 Metadata saved to storage database")
                    
                    click.echo("✅ Download completed successfully!")
                    
                except Exception as e:
                    click.echo(f"❌ Download failed: {e}", err=True)
                    raise
    
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


@cli.group()
@click.pass_context
def storage(ctx):
    """Manage local storage and metadata."""
    pass


@storage.command()
@click.pass_context
def stats(ctx):
    """Show storage statistics."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    stats = storage_manager.get_storage_stats()
    
    click.echo("📊 Storage Statistics")
    click.echo("=" * 50)
    click.echo(f"Total Models: {stats.get('total_models', 0)}")
    click.echo(f"Total Versions: {stats.get('total_versions', 0)}")
    click.echo(f"Total Files: {stats.get('total_files', 0)}")
    click.echo(f"Total Size: {stats.get('total_size_human', '0 B')}")
    click.echo(f"Last Updated: {stats.get('last_updated', 'Never')}")
    
    if stats.get('disk_total_bytes', 0) > 0:
        click.echo("\n💾 Disk Usage")
        click.echo(f"Free Space: {stats.get('disk_free_human', '0 B')}")
        click.echo(f"Total Space: {stats.get('disk_total_human', '0 B')}")
        click.echo(f"Used Space: {stats.get('disk_used_human', '0 B')}")


@storage.command()
@click.argument('model_id', type=int)
@click.pass_context
def find(ctx, model_id: int):
    """Find a model in local storage."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    model = storage_manager.find_model_by_id(model_id)
    
    if model:
        click.echo(f"✅ Found model: {model['name']}")
        click.echo(f"Type: {model['type']}")
        click.echo(f"Creator: {model['creator']}")
        click.echo(f"Downloaded: {model['downloaded_at']}")
        click.echo(f"Local Path: {model['local_path']}")
    else:
        click.echo(f"❌ Model {model_id} not found in local storage")


@storage.command()
@click.argument('name')
@click.pass_context
def search_local(ctx, name: str):
    """Search for models by name in local storage."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    models = storage_manager.find_models_by_name(name)
    
    if models:
        click.echo(f"Found {len(models)} models matching '{name}':")
        click.echo("-" * 50)
        for model in models:
            click.echo(f"ID: {model['id']} - {model['name']}")
            click.echo(f"  Type: {model['type']}")
            click.echo(f"  Creator: {model['creator']}")
            click.echo(f"  Downloaded: {model['downloaded_at']}")
            click.echo()
    else:
        click.echo(f"No models found matching '{name}'")


@storage.command()
@click.option('--type', '-t', help='Filter by model type')
@click.option('--limit', '-l', type=int, default=10, help='Number of results')
@click.pass_context
def recent(ctx, type: Optional[str], limit: int):
    """Show recently downloaded models."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    if type:
        models = storage_manager.get_models_by_type(type)
    else:
        models = storage_manager.get_recently_downloaded(limit)
    
    if models:
        click.echo(f"📥 Recently Downloaded Models ({len(models)}):")
        click.echo("-" * 50)
        for model in models:
            click.echo(f"ID: {model['id']} - {model['name']}")
            click.echo(f"  Type: {model['type']}")
            click.echo(f"  Creator: {model['creator']}")
            click.echo(f"  Downloaded: {model['downloaded_at']}")
            click.echo()
    else:
        click.echo("No downloaded models found")


@storage.command()
@click.pass_context
def cleanup(ctx):
    """Clean up orphaned files and update database."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    click.echo("🧹 Cleaning up orphaned files...")
    
    result = storage_manager.cleanup_orphaned_files()
    
    click.echo(f"✅ Cleanup complete:")
    click.echo(f"  Orphaned files removed: {result['orphaned_files']}")
    click.echo(f"  Orphaned directories removed: {result['orphaned_dirs']}")
    click.echo(f"  Space freed: {result['freed_human']}")


@storage.command()
@click.argument('output_path', type=click.Path())
@click.pass_context
def export(ctx, output_path: str):
    """Export metadata to JSON file."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    output_file = Path(output_path)
    
    try:
        storage_manager.export_metadata(output_file)
        click.echo(f"✅ Metadata exported to: {output_file}")
    except Exception as e:
        click.echo(f"❌ Export failed: {e}", err=True)


@storage.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.pass_context
def import_metadata(ctx, input_path: str):
    """Import metadata from JSON file."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    
    input_file = Path(input_path)
    
    try:
        result = storage_manager.import_metadata(input_file)
        click.echo(f"✅ Import complete:")
        click.echo(f"  Models imported: {result['imported_models']}")
        click.echo(f"  Versions imported: {result['imported_versions']}")
    except Exception as e:
        click.echo(f"❌ Import failed: {e}", err=True)


@storage.command()
@click.option('--name', '-n', help='Backup name')
@click.pass_context
def backup(ctx, name: Optional[str]):
    """Create a backup of all metadata."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    backup_manager = BackupManager(storage_manager)
    
    try:
        backup_path = backup_manager.create_backup(name)
        click.echo(f"✅ Backup created: {backup_path}")
    except Exception as e:
        click.echo(f"❌ Backup failed: {e}", err=True)


@storage.command()
@click.argument('backup_path', type=click.Path(exists=True))
@click.pass_context
def restore(ctx, backup_path: str):
    """Restore from backup."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    backup_manager = BackupManager(storage_manager)
    
    if click.confirm(f"Are you sure you want to restore from {backup_path}?"):
        try:
            result = backup_manager.restore_backup(Path(backup_path))
            click.echo(f"✅ Restore complete:")
            click.echo(f"  Models restored: {result['imported_models']}")
            click.echo(f"  Versions restored: {result['imported_versions']}")
        except Exception as e:
            click.echo(f"❌ Restore failed: {e}", err=True)


@storage.command()
@click.pass_context
def backups(ctx):
    """List available backups."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    backup_manager = BackupManager(storage_manager)
    
    backups = backup_manager.list_backups()
    
    if backups:
        click.echo(f"📋 Available Backups ({len(backups)}):")
        click.echo("-" * 70)
        for backup in backups:
            click.echo(f"Name: {backup['name']}")
            click.echo(f"  Size: {backup['size_human']}")
            click.echo(f"  Created: {backup['created']}")
            click.echo(f"  Path: {backup['path']}")
            click.echo()
    else:
        click.echo("No backups found")


@storage.command()
@click.option('--keep', '-k', type=int, default=10, help='Number of backups to keep')
@click.pass_context
def cleanup_backups(ctx, keep: int):
    """Clean up old backups."""
    config = ctx.obj['config']
    storage_manager = StorageManager(config)
    backup_manager = BackupManager(storage_manager)
    
    removed = backup_manager.cleanup_old_backups(keep)
    click.echo(f"✅ Removed {removed} old backups, keeping {keep} most recent")


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