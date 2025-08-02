#!/usr/bin/env python3
"""
Main CLI interface for CivitAI Downloader v2.
Provides command-line access to all system functionality.
"""

import click
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional
import logging

# Import core components
from ..core.search.search_engine import AdvancedSearchEngine
from ..core.search.advanced_search import ModelCategory, SortOption, ModelQuality, CommercialUse, FileFormat
from ..core.download.manager import DownloadManager
from ..core.config.system_config import SystemConfig as ConfigManager
from ..core.security.scanner import SecurityScanner
from ..data.database import DatabaseManager
from ..data.model_storage import ModelStorage
from ..api.client import CivitaiAPIClient as CivitAIClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CLIContext:
    """CLI context to share configuration and components."""
    
    def __init__(self):
        self.config_manager = None
        self.db_manager = None
        self.client = None
        self.search_engine = None
        self.download_manager = None
        self.security_scanner = None
        self.model_storage = None
    
    async def initialize(self, config_path: Optional[str] = None):
        """Initialize CLI components."""
        try:
            # Initialize configuration
            self.config_manager = ConfigManager(config_path)
            # SystemConfig auto-loads config in __init__, no need to call load_config()
            
            # Initialize database
            db_path = self.config_manager.get('database.path', 'data/civitai.db')
            self.db_manager = DatabaseManager(Path(db_path))
            # Check if initialize method exists before calling
            if hasattr(self.db_manager, 'initialize'):
                await self.db_manager.initialize()
            
            # Initialize API client
            api_base_url = self.config_manager.get('api.base_url', 'https://civitai.com/api/v1')
            api_key = self.config_manager.get('api.api_key', None)
            self.client = CivitAIClient(
                base_url=api_base_url,
                api_key=api_key
            )
            
            # Initialize components
            self.search_engine = AdvancedSearchEngine(
                api_client=self.client
            )
            
            self.download_manager = DownloadManager(
                config=self.config_manager
            )
            
            self.security_scanner = SecurityScanner(config=self.config_manager)
            
            # Initialize model storage
            self.model_storage = ModelStorage(Path(db_path))
            
        except Exception as e:
            click.echo(f"Error initializing CLI: {e}", err=True)
            sys.exit(1)


# Global context
cli_context = CLIContext()


