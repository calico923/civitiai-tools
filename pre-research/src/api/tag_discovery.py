#!/usr/bin/env python3
"""
Tag discovery utilities for CivitAI API.
Since there's no dedicated tags endpoint, this module provides methods
to discover available tags through model searches.
"""

import json
import time
from typing import Set, List, Dict, Optional
from pathlib import Path
from collections import Counter

from .client import CivitaiClient


class TagDiscovery:
    """Discover and analyze available tags from CivitAI API."""
    
    def __init__(self, client: CivitaiClient):
        self.client = client
        self.discovered_tags: Set[str] = set()
        self.tag_statistics: Dict[str, int] = {}
    
    def discover_all_tags(self, 
                         model_types: Optional[List[str]] = None,
                         max_pages_per_type: int = 10,
                         delay_between_requests: float = 2.0) -> Set[str]:
        """
        Discover all available tags by searching across model types.
        
        Args:
            model_types: List of model types to search. Defaults to all major types.
            max_pages_per_type: Maximum pages to search per model type
            delay_between_requests: Delay between API requests in seconds
            
        Returns:
            Set of discovered tags
        """
        if model_types is None:
            model_types = ["Checkpoint", "LORA", "TextualInversion", "Hypernetwork"]
        
        all_tags = set()
        tag_counts = Counter()
        
        for model_type in model_types:
            print(f"Discovering tags for {model_type} models...")
            
            try:
                # Search with cursor-based pagination
                models = self.client.search_models_with_cursor(
                    types=[model_type],
                    limit=200,  # Maximum
                    max_pages=max_pages_per_type
                )
                
                for model in models:
                    model_tags = model.get('tags', [])
                    all_tags.update(model_tags)
                    tag_counts.update(model_tags)
                    
                    # Add delay to respect rate limits
                    time.sleep(delay_between_requests)
                    
            except Exception as e:
                print(f"Error discovering tags for {model_type}: {e}")
                continue
        
        self.discovered_tags = all_tags
        self.tag_statistics = dict(tag_counts)
        
        return all_tags
    
    def get_tags_by_category(self) -> Dict[str, List[str]]:
        """
        Categorize discovered tags based on common patterns.
        
        Returns:
            Dictionary with categorized tags
        """
        categories = {
            "base_models": [],
            "styles": [],
            "content_types": [],
            "technical": [],
            "quality": [],
            "other": []
        }
        
        # Known categorization patterns
        base_model_tags = {"pony", "illustrious", "noobai", "animagine", "sdxl", "sd1.5", "base model"}
        style_tags = {"style", "concept", "character", "realistic", "anime", "cartoon", "3d"}
        content_tags = {"nsfw", "sfw", "portrait", "landscape", "object", "clothing"}
        technical_tags = {"lora", "checkpoint", "embedding", "hypernetwork", "pruned"}
        quality_tags = {"high quality", "detailed", "masterpiece", "best quality"}
        
        for tag in self.discovered_tags:
            tag_lower = tag.lower()
            
            if tag_lower in base_model_tags or any(bm in tag_lower for bm in base_model_tags):
                categories["base_models"].append(tag)
            elif tag_lower in style_tags or any(st in tag_lower for st in style_tags):
                categories["styles"].append(tag)
            elif tag_lower in content_tags or any(ct in tag_lower for ct in content_tags):
                categories["content_types"].append(tag)
            elif tag_lower in technical_tags or any(tt in tag_lower for tt in technical_tags):
                categories["technical"].append(tag)
            elif tag_lower in quality_tags or any(qt in tag_lower for qt in quality_tags):
                categories["quality"].append(tag)
            else:
                categories["other"].append(tag)
        
        # Sort each category
        for category in categories:
            categories[category].sort()
        
        return categories
    
    def get_popular_tags(self, min_count: int = 10) -> List[tuple]:
        """
        Get popular tags based on usage frequency.
        
        Args:
            min_count: Minimum usage count to be considered popular
            
        Returns:
            List of (tag, count) tuples sorted by frequency
        """
        if not self.tag_statistics:
            return []
        
        popular = [(tag, count) for tag, count in self.tag_statistics.items() 
                  if count >= min_count]
        
        return sorted(popular, key=lambda x: x[1], reverse=True)
    
    def search_tags(self, pattern: str, case_sensitive: bool = False) -> List[str]:
        """
        Search for tags matching a pattern.
        
        Args:
            pattern: Search pattern
            case_sensitive: Whether to match case sensitively
            
        Returns:
            List of matching tags
        """
        if not case_sensitive:
            pattern = pattern.lower()
        
        matches = []
        for tag in self.discovered_tags:
            search_tag = tag if case_sensitive else tag.lower()
            if pattern in search_tag:
                matches.append(tag)
        
        return sorted(matches)
    
    def export_tags(self, output_path: str, format: str = "json") -> None:
        """
        Export discovered tags to file.
        
        Args:
            output_path: Output file path
            format: Export format ("json", "txt", "csv")
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            data = {
                "total_tags": len(self.discovered_tags),
                "categories": self.get_tags_by_category(),
                "popular_tags": self.get_popular_tags(),
                "all_tags": sorted(list(self.discovered_tags)),
                "statistics": self.tag_statistics
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# CivitAI Available Tags\n\n")
                f.write(f"Total tags discovered: {len(self.discovered_tags)}\n\n")
                
                categories = self.get_tags_by_category()
                for category, tags in categories.items():
                    if tags:
                        f.write(f"## {category.replace('_', ' ').title()}\n")
                        for tag in tags:
                            count = self.tag_statistics.get(tag, 0)
                            f.write(f"- {tag} ({count} models)\n")
                        f.write("\n")
        
        elif format == "csv":
            import csv
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["tag", "count", "category"])
                
                categories = self.get_tags_by_category()
                for category, tags in categories.items():
                    for tag in tags:
                        count = self.tag_statistics.get(tag, 0)
                        writer.writerow([tag, count, category])
        
        print(f"Tags exported to {output_path}")


def main():
    """Example usage of tag discovery."""
    import os
    
    # Initialize client
    api_key = os.getenv("CIVITAI_API_KEY")
    if not api_key:
        print("Error: CIVITAI_API_KEY environment variable not set")
        return
    
    client = CivitaiClient(api_key)
    discovery = TagDiscovery(client)
    
    # Discover tags
    print("Starting tag discovery...")
    tags = discovery.discover_all_tags(max_pages_per_type=5)
    
    print(f"Discovered {len(tags)} unique tags")
    
    # Export results
    output_dir = Path("outputs/analysis/tags")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    discovery.export_tags(output_dir / "all_tags.json", "json")
    discovery.export_tags(output_dir / "all_tags.txt", "txt")
    discovery.export_tags(output_dir / "all_tags.csv", "csv")
    
    # Show popular tags
    popular = discovery.get_popular_tags(min_count=50)
    print(f"\nTop 10 most popular tags:")
    for tag, count in popular[:10]:
        print(f"  {tag}: {count} models")


if __name__ == "__main__":
    main()