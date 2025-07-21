#!/usr/bin/env python3
"""
Search configuration for CivitAI Downloader.
Centralizes configurable parameters for search functionality.
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class SearchConfig:
    """Configurable search parameters."""
    
    # API limits
    DEFAULT_PAGE_LIMIT: int = 100
    MAX_PAGE_LIMIT: int = 200
    DEFAULT_TIMEOUT: int = 30
    
    # Retry configuration
    DEFAULT_MAX_RETRIES: int = 3
    DEFAULT_BACKOFF_BASE: float = 2.0
    
    # Cache configuration
    DEFAULT_CACHE_TTL: int = 900  # 15 minutes
    
    # Download limits
    DEFAULT_MIN_DOWNLOADS: int = 0
    DEFAULT_MAX_DOWNLOADS: int = 1000000
    
    # Base models configuration
    KNOWN_BASE_MODELS: List[str] = field(default_factory=lambda: [
        # SD 1.x series
        'SD 1.4', 'SD 1.5', 'SD 1.5 Inpainting', 'SD 1.5 LCM',
        
        # SD 2.x series
        'SD 2.0', 'SD 2.1', 'SD 2.1 Unclip', 'SD 2.1 768',
        
        # SDXL series
        'SDXL 1.0', 'SDXL 1.0 LCM', 'SDXL Turbo', 'SDXL Lightning',
        'SDXL Refiner', 'SDXL Inpainting', 'SDXL Instruct',
        
        # Anime-focused models
        'Illustrious', 'Illustrious XL', 'NoobAI', 'NoobAI XL',
        'Pony Diffusion V6 XL', 'Pony Diffusion', 'AnimagineXL',
        'AnythingV3', 'AnythingV4', 'AnythingV5', 'Counterfeit',
        
        # Realistic models
        'Realistic Vision', 'DreamShaper', 'Deliberate', 'Protogen',
        'Rev Animated', 'Lyriel', 'AbsoluteReality', 'Photon',
        
        # Special purpose
        'ControlNet', 'IP-Adapter', 'T2I-Adapter', 'InstantID',
        'Stable Cascade', 'PixArt', 'DeepFloyd IF',
        
        # Legacy models
        'Stable Diffusion v1', 'Stable Diffusion v2',
        'Waifu Diffusion', 'Trinart', 'Novel AI',
        
        # Community favorites
        'Juggernaut', 'Dreamlike', 'Openjourney', 'Analog Diffusion',
        'Redshift Diffusion', 'Arcane Diffusion', 'Future Diffusion',
        
        # Flux models
        'FLUX.1', 'FLUX.1-dev', 'FLUX.1-schnell'
    ])
    
    # Risk tolerance levels
    RISK_TOLERANCE_LEVELS: Dict[str, List[str]] = field(default_factory=lambda: {
        'low': ['LOW'],
        'medium': ['LOW', 'MEDIUM'],
        'high': ['LOW', 'MEDIUM', 'HIGH'],
        'critical': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    })
    
    @classmethod
    def from_env(cls) -> 'SearchConfig':
        """Create config from environment variables."""
        config = cls()
        
        # Override with environment variables if present
        if page_limit := os.getenv('CIVITAI_DEFAULT_PAGE_LIMIT'):
            config.DEFAULT_PAGE_LIMIT = int(page_limit)
            
        if max_limit := os.getenv('CIVITAI_MAX_PAGE_LIMIT'):
            config.MAX_PAGE_LIMIT = int(max_limit)
            
        if cache_ttl := os.getenv('CIVITAI_CACHE_TTL'):
            config.DEFAULT_CACHE_TTL = int(cache_ttl)
            
        if base_models := os.getenv('CIVITAI_BASE_MODELS'):
            # Parse comma-separated list
            config.KNOWN_BASE_MODELS = [m.strip() for m in base_models.split(',')]
            
        return config
    
    def get_base_models(self) -> List[str]:
        """Get list of known base models."""
        return self.KNOWN_BASE_MODELS.copy()
    
    def add_base_model(self, model_name: str) -> None:
        """Add a new base model to the known list."""
        if model_name and model_name not in self.KNOWN_BASE_MODELS:
            self.KNOWN_BASE_MODELS.append(model_name)
    
    def get_risk_levels(self, tolerance: str = 'low') -> List[str]:
        """Get allowed risk levels for given tolerance."""
        return self.RISK_TOLERANCE_LEVELS.get(tolerance, ['LOW'])