#!/usr/bin/env python3
"""
Enhanced model collection script that includes both download URLs and model page URLs
with optional validation.

Example usage:
    python enhanced_collection.py DanMogren --type LORA --base-models illustrious
    python enhanced_collection.py DanMogren --validate-urls --export-html
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
from src.core.enhanced_url_collector import EnhancedURLCollector


class EnhancedModelCollector:
    """Enhanced model collector with page URLs and validation."""
    
    def __init__(self, api_key: str):
        self.client = CivitaiClient(api_key)
        self.enhanced_collector = EnhancedURLCollector(api_key=api_key)
    
    def collect_user_models_enhanced(self, 
                                   username: str,
                                   model_types: Optional[List[str]] = None,
                                   base_models: Optional[List[str]] = None,
                                   tags: Optional[List[str]] = None,
                                   sort_order: str = "Newest",
                                   max_pages: int = 50,
                                   validate_urls: bool = False) -> List:
        """
        Collect enhanced model information for a specific user.
        
        Args:
            username: Username of the creator
            model_types: Optional list of model types to filter by
            base_models: Optional list of base models to filter by
            tags: Optional list of tags to filter by
            sort_order: Sort order for results
            max_pages: Maximum pages to retrieve
            validate_urls: Whether to validate download URLs
            
        Returns:
            List of enhanced ModelInfo objects
        """
        print(f"🔍 Collecting enhanced model information for user: {username}")
        print(f"📋 Filters: Types={model_types}, Base Models={base_models}, Tags={tags}")
        print(f"📊 Sort: {sort_order}, Max Pages: {max_pages}")
        
        # Collect raw model data
        models = self._search_models_by_user(
            username=username,
            types=model_types,
            base_models=base_models,
            tags=tags,
            sort=sort_order,
            max_pages=max_pages
        )
        
        if not models:
            print(f"❌ No models found for user: {username}")
            return []
        
        print(f"✅ Found {len(models)} models")
        
        # Convert to enhanced model info
        print("🔄 Processing enhanced model information...")
        model_infos = self.enhanced_collector.collect_enhanced_model_info(models)
        
        if validate_urls:
            print("🔍 Validating download URLs...")
            model_infos = self.enhanced_collector.validate_download_urls(model_infos)
        
        return model_infos
    
    def collect_comprehensive_enhanced(self,
                                     base_models: List[str],
                                     model_types: List[str],
                                     tags: List[str],
                                     sort_orders: List[str],
                                     max_pages_per_combination: int = 3,
                                     validate_urls: bool = False) -> List:
        """
        Collect comprehensive enhanced dataset covering all combinations.
        """
        print("🚀 Starting comprehensive enhanced collection...")
        print(f"📊 Combinations: {len(base_models)} base models × {len(model_types)} types × {len(tags)} tags × {len(sort_orders)} sorts")
        
        all_models = []
        total_combinations = len(base_models) * len(model_types) * len(tags) * len(sort_orders)
        current_combination = 0
        
        for base_model in base_models:
            for model_type in model_types:
                for tag in tags:
                    for sort_order in sort_orders:
                        current_combination += 1
                        
                        print(f"\n📈 Progress: {current_combination}/{total_combinations}")
                        print(f"🔍 Searching: {base_model} {model_type} with tag '{tag}' sorted by {sort_order}")
                        
                        try:
                            # Method 1: Direct tag search
                            models_direct = self.client.search_models_with_cursor(
                                tag=tag,
                                types=[model_type],
                                base_models=[base_model.title()],  # 正確な大文字小文字
                                sort=sort_order,
                                limit=100,  # API制限に従う
                                max_pages=max_pages_per_combination
                            )
                            
                            # Method 2: Base model search with client-side filtering
                            models_base = self.client.search_models_with_cursor(
                                base_models=[base_model.title()],  # 正確な大文字小文字
                                types=[model_type],
                                sort=sort_order,
                                limit=100,  # API制限に従う
                                max_pages=max_pages_per_combination
                            )
                            
                            # Filter base model results by tag
                            models_base_filtered = []
                            for model in models_base:
                                model_tags = [t.lower() for t in model.get('tags', [])]
                                if tag.lower() in model_tags:
                                    models_base_filtered.append(model)
                            
                            # Combine and deduplicate
                            combined_models = models_direct + models_base_filtered
                            unique_models = {}
                            
                            for model in combined_models:
                                model_id = model.get('id')
                                if model_id and model_id not in unique_models:
                                    unique_models[model_id] = model
                            
                            all_models.extend(list(unique_models.values()))
                            print(f"✅ Found {len(unique_models)} unique models")
                            
                            # Rate limiting
                            import time
                            time.sleep(2)
                            
                        except Exception as e:
                            print(f"❌ Error in combination {current_combination}: {e}")
                            continue
        
        # Remove duplicates across all combinations
        print("\n🔄 Removing duplicates across all combinations...")
        unique_all_models = {}
        for model in all_models:
            model_id = model.get('id')
            if model_id and model_id not in unique_all_models:
                unique_all_models[model_id] = model
        
        final_models = list(unique_all_models.values())
        print(f"✅ Final unique models: {len(final_models)}")
        
        # Convert to enhanced model info
        print("🔄 Processing enhanced model information...")
        model_infos = self.enhanced_collector.collect_enhanced_model_info(final_models)
        
        if validate_urls:
            print("🔍 Validating download URLs...")
            model_infos = self.enhanced_collector.validate_download_urls(model_infos)
        
        return model_infos
    
    def _search_models_by_user(self, 
                              username: str,
                              types: Optional[List[str]] = None,
                              base_models: Optional[List[str]] = None,
                              tags: Optional[List[str]] = None,
                              sort: str = "Newest",
                              max_pages: int = 50) -> List[Dict]:
        """Search models by user with filtering."""
        all_models = []
        cursor = None
        page_count = 0
        
        while page_count < max_pages:
            try:
                # Build parameters
                params = {
                    'username': username,
                    'limit': 100,  # API制限に従う
                    'sort': sort
                }
                
                if types:
                    params['types'] = types
                
                if base_models:
                    # 正確なベースモデル名を使用
                    corrected_base_models = []
                    for bm in base_models:
                        if bm.lower() == "illustrious":
                            corrected_base_models.append("Illustrious")
                        elif bm.lower() == "noobai":
                            corrected_base_models.append("NoobAI")
                        elif bm.lower() == "pony":
                            corrected_base_models.append("Pony")
                        else:
                            corrected_base_models.append(bm.title())
                    params['baseModels'] = corrected_base_models
                
                if tags:
                    params['tag'] = tags[0]  # API supports only one tag
                
                if cursor:
                    params['cursor'] = cursor
                
                # Make API request
                response = self.client.request('GET', '/models', params=params)
                data = response.json()
                
                # Extract models
                models = data.get('items', [])
                if not models:
                    break
                
                # Filter by username and additional criteria
                user_models = []
                for model in models:
                    creator = model.get('creator', {})
                    if isinstance(creator, dict):
                        model_username = creator.get('username', '')
                        if model_username.lower() == username.lower():
                            if self._matches_filters(model, base_models, tags):
                                user_models.append(model)
                
                all_models.extend(user_models)
                
                # Check for next page
                metadata = data.get('metadata', {})
                cursor = metadata.get('nextCursor')
                
                if not cursor:
                    break
                
                page_count += 1
                print(f"📄 Processed page {page_count}, found {len(user_models)} models")
                
                # Rate limiting
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Error on page {page_count + 1}: {e}")
                break
        
        return all_models
    
    def _matches_filters(self, model: Dict, base_models: Optional[List[str]], tags: Optional[List[str]]) -> bool:
        """Check if model matches the specified filters."""
        # Check base models
        if base_models:
            model_tags = [tag.lower() for tag in model.get('tags', [])]
            model_versions = model.get('modelVersions', [])
            
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


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Enhanced CivitAI model collection with page URLs and validation"
    )
    
    # Collection mode
    collection_group = parser.add_mutually_exclusive_group(required=True)
    collection_group.add_argument(
        "--user",
        help="Username of the creator to collect models from"
    )
    collection_group.add_argument(
        "--comprehensive",
        action="store_true",
        help="Comprehensive collection mode"
    )
    
    # Filters
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
        help="Filter by tag(s)"
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
    
    # Enhancement options
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help="Validate that download URLs are accessible"
    )
    parser.add_argument(
        "--export-html",
        action="store_true",
        help="Export browsable HTML format"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir",
        default="outputs/enhanced",
        help="Output directory (default: outputs/enhanced)"
    )
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("❌ Error: Please set CIVITAI_API_KEY environment variable")
        sys.exit(1)
    
    # Initialize collector
    collector = EnhancedModelCollector(api_key)
    collector.enhanced_collector.output_dir = Path(args.output_dir)
    collector.enhanced_collector.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect models
    if args.user:
        model_infos = collector.collect_user_models_enhanced(
            username=args.user,
            model_types=args.type,
            base_models=args.base_models,
            tags=args.tags,
            sort_order=args.sort,
            max_pages=args.max_pages,
            validate_urls=args.validate_urls
        )
        
        if model_infos:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"{args.user}_enhanced_{timestamp}"
            
            # Export results
            print("\n📁 Exporting results...")
            exported_files = collector.enhanced_collector.export_all_formats(
                model_infos, base_filename
            )
            
            if args.export_html:
                print(f"🌐 HTML: {exported_files['html']}")
            
            print(f"📊 CSV: {exported_files['csv']}")
            print(f"📋 JSON: {exported_files['json']}")
            
            # Print summary
            print(f"\n✅ Collection completed!")
            print(f"📊 Total models: {len(model_infos)}")
            print(f"👤 User: {args.user}")
            if args.validate_urls:
                print("✅ URLs validated")
    
    elif args.comprehensive:
        # Set default values for comprehensive collection
        base_models = args.base_models or ["illustrious", "noobai", "pony"]
        model_types = args.type or ["Checkpoint", "LORA", "LyCORIS"]
        tags = args.tags or ["style", "concept", "pose", "nsfw", "sexy", "hentai"]
        sort_orders = [args.sort] if args.sort != "Newest" else ["Highest Rated", "Most Downloaded"]
        
        model_infos = collector.collect_comprehensive_enhanced(
            base_models=base_models,
            model_types=model_types,
            tags=tags,
            sort_orders=sort_orders,
            max_pages_per_combination=3,
            validate_urls=args.validate_urls
        )
        
        if model_infos:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"comprehensive_enhanced_{timestamp}"
            
            # Export results
            print("\n📁 Exporting comprehensive results...")
            exported_files = collector.enhanced_collector.export_all_formats(
                model_infos, base_filename
            )
            
            if args.export_html:
                print(f"🌐 HTML: {exported_files['html']}")
            
            print(f"📊 CSV: {exported_files['csv']}")
            print(f"📋 JSON: {exported_files['json']}")
            
            # Print summary
            print(f"\n✅ Comprehensive collection completed!")
            print(f"📊 Total models: {len(model_infos)}")
            if args.validate_urls:
                print("✅ URLs validated")


if __name__ == "__main__":
    main()