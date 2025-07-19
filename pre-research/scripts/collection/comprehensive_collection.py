#!/usr/bin/env python3
"""
Comprehensive model collection script for specific requirements.

Target specifications:
- BASE MODELS: illustrious, noobai, pony
- TYPES: Checkpoint, LoRA, LyCORIS
- TAGS: style, concept, pose, nsfw, sexy, hentai
- SORT ORDERS: Highest Rated, Most Downloaded, Most Liked, Most Collected, Most Images, Newest, Oldest, Most Discussed
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Set
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.api.client import CivitaiClient
from src.core.url_collector import URLCollector

class ComprehensiveModelCollector:
    """Collect models based on comprehensive requirements."""
    
    def __init__(self, api_key: str):
        self.client = CivitaiClient(api_key)
        self.url_collector = URLCollector()
        
        # Target specifications
        self.base_models = ["illustrious", "noobai", "pony"]
        self.model_types = ["Checkpoint", "LORA", "LyCORIS"]
        self.required_tags = ["style", "concept", "pose", "nsfw", "sexy", "hentai"]
        self.sort_orders = [
            "Highest Rated",
            "Most Downloaded", 
            "Most Liked",
            "Most Collected",
            "Most Images",
            "Newest",
            "Oldest",
            "Most Discussed"
        ]
    
    def collect_models_by_tag_and_base_model(self, 
                                           tag: str,
                                           base_model: str,
                                           model_type: str,
                                           sort_order: str,
                                           max_pages: int = 10) -> List[Dict]:
        """
        Collect models using specific tag, base model, type, and sort order.
        """
        print(f"Collecting {model_type} models with tag '{tag}' for {base_model} base model, sorted by {sort_order}...")
        
        try:
            # Method 1: Direct tag search
            models_direct = self.client.search_models_with_cursor(
                tag=tag,
                types=[model_type],
                sort=sort_order,
                limit=200,
                max_pages=max_pages
            )
            
            # Method 2: Base model search with client-side filtering
            models_base = self.client.search_models_with_cursor(
                base_models=[base_model],
                types=[model_type],
                sort=sort_order,
                limit=200,
                max_pages=max_pages
            )
            
            # Filter base model results by tag
            models_base_filtered = []
            for model in models_base:
                model_tags = [t.lower() for t in model.get('tags', [])]
                if tag.lower() in model_tags:
                    models_base_filtered.append(model)
            
            # Combine and deduplicate
            all_models = models_direct + models_base_filtered
            unique_models = {}
            
            for model in all_models:
                model_id = model.get('id')
                if model_id and model_id not in unique_models:
                    # Additional filtering for base model
                    if self._has_base_model(model, base_model):
                        unique_models[model_id] = model
            
            print(f"Found {len(unique_models)} unique models")
            return list(unique_models.values())
            
        except Exception as e:
            print(f"Error collecting models: {e}")
            return []
    
    def _has_base_model(self, model: Dict, target_base_model: str) -> bool:
        """Check if model has the target base model."""
        # Check tags
        model_tags = [t.lower() for t in model.get('tags', [])]
        if target_base_model.lower() in model_tags:
            return True
        
        # Check model versions base model field
        model_versions = model.get('modelVersions', [])
        if model_versions:
            base_model = model_versions[0].get('baseModel', '').lower()
            if target_base_model.lower() in base_model:
                return True
        
        return False
    
    def collect_comprehensive_dataset(self, max_pages_per_combination: int = 5) -> Dict:
        """
        Collect comprehensive dataset covering all combinations.
        """
        print("Starting comprehensive model collection...")
        print(f"Base models: {self.base_models}")
        print(f"Model types: {self.model_types}")
        print(f"Tags: {self.required_tags}")
        print(f"Sort orders: {self.sort_orders}")
        
        all_results = {}
        total_combinations = len(self.base_models) * len(self.model_types) * len(self.required_tags) * len(self.sort_orders)
        current_combination = 0
        
        for base_model in self.base_models:
            for model_type in self.model_types:
                for tag in self.required_tags:
                    for sort_order in self.sort_orders:
                        current_combination += 1
                        
                        print(f"\nProgress: {current_combination}/{total_combinations}")
                        
                        # Create unique key for this combination
                        key = f"{base_model}_{model_type}_{tag}_{sort_order.replace(' ', '_').lower()}"
                        
                        # Collect models
                        models = self.collect_models_by_tag_and_base_model(
                            tag=tag,
                            base_model=base_model,
                            model_type=model_type,
                            sort_order=sort_order,
                            max_pages=max_pages_per_combination
                        )
                        
                        all_results[key] = models
                        
                        # Rate limiting
                        time.sleep(2)
        
        return all_results
    
    def consolidate_results(self, all_results: Dict) -> Dict:
        """
        Consolidate results by base model and type, removing duplicates.
        """
        print("\nConsolidating results...")
        
        consolidated = {}
        
        for base_model in self.base_models:
            for model_type in self.model_types:
                key = f"{base_model}_{model_type}"
                consolidated[key] = {}
                
                # Collect all models for this base model + type combination
                all_models = []
                for tag in self.required_tags:
                    for sort_order in self.sort_orders:
                        result_key = f"{base_model}_{model_type}_{tag}_{sort_order.replace(' ', '_').lower()}"
                        if result_key in all_results:
                            all_models.extend(all_results[result_key])
                
                # Deduplicate by model ID
                unique_models = {}
                for model in all_models:
                    model_id = model.get('id')
                    if model_id and model_id not in unique_models:
                        unique_models[model_id] = model
                
                consolidated[key] = list(unique_models.values())
                print(f"{key}: {len(consolidated[key])} unique models")
        
        return consolidated
    
    def export_results(self, consolidated_results: Dict, output_base_dir: str = "outputs") -> None:
        """
        Export consolidated results to organized directory structure.
        """
        print("\nExporting results...")
        
        base_dir = Path(output_base_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        summary_data = {
            "timestamp": timestamp,
            "total_combinations_searched": len(self.base_models) * len(self.model_types) * len(self.required_tags) * len(self.sort_orders),
            "base_models": self.base_models,
            "model_types": self.model_types,
            "required_tags": self.required_tags,
            "sort_orders": self.sort_orders,
            "results": {}
        }
        
        for key, models in consolidated_results.items():
            if not models:
                continue
            
            # Parse key
            parts = key.split('_')
            base_model = parts[0]
            model_type = parts[1]
            
            # Determine output directory
            if model_type.lower() == "checkpoint":
                output_dir = base_dir / "checkpoints" / base_model
            else:  # LoRA or LyCORIS
                output_dir = base_dir / "loras" / base_model
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename_base = f"{base_model}_{model_type.lower()}_comprehensive_{timestamp}"
            
            # Export in multiple formats
            urls = self.url_collector.collect_model_urls(models)
            
            if urls:
                # Export files
                csv_file = self.url_collector.export_to_csv(urls, output_dir / f"{filename_base}.csv")
                json_file = self.url_collector.export_to_json(urls, output_dir / f"{filename_base}.json")
                txt_file = self.url_collector.export_to_text(urls, output_dir / f"{filename_base}.txt")
                
                print(f"Exported {len(urls)} URLs for {key}")
                print(f"  CSV: {csv_file}")
                print(f"  JSON: {json_file}")
                print(f"  TXT: {txt_file}")
                
                # Add to summary
                summary_data["results"][key] = {
                    "model_count": len(models),
                    "url_count": len(urls),
                    "files": {
                        "csv": str(csv_file),
                        "json": str(json_file),
                        "txt": str(txt_file)
                    }
                }
        
        # Export summary
        summary_file = base_dir / "analysis" / f"comprehensive_collection_summary_{timestamp}.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nSummary exported to: {summary_file}")
        
        # Print final statistics
        total_models = sum(len(models) for models in consolidated_results.values())
        total_urls = sum(data["url_count"] for data in summary_data["results"].values())
        
        print(f"\n=== COLLECTION SUMMARY ===")
        print(f"Total unique models collected: {total_models}")
        print(f"Total URLs generated: {total_urls}")
        print(f"Base models covered: {len(self.base_models)}")
        print(f"Model types covered: {len(self.model_types)}")
        print(f"Tags searched: {len(self.required_tags)}")
        print(f"Sort orders used: {len(self.sort_orders)}")


def main():
    """Main execution function."""
    # Get API key
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("Error: Please set CIVITAI_API_KEY environment variable")
        return
    
    # Initialize collector
    collector = ComprehensiveModelCollector(api_key)
    
    # Collect comprehensive dataset
    all_results = collector.collect_comprehensive_dataset(max_pages_per_combination=3)
    
    # Consolidate results
    consolidated = collector.consolidate_results(all_results)
    
    # Export results
    collector.export_results(consolidated)
    
    print("\nComprehensive collection completed!")


if __name__ == "__main__":
    main()