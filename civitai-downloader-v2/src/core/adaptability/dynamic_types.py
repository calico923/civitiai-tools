#!/usr/bin/env python3
"""
Dynamic Model Type Management.
Implements requirement 15.1: Automatic detection of new model types.
"""

import logging
import time
from typing import Dict, Set, List, Any, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelTypeInfo:
    """Information about a model type."""
    name: str
    display_name: str
    description: str
    file_extensions: Set[str] = field(default_factory=set)
    typical_size_range: tuple = (0, float('inf'))  # MB
    common_tags: Set[str] = field(default_factory=set)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    occurrence_count: int = 0
    is_official: bool = False
    confidence_score: float = 0.0  # 0.0 to 1.0


class DynamicModelTypeManager:
    """
    Manages dynamic detection and adaptation of model types.
    Implements requirement 15.1: New model type auto-detection.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize dynamic model type manager.
        
        Args:
            cache_dir: Directory to cache model type information
        """
        self.cache_dir = cache_dir or Path("./model_type_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Known model types (official)
        self.known_types: Dict[str, ModelTypeInfo] = {
            "Checkpoint": ModelTypeInfo(
                name="Checkpoint",
                display_name="Checkpoint",
                description="Full model checkpoint",
                file_extensions={".ckpt", ".safetensors", ".pt"},
                typical_size_range=(1000, 10000),  # 1-10GB
                common_tags={"base model", "checkpoint"},
                is_official=True,
                confidence_score=1.0
            ),
            "LORA": ModelTypeInfo(
                name="LORA",
                display_name="LoRA",
                description="Low-Rank Adaptation",
                file_extensions={".safetensors", ".pt"},
                typical_size_range=(10, 500),  # 10MB-500MB
                common_tags={"lora", "character", "style"},
                is_official=True,
                confidence_score=1.0
            ),
            "TextualInversion": ModelTypeInfo(
                name="TextualInversion",
                display_name="Textual Inversion",
                description="Textual Inversion embedding",
                file_extensions={".pt", ".bin", ".safetensors"},
                typical_size_range=(0.01, 50),  # 10KB-50MB
                common_tags={"embedding", "textual inversion"},
                is_official=True,
                confidence_score=1.0
            ),
            "Hypernetwork": ModelTypeInfo(
                name="Hypernetwork",
                display_name="Hypernetwork",
                description="Hypernetwork model",
                file_extensions={".pt", ".safetensors"},
                typical_size_range=(50, 1000),  # 50MB-1GB
                common_tags={"hypernetwork"},
                is_official=True,
                confidence_score=1.0
            ),
            "AestheticGradient": ModelTypeInfo(
                name="AestheticGradient",
                display_name="Aesthetic Gradient",
                description="Aesthetic gradient model",
                file_extensions={".pt"},
                typical_size_range=(1, 100),
                common_tags={"aesthetic", "gradient"},
                is_official=True,
                confidence_score=1.0
            ),
            "Controlnet": ModelTypeInfo(
                name="Controlnet",
                display_name="ControlNet",
                description="ControlNet model",
                file_extensions={".pt", ".safetensors", ".ckpt"},
                typical_size_range=(500, 5000),
                common_tags={"controlnet", "control"},
                is_official=True,
                confidence_score=1.0
            ),
            "Poses": ModelTypeInfo(
                name="Poses",
                display_name="Poses",
                description="Pose models and datasets",
                file_extensions={".json", ".zip"},
                typical_size_range=(0.1, 100),
                common_tags={"poses", "dataset"},
                is_official=True,
                confidence_score=1.0
            )
        }
        
        # Detected types (discovered dynamically)
        self.detected_types: Dict[str, ModelTypeInfo] = {}
        
        # Pattern analysis data
        self.type_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Load cached data
        self._load_cached_data()
    
    def analyze_model_data(self, model_data: Dict[str, Any]) -> Optional[str]:
        """
        Analyze model data to determine or detect model type.
        
        Args:
            model_data: Model data from API
            
        Returns:
            Model type name (known or detected)
        """
        # Get explicit type from data
        explicit_type = model_data.get('type')
        if explicit_type:
            self._record_type_observation(explicit_type, model_data)
            return explicit_type
        
        # Attempt to infer type from model data
        inferred_type = self._infer_model_type(model_data)
        if inferred_type:
            self._record_type_observation(inferred_type, model_data)
            return inferred_type
        
        return None
    
    def _infer_model_type(self, model_data: Dict[str, Any]) -> Optional[str]:
        """Infer model type from model data patterns."""
        # Analyze file information
        files = []
        for version in model_data.get('modelVersions', []):
            files.extend(version.get('files', []))
        
        if not files:
            return None
        
        # Get file characteristics
        file_sizes = [f.get('sizeKB', 0) / 1024 for f in files]  # Convert to MB
        file_names = [f.get('name', '').lower() for f in files]
        
        # Check against known patterns
        for type_name, type_info in self.known_types.items():
            if self._matches_type_pattern(file_sizes, file_names, type_info):
                return type_name
        
        # Check against detected patterns
        for type_name, type_info in self.detected_types.items():
            if self._matches_type_pattern(file_sizes, file_names, type_info):
                return type_name
        
        # Attempt to detect new type
        return self._detect_new_type(model_data, file_sizes, file_names)
    
    def _matches_type_pattern(self, file_sizes: List[float], 
                            file_names: List[str], 
                            type_info: ModelTypeInfo) -> bool:
        """Check if files match a type pattern."""
        # Size range check
        if file_sizes:
            avg_size = sum(file_sizes) / len(file_sizes)
            min_size, max_size = type_info.typical_size_range
            if not (min_size <= avg_size <= max_size):
                return False
        
        # File extension check
        if type_info.file_extensions:
            has_matching_ext = False
            for name in file_names:
                for ext in type_info.file_extensions:
                    if name.endswith(ext.lower()):
                        has_matching_ext = True
                        break
                if has_matching_ext:
                    break
            
            if not has_matching_ext:
                return False
        
        return True
    
    def _detect_new_type(self, model_data: Dict[str, Any], 
                        file_sizes: List[float], 
                        file_names: List[str]) -> Optional[str]:
        """Attempt to detect a new model type."""
        # Look for type hints in model name, description, or tags
        model_name = model_data.get('name', '').lower()
        description = model_data.get('description', '').lower()
        tags = [tag.get('name', '').lower() for tag in model_data.get('tags', [])]
        
        # Common type indicators
        type_indicators = {
            'adapter': ['adapter', 'lora', 'dreambooth'],
            'embedding': ['embedding', 'textual', 'inversion'],
            'upscaler': ['upscale', 'esrgan', 'real-esrgan'],
            'vae': ['vae', 'variational', 'autoencoder'],
            'motion': ['motion', 'animate', 'video'],
            'inpainting': ['inpaint', 'mask', 'fill'],
            'style': ['style', 'artistic', 'art'],
            'character': ['character', 'person', 'celebrity'],
            'concept': ['concept', 'abstract', 'idea'],
            'tool': ['tool', 'utility', 'helper']
        }
        
        # Check for indicators
        all_text = f"{model_name} {description} {' '.join(tags)}"
        
        for potential_type, indicators in type_indicators.items():
            if any(indicator in all_text for indicator in indicators):
                # Create new detected type
                new_type = ModelTypeInfo(
                    name=potential_type.capitalize(),
                    display_name=potential_type.capitalize(),
                    description=f"Detected {potential_type} model type",
                    typical_size_range=(
                        min(file_sizes) if file_sizes else 0,
                        max(file_sizes) if file_sizes else float('inf')
                    ),
                    common_tags=set(tags),
                    is_official=False,
                    confidence_score=0.5  # Initial confidence
                )
                
                # Add file extensions from observed files
                for name in file_names:
                    if '.' in name:
                        ext = '.' + name.split('.')[-1]
                        new_type.file_extensions.add(ext)
                
                self.detected_types[potential_type.capitalize()] = new_type
                logger.info(f"Detected new model type: {potential_type.capitalize()}")
                
                return potential_type.capitalize()
        
        return None
    
    def _record_type_observation(self, type_name: str, model_data: Dict[str, Any]) -> None:
        """Record an observation of a model type."""
        current_time = time.time()
        
        # Find the type info
        type_info = None
        if type_name in self.known_types:
            type_info = self.known_types[type_name]
        elif type_name in self.detected_types:
            type_info = self.detected_types[type_name]
        else:
            # Create new detected type
            type_info = ModelTypeInfo(
                name=type_name,
                display_name=type_name,
                description=f"Auto-detected type: {type_name}",
                is_official=False,
                confidence_score=0.3
            )
            self.detected_types[type_name] = type_info
            logger.info(f"New model type discovered: {type_name}")
        
        # Update observation data
        type_info.last_seen = current_time
        type_info.occurrence_count += 1
        
        # Update confidence score for detected types
        if not type_info.is_official:
            # Increase confidence based on frequency
            type_info.confidence_score = min(
                1.0,
                type_info.confidence_score + 0.1
            )
        
        # Extract and update common tags
        tags = [tag.get('name', '').lower() for tag in model_data.get('tags', [])]
        type_info.common_tags.update(tags[:5])  # Keep top 5 most recent tags
        
        # Update patterns
        self._update_type_patterns(type_name, model_data)
    
    def _update_type_patterns(self, type_name: str, model_data: Dict[str, Any]) -> None:
        """Update pattern analysis for a model type."""
        if type_name not in self.type_patterns:
            self.type_patterns[type_name] = {
                'name_patterns': set(),
                'tag_frequency': {},
                'file_patterns': set(),
                'size_distribution': []
            }
        
        patterns = self.type_patterns[type_name]
        
        # Name patterns
        model_name = model_data.get('name', '').lower()
        name_words = set(model_name.split())
        patterns['name_patterns'].update(name_words)
        
        # Tag frequency
        tags = [tag.get('name', '').lower() for tag in model_data.get('tags', [])]
        for tag in tags:
            patterns['tag_frequency'][tag] = patterns['tag_frequency'].get(tag, 0) + 1
        
        # File patterns
        for version in model_data.get('modelVersions', []):
            for file_info in version.get('files', []):
                file_name = file_info.get('name', '').lower()
                if '.' in file_name:
                    ext = '.' + file_name.split('.')[-1]
                    patterns['file_patterns'].add(ext)
                
                # Size distribution
                size_mb = file_info.get('sizeKB', 0) / 1024
                patterns['size_distribution'].append(size_mb)
                
                # Keep only recent size samples (last 100)
                if len(patterns['size_distribution']) > 100:
                    patterns['size_distribution'] = patterns['size_distribution'][-100:]
    
    def get_all_types(self) -> Dict[str, ModelTypeInfo]:
        """Get all known and detected model types."""
        all_types = {}
        all_types.update(self.known_types)
        all_types.update(self.detected_types)
        return all_types
    
    def get_type_info(self, type_name: str) -> Optional[ModelTypeInfo]:
        """Get information about a specific type."""
        if type_name in self.known_types:
            return self.known_types[type_name]
        elif type_name in self.detected_types:
            return self.detected_types[type_name]
        return None
    
    def get_detection_summary(self) -> Dict[str, Any]:
        """Get summary of type detection activity."""
        return {
            "known_types": len(self.known_types),
            "detected_types": len(self.detected_types),
            "total_types": len(self.known_types) + len(self.detected_types),
            "high_confidence_detected": len([
                t for t in self.detected_types.values() 
                if t.confidence_score > 0.8
            ]),
            "recent_detections": [
                t.name for t in self.detected_types.values()
                if time.time() - t.first_seen < 86400  # Last 24 hours
            ]
        }
    
    def _load_cached_data(self) -> None:
        """Load cached model type data."""
        cache_file = self.cache_dir / "model_types.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Load detected types
                for type_name, type_data in cached_data.get('detected_types', {}).items():
                    type_info = ModelTypeInfo(
                        name=type_data['name'],
                        display_name=type_data['display_name'],
                        description=type_data['description'],
                        file_extensions=set(type_data.get('file_extensions', [])),
                        typical_size_range=tuple(type_data.get('typical_size_range', [0, float('inf')])),
                        common_tags=set(type_data.get('common_tags', [])),
                        first_seen=type_data.get('first_seen', time.time()),
                        last_seen=type_data.get('last_seen', time.time()),
                        occurrence_count=type_data.get('occurrence_count', 0),
                        is_official=type_data.get('is_official', False),
                        confidence_score=type_data.get('confidence_score', 0.0)
                    )
                    self.detected_types[type_name] = type_info
                
                # Load patterns
                self.type_patterns = cached_data.get('type_patterns', {})
                
                logger.debug(f"Loaded {len(self.detected_types)} detected model types from cache")
                
            except Exception as e:
                logger.warning(f"Failed to load cached model type data: {e}")
    
    def _save_cached_data(self) -> None:
        """Save model type data to cache."""
        cache_file = self.cache_dir / "model_types.json"
        
        try:
            cache_data = {
                'detected_types': {
                    name: {
                        'name': info.name,
                        'display_name': info.display_name,
                        'description': info.description,
                        'file_extensions': list(info.file_extensions),
                        'typical_size_range': list(info.typical_size_range),
                        'common_tags': list(info.common_tags),
                        'first_seen': info.first_seen,
                        'last_seen': info.last_seen,
                        'occurrence_count': info.occurrence_count,
                        'is_official': info.is_official,
                        'confidence_score': info.confidence_score
                    }
                    for name, info in self.detected_types.items()
                },
                'type_patterns': {
                    name: {
                        'name_patterns': list(patterns['name_patterns']),
                        'tag_frequency': patterns['tag_frequency'],
                        'file_patterns': list(patterns['file_patterns']),
                        'size_distribution': patterns['size_distribution'][-50:]  # Keep last 50
                    }
                    for name, patterns in self.type_patterns.items()
                }
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug("Saved model type data to cache")
            
        except Exception as e:
            logger.warning(f"Failed to save model type data: {e}")
    
    def cleanup_old_detections(self, max_age_days: int = 30) -> int:
        """
        Clean up old, low-confidence detections.
        
        Args:
            max_age_days: Maximum age for low-confidence detections
            
        Returns:
            Number of types removed
        """
        cutoff_time = time.time() - (max_age_days * 86400)
        removed = []
        
        for type_name, type_info in list(self.detected_types.items()):
            if (type_info.confidence_score < 0.5 and 
                type_info.last_seen < cutoff_time):
                removed.append(type_name)
                del self.detected_types[type_name]
                if type_name in self.type_patterns:
                    del self.type_patterns[type_name]
        
        if removed:
            logger.info(f"Cleaned up {len(removed)} old model type detections")
            self._save_cached_data()
        
        return len(removed)