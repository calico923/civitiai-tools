#!/usr/bin/env python3
"""
CivitAI Version Management Client.

Provides comprehensive version management functionality for CivitAI models,
including version comparison, update detection, and version-specific operations.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from pathlib import Path
import logging

from .client import CivitaiAPIClient
from ..data.models.file_models import ModelFile, FileHashes

logger = logging.getLogger(__name__)


class ModelVersion:
    """Represents a single model version with comprehensive metadata."""
    
    def __init__(self, version_data: Dict[str, Any]):
        """Initialize from API response data."""
        self.id: int = version_data['id']
        self.name: str = version_data.get('name', '')
        self.base_model: str = version_data.get('baseModel', '')
        self.base_model_type: str = version_data.get('baseModelType', 'Standard')
        self.description: str = version_data.get('description', '')
        self.status: str = version_data.get('status', 'Unknown')
        self.availability: str = version_data.get('availability', 'Public')
        
        # Parse timestamps
        self.created_at = self._parse_timestamp(version_data.get('createdAt'))
        self.published_at = self._parse_timestamp(version_data.get('publishedAt'))
        
        # Version ordering (0 = latest)
        self.index: int = version_data.get('index', 999)
        
        # Download information
        self.download_url: Optional[str] = version_data.get('downloadUrl')
        
        # Statistics
        self.stats = version_data.get('stats', {})
        self.download_count = self.stats.get('downloadCount', 0)
        self.rating = self.stats.get('rating', 0.0)
        self.thumbs_up_count = self.stats.get('thumbsUpCount', 0)
        self.thumbs_down_count = self.stats.get('thumbsDownCount', 0)
        
        # Files and hashes
        self.files: List[ModelFile] = self._parse_files(version_data.get('files', []))
        
        # Images and metadata
        self.images = version_data.get('images', [])
        self.metadata = version_data.get('metadata', {})
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime object."""
        if not timestamp_str:
            return None
        
        try:
            # Handle 'Z' timezone indicator
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return None
    
    def _parse_files(self, files_data: List[Dict[str, Any]]) -> List[ModelFile]:
        """Parse files data into ModelFile objects."""
        files = []
        
        for file_data in files_data:
            try:
                # Extract hash information
                hashes_data = file_data.get('hashes', {})
                file_hashes = FileHashes(**hashes_data)
                
                # Create ModelFile object (simplified, adjust field mapping as needed)
                model_file = ModelFile(
                    id=file_data['id'],
                    url=file_data.get('downloadUrl', self.download_url or ''),
                    sizeKB=file_data.get('sizeKB', 0),
                    name=file_data.get('name', ''),
                    type=file_data.get('type', 'Model'),
                    format=file_data.get('metadata', {}).get('format', 'Other'),
                    pickleScanResult=file_data.get('pickleScanResult', 'Pending'),
                    virusScanResult=file_data.get('virusScanResult', 'Pending'),
                    hashes=file_hashes,
                    downloadUrl=file_data.get('downloadUrl'),
                    primary=file_data.get('primary', False),
                    metadata=file_data.get('metadata', {})
                )
                files.append(model_file)
                
            except Exception as e:
                logger.warning(f"Failed to parse file data: {e}")
                continue
        
        return files
    
    @property
    def is_published(self) -> bool:
        """Check if version is published."""
        return self.status == 'Published'
    
    @property
    def is_latest(self) -> bool:
        """Check if this is the latest version (index = 0)."""
        return self.index == 0
    
    @property
    def primary_file(self) -> Optional[ModelFile]:
        """Get the primary file for this version."""
        for file in self.files:
            if file.primary:
                return file
        return self.files[0] if self.files else None
    
    @property
    def like_ratio(self) -> float:
        """Calculate like ratio (thumbs up / total votes)."""
        total_votes = self.thumbs_up_count + self.thumbs_down_count
        if total_votes == 0:
            return 0.0
        return self.thumbs_up_count / total_votes
    
    def get_size_info(self) -> Dict[str, Any]:
        """Get comprehensive size information."""
        primary = self.primary_file
        if not primary:
            return {'total_files': len(self.files), 'total_size_mb': 0}
        
        total_size_kb = sum(f.sizeKB for f in self.files)
        
        return {
            'total_files': len(self.files),
            'primary_file_size_mb': primary.get_size_mb(),
            'total_size_mb': total_size_kb / 1024,
            'primary_file_name': primary.name,
            'primary_file_format': primary.format
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'base_model': self.base_model,
            'base_model_type': self.base_model_type,
            'description': self.description,
            'status': self.status,
            'availability': self.availability,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'index': self.index,
            'download_url': self.download_url,
            'stats': self.stats,
            'like_ratio': self.like_ratio,
            'is_published': self.is_published,
            'is_latest': self.is_latest,
            'size_info': self.get_size_info(),
            'files_count': len(self.files)
        }


class VersionComparison:
    """Comparison result between two model versions."""
    
    def __init__(self, version1: ModelVersion, version2: ModelVersion):
        """Initialize comparison between two versions."""
        self.version1 = version1
        self.version2 = version2
        
        # Basic info comparison
        self.version1_newer = self._is_newer(version1, version2)
        self.same_base_model = version1.base_model == version2.base_model
        
        # Statistics comparison
        self.download_diff = version1.download_count - version2.download_count
        self.rating_diff = version1.rating - version2.rating
        self.like_ratio_diff = version1.like_ratio - version2.like_ratio
        
        # Size comparison
        v1_size = version1.get_size_info()
        v2_size = version2.get_size_info()
        self.size_diff_mb = v1_size['total_size_mb'] - v2_size['total_size_mb']
        
        # Time comparison
        self.days_apart = self._calculate_days_apart()
    
    def _is_newer(self, v1: ModelVersion, v2: ModelVersion) -> bool:
        """Determine if version1 is newer than version2."""
        # Primary: index comparison (lower index = newer)
        if v1.index != v2.index:
            return v1.index < v2.index
        
        # Secondary: published date comparison
        if v1.published_at and v2.published_at:
            return v1.published_at > v2.published_at
        
        # Fallback: created date comparison
        if v1.created_at and v2.created_at:
            return v1.created_at > v2.created_at
        
        return False
    
    def _calculate_days_apart(self) -> Optional[int]:
        """Calculate days between version publication dates."""
        if not (self.version1.published_at and self.version2.published_at):
            return None
        
        diff = self.version1.published_at - self.version2.published_at
        return diff.days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'version1': {
                'id': self.version1.id,
                'name': self.version1.name,
                'is_newer': self.version1_newer
            },
            'version2': {
                'id': self.version2.id,
                'name': self.version2.name,
                'is_newer': not self.version1_newer
            },
            'same_base_model': self.same_base_model,
            'statistics': {
                'download_diff': self.download_diff,
                'rating_diff': self.rating_diff,
                'like_ratio_diff': self.like_ratio_diff
            },
            'size_diff_mb': self.size_diff_mb,
            'days_apart': self.days_apart
        }


class VersionClient:
    """
    Client for CivitAI version management operations.
    
    Provides high-level version management functionality including:
    - Version retrieval and filtering
    - Version comparison
    - Update detection
    - Version-specific downloads
    """
    
    def __init__(self, api_client: CivitaiAPIClient):
        """Initialize with CivitAI API client."""
        self.api_client = api_client
        self._version_cache: Dict[int, List[ModelVersion]] = {}
    
    async def get_model_versions(self, model_id: int, force_refresh: bool = False) -> List[ModelVersion]:
        """
        Get all versions for a model.
        
        Args:
            model_id: CivitAI model ID
            force_refresh: Force refresh from API (ignore cache)
            
        Returns:
            List of ModelVersion objects sorted by index (latest first)
        """
        if not force_refresh and model_id in self._version_cache:
            return self._version_cache[model_id]
        
        try:
            model_data = await self.api_client.get_models({'ids': [model_id]})
            
            if not model_data.get('items'):
                logger.warning(f"Model {model_id} not found")
                return []
            
            model = model_data['items'][0]
            versions_data = model.get('modelVersions', [])
            
            # Parse versions
            versions = []
            for version_data in versions_data:
                try:
                    version = ModelVersion(version_data)
                    versions.append(version)
                except Exception as e:
                    logger.warning(f"Failed to parse version {version_data.get('id', 'unknown')}: {e}")
                    continue
            
            # Sort by index (latest first)
            versions.sort(key=lambda v: v.index)
            
            # Cache results
            self._version_cache[model_id] = versions
            
            return versions
            
        except Exception as e:
            logger.error(f"Failed to get versions for model {model_id}: {e}")
            return []
    
    async def get_version_by_id(self, version_id: int) -> Optional[ModelVersion]:
        """
        Get specific version by ID.
        
        Args:
            version_id: Version ID
            
        Returns:
            ModelVersion object or None if not found
        """
        try:
            # Use direct version endpoint if available
            response = await self.api_client._http_client.get(
                f"{self.api_client.base_url}/model-versions/{version_id}"
            )
            
            if response.status_code == 200:
                version_data = response.json()
                return ModelVersion(version_data)
            else:
                logger.warning(f"Version {version_id} not found (status: {response.status_code})")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get version {version_id}: {e}")
            return None
    
    async def get_latest_version(self, model_id: int) -> Optional[ModelVersion]:
        """
        Get the latest published version of a model.
        
        Args:
            model_id: CivitAI model ID
            
        Returns:
            Latest ModelVersion or None if not found
        """
        versions = await self.get_model_versions(model_id)
        
        # Find latest published version
        published_versions = [v for v in versions if v.is_published]
        
        if not published_versions:
            return None
        
        # Return version with lowest index (latest)
        return min(published_versions, key=lambda v: v.index)
    
    async def filter_versions(
        self, 
        model_id: int, 
        base_model: Optional[str] = None,
        status: Optional[str] = None,
        min_downloads: Optional[int] = None,
        min_rating: Optional[float] = None
    ) -> List[ModelVersion]:
        """
        Filter versions by criteria.
        
        Args:
            model_id: CivitAI model ID
            base_model: Filter by base model (e.g., "SDXL 1.0", "Pony")
            status: Filter by status (e.g., "Published")
            min_downloads: Minimum download count
            min_rating: Minimum rating
            
        Returns:
            Filtered list of ModelVersion objects
        """
        versions = await self.get_model_versions(model_id)
        filtered = versions
        
        if base_model:
            filtered = [v for v in filtered if v.base_model.lower() == base_model.lower()]
        
        if status:
            filtered = [v for v in filtered if v.status == status]
        
        if min_downloads is not None:
            filtered = [v for v in filtered if v.download_count >= min_downloads]
        
        if min_rating is not None:
            filtered = [v for v in filtered if v.rating >= min_rating]
        
        return filtered
    
    def compare_versions(self, version1: ModelVersion, version2: ModelVersion) -> VersionComparison:
        """
        Compare two versions.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            VersionComparison object
        """
        return VersionComparison(version1, version2)
    
    async def check_for_updates(
        self, 
        model_id: int, 
        last_check_time: datetime,
        only_published: bool = True
    ) -> List[ModelVersion]:
        """
        Check for new versions since last check.
        
        Args:
            model_id: CivitAI model ID
            last_check_time: Last check timestamp
            only_published: Only include published versions
            
        Returns:
            List of new versions
        """
        versions = await self.get_model_versions(model_id, force_refresh=True)
        
        new_versions = []
        for version in versions:
            if not version.published_at:
                continue
            
            if only_published and not version.is_published:
                continue
            
            if version.published_at > last_check_time:
                new_versions.append(version)
        
        return new_versions
    
    async def get_version_stats_summary(self, model_id: int) -> Dict[str, Any]:
        """
        Get summary statistics for all versions of a model.
        
        Args:
            model_id: CivitAI model ID
            
        Returns:
            Statistics summary dictionary
        """
        versions = await self.get_model_versions(model_id)
        
        if not versions:
            return {}
        
        published_versions = [v for v in versions if v.is_published]
        
        # Calculate aggregated statistics
        total_downloads = sum(v.download_count for v in published_versions)
        avg_rating = sum(v.rating for v in published_versions) / len(published_versions) if published_versions else 0
        total_thumbs_up = sum(v.thumbs_up_count for v in published_versions)
        
        # Base model distribution
        base_models = {}
        for version in published_versions:
            base_model = version.base_model
            if base_model not in base_models:
                base_models[base_model] = 0
            base_models[base_model] += 1
        
        # Version timeline
        timeline = []
        for version in published_versions:
            if version.published_at:
                timeline.append({
                    'version_id': version.id,
                    'version_name': version.name,
                    'published_at': version.published_at.isoformat(),
                    'download_count': version.download_count
                })
        
        timeline.sort(key=lambda x: x['published_at'])
        
        return {
            'model_id': model_id,
            'total_versions': len(versions),
            'published_versions': len(published_versions),
            'total_downloads': total_downloads,
            'average_rating': avg_rating,
            'total_thumbs_up': total_thumbs_up,
            'base_model_distribution': base_models,
            'version_timeline': timeline,
            'latest_version': published_versions[0].to_dict() if published_versions else None
        }
    
    def clear_cache(self):
        """Clear version cache."""
        self._version_cache.clear()