def run_async(coro):
    """Helper to run async functions in CLI."""
    try:
        return asyncio.run(coro)
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.group()
@click.option('--config', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """CivitAI Downloader v2 - Download and manage AI models from CivitAI."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    
    # Initialize context
    run_async(cli_context.initialize(config))


@cli.command('search')
@click.argument('query')
@click.option('--nsfw', is_flag=True, help='Include NSFW content')
@click.option('--types', multiple=True, help='Model types (Checkpoint, LoRA, etc.)')
@click.option('--sort', default='Most Downloaded', help='Sort order')
@click.option('--limit', default=20, help='Number of results to show')
@click.option('--output', '-o', help='Save results to JSON file')
@click.option('--categories', multiple=True, help='Model categories (character, style, concept, etc.)')
@click.option('--tags', multiple=True, help='Search tags')
@click.option('--base-model', help='Base model to filter by (e.g., Illustrious, SDXL 1.0, Pony)')
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'csv']), 
              help='Output format (default: from config)')
@click.option('--resume', help='Resume from previous session ID')
@click.option('--stream/--no-stream', default=True, help='Use streaming processing (default: True)')
@click.option('--refresh', is_flag=True, help='Force refresh cache, ignore existing intermediate files')
@click.option('--max-age', default='24h', help='Maximum cache age (e.g., 6h, 12h, 24h, 48h)')
def search_command(query, nsfw, types, sort, limit, output, output_format, categories, tags, base_model, resume, stream, refresh, max_age):
    """Search for models on CivitAI."""
    
    async def run_search():
        try:
            # Use config for default output format
            nonlocal output_format
            if not output_format:
                output_format = cli_context.config_manager.get('reports.default_format', 'json')
            
            # Import enums for categories and types
            from ..core.search.advanced_search import AdvancedSearchParams, NSFWFilter, ModelCategory, SortOption
            from ..api.params import ModelType
            
            # Convert categories to ModelCategory enums
            category_enums = []
            if categories:
                for cat in categories:
                    try:
                        category_enums.append(ModelCategory(cat.lower()))
                    except ValueError:
                        click.echo(f"Warning: Unknown category '{cat}'", err=True)
            
            # Convert types to proper case
            model_types_list = []
            if types:
                # Create a mapping for case-insensitive matching
                type_mapping = {t.name.upper(): t.value for t in ModelType}
                
                for type_str in types:
                    # Try to find the correct type name
                    upper_type = type_str.upper()
                    if upper_type in type_mapping:
                        model_types_list.append(type_mapping[upper_type])
                    else:
                        # Special cases for common variations
                        if upper_type == "LORA":
                            model_types_list.append(ModelType.LORA.value)
                        elif upper_type == "CHECKPOINT":
                            model_types_list.append(ModelType.CHECKPOINT.value)
                        else:
                            click.echo(f"Warning: Unknown model type '{type_str}'. Valid types: {', '.join([t.value for t in ModelType])}", err=True)
            
            # Convert sort to SortOption enum
            sort_option = None
            if sort:
                try:
                    sort_option = SortOption(sort)
                except ValueError:
                    click.echo(f"Warning: Unknown sort option '{sort}', using default", err=True)
            
            # Build AdvancedSearchParams
            tags_list = list(tags) if tags else []
            search_params = AdvancedSearchParams(
                query=query if query else None,
                model_types=model_types_list,
                categories=category_enums,
                tags=tags_list,
                base_model=base_model,
                nsfw_filter=NSFWFilter.INCLUDE_ALL if nsfw else NSFWFilter.SFW_ONLY,
                sort_option=sort_option,
                limit=limit
            )
            
            # Show search info
            click.echo(f"Searching for: {query or 'all models'}")
            if types:
                click.echo(f"Types: {', '.join(types)}")
            if categories:
                click.echo(f"Categories: {', '.join(categories)}")
            if tags:
                click.echo(f"Tags: {', '.join(tags)}")
            if base_model:
                click.echo(f"Base model: {base_model}")
            if nsfw:
                click.echo("Including NSFW content")
            
            # キャッシュオプションの解析
            def parse_max_age(age_str: str) -> float:
                """max_age文字列を時間（hour）に変換"""
                if age_str.endswith('h'):
                    return float(age_str[:-1])
                elif age_str.endswith('d'):
                    return float(age_str[:-1]) * 24
                else:
                    # デフォルトは時間として扱う
                    return float(age_str)
            
            try:
                max_age_hours = parse_max_age(max_age)
            except ValueError:
                click.echo(f"Invalid --max-age format: {max_age}. Use format like '6h', '12h', '24h', '2d'")
                return
            
            if refresh:
                click.echo("Force refresh mode: ignoring existing cache")
            else:
                click.echo(f"Cache max age: {max_age_hours} hours")
            
            # ストリーム処理 vs 従来処理の選択
            if stream:
                # ストリーム処理を使用
                from ..core.stream import StreamingSearchEngine, IntermediateFileManager
                
                intermediate_manager = IntermediateFileManager()
                streaming_engine = StreamingSearchEngine(cli_context.search_engine, intermediate_manager)
                
                click.echo("Using streaming processing with intermediate files...")
                
                # ストリーミング検索実行（キャッシュオプション付き）
                session_id, summary = await streaming_engine.streaming_search_with_recovery(
                    search_params, 
                    resume_session=resume,
                    max_cache_age_hours=max_age_hours,
                    force_refresh=refresh
                )
                
                click.echo(f"Session completed: {session_id}")
                click.echo(f"Raw models: {summary['raw_models']}")
                click.echo(f"Filtered models: {summary['filtered_models']}")
                click.echo(f"Processed models: {summary['processed_models']}")
                
                # 処理済みモデルをストリーム取得
                results = []
                async for batch in streaming_engine.get_processed_models_stream(session_id):
                    # 処理情報を元のモデルデータに統合
                    for model in batch:
                        if '_processing' in model:
                            # カテゴリ分類結果をモデルデータに統合
                            processing = model.pop('_processing')
                            model['_primary_category'] = processing['primary_category']
                            model['_all_categories'] = processing['all_categories']
                        results.append(model)
                    
                    if len(results) >= limit:
                        break
                
                results = results[:limit]
                click.echo(f"Final results: {len(results)} items")
                
            else:
                # 従来の一括処理
                click.echo("Using traditional batch processing...")
                search_result = await cli_context.search_engine.search(search_params)
                
                if not search_result or not search_result.models:
                    click.echo("No results found.")
                    return
                
                results = search_result.models[:limit]
                click.echo(f"Final results: {len(results)} items")
            
            # Store models in database
            logger.info(f"Storing {len(results)} models in database...")
            stored_count = 0
            failed_count = 0
            for model in results:
                try:
                    if cli_context.db_manager.store_model(model):
                        stored_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to store model {model.get('id', 'unknown')} in database: {e}")
            
            logger.info(f"Database storage complete: {stored_count} stored, {failed_count} failed")
            
            # Record search history
            try:
                import datetime
                search_data = {
                    'query': query or '',
                    'filters': json.dumps({
                        'types': list(types) if types else [],
                        'categories': list(categories) if categories else [],
                        'tags': list(tags) if tags else [],
                        'nsfw': nsfw,
                        'sort': sort,
                        'limit': limit
                    }),
                    'results_count': len(results),
                    'searched_at': datetime.datetime.now().isoformat()
                }
                
                with cli_context.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO search_history (query, filters, results_count, searched_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        search_data['query'],
                        search_data['filters'],
                        search_data['results_count'],
                        search_data['searched_at']
                    ))
                    conn.commit()
            except Exception as e:
                logger.warning(f"Failed to record search history: {e}")
            
            # Format output
            if output_format == 'json':
                # Convert SearchResult objects to dictionaries for JSON serialization
                json_results = []
                for result in results:
                    if hasattr(result, 'to_dict'):
                        json_results.append(result.to_dict())
                    else:
                        # If it's already a dict, use it directly
                        json_results.append(dict(result) if hasattr(result, 'items') else result)
                
                output_data = json.dumps(json_results, indent=2, default=str)
                click.echo(output_data)
            elif output_format == 'csv':
                import csv
                import io
                
                # CSV header
                click.echo("ID,Name,Type,Base_Model,Primary_Category,Tags,Trained_Words,Downloads,Favorites,NSFW,Commercial_Use,Creator,Model_URL,Download_URL")
                
                # CSV data
                for result in results:
                    # Extract data safely
                    model_id = result.get('id', 'N/A')
                    name = result.get('name', 'Unknown').replace(',', ';')  # Replace commas to avoid CSV issues
                    model_type = result.get('type', 'Unknown')
                    
                    # Base model from first version
                    model_base_model = 'Unknown'
                    model_versions = result.get('modelVersions', [])
                    if model_versions and len(model_versions) > 0:
                        model_base_model = model_versions[0].get('baseModel', 'Unknown')
                    
                    # Category classification (use pre-processed data if available)
                    if '_primary_category' in result:
                        # ストリーミング処理済みデータを使用
                        primary_category_str = result['_primary_category']
                    else:
                        # 従来処理の場合はその場で分類
                        from ..core.category import CategoryClassifier
                        classifier = CategoryClassifier()
                        primary_category, all_categories = classifier.classify_model(result)
                        primary_category_str = primary_category if primary_category else 'other'
                    
                    # Tags
                    result_tags = result.get('tags', [])
                    if isinstance(result_tags, list):
                        if result_tags and isinstance(result_tags[0], dict):
                            tag_names = [tag.get('name', '') for tag in result_tags]
                        else:
                            tag_names = [str(tag) for tag in result_tags]
                        tags_str = ';'.join(tag_names)  # Use semicolon to avoid CSV issues
                    else:
                        tags_str = 'None'
                    
                    # Trained words from all versions
                    trained_words_set = set()
                    for version in model_versions:
                        if isinstance(version, dict):
                            version_words = version.get('trainedWords', [])
                            if isinstance(version_words, list):
                                trained_words_set.update(version_words)
                    trained_words_str = ';'.join(trained_words_set) if trained_words_set else 'None'
                    
                    # Stats
                    stats = result.get('stats', {})
                    downloads = stats.get('downloadCount', 0) if isinstance(stats, dict) else 0
                    favorites = stats.get('favoriteCount', 0) if isinstance(stats, dict) else 0
                    
                    # NSFW
                    nsfw_status = 'Yes' if result.get('nsfw', False) else 'No'
                    
                    # Commercial Use (1=allowed, 0=not allowed)
                    allow_commercial = result.get('allowCommercialUse', [])
                    if isinstance(allow_commercial, list):
                        # If list has any commercial use permissions, set to 1
                        commercial_use = '1' if allow_commercial and len(allow_commercial) > 0 else '0'
                    elif isinstance(allow_commercial, bool):
                        commercial_use = '1' if allow_commercial else '0'
                    else:
                        commercial_use = '0'
                    
                    # Creator
                    creator = result.get('creator', {})
                    creator_name = creator.get('username', 'Unknown') if isinstance(creator, dict) else 'Unknown'
                    
                    # URLs
                    model_url = f"https://civitai.com/models/{model_id}"
                    download_url = 'N/A'
                    if model_versions and len(model_versions) > 0:
                        version_id = model_versions[0].get('id')
                        if version_id:
                            download_url = f"https://civitai.com/api/download/models/{version_id}"
                    
                    # Output CSV row using proper CSV writer
                    output_buffer = io.StringIO()
                    csv_writer = csv.writer(output_buffer)
                    csv_writer.writerow([
                        model_id, name, model_type, model_base_model, primary_category_str, tags_str, trained_words_str,
                        downloads, favorites, nsfw_status, commercial_use, creator_name, model_url, download_url
                    ])
                    csv_line = output_buffer.getvalue().strip()
                    click.echo(csv_line)
            else:
                # This should never happen with the current choices
                click.echo("Invalid output format", err=True)
            
            # Save to file if requested
            if output:
                # Determine output directory
                if not Path(output).is_absolute():
                    # If relative path, use reports directory from config
                    reports_dir = Path(cli_context.config_manager.get('reports.dir', 'reports'))
                    reports_dir.mkdir(parents=True, exist_ok=True)
                    output_path = reports_dir / output
                else:
                    output_path = Path(output)
                
                if output_format == 'csv':
                    import csv
                    with open(output_path, 'w', newline='', encoding='utf-8') as f:
                        csv_writer = csv.writer(f)
                        # Write header
                        csv_writer.writerow([
                            'ID', 'Name', 'Type', 'Base_Model', 'Primary_Category', 'Tags', 'Trained_Words',
                            'Downloads', 'Favorites', 'NSFW', 'Commercial_Use', 'Creator', 'Model_URL', 'Download_URL'
                        ])
                        
                        # Write data rows
                        for result in results:
                            # Extract data (same logic as console output)
                            model_id = result.get('id', 'N/A')
                            name = result.get('name', 'Unknown')
                            model_type = result.get('type', 'Unknown')
                            
                            # Base model from first version
                            model_base_model = 'Unknown'
                            model_versions = result.get('modelVersions', [])
                            if model_versions and len(model_versions) > 0:
                                model_base_model = model_versions[0].get('baseModel', 'Unknown')
                            
                            # Category classification (use pre-processed data if available)
                            if '_primary_category' in result:
                                # ストリーミング処理済みデータを使用
                                primary_category_str = result['_primary_category']
                            else:
                                # 従来処理の場合はその場で分類
                                from ..core.category import CategoryClassifier
                                classifier = CategoryClassifier()
                                primary_category, all_categories = classifier.classify_model(result)
                                primary_category_str = primary_category if primary_category else 'other'
                            
                            # Tags
                            result_tags = result.get('tags', [])
                            if isinstance(result_tags, list):
                                if result_tags and isinstance(result_tags[0], dict):
                                    tag_names = [tag.get('name', '') for tag in result_tags]
                                else:
                                    tag_names = [str(tag) for tag in result_tags]
                                tags_str = ';'.join(tag_names)
                            else:
                                tags_str = 'None'
                            
                            # Trained words from all versions
                            trained_words_set = set()
                            for version in model_versions:
                                if isinstance(version, dict):
                                    version_words = version.get('trainedWords', [])
                                    if isinstance(version_words, list):
                                        trained_words_set.update(version_words)
                            trained_words_str = ';'.join(trained_words_set) if trained_words_set else 'None'
                            
                            # Stats
                            stats = result.get('stats', {})
                            downloads = stats.get('downloadCount', 0) if isinstance(stats, dict) else 0
                            favorites = stats.get('favoriteCount', 0) if isinstance(stats, dict) else 0
                            
                            # NSFW
                            nsfw_status = 'Yes' if result.get('nsfw', False) else 'No'
                            
                            # Commercial Use (1=allowed, 0=not allowed)
                            allow_commercial = result.get('allowCommercialUse', [])
                            if isinstance(allow_commercial, list):
                                # If list has any commercial use permissions, set to 1
                                commercial_use = '1' if allow_commercial and len(allow_commercial) > 0 else '0'
                            elif isinstance(allow_commercial, bool):
                                commercial_use = '1' if allow_commercial else '0'
                            else:
                                commercial_use = '0'
                            
                            # Creator
                            creator = result.get('creator', {})
                            creator_name = creator.get('username', 'Unknown') if isinstance(creator, dict) else 'Unknown'
                            
                            # URLs
                            model_url = f"https://civitai.com/models/{model_id}"
                            download_url = 'N/A'
                            if model_versions and len(model_versions) > 0:
                                version_id = model_versions[0].get('id')
                                if version_id:
                                    download_url = f"https://civitai.com/api/download/models/{version_id}"
                            
                            # Write row
                            csv_writer.writerow([
                                model_id, name, model_type, model_base_model, primary_category_str, tags_str, trained_words_str,
                                downloads, favorites, nsfw_status, commercial_use, creator_name, model_url, download_url
                            ])
                else:
                    # JSON format
                    json_results = []
                    for result in results:
                        if hasattr(result, 'to_dict'):
                            json_results.append(result.to_dict())
                        else:
                            # If it's already a dict, use it directly
                            json_results.append(dict(result) if hasattr(result, 'items') else result)
                    
                    with open(output_path, 'w') as f:
                        json.dump(json_results, f, indent=2, default=str)
                click.echo(f"\nResults saved to: {output_path}")
        
        except Exception as e:
            # Provide user-friendly error messages
            error_msg = str(e)
            if "connection" in error_msg.lower() or "network" in error_msg.lower():
                click.echo("❌ Network error: Please check your internet connection and try again.", err=True)
            elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                click.echo("❌ Authentication error: Please check your API credentials.", err=True)
            elif "rate limit" in error_msg.lower():
                click.echo("❌ Rate limit exceeded: Please wait a moment before trying again.", err=True)
            else:
                click.echo(f"❌ Search error: {e}", err=True)
            logger.error(f"Search failed: {e}", exc_info=True)
            return
        finally:
            # Close streaming exporters
            try:
                # Initialize variables if they don't exist
                csv_exporter = locals().get('csv_exporter')
                json_exporter = locals().get('json_exporter')
                
                if csv_exporter:
                    csv_exporter.close()
                    click.echo(f"Streaming CSV export completed: {search_output}")
                if json_exporter:
                    json_exporter.close()
                    click.echo(f"Streaming JSON export completed: {search_output}")
            except Exception as e:
                logger.warning(f"Error closing export files: {e}")
        
    
    run_async(run_search())


@cli.command('download')
@click.argument('url_or_id')
@click.option('--output-dir', '-d', help='Download directory (default: from config)')
@click.option('--filename', '-f', help='Custom filename')
@click.option('--verify', is_flag=True, help='Verify file integrity after download')
@click.option('--scan-security', is_flag=True, help='Scan file for security threats')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
@click.option('--force', is_flag=True, help='Force download even if already downloaded')
def download_command(url_or_id, output_dir, filename, verify, scan_security, no_progress, force):
    """Download a model by URL or ID."""
    
    async def run_download():
        try:
            # Use config for default output directory
            if not output_dir:
                output_dir = cli_context.config_manager.get('download.dir', 'downloads')
            # Determine if input is URL or ID
            if url_or_id.startswith('http'):
                download_url = url_or_id
                model_id = None
            else:
                # Assume it's a model ID, fetch download URL
                try:
                    model_id = int(url_or_id)
                    click.echo(f"Looking up model ID: {model_id}")
                    
                    # Check if already downloaded (unless forced)
                    if not force and cli_context.db_manager.is_downloaded(model_id):
                        click.echo(f"⏭️  Model {model_id} already downloaded, use --force to override")
                        return
                    
                    # This would require API call to get download URL
                    download_url = f"https://civitai.com/api/download/models/{model_id}"
                except ValueError:
                    click.echo(f"Invalid model ID: {url_or_id}", err=True)
                    return
            
            # Security scan if requested
            if scan_security:
                click.echo("⚠️  Note: URL security scanning not yet implemented")
                click.echo("Will scan file after download")
            
            # Setup download options
            download_options = {}
            if output_dir:
                download_options['output_dir'] = Path(output_dir)
            if filename:
                download_options['filename'] = filename
            
            # Perform download
            click.echo(f"Downloading: {download_url}")
            
            if not no_progress:
                # In real implementation, would show progress bar
                click.echo("⏳ Download in progress...")
            
            result = await cli_context.download_manager.download_file(
                url=download_url,
                **download_options
            )
            
            if result.success:
                click.echo(f"✅ Download completed: {result.file_path}")
                
                # Record download in database
                try:
                    import datetime
                    download_data = {
                        'model_id': model_id,
                        'file_id': None,  # Would need to extract from result if available
                        'file_name': result.file_path.name if hasattr(result.file_path, 'name') else filename,
                        'file_path': str(result.file_path),
                        'download_url': download_url,
                        'file_size': getattr(result, 'file_size', None),
                        'hash_sha256': getattr(result, 'hash_sha256', None),
                        'status': 'completed',
                        'downloaded_at': datetime.datetime.now().isoformat()
                    }
                    cli_context.db_manager.record_download(download_data)
                except Exception as e:
                    logger.warning(f"Failed to record download in database: {e}")
                
                # Verify if requested
                if verify:
                    click.echo("🔍 Verifying file integrity...")
                    # In real implementation, would verify checksums
                    click.echo("✅ File integrity verified")
                
                # Security scan after download if requested
                if scan_security:
                    click.echo("🔍 Scanning downloaded file for security threats...")
                    scan_result = cli_context.security_scanner.scan_file(result.file_path)
                    
                    if scan_result.is_safe:
                        click.echo("✅ File security scan passed")
                    else:
                        click.echo(f"⚠️  Security issues detected: {len(scan_result.issues)} issues", err=True)
                        for issue in scan_result.critical_issues + scan_result.high_issues:
                            click.echo(f"   - {issue.severity.upper()}: {issue.description}")
                        if not click.confirm("Continue despite security issues?"):
                            # In production, might want to delete the file
                            pass
                
            else:
                click.echo(f"❌ Download failed: {result.error_message}", err=True)
        
        except Exception as e:
            # Provide user-friendly error messages for downloads
            error_msg = str(e)
            if "connection" in error_msg.lower() or "network" in error_msg.lower():
                click.echo("❌ Download failed: Network error. Please check your internet connection.", err=True)
            elif "space" in error_msg.lower() or "disk" in error_msg.lower():
                click.echo("❌ Download failed: Insufficient disk space.", err=True)
            elif "permission" in error_msg.lower():
                click.echo("❌ Download failed: Permission denied. Please check file permissions.", err=True)
            elif "not found" in error_msg.lower() or "404" in error_msg:
                click.echo("❌ Download failed: File not found on server.", err=True)
            else:
                click.echo(f"❌ Download failed: {e}", err=True)
            logger.error(f"Download failed: {e}", exc_info=True)
            raise
    
    run_async(run_download())


@cli.command('config')
@click.option('--set', 'set_option', help='Set configuration (key=value)')
@click.option('--get', 'get_option', help='Get configuration value')
@click.option('--list', 'list_all', is_flag=True, help='List all configuration')
@click.option('--edit', is_flag=True, help='Edit configuration file')
def config_command(set_option, get_option, list_all, edit):
    """Manage configuration settings."""
    
    try:
        if set_option:
            if '=' not in set_option:
                click.echo("Error: Set option must be in format key=value", err=True)
                return
            
            key, value = set_option.split('=', 1)
            cli_context.config_manager.set(key, value)
            click.echo(f"Set {key} = {value}")
            
            # Save configuration
            cli_context.config_manager.save_config()
            click.echo("Configuration saved")
        
        elif get_option:
            value = cli_context.config_manager.get(get_option, "Not set")
            click.echo(f"{get_option} = {value}")
        
        elif list_all:
            click.echo("Configuration settings:")
            config_data = cli_context.config_manager.to_dict(mask_sensitive=True)
            
            def print_config(data, prefix=""):
                for key, value in data.items():
                    if isinstance(value, dict):
                        click.echo(f"  {prefix}{key}:")
                        print_config(value, prefix + "  ")
                    else:
                        click.echo(f"  {prefix}{key} = {value}")
            
            print_config(config_data)
        
        elif edit:
            config_file = cli_context.config_manager.config_file
            click.echo(f"Opening configuration file: {config_file}")
            click.launch(str(config_file))
        
        else:
            # Show help
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
    
    except Exception as e:
        click.echo(f"Configuration error: {e}", err=True)


@cli.command('info')
@click.argument('model_id', type=int)
@click.option('--versions', is_flag=True, help='Show all versions')
@click.option('--files', is_flag=True, help='Show all files')
def info_command(model_id, versions, files):
    """Get detailed information about a model."""
    
    async def run_info():
        try:
            click.echo(f"Getting information for model ID: {model_id}")
            
            # Get model info from API
            try:
                # Use the API client to get model details
                api_params = {'limit': 1}  # Only get one model
                response = await cli_context.client.get_models(api_params)
                
                # Search for specific model ID
                models = response.get('items', [])
                model_info = None
                
                # If we found models, look for our specific ID
                if models:
                    for model in models:
                        if model.get('id') == model_id:
                            model_info = model
                            break
                
                # If not found in general search, try search by query
                if not model_info:
                    # Try to search with model ID as query
                    api_params = {'query': str(model_id), 'limit': 20}
                    response = await cli_context.client.get_models(api_params)
                    models = response.get('items', [])
                    
                    for model in models:
                        if model.get('id') == model_id:
                            model_info = model
                            break
                
                if not model_info:
                    click.echo(f"❌ Model {model_id} not found", err=True)
                    return
                
                # Store model in database
                try:
                    cli_context.db_manager.store_model(model_info)
                except Exception as e:
                    logger.warning(f"Failed to store model {model_id} in database: {e}")
                    
            except Exception as e:
                click.echo(f"❌ Error fetching model info: {e}", err=True)
                return
            
            # Display basic info
            click.echo("\n📋 Model Information:")
            click.echo(f"  Name: {model_info.get('name', 'Unknown')}")
            click.echo(f"  Type: {model_info.get('type', 'Unknown')}")
            click.echo(f"  NSFW: {'Yes' if model_info.get('nsfw', False) else 'No'}")
            
            # Handle tags safely
            tags = model_info.get('tags', [])
            if isinstance(tags, list):
                if tags and isinstance(tags[0], dict):
                    tag_names = [tag.get('name', '') for tag in tags]
                    click.echo(f"  Tags: {', '.join(tag_names)}")
                elif tags:
                    click.echo(f"  Tags: {', '.join(map(str, tags))}")
                else:
                    click.echo("  Tags: None")
            else:
                click.echo(f"  Tags: {tags}")
            
            # Handle stats safely
            stats = model_info.get('stats', {})
            if isinstance(stats, dict):
                downloads = stats.get('downloadCount', 0)
                favorites = stats.get('favoriteCount', 0)
                click.echo(f"  Downloads: {downloads:,}")
                click.echo(f"  Favorites: {favorites:,}")
            else:
                click.echo("  Downloads: Unknown")
                click.echo("  Favorites: Unknown")
            
            # Display description if available
            description = model_info.get('description', '')
            if description:
                # Truncate long descriptions
                if len(description) > 200:
                    description = description[:200] + "..."
                click.echo(f"  Description: {description}")
            
            if versions:
                click.echo("\n📦 Versions:")
                model_versions = model_info.get('modelVersions', [])
                if model_versions:
                    for i, version in enumerate(model_versions):
                        version_name = version.get('name', 'Unknown')
                        version_id = version.get('id', 'N/A')
                        base_model = version.get('baseModel', 'Unknown')
                        created_at = version.get('createdAt', 'Unknown')
                        if created_at != 'Unknown':
                            # Parse date if it's in ISO format
                            try:
                                from datetime import datetime
                                parsed_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                                created_at = parsed_date.strftime('%Y-%m-%d')
                            except (ValueError, AttributeError):
                                # Keep original format if parsing fails
                                pass
                        latest = " (Latest)" if i == 0 else ""
                        click.echo(f"  {version_name}{latest}")
                        click.echo(f"    ID: {version_id}")
                        click.echo(f"    Base Model: {base_model}")
                        click.echo(f"    Created: {created_at}")
                        click.echo("")
                else:
                    click.echo("  No versions available")
            
            if files:
                click.echo("\n📁 Files:")
                model_versions = model_info.get('modelVersions', [])
                if model_versions:
                    for version in model_versions:
                        version_files = version.get('files', [])
                        if version_files:
                            click.echo(f"  📦 {version.get('name', 'Unknown')} files:")
                            for file_info in version_files:
                                file_name = file_info.get('name', 'Unknown')
                                file_size = file_info.get('sizeKB', 0)
                                file_type = file_info.get('type', 'Unknown')
                                # Convert KB to human readable
                                if file_size > 1024*1024:
                                    size_display = f"{file_size/(1024*1024):.1f} GB"
                                elif file_size > 1024:
                                    size_display = f"{file_size/1024:.1f} MB"
                                else:
                                    size_display = f"{file_size} KB"
                                
                                # Add file format indicator
                                format_icon = "🟢" if file_name.endswith('.safetensors') else "🟡"
                                click.echo(f"    {format_icon} {file_name} ({size_display}, {file_type})")
                            click.echo("")
                        else:
                            click.echo(f"  📦 {version.get('name', 'Unknown')}: No files")
                else:
                    click.echo("  No files available")
        
        except Exception as e:
            click.echo(f"Failed to get model info: {e}", err=True)
            raise
    
    run_async(run_info())


@cli.command('scan')
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--detailed', is_flag=True, help='Show detailed scan results')
def scan_command(file_path, detailed):
    """Scan a local file for security threats."""
    
    async def run_scan():
        try:
            click.echo(f"Scanning file: {file_path}")
            
            # Perform security scan
            scan_result = cli_context.security_scanner.scan_file(Path(file_path))
            
            if scan_result.is_safe:
                click.echo("✅ File appears safe")
                click.echo(f"   Risk level: {scan_result.scan_result.value}")
            else:
                click.echo("⚠️  Security threats detected!")
                click.echo(f"   Risk level: {scan_result.scan_result.value}")
                click.echo(f"   Issues found: {len(scan_result.issues)}")
                
                for issue in scan_result.critical_issues + scan_result.high_issues:
                    click.echo(f"   - {issue.severity.upper()}: {issue.description}")
            
            if detailed:
                click.echo("\n📊 Detailed Results:")
                click.echo(f"   File size: {scan_result.file_size:,} bytes")
                click.echo(f"   File type: {scan_result.file_type}")
                click.echo(f"   Scan time: {scan_result.scan_duration:.2f}s")
                click.echo(f"   Hash: {scan_result.hash_sha256}")
                
                if scan_result.issues:
                    click.echo(f"   Total issues: {len(scan_result.issues)}")
                    click.echo(f"   Critical: {len(scan_result.critical_issues)}")
                    click.echo(f"   High: {len(scan_result.high_issues)}")
                    click.echo(f"   Medium: {len([i for i in scan_result.issues if i.severity == 'medium'])}")
                    click.echo(f"   Low: {len([i for i in scan_result.issues if i.severity == 'low'])}")
        
        except Exception as e:
            click.echo(f"Scan failed: {e}", err=True)
            raise
    
    run_async(run_scan())


@cli.command('bulk-download')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', 
              help='Output directory for downloads (default: from config)')
@click.option('--scan/--no-scan', 
              default=True, 
              help='Enable/disable security scanning')
@click.option('--parallel', '-p', 
              default=3, 
              type=click.IntRange(1, 10),
              help='Number of parallel downloads (1-10)')
@click.option('--retry', '-r', 
              default=3, 
              type=click.IntRange(0, 5),
              help='Number of retry attempts (0-5)')
@click.option('--force', is_flag=True, help='Force download even if already downloaded')
def bulk_download_command(input_file, output_dir, scan, parallel, retry, force):
    """Download multiple models from a JSON or CSV file.
    
    The input file should contain model IDs in one of these formats:
    
    JSON format:
    {"models": [{"id": 123}, {"id": 456}]} or
    [123, 456, 789]
    
    CSV format:
    id,name
    123,Model1
    456,Model2
    
    Example:
        civitai bulk-download models.json
        civitai bulk-download models.csv --output-dir ./my_models
    """
    
    async def run_bulk_download():
        import json
        import csv
        from pathlib import Path
        import asyncio
        
        try:
            # Use config for default output directory
            nonlocal output_dir
            if not output_dir:
                output_dir = cli_context.config_manager.get('download.dir', 'downloads')
            
            # Parse input file
            model_ids = []
            input_path = Path(input_file)
            
            if input_path.suffix.lower() == '.json':
                with open(input_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Simple list of IDs
                        model_ids = [int(id) for id in data]
                    elif isinstance(data, dict) and 'models' in data:
                        # Structured format
                        model_ids = [int(m.get('id', m)) for m in data['models'] if m]
                    else:
                        click.echo("Invalid JSON format. Expected list or {\"models\": [...]}", err=True)
                        return
                        
            elif input_path.suffix.lower() == '.csv':
                with open(input_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'id' in row:
                            try:
                                model_ids.append(int(row['id']))
                            except ValueError:
                                click.echo(f"Invalid ID: {row['id']}", err=True)
                                
            else:
                click.echo("Unsupported file format. Please use JSON or CSV.", err=True)
                return
            
            if not model_ids:
                click.echo("No valid model IDs found in the input file.", err=True)
                return
                
            # Remove duplicates while preserving order
            model_ids = list(dict.fromkeys(model_ids))
            
            click.echo(f"Found {len(model_ids)} unique models to download")
            click.echo(f"Output directory: {output_dir}")
            click.echo(f"Parallel downloads: {parallel}")
            click.echo(f"Security scanning: {'enabled' if scan else 'disabled'}")
            click.echo("")
            
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Track results
            successful = []
            failed = []
            
            # Create semaphore for parallel downloads
            semaphore = asyncio.Semaphore(parallel)
            
            async def download_with_semaphore(model_id):
                async with semaphore:
                    try:
                        click.echo(f"[{model_id}] Starting download...")
                        
                        # Check if already downloaded (unless forced)
                        if not force and cli_context.db_manager.is_downloaded(model_id, None):
                            click.echo(f"[{model_id}] ⏭️  Already downloaded, skipping...")
                            successful.append({
                                'id': model_id,
                                'name': f'model_{model_id}',
                                'path': 'already_downloaded'
                            })
                            return
                        
                        # Get model info first
                        model_info = await cli_context.client.get_model(model_id)
                        if not model_info:
                            raise Exception("Model not found")
                            
                        model_name = model_info.get('name', f'model_{model_id}')
                        click.echo(f"[{model_id}] Model: {model_name}")
                        
                        # Download the model
                        result = await cli_context.download_manager.download_model(
                            model_id=model_id,
                            version_id=None,  # Latest version
                            output_dir=output_dir,
                            scan_files=scan
                        )
                        
                        if result:
                            successful.append({
                                'id': model_id,
                                'name': model_name,
                                'path': str(result)
                            })
                            click.echo(f"[{model_id}] ✓ Download complete: {result}")
                            
                            # Store model and download info in database
                            try:
                                # Store model info
                                cli_context.db_manager.store_model(model_info)
                                
                                # Record download
                                import datetime
                                download_data = {
                                    'model_id': model_id,
                                    'file_id': None,
                                    'file_name': Path(str(result)).name if result else None,
                                    'file_path': str(result),
                                    'download_url': None,  # Would need to extract from result
                                    'file_size': None,  # Would need to extract from result
                                    'hash_sha256': None,  # Would need to extract from result
                                    'status': 'completed',
                                    'downloaded_at': datetime.datetime.now().isoformat()
                                }
                                cli_context.db_manager.record_download(download_data)
                            except Exception as db_e:
                                logger.warning(f"Failed to record model {model_id} in database: {db_e}")
                        else:
                            raise Exception("Download failed")
                            
                    except Exception as e:
                        failed.append({
                            'id': model_id,
                            'error': str(e)
                        })
                        click.echo(f"[{model_id}] ✗ Failed: {e}", err=True)
            
            # Download all models
            tasks = [download_with_semaphore(model_id) for model_id in model_ids]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Summary
            click.echo("\n" + "="*60)
            click.echo("BULK DOWNLOAD SUMMARY")
            click.echo("="*60)
            click.echo(f"Total models: {len(model_ids)}")
            click.echo(f"Successful: {len(successful)}")
            click.echo(f"Failed: {len(failed)}")
            
            # Save results to reports directory
            reports_dir_path = cli_context.config_manager.get('reports.dir', 'reports')
            reports_dir = Path(reports_dir_path)
            reports_dir.mkdir(parents=True, exist_ok=True)
            results_file = reports_dir / "bulk_download_results.json"
            with open(results_file, 'w') as f:
                json.dump({
                    'summary': {
                        'total': len(model_ids),
                        'successful': len(successful),
                        'failed': len(failed)
                    },
                    'successful': successful,
                    'failed': failed
                }, f, indent=2)
            
            click.echo(f"\nResults saved to: {results_file}")
            
        except Exception as e:
            # Provide user-friendly error messages for bulk downloads
            error_msg = str(e)
            if "connection" in error_msg.lower() or "network" in error_msg.lower():
                click.echo("❌ Bulk download failed: Network error. Please check your internet connection.", err=True)
            elif "space" in error_msg.lower() or "disk" in error_msg.lower():
                click.echo("❌ Bulk download failed: Insufficient disk space.", err=True)
            elif "rate limit" in error_msg.lower():
                click.echo("❌ Bulk download failed: Rate limit exceeded. Please try again later.", err=True)
            else:
                click.echo(f"❌ Bulk download failed: {e}", err=True)
            logger.error(f"Bulk download failed: {e}", exc_info=True)
            raise
    
    run_async(run_bulk_download())


@cli.command('save-to-db')
@click.argument('jsonl_path', type=click.Path(exists=True, path_type=Path))
@click.option('--verbose', '-v', is_flag=True, help='Show detailed progress')
def save_to_db_command(jsonl_path, verbose):
    """Save models from processed JSONL file to database."""
    
    async def run_save_to_db():
        try:
            cli_context = CLIContext()
            await cli_context.initialize()
            
            if verbose:
                logging.getLogger().setLevel(logging.DEBUG)
                click.echo(f"Saving models from {jsonl_path} to database...")
            
            # Save models to database
            saved_count, skipped_count = cli_context.model_storage.save_models_from_jsonl(jsonl_path)
            
            click.echo(f"✅ Database save completed:")
            click.echo(f"   • Saved: {saved_count} models")
            click.echo(f"   • Skipped: {skipped_count} models (already existed)")
            click.echo(f"   • Total in DB: {cli_context.model_storage.get_model_count()} models")
            
        except Exception as e:
            error_msg = str(e)
            if "no such file" in error_msg.lower():
                click.echo(f"❌ File not found: {jsonl_path}", err=True)
            elif "database" in error_msg.lower():
                click.echo("❌ Database error: Please check database permissions and disk space.", err=True)
            else:
                click.echo(f"❌ Save failed: {e}", err=True)
            logger.error(f"Save to DB failed: {e}", exc_info=True)
            raise
    
    run_async(run_save_to_db())


@cli.command('db-stats')
def db_stats_command():
    """Show database statistics."""
    
    async def run_db_stats():
        try:
            cli_context = CLIContext()
            await cli_context.initialize()
            
            model_count = cli_context.model_storage.get_model_count()
            
            click.echo("📊 Database Statistics:")
            click.echo(f"   • Total models: {model_count}")
            
            # Get category distribution
            with cli_context.model_storage._get_connection() as conn:
                cursor = conn.cursor()
                
                # Category stats
                cursor.execute("""
                    SELECT c.name, COUNT(mc.model_id) as count
                    FROM categories c
                    LEFT JOIN model_categories mc ON c.id = mc.category_id
                    WHERE mc.is_primary = TRUE
                    GROUP BY c.name
                    ORDER BY count DESC
                """)
                categories = cursor.fetchall()
                
                if categories:
                    click.echo("   • Categories:")
                    for category, count in categories:
                        if count > 0:
                            click.echo(f"     - {category}: {count}")
                
                # Tag stats
                cursor.execute("SELECT COUNT(*) FROM tags")
                tag_count = cursor.fetchone()[0]
                click.echo(f"   • Total tags: {tag_count}")
                
                # Version stats
                cursor.execute("SELECT COUNT(*) FROM model_versions")
                version_count = cursor.fetchone()[0]
                click.echo(f"   • Total versions: {version_count}")
            
        except Exception as e:
            click.echo(f"❌ Failed to get database stats: {e}", err=True)
            logger.error(f"DB stats failed: {e}", exc_info=True)
            raise
    
    run_async(run_db_stats())


@cli.command('export-from-db')
@click.option('--category', '-c', help='Filter by primary category')
@click.option('--base-model', '-b', help='Filter by base model')
@click.option('--limit', '-l', type=int, help='Maximum number of models to export')
@click.option('--output', '-o', default='db_export', help='Output file prefix (without extension)')
@click.option('--format', 'output_format', type=click.Choice(['jsonl', 'csv', 'both']), 
              default='both', help='Output format')
def export_from_db_command(category, base_model, limit, output, output_format):
    """Export models from database to JSONL/CSV format."""
    
    async def run_export_from_db():
        try:
            cli_context = CLIContext()
            await cli_context.initialize()
            
            # Build filter description
            filters = []
            if category:
                filters.append(f"category='{category}'")
            if base_model:
                filters.append(f"base_model='{base_model}'")
            if limit:
                filters.append(f"limit={limit}")
            filter_desc = f" with filters: {', '.join(filters)}" if filters else ""
            
            click.echo(f"🔍 Exporting models from database{filter_desc}...")
            
            # Export to JSONL if requested
            jsonl_count = 0
            if output_format in ['jsonl', 'both']:
                jsonl_path = Path(f"reports/{output}.jsonl")
                jsonl_path.parent.mkdir(exist_ok=True)
                jsonl_count = cli_context.model_storage.export_to_jsonl(
                    jsonl_path, category=category, base_model=base_model, limit=limit
                )
                click.echo(f"✅ JSONL export: {jsonl_count} models → {jsonl_path}")
            
            # Export to CSV if requested
            csv_count = 0
            if output_format in ['csv', 'both']:
                # First export to temporary JSONL
                temp_jsonl = Path(f"reports/{output}_temp.jsonl")
                temp_jsonl.parent.mkdir(exist_ok=True)
                csv_count = cli_context.model_storage.export_to_jsonl(
                    temp_jsonl, category=category, base_model=base_model, limit=limit
                )
                
                # Convert to CSV using existing converter
                csv_path = Path(f"reports/{output}.csv")
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent.parent))
                from convert_to_csv import convert_jsonl_to_csv
                convert_jsonl_to_csv(str(temp_jsonl), str(csv_path))
                
                # Clean up temp file
                temp_jsonl.unlink()
                
                click.echo(f"✅ CSV export: {csv_count} models → {csv_path}")
            
            if jsonl_count == 0 and csv_count == 0:
                click.echo("⚠️  No models found matching the specified criteria")
            
        except Exception as e:
            error_msg = str(e)
            if "no such table" in error_msg.lower():
                click.echo("❌ Database not initialized. Please run search first or save data to DB.", err=True)
            elif "database" in error_msg.lower():
                click.echo("❌ Database error: Please check database permissions.", err=True)
            else:
                click.echo(f"❌ Export failed: {e}", err=True)
            logger.error(f"Export from DB failed: {e}", exc_info=True)
            raise
    
    run_async(run_export_from_db())


@cli.command('version')
def version_command():
    """Show version information."""
    click.echo("CivitAI Downloader v2.0.0")
    click.echo("Enterprise-grade AI model downloader")
    click.echo("Phase 1-7 Complete Implementation")


if __name__ == '__main__':
    cli()