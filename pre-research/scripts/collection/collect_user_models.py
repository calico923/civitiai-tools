#!/usr/bin/env python3
"""
Collect all models created by a specific user from CivitAI API.

Example usage:
    python collect_user_models.py DanMogren
    python collect_user_models.py username --type LORA --sort Newest
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector


class UserModelCollector:
    """Collect all models created by a specific user."""
    
    def __init__(self, api_key: str):
        self.client = CivitaiClient(api_key)
        self.url_collector = URLCollector()
    
    def collect_user_models(self, 
                           username: str,
                           model_types: Optional[List[str]] = None,
                           base_models: Optional[List[str]] = None,
                           tags: Optional[List[str]] = None,
                           sort_order: str = "Newest",
                           max_pages: int = 50) -> List[Dict]:
        """
        Collect all models created by a specific user with optional filtering.
        
        Args:
            username: The username of the creator
            model_types: Optional list of model types to filter by
            base_models: Optional list of base models to filter by
            tags: Optional list of tags to filter by
            sort_order: Sort order for results
            max_pages: Maximum pages to retrieve
            
        Returns:
            List of models created by the user
        """
        print(f"Collecting models by user: {username}")
        print(f"Model types: {model_types or 'All'}")
        print(f"Base models: {base_models or 'All'}")
        print(f"Tags: {tags or 'All'}")
        print(f"Sort order: {sort_order}")
        print(f"Max pages: {max_pages}")
        
        try:
            # Use the existing search_models_with_cursor method
            # We'll need to extend it to support username parameter
            models = self._search_models_by_user(
                username=username,
                types=model_types,
                base_models=base_models,
                tags=tags,
                sort=sort_order,
                max_pages=max_pages
            )
            
            print(f"Found {len(models)} models by {username}")
            return models
            
        except Exception as e:
            print(f"Error collecting models for user {username}: {e}")
            return []
    
    def _search_models_by_user(self, 
                              username: str,
                              types: Optional[List[str]] = None,
                              base_models: Optional[List[str]] = None,
                              tags: Optional[List[str]] = None,
                              sort: str = "Newest",
                              max_pages: int = 50) -> List[Dict]:
        """
        Search models by user using extended client functionality with filtering.
        
        Note: This extends the existing client to support username and filtering parameters.
        """
        all_models = []
        cursor = None
        page_count = 0
        
        while page_count < max_pages:
            try:
                # Build parameters
                params = {
                    'username': username,
                    'limit': 200,  # Maximum
                    'sort': sort
                }
                
                if types:
                    params['types'] = types
                
                if base_models:
                    params['baseModels'] = base_models
                
                # Note: Only one tag can be specified in API, so we'll use the first one
                # and filter others client-side
                if tags:
                    params['tag'] = tags[0]
                
                if cursor:
                    params['cursor'] = cursor
                
                # Make API request
                response = self.client.request('GET', '/models', params=params)
                data = response.json()
                
                # Extract models
                models = data.get('items', [])
                if not models:
                    break
                
                # Filter by username to ensure accuracy
                # (API might return models that don't exactly match)
                user_models = []
                for model in models:
                    creator = model.get('creator', {})
                    if isinstance(creator, dict):
                        model_username = creator.get('username', '')
                        if model_username.lower() == username.lower():
                            # Additional client-side filtering
                            if self._matches_filters(model, base_models, tags):
                                user_models.append(model)
                
                all_models.extend(user_models)
                
                # Check for next page
                metadata = data.get('metadata', {})
                cursor = metadata.get('nextCursor')
                
                if not cursor:
                    break
                
                page_count += 1
                print(f"Processed page {page_count}, found {len(user_models)} models")
                
                # Rate limiting
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"Error on page {page_count + 1}: {e}")
                break
        
        return all_models
    
    def _matches_filters(self, model: Dict, base_models: Optional[List[str]], tags: Optional[List[str]]) -> bool:
        """
        Check if model matches the specified filters.
        
        Args:
            model: Model data
            base_models: List of base models to filter by
            tags: List of tags to filter by
            
        Returns:
            True if model matches all filters
        """
        # Check base models
        if base_models:
            model_tags = [tag.lower() for tag in model.get('tags', [])]
            model_versions = model.get('modelVersions', [])
            
            # Check if any base model matches
            base_model_match = False
            
            # Check tags for base model
            for base_model in base_models:
                if base_model.lower() in model_tags:
                    base_model_match = True
                    break
            
            # Check model versions for base model
            if not base_model_match and model_versions:
                for version in model_versions:
                    version_base_model = version.get('baseModel', '').lower()
                    for base_model in base_models:
                        if base_model.lower() in version_base_model:
                            base_model_match = True
                            break
                    if base_model_match:
                        break
            
            if not base_model_match:
                return False
        
        # Check tags (all tags must be present)
        if tags:
            model_tags = [tag.lower() for tag in model.get('tags', [])]
            for required_tag in tags:
                if required_tag.lower() not in model_tags:
                    return False
        
        return True
    
    def analyze_user_models(self, models: List[Dict]) -> Dict:
        """
        Analyze the collected models to provide statistics.
        
        Args:
            models: List of models to analyze
            
        Returns:
            Dictionary with analysis results
        """
        if not models:
            return {}
        
        # Basic statistics
        total_models = len(models)
        
        # Group by type
        type_counts = {}
        for model in models:
            model_type = model.get('type', 'Unknown')
            type_counts[model_type] = type_counts.get(model_type, 0) + 1
        
        # Group by base model (from tags)
        base_model_counts = {}
        base_model_tags = ['pony', 'illustrious', 'noobai', 'animagine', 'sdxl', 'sd1.5']
        
        for model in models:
            tags = [tag.lower() for tag in model.get('tags', [])]
            found_base = False
            
            for base_tag in base_model_tags:
                if base_tag in tags:
                    base_model_counts[base_tag] = base_model_counts.get(base_tag, 0) + 1
                    found_base = True
                    break
            
            if not found_base:
                base_model_counts['other'] = base_model_counts.get('other', 0) + 1
        
        # Collect all tags
        all_tags = []
        for model in models:
            all_tags.extend(model.get('tags', []))
        
        # Count tag frequency
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Get top tags
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # Calculate total file sizes
        total_size = 0
        file_count = 0
        
        for model in models:
            for version in model.get('modelVersions', []):
                for file in version.get('files', []):
                    size_kb = file.get('sizeKB', 0)
                    if size_kb:
                        total_size += size_kb
                        file_count += 1
        
        return {
            'total_models': total_models,
            'model_types': type_counts,
            'base_models': base_model_counts,
            'total_files': file_count,
            'total_size_gb': round(total_size / (1024 * 1024), 2),
            'top_tags': top_tags,
            'models_with_versions': len([m for m in models if m.get('modelVersions')])
        }
    
    def export_user_models(self, 
                          username: str,
                          models: List[Dict],
                          analysis: Dict,
                          output_dir: str = "outputs") -> Dict:
        """
        Export user models to files.
        
        Args:
            username: The username
            models: List of models to export
            analysis: Analysis results
            output_dir: Output directory
            
        Returns:
            Dictionary with export information
        """
        if not models:
            print(f"No models found for user {username}")
            return {}
        
        # Create output directory
        base_dir = Path(output_dir) / "users" / username
        base_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export URLs
        urls = self.url_collector.collect_model_urls(models)
        
        if urls:
            # Export in multiple formats
            csv_file = self.url_collector.export_to_csv(
                urls, base_dir / f"{username}_models_{timestamp}.csv"
            )
            json_file = self.url_collector.export_to_json(
                urls, base_dir / f"{username}_models_{timestamp}.json"
            )
            txt_file = self.url_collector.export_to_text(
                urls, base_dir / f"{username}_models_{timestamp}.txt"
            )
            
            print(f"Exported {len(urls)} URLs for user {username}")
            print(f"  CSV: {csv_file}")
            print(f"  JSON: {json_file}")
            print(f"  TXT: {txt_file}")
        
        # Export analysis
        analysis_file = base_dir / f"{username}_analysis_{timestamp}.json"
        
        analysis_data = {
            "username": username,
            "collection_timestamp": timestamp,
            "analysis": analysis,
            "total_models": len(models),
            "total_urls": len(urls) if urls else 0
        }
        
        import json
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis exported to: {analysis_file}")
        
        return {
            "username": username,
            "total_models": len(models),
            "total_urls": len(urls) if urls else 0,
            "files": {
                "csv": str(csv_file) if urls else None,
                "json": str(json_file) if urls else None,
                "txt": str(txt_file) if urls else None,
                "analysis": str(analysis_file)
            }
        }


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Collect all models created by a specific CivitAI user"
    )
    parser.add_argument(
        "username",
        help="Username of the creator to collect models from"
    )
    parser.add_argument(
        "--type", "--types",
        nargs="+",
        choices=["Checkpoint", "LORA", "LyCORIS", "TextualInversion", "Hypernetwork"],
        help="Filter by model type(s)"
    )
    parser.add_argument(
        "--base-models",
        nargs="+",
        choices=["pony", "illustrious", "noobai", "animagine", "sdxl", "sd1.5"],
        help="Filter by base model(s)"
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        help="Filter by tag(s) - all tags must be present"
    )
    parser.add_argument(
        "--sort",
        choices=["Newest", "Oldest", "Most Downloaded", "Highest Rated", "Most Liked"],
        default="Newest",
        help="Sort order (default: Newest)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum pages to retrieve (default: 50)"
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Output directory (default: outputs)"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("Error: Please set CIVITAI_API_KEY environment variable")
        sys.exit(1)
    
    # Initialize collector
    collector = UserModelCollector(api_key)
    
    # Collect models
    models = collector.collect_user_models(
        username=args.username,
        model_types=args.type,
        base_models=args.base_models,
        tags=args.tags,
        sort_order=args.sort,
        max_pages=args.max_pages
    )
    
    if not models:
        print(f"No models found for user: {args.username}")
        return
    
    # Analyze models
    analysis = collector.analyze_user_models(models)
    
    # Print analysis
    print(f"\n=== ANALYSIS FOR USER: {args.username} ===")
    print(f"Total models: {analysis.get('total_models', 0)}")
    print(f"Total files: {analysis.get('total_files', 0)}")
    print(f"Total size: {analysis.get('total_size_gb', 0)} GB")
    
    print(f"\nModel types:")
    for model_type, count in analysis.get('model_types', {}).items():
        print(f"  {model_type}: {count}")
    
    print(f"\nBase models:")
    for base_model, count in analysis.get('base_models', {}).items():
        print(f"  {base_model}: {count}")
    
    print(f"\nTop 10 tags:")
    for tag, count in analysis.get('top_tags', [])[:10]:
        print(f"  {tag}: {count}")
    
    # Export results
    export_info = collector.export_user_models(
        username=args.username,
        models=models,
        analysis=analysis,
        output_dir=args.output_dir
    )
    
    print(f"\n=== EXPORT COMPLETE ===")
    print(f"Files exported to: outputs/users/{args.username}/")


if __name__ == "__main__":
    main()