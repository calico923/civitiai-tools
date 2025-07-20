#!/usr/bin/env python3
"""
Feature Manager for CivitAI Downloader.
Manages unofficial features, risk assessment, and fallback strategies.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class RiskLevel(Enum):
    """Risk levels for unofficial features."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FeatureStatus(Enum):
    """Feature availability status."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    EXPERIMENTAL = "EXPERIMENTAL"
    DEPRECATED = "DEPRECATED"


@dataclass
class FeatureRiskProfile:
    """Profile containing risk assessment for a feature."""
    feature_name: str
    risk_level: str
    fallback_strategy: str
    success_rate: float
    last_tested: datetime
    attempts: int = field(default=0)
    successes: int = field(default=0)


class FeatureManager:
    """Manages unofficial CivitAI features and their fallback strategies."""
    
    def __init__(self):
        """Initialize feature manager."""
        self.features = {}
        self.risk_profiles = {}
        self.enabled_features = set()
        self.feature_stats = {}
        self.configuration = {
            'enable_unofficial_features': True,
            'risk_tolerance': 'MEDIUM',
            'fallback_enabled': True,
            'max_retries': 3
        }
        self._stats_file = Path.home() / ".civitai" / "feature_stats.json"
        self._config_file = Path.home() / ".civitai" / "feature_config.json"
        self._ensure_config_dir()
        self._load_configuration()
        self._initialize_default_features()
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self._stats_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _initialize_default_features(self):
        """Initialize default feature profiles."""
        default_features = [
            ('advanced_search', 'MEDIUM', 'official_search', 0.85),
            ('custom_sort', 'LOW', 'default_sort', 0.90),
            ('category_filter', 'LOW', 'basic_filter', 0.95),
            ('unofficial_api_fields', 'HIGH', 'official_fields', 0.70)
        ]
        
        for name, risk, fallback, success_rate in default_features:
            self.risk_profiles[name] = FeatureRiskProfile(
                feature_name=name,
                risk_level=risk,
                fallback_strategy=fallback,
                success_rate=success_rate,
                last_tested=datetime.now()
            )
            self.enabled_features.add(name)
    
    def assess_feature_availability(self) -> Dict[str, FeatureStatus]:
        """
        Assess availability of all managed features.
        
        Returns:
            Dictionary mapping feature names to their status
        """
        availability = {}
        
        for feature_name in self.risk_profiles.keys():
            # Simulate feature availability check
            if feature_name in self.enabled_features:
                profile = self.risk_profiles[feature_name]
                if profile.success_rate > 0.8:
                    availability[feature_name] = FeatureStatus.AVAILABLE
                elif profile.success_rate > 0.5:
                    availability[feature_name] = FeatureStatus.EXPERIMENTAL
                else:
                    availability[feature_name] = FeatureStatus.DEPRECATED
            else:
                availability[feature_name] = FeatureStatus.UNAVAILABLE
        
        return availability
    
    def evaluate_risk_level(self, feature_name: str) -> str:
        """
        Evaluate risk level for a specific feature.
        
        Args:
            feature_name: Name of the feature to evaluate
            
        Returns:
            Risk level string (LOW, MEDIUM, HIGH)
        """
        if feature_name in self.risk_profiles:
            return self.risk_profiles[feature_name].risk_level
        
        # Default risk assessment based on feature name
        if 'stable' in feature_name.lower():
            return RiskLevel.LOW.value
        elif 'experimental' in feature_name.lower():
            return RiskLevel.HIGH.value
        elif 'beta' in feature_name.lower():
            return RiskLevel.MEDIUM.value
        
        return RiskLevel.MEDIUM.value
    
    def get_fallback_chain(self, feature_name: str) -> List[str]:
        """
        Generate fallback chain for a feature.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            List of fallback methods in order of preference
        """
        fallback_chain = [feature_name]
        
        if feature_name in self.risk_profiles:
            fallback_strategy = self.risk_profiles[feature_name].fallback_strategy
            fallback_chain.append(fallback_strategy)
        
        # Add common fallback strategies
        if 'search' in feature_name:
            fallback_chain.extend(['basic_search', 'official_search'])
        elif 'sort' in feature_name:
            fallback_chain.extend(['default_sort', 'name_sort'])
        elif 'filter' in feature_name:
            fallback_chain.extend(['basic_filter', 'no_filter'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_chain = []
        for method in fallback_chain:
            if method not in seen:
                seen.add(method)
                unique_chain.append(method)
        
        return unique_chain
    
    def update_feature_status(self, feature_name: str, success: bool) -> None:
        """
        Update feature status based on usage result.
        
        Args:
            feature_name: Name of the feature
            success: Whether the feature operation was successful
        """
        if feature_name not in self.feature_stats:
            self.feature_stats[feature_name] = {
                'total_attempts': 0,
                'success_count': 0,
                'failure_count': 0,
                'last_updated': datetime.now().isoformat()
            }
        
        stats = self.feature_stats[feature_name]
        stats['total_attempts'] += 1
        stats['last_updated'] = datetime.now().isoformat()
        
        if success:
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1
        
        # Update success rate in risk profile
        if feature_name in self.risk_profiles:
            profile = self.risk_profiles[feature_name]
            profile.attempts += 1
            if success:
                profile.successes += 1
            profile.success_rate = profile.successes / profile.attempts if profile.attempts > 0 else 0
            profile.last_tested = datetime.now()
        
        self._save_stats()
    
    def get_feature_statistics(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific feature.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            Feature statistics or None if not found
        """
        if feature_name not in self.feature_stats:
            return None
        
        stats = self.feature_stats[feature_name].copy()
        if stats['total_attempts'] > 0:
            stats['success_rate'] = stats['success_count'] / stats['total_attempts']
        else:
            stats['success_rate'] = 0.0
        
        return stats
    
    def configure_features(self, config: Dict[str, Any]) -> None:
        """
        Configure feature manager settings.
        
        Args:
            config: Configuration dictionary
        """
        self.configuration.update(config)
        self._save_configuration()
    
    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current configuration.
        
        Returns:
            Current configuration dictionary
        """
        return self.configuration.copy()
    
    def detect_unofficial_features(self) -> List[str]:
        """
        Detect available unofficial features.
        
        Returns:
            List of detected feature names
        """
        # In real implementation, would probe CivitAI API for unofficial endpoints
        detected = []
        
        # Check known unofficial features
        known_features = [
            'advanced_search',
            'custom_sort',
            'category_filter',
            'unofficial_api_fields',
            'batch_download',
            'metadata_extraction'
        ]
        
        for feature in known_features:
            if self.validate_feature(feature):
                detected.append(feature)
        
        return detected
    
    def validate_feature(self, feature_name: str) -> bool:
        """
        Validate if a feature is available and working.
        
        Args:
            feature_name: Name of the feature to validate
            
        Returns:
            True if feature is valid, False otherwise
        """
        # Simulate feature validation
        if feature_name in self.risk_profiles:
            profile = self.risk_profiles[feature_name]
            return profile.success_rate > 0.5
        
        # For unknown features, assume they need validation
        return feature_name in self.enabled_features
    
    def record_feature_usage(self, feature_name: str, success: bool, duration: float) -> None:
        """
        Record feature usage for analytics.
        
        Args:
            feature_name: Name of the feature used
            success: Whether the usage was successful
            duration: Duration of the operation in seconds
        """
        if feature_name not in self.feature_stats:
            self.feature_stats[feature_name] = {
                'total_attempts': 0,
                'success_count': 0,
                'failure_count': 0,
                'total_duration': 0.0,
                'usage_history': []
            }
        
        stats = self.feature_stats[feature_name]
        stats['total_attempts'] += 1
        stats['total_duration'] += duration
        
        if success:
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1
        
        # Record individual usage
        usage_record = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'duration': duration
        }
        
        if 'usage_history' not in stats:
            stats['usage_history'] = []
        
        stats['usage_history'].append(usage_record)
        
        # Keep only last 100 records
        if len(stats['usage_history']) > 100:
            stats['usage_history'] = stats['usage_history'][-100:]
        
        self._save_stats()
    
    def get_usage_analytics(self) -> Dict[str, Any]:
        """
        Get overall usage analytics.
        
        Returns:
            Analytics dictionary
        """
        total_usage = 0
        total_successes = 0
        total_duration = 0.0
        feature_breakdown = {}
        
        for feature_name, stats in self.feature_stats.items():
            attempts = stats.get('total_attempts', 0)
            successes = stats.get('success_count', 0)
            duration = stats.get('total_duration', 0.0)
            
            total_usage += attempts
            total_successes += successes
            total_duration += duration
            
            if attempts > 0:
                feature_breakdown[feature_name] = {
                    'usage_count': attempts,
                    'success_rate': successes / attempts,
                    'average_duration': duration / attempts
                }
        
        analytics = {
            'total_usage': total_usage,
            'success_rate': total_successes / total_usage if total_usage > 0 else 0,
            'average_duration': total_duration / total_usage if total_usage > 0 else 0,
            'feature_breakdown': feature_breakdown
        }
        
        return analytics
    
    def get_feature_analytics(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """
        Get analytics for a specific feature.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            Feature-specific analytics or None
        """
        if feature_name not in self.feature_stats:
            return None
        
        stats = self.feature_stats[feature_name]
        attempts = stats.get('total_attempts', 0)
        successes = stats.get('success_count', 0)
        duration = stats.get('total_duration', 0.0)
        
        if attempts == 0:
            return None
        
        return {
            'usage_count': attempts,
            'success_rate': successes / attempts,
            'average_duration': duration / attempts,
            'last_used': stats.get('last_updated', 'Never')
        }
    
    def enable_feature(self, feature_name: str) -> None:
        """
        Enable a specific feature.
        
        Args:
            feature_name: Name of the feature to enable
        """
        self.enabled_features.add(feature_name)
        self._save_configuration()
    
    def disable_feature(self, feature_name: str) -> None:
        """
        Disable a specific feature.
        
        Args:
            feature_name: Name of the feature to disable
        """
        self.enabled_features.discard(feature_name)
        self._save_configuration()
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled.
        
        Args:
            feature_name: Name of the feature to check
            
        Returns:
            True if feature is enabled, False otherwise
        """
        return feature_name in self.enabled_features
    
    def get_enabled_features(self) -> List[str]:
        """
        Get list of enabled features.
        
        Returns:
            List of enabled feature names
        """
        return list(self.enabled_features)
    
    def get_disabled_features(self) -> List[str]:
        """
        Get list of disabled features.
        
        Returns:
            List of disabled feature names
        """
        all_features = set(self.risk_profiles.keys())
        return list(all_features - self.enabled_features)
    
    def _save_stats(self) -> None:
        """Save feature statistics to file."""
        try:
            with open(self._stats_file, 'w') as f:
                json.dump(self.feature_stats, f, indent=2)
        except Exception:
            pass
    
    def _load_stats(self) -> None:
        """Load feature statistics from file."""
        if self._stats_file.exists():
            try:
                with open(self._stats_file, 'r') as f:
                    self.feature_stats = json.load(f)
            except Exception:
                self.feature_stats = {}
    
    def _save_configuration(self) -> None:
        """Save configuration to file."""
        config_data = {
            'configuration': self.configuration,
            'enabled_features': list(self.enabled_features)
        }
        try:
            with open(self._config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception:
            pass
    
    def _load_configuration(self) -> None:
        """Load configuration from file."""
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r') as f:
                    config_data = json.load(f)
                
                if 'configuration' in config_data:
                    self.configuration.update(config_data['configuration'])
                
                if 'enabled_features' in config_data:
                    self.enabled_features = set(config_data['enabled_features'])
            except Exception:
                pass