#!/usr/bin/env python3
"""
Organize outputs directory by moving files to appropriate subdirectories
based on their content and naming patterns.
"""

import os
import shutil
import re
from pathlib import Path

def organize_outputs():
    """Organize files in outputs/urls/ into structured subdirectories."""
    
    base_dir = Path("/Users/kuniaki-k/Code/civitiai/outputs")
    urls_dir = base_dir / "urls"
    
    if not urls_dir.exists():
        print("No urls directory found")
        return
    
    # Create organized directory structure
    directories = {
        "checkpoints": {
            "pony": base_dir / "checkpoints" / "pony",
            "illustrious": base_dir / "checkpoints" / "illustrious", 
            "noobai": base_dir / "checkpoints" / "noobai",
            "animagine": base_dir / "checkpoints" / "animagine"
        },
        "loras": {
            "style": base_dir / "loras" / "style",
            "pony": base_dir / "loras" / "pony",
            "illustrious": base_dir / "loras" / "illustrious",
            "noobai": base_dir / "loras" / "noobai",
            "all": base_dir / "loras" / "all"
        },
        "analysis": base_dir / "analysis",
        "debug": base_dir / "debug",
        "archive": base_dir / "archive"
    }
    
    # Create directories
    for category in directories.values():
        if isinstance(category, dict):
            for subdir in category.values():
                subdir.mkdir(parents=True, exist_ok=True)
        else:
            category.mkdir(parents=True, exist_ok=True)
    
    # File organization rules
    def get_destination(filename):
        """Determine the destination directory for a file."""
        name = filename.lower()
        
        # Demo files
        if name.startswith("demo_"):
            return directories["debug"]
        
        # Analysis files
        if "analysis" in name or "summary" in name:
            return directories["analysis"]
        
        # Checkpoint files
        if "checkpoint" in name:
            if "pony" in name:
                return directories["checkpoints"]["pony"]
            elif "illustrious" in name:
                return directories["checkpoints"]["illustrious"]
            elif "noobai" in name:
                return directories["checkpoints"]["noobai"]
            elif "animagine" in name:
                return directories["checkpoints"]["animagine"]
            else:
                return directories["checkpoints"]["pony"]  # Default
        
        # LoRA files
        if "lora" in name:
            if "style" in name:
                if "pony" in name:
                    return directories["loras"]["pony"]
                elif "illustrious" in name:
                    return directories["loras"]["illustrious"]
                elif "noobai" in name:
                    return directories["loras"]["noobai"]
                elif "all" in name:
                    return directories["loras"]["all"]
                else:
                    return directories["loras"]["style"]
            else:
                return directories["loras"]["all"]
        
        # Base model files
        if "base model" in name:
            return directories["archive"]
        
        # Default to archive
        return directories["archive"]
    
    # Move files
    moved_files = []
    for file_path in urls_dir.glob("*"):
        if file_path.is_file():
            dest_dir = get_destination(file_path.name)
            dest_path = dest_dir / file_path.name
            
            try:
                shutil.move(str(file_path), str(dest_path))
                moved_files.append((file_path.name, dest_dir.relative_to(base_dir)))
                print(f"Moved: {file_path.name} → {dest_dir.relative_to(base_dir)}")
            except Exception as e:
                print(f"Error moving {file_path.name}: {e}")
    
    # Create summary report
    summary_path = base_dir / "organization_summary.txt"
    with open(summary_path, 'w') as f:
        f.write("File Organization Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total files moved: {len(moved_files)}\n\n")
        
        # Group by destination
        by_destination = {}
        for filename, dest in moved_files:
            dest_str = str(dest)
            if dest_str not in by_destination:
                by_destination[dest_str] = []
            by_destination[dest_str].append(filename)
        
        for dest, files in sorted(by_destination.items()):
            f.write(f"{dest}/ ({len(files)} files)\n")
            for filename in sorted(files):
                f.write(f"  - {filename}\n")
            f.write("\n")
    
    print(f"\nOrganization complete! Summary written to {summary_path}")
    print(f"Total files organized: {len(moved_files)}")
    
    # Clean up empty urls directory
    if urls_dir.exists() and not any(urls_dir.iterdir()):
        urls_dir.rmdir()
        print("Removed empty urls directory")

if __name__ == "__main__":
    organize_outputs()