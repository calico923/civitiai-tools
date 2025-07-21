#!/usr/bin/env python3
"""
API Change Detection System.
Implements requirement 15.1-15.3: Dynamic API adaptation.
"""

import logging
import asyncio
import time
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class APICapability(Enum):
    """API capabilities that can be detected."""
    # Search capabilities
    ADVANCED_SEARCH = "advanced_search"
    CUSTOM_SORTING = "custom_sorting"
    CATEGORY_FILTERING = "category_filtering"
    BULK_OPERATIONS = "bulk_operations"
    
    # Pagination capabilities
    CURSOR_PAGINATION = "cursor_pagination"
    OFFSET_PAGINATION = "offset_pagination"
    
    # Data capabilities
    METADATA_FIELDS = "metadata_fields"
    LICENSE_FIELDS = "license_fields"
    SECURITY_FIELDS = "security_fields"
    
    # Future capabilities
    UNKNOWN_CAPABILITY = "unknown_capability"


@dataclass
class APIEndpoint:
    """API endpoint information."""
    path: str
    method: str
    parameters: Set[str] = field(default_factory=set)
    response_fields: Set[str] = field(default_factory=set)
    capabilities: Set[APICapability] = field(default_factory=set)
    last_checked: Optional[float] = None
    is_documented: bool = False
    risk_level: str = "unknown"


@dataclass
class APIChangeEvent:
    """Represents a detected API change."""
    timestamp: float
    change_type: str  # "added", "removed", "modified"
    endpoint: str
    detail: str
    impact_level: str  # "low", "medium", "high", "critical"
    suggested_action: str


class APIChangeDetector:
    """
    Detects changes in the CivitAI API per requirement 15.3.
    Monitors endpoints, parameters, and response structures.
    """
    
    def __init__(self, api_client=None, cache_dir: Optional[Path] = None):
        """
        Initialize API change detector.
        
        Args:
            api_client: API client instance
            cache_dir: Directory to store API snapshots
        """
        self.api_client = api_client
        self.cache_dir = cache_dir or Path("./api_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Known endpoints and their capabilities
        self.endpoints: Dict[str, APIEndpoint] = {
            "/v1/models": APIEndpoint(
                path="/v1/models",
                method="GET",
                parameters={"limit", "page", "query", "tag", "username", "types", "sort", "period"},
                capabilities={APICapability.ADVANCED_SEARCH, APICapability.CUSTOM_SORTING},
                is_documented=True,
                risk_level="low"
            ),
            "/v1/models/{id}": APIEndpoint(
                path="/v1/models/{id}",
                method="GET",
                parameters={"id"},
                capabilities={APICapability.METADATA_FIELDS},
                is_documented=True,
                risk_level="low"
            ),
            "/v1/model-versions/{id}": APIEndpoint(
                path="/v1/model-versions/{id}",
                method="GET",
                parameters={"id"},
                capabilities={APICapability.METADATA_FIELDS},
                is_documented=True,
                risk_level="low"
            )
        }
        
        self.change_history: List[APIChangeEvent] = []
        self.last_full_scan: Optional[float] = None
        
        # Load cached API state
        self._load_cached_state()
    
    async def detect_api_changes(self, force_full_scan: bool = False) -> List[APIChangeEvent]:
        """
        Detect changes in the API structure.
        
        Args:
            force_full_scan: Force a complete API scan
            
        Returns:
            List of detected changes
        """
        logger.info("Starting API change detection")
        changes = []
        
        try:
            # Scan all known endpoints
            for endpoint_key, endpoint in self.endpoints.items():
                endpoint_changes = await self._scan_endpoint(endpoint)
                changes.extend(endpoint_changes)
            
            # Discover new endpoints (if full scan)
            if force_full_scan or self._should_perform_full_scan():
                new_endpoints = await self._discover_new_endpoints()
                for endpoint in new_endpoints:
                    changes.append(APIChangeEvent(
                        timestamp=time.time(),
                        change_type="added",
                        endpoint=endpoint.path,
                        detail=f"New endpoint discovered: {endpoint.path}",
                        impact_level="medium",
                        suggested_action="Evaluate new endpoint capabilities"
                    ))
                    self.endpoints[endpoint.path] = endpoint
            
            # Update scan timestamp
            self.last_full_scan = time.time()
            
            # Cache current state
            self._cache_current_state()
            
            # Record changes
            self.change_history.extend(changes)
            
            if changes:
                logger.info(f"Detected {len(changes)} API changes")
            
            return changes
            
        except Exception as e:
            logger.error(f"API change detection failed: {e}")
            return []
    
    async def _scan_endpoint(self, endpoint: APIEndpoint) -> List[APIChangeEvent]:
        """Scan a specific endpoint for changes."""
        changes = []
        
        if not self.api_client:
            return changes
        
        try:
            # Make test request to endpoint
            response = await self._test_endpoint(endpoint)
            
            if response is None:
                return changes
            
            # Analyze response structure
            current_fields = self._extract_response_fields(response)
            
            # Compare with known fields
            if endpoint.response_fields:
                added_fields = current_fields - endpoint.response_fields
                removed_fields = endpoint.response_fields - current_fields
                
                for field in added_fields:
                    changes.append(APIChangeEvent(
                        timestamp=time.time(),
                        change_type="added",
                        endpoint=endpoint.path,
                        detail=f"New response field: {field}",
                        impact_level="low",
                        suggested_action="Update field extractors"
                    ))
                
                for field in removed_fields:
                    changes.append(APIChangeEvent(
                        timestamp=time.time(),
                        change_type="removed",
                        endpoint=endpoint.path,
                        detail=f"Removed response field: {field}",
                        impact_level="medium",
                        suggested_action="Update dependent code"
                    ))
            
            # Update endpoint information
            endpoint.response_fields = current_fields
            endpoint.last_checked = time.time()
            
        except Exception as e:
            logger.warning(f"Failed to scan endpoint {endpoint.path}: {e}")
        
        return changes
    
    async def _test_endpoint(self, endpoint: APIEndpoint) -> Optional[Dict[str, Any]]:
        """Test an endpoint with minimal parameters."""
        try:
            if endpoint.path == "/v1/models":
                # Test models endpoint with minimal params
                response = await self.api_client.search_models({"limit": 1})
                return response
            elif endpoint.path.startswith("/v1/models/"):
                # Skip individual model endpoints in routine scans
                return None
            else:
                # For other endpoints, attempt basic call
                return None
                
        except Exception as e:
            logger.debug(f"Endpoint test failed for {endpoint.path}: {e}")
            return None
    
    def _extract_response_fields(self, response: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Extract all field paths from a response."""
        fields = set()
        
        if isinstance(response, dict):
            for key, value in response.items():
                field_path = f"{prefix}.{key}" if prefix else key
                fields.add(field_path)
                
                # Recursively extract nested fields
                if isinstance(value, (dict, list)):
                    nested_fields = self._extract_response_fields(value, field_path)
                    fields.update(nested_fields)
        
        elif isinstance(response, list) and response:
            # Extract fields from first item in list
            first_item = response[0]
            if isinstance(first_item, dict):
                nested_fields = self._extract_response_fields(first_item, prefix)
                fields.update(nested_fields)
        
        return fields
    
    async def _discover_new_endpoints(self) -> List[APIEndpoint]:
        """Attempt to discover new API endpoints."""
        # This is a placeholder for endpoint discovery logic
        # In practice, this might involve:
        # - Checking API documentation
        # - Testing common endpoint patterns
        # - Monitoring network traffic
        
        logger.debug("Endpoint discovery not implemented")
        return []
    
    def _should_perform_full_scan(self) -> bool:
        """Determine if a full API scan should be performed."""
        if not self.last_full_scan:
            return True
        
        # Full scan every 24 hours
        return time.time() - self.last_full_scan > 86400
    
    def get_api_capabilities(self) -> Dict[str, Set[APICapability]]:
        """Get current API capabilities by endpoint."""
        return {
            endpoint.path: endpoint.capabilities
            for endpoint in self.endpoints.values()
        }
    
    def get_change_summary(self, hours: int = 24) -> Dict[str, int]:
        """Get summary of changes in the last N hours."""
        cutoff = time.time() - (hours * 3600)
        recent_changes = [
            change for change in self.change_history
            if change.timestamp > cutoff
        ]
        
        summary = {
            "total_changes": len(recent_changes),
            "added": len([c for c in recent_changes if c.change_type == "added"]),
            "removed": len([c for c in recent_changes if c.change_type == "removed"]),
            "modified": len([c for c in recent_changes if c.change_type == "modified"]),
            "high_impact": len([c for c in recent_changes if c.impact_level in ["high", "critical"]])
        }
        
        return summary
    
    def _load_cached_state(self) -> None:
        """Load cached API state from disk."""
        cache_file = self.cache_dir / "api_state.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Restore endpoint states
                for path, endpoint_data in cached_data.get("endpoints", {}).items():
                    if path in self.endpoints:
                        endpoint = self.endpoints[path]
                        endpoint.response_fields = set(endpoint_data.get("response_fields", []))
                        endpoint.last_checked = endpoint_data.get("last_checked")
                
                # Restore change history
                for change_data in cached_data.get("change_history", []):
                    change = APIChangeEvent(**change_data)
                    self.change_history.append(change)
                
                self.last_full_scan = cached_data.get("last_full_scan")
                
                logger.debug("Loaded cached API state")
                
            except Exception as e:
                logger.warning(f"Failed to load cached API state: {e}")
    
    def _cache_current_state(self) -> None:
        """Cache current API state to disk."""
        cache_file = self.cache_dir / "api_state.json"
        
        try:
            cache_data = {
                "endpoints": {
                    path: {
                        "response_fields": list(endpoint.response_fields),
                        "last_checked": endpoint.last_checked
                    }
                    for path, endpoint in self.endpoints.items()
                },
                "change_history": [
                    {
                        "timestamp": change.timestamp,
                        "change_type": change.change_type,
                        "endpoint": change.endpoint,
                        "detail": change.detail,
                        "impact_level": change.impact_level,
                        "suggested_action": change.suggested_action
                    }
                    for change in self.change_history[-100:]  # Keep last 100 changes
                ],
                "last_full_scan": self.last_full_scan
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug("Cached API state")
            
        except Exception as e:
            logger.warning(f"Failed to cache API state: {e}")
    
    def suggest_adaptations(self, changes: List[APIChangeEvent]) -> List[str]:
        """Suggest code adaptations based on detected changes."""
        suggestions = []
        
        for change in changes:
            if change.impact_level in ["high", "critical"]:
                suggestions.append(
                    f"URGENT: {change.detail} - {change.suggested_action}"
                )
            elif change.impact_level == "medium":
                suggestions.append(
                    f"ATTENTION: {change.detail} - {change.suggested_action}"
                )
        
        return suggestions