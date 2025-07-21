#!/usr/bin/env python3
"""
License Management System.
Implements requirement 9: License information and compliance management.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
import logging
import time
import json

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """License types for model usage."""
    ALLOW_COMMERCIAL_USE = "allowCommercialUse"
    ALLOW_DERIVATIVES = "allowDerivatives"  
    ALLOW_DIFFERENT_LICENSE = "allowDifferentLicense"
    ALLOW_NO_CREDIT = "allowNoCredit"


class LicenseStatus(Enum):
    """License status values."""
    ALLOWED = "allowed"
    DISALLOWED = "disallowed"
    UNKNOWN = "unknown"
    REQUIRED = "required"


@dataclass
class LicenseInfo:
    """
    Comprehensive license information per requirement 9.1.
    Tracks all 4 license fields from CivitAI API.
    """
    allow_commercial_use: LicenseStatus
    allow_derivatives: LicenseStatus
    allow_different_license: LicenseStatus
    allow_no_credit: LicenseStatus
    
    # Additional metadata
    license_name: Optional[str] = None
    license_url: Optional[str] = None
    license_description: Optional[str] = None
    attribution_required: bool = True
    
    # Validation metadata
    collected_at: float = None
    source_model_id: Optional[int] = None
    
    def __post_init__(self):
        if self.collected_at is None:
            self.collected_at = time.time()
    
    def is_commercial_safe(self) -> bool:
        """Check if model is safe for commercial use."""
        return self.allow_commercial_use == LicenseStatus.ALLOWED
    
    def requires_attribution(self) -> bool:
        """Check if attribution is required."""
        return not (self.allow_no_credit == LicenseStatus.ALLOWED)
    
    def allows_derivatives(self) -> bool:
        """Check if derivative works are allowed."""
        return self.allow_derivatives == LicenseStatus.ALLOWED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export."""
        return {
            'license_fields': {
                'allowCommercialUse': self.allow_commercial_use.value,
                'allowDerivatives': self.allow_derivatives.value,
                'allowDifferentLicense': self.allow_different_license.value,
                'allowNoCredit': self.allow_no_credit.value
            },
            'metadata': {
                'license_name': self.license_name,
                'license_url': self.license_url,
                'license_description': self.license_description,
                'attribution_required': self.attribution_required,
                'collected_at': self.collected_at,
                'source_model_id': self.source_model_id
            },
            'compliance_flags': {
                'commercial_safe': self.is_commercial_safe(),
                'requires_attribution': self.requires_attribution(),
                'allows_derivatives': self.allows_derivatives()
            }
        }


@dataclass
class LicenseFilterConfig:
    """Configuration for license-based filtering per requirement 9.6."""
    commercial_use_only: bool = False
    require_derivatives: bool = False
    attribution_optional: bool = False
    exclude_restrictive: bool = False
    
    def matches_license(self, license_info: LicenseInfo) -> bool:
        """Check if license matches filter criteria."""
        if self.commercial_use_only and not license_info.is_commercial_safe():
            return False
            
        if self.require_derivatives and not license_info.allows_derivatives():
            return False
            
        if self.attribution_optional and license_info.requires_attribution():
            return False
            
        if self.exclude_restrictive:
            # Exclude models with any restrictive licensing
            restrictive_fields = [
                license_info.allow_commercial_use == LicenseStatus.DISALLOWED,
                license_info.allow_derivatives == LicenseStatus.DISALLOWED,
                license_info.allow_different_license == LicenseStatus.DISALLOWED
            ]
            if any(restrictive_fields):
                return False
                
        return True


class LicenseManager:
    """
    License information manager implementing requirement 9.
    
    Provides:
    - License field collection (9.1)
    - License compliance checking (9.5)
    - Commercial use filtering (9.6)
    """
    
    def __init__(self):
        """Initialize license manager."""
        self.license_cache: Dict[int, LicenseInfo] = {}
        self.compliance_warnings: List[Dict[str, Any]] = []
        
    def extract_license_info(self, model_data: Dict[str, Any]) -> LicenseInfo:
        """
        Extract license information from model data per requirement 9.1.
        
        Args:
            model_data: Model data from CivitAI API
            
        Returns:
            LicenseInfo with all 4 required license fields
        """
        model_id = model_data.get('id')
        
        # Extract the 4 required license fields
        def parse_license_value(value: Any) -> LicenseStatus:
            """Parse license value to standard status."""
            if value is True:
                return LicenseStatus.ALLOWED
            elif value is False:
                return LicenseStatus.DISALLOWED
            elif value == "allowed":
                return LicenseStatus.ALLOWED
            elif value == "disallowed":
                return LicenseStatus.DISALLOWED
            elif value == "required":
                return LicenseStatus.REQUIRED
            else:
                return LicenseStatus.UNKNOWN
        
        license_info = LicenseInfo(
            allow_commercial_use=parse_license_value(
                model_data.get('allowCommercialUse')
            ),
            allow_derivatives=parse_license_value(
                model_data.get('allowDerivatives')
            ),
            allow_different_license=parse_license_value(
                model_data.get('allowDifferentLicense')
            ),
            allow_no_credit=parse_license_value(
                model_data.get('allowNoCredit')
            ),
            license_name=model_data.get('license'),
            license_url=model_data.get('licenseUrl'),
            license_description=model_data.get('licenseDescription'),
            source_model_id=model_id
        )
        
        # Cache for future reference
        if model_id:
            self.license_cache[model_id] = license_info
            
        return license_info
    
    def check_compliance_warnings(self, license_info: LicenseInfo, 
                                 intended_use: str = "general") -> List[str]:
        """
        Check for license compliance warnings per requirement 9.5.
        
        Args:
            license_info: License information to check
            intended_use: Intended use case ("commercial", "derivative", etc.)
            
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Commercial use warnings
        if intended_use == "commercial":
            if license_info.allow_commercial_use == LicenseStatus.DISALLOWED:
                warnings.append(
                    "⚠️  Commercial use is explicitly disallowed for this model"
                )
            elif license_info.allow_commercial_use == LicenseStatus.UNKNOWN:
                warnings.append(
                    "⚠️  Commercial use permission is unclear - verify license manually"
                )
        
        # Attribution warnings
        if license_info.requires_attribution():
            warnings.append(
                "ℹ️  Attribution required - ensure proper credit is given"
            )
        
        # Derivative work warnings
        if intended_use == "derivative":
            if license_info.allow_derivatives == LicenseStatus.DISALLOWED:
                warnings.append(
                    "⚠️  Derivative works are not allowed for this model"
                )
            elif license_info.allow_derivatives == LicenseStatus.UNKNOWN:
                warnings.append(
                    "⚠️  Derivative work permission is unclear - verify license manually"
                )
        
        # Different license warnings
        if license_info.allow_different_license == LicenseStatus.DISALLOWED:
            warnings.append(
                "⚠️  Using a different license for derivative works is not allowed"
            )
        
        # Unknown license warnings
        unknown_fields = []
        if license_info.allow_commercial_use == LicenseStatus.UNKNOWN:
            unknown_fields.append("commercial use")
        if license_info.allow_derivatives == LicenseStatus.UNKNOWN:
            unknown_fields.append("derivatives")
        if license_info.allow_different_license == LicenseStatus.UNKNOWN:
            unknown_fields.append("different license")
        if license_info.allow_no_credit == LicenseStatus.UNKNOWN:
            unknown_fields.append("attribution")
            
        if unknown_fields:
            warnings.append(
                f"⚠️  License terms unclear for: {', '.join(unknown_fields)}. "
                "Please verify with model author."
            )
        
        # Log warnings for audit trail
        if warnings:
            self.compliance_warnings.append({
                'timestamp': time.time(),
                'model_id': license_info.source_model_id,
                'intended_use': intended_use,
                'warnings': warnings
            })
            
        return warnings
    
    def filter_commercial_models(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter models for commercial use per requirement 9.6.
        
        Args:
            models: List of model data dictionaries
            
        Returns:
            Filtered list containing only commercially safe models
        """
        commercial_safe = []
        
        for model in models:
            license_info = self.extract_license_info(model)
            
            if license_info.is_commercial_safe():
                # Add license compliance info to model data
                model['license_compliance'] = {
                    'commercial_safe': True,
                    'requires_attribution': license_info.requires_attribution(),
                    'allows_derivatives': license_info.allows_derivatives(),
                    'compliance_checked_at': time.time()
                }
                commercial_safe.append(model)
            else:
                logger.info(f"Filtered out model {model.get('id')} - not commercially safe")
        
        logger.info(f"Commercial filtering: {len(commercial_safe)}/{len(models)} models approved")
        return commercial_safe
    
    def apply_license_filter(self, models: List[Dict[str, Any]], 
                           filter_config: LicenseFilterConfig) -> List[Dict[str, Any]]:
        """
        Apply comprehensive license filtering.
        
        Args:
            models: List of model data dictionaries
            filter_config: License filter configuration
            
        Returns:
            Filtered list of models matching license criteria
        """
        filtered_models = []
        
        for model in models:
            license_info = self.extract_license_info(model)
            
            if filter_config.matches_license(license_info):
                # Add license compliance metadata
                model['license_compliance'] = license_info.to_dict()['compliance_flags']
                model['license_compliance']['filter_applied'] = True
                model['license_compliance']['filtered_at'] = time.time()
                
                filtered_models.append(model)
            else:
                logger.debug(f"Model {model.get('id')} filtered out by license criteria")
        
        logger.info(
            f"License filtering: {len(filtered_models)}/{len(models)} models "
            f"passed filter criteria"
        )
        return filtered_models
    
    def get_license_summary(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate license compliance summary for export per requirement 9.5.
        
        Args:
            models: List of models with license information
            
        Returns:
            Comprehensive license summary
        """
        license_stats = {
            'total_models': len(models),
            'commercial_safe': 0,
            'requires_attribution': 0,
            'allows_derivatives': 0,
            'restrictive_licenses': 0,
            'unknown_licenses': 0,
            'license_types': {},
            'compliance_warnings': len(self.compliance_warnings)
        }
        
        for model in models:
            license_info = self.extract_license_info(model)
            
            if license_info.is_commercial_safe():
                license_stats['commercial_safe'] += 1
                
            if license_info.requires_attribution():
                license_stats['requires_attribution'] += 1
                
            if license_info.allows_derivatives():
                license_stats['allows_derivatives'] += 1
            
            # Count restrictive licenses
            restrictive_fields = [
                license_info.allow_commercial_use == LicenseStatus.DISALLOWED,
                license_info.allow_derivatives == LicenseStatus.DISALLOWED
            ]
            if any(restrictive_fields):
                license_stats['restrictive_licenses'] += 1
            
            # Count unknown licenses
            unknown_fields = [
                license_info.allow_commercial_use == LicenseStatus.UNKNOWN,
                license_info.allow_derivatives == LicenseStatus.UNKNOWN,
                license_info.allow_different_license == LicenseStatus.UNKNOWN,
                license_info.allow_no_credit == LicenseStatus.UNKNOWN
            ]
            if any(unknown_fields):
                license_stats['unknown_licenses'] += 1
            
            # Track license types
            license_name = license_info.license_name or "Unknown"
            if license_name not in license_stats['license_types']:
                license_stats['license_types'][license_name] = 0
            license_stats['license_types'][license_name] += 1
        
        # Calculate percentages
        total = license_stats['total_models']
        if total > 0:
            license_stats['commercial_safe_percent'] = round(
                license_stats['commercial_safe'] / total * 100, 1
            )
            license_stats['attribution_required_percent'] = round(
                license_stats['requires_attribution'] / total * 100, 1
            )
            license_stats['derivatives_allowed_percent'] = round(
                license_stats['allows_derivatives'] / total * 100, 1
            )
        
        return license_stats
    
    def format_license_display(self, license_info: LicenseInfo, 
                              format_type: str = "table") -> str:
        """
        Format license information for display per requirement 9.5.
        
        Args:
            license_info: License information to format
            format_type: Display format ("table", "compact", "detailed")
            
        Returns:
            Formatted license information string
        """
        if format_type == "compact":
            flags = []
            if license_info.is_commercial_safe():
                flags.append("✅ Commercial")
            else:
                flags.append("❌ Commercial")
                
            if license_info.allows_derivatives():
                flags.append("✅ Derivatives")
            else:
                flags.append("❌ Derivatives")
                
            if not license_info.requires_attribution():
                flags.append("✅ No Credit Required")
            else:
                flags.append("⚠️  Attribution Required")
                
            return " | ".join(flags)
        
        elif format_type == "detailed":
            details = []
            details.append(f"License: {license_info.license_name or 'Unknown'}")
            
            if license_info.license_description:
                details.append(f"Description: {license_info.license_description}")
            
            details.append("Permissions:")
            details.append(f"  Commercial Use: {license_info.allow_commercial_use.value}")
            details.append(f"  Derivatives: {license_info.allow_derivatives.value}")
            details.append(f"  Different License: {license_info.allow_different_license.value}")
            details.append(f"  No Credit Required: {license_info.allow_no_credit.value}")
            
            if license_info.license_url:
                details.append(f"License URL: {license_info.license_url}")
            
            return "\n".join(details)
        
        else:  # table format
            table = "License Information:\n"
            table += "-" * 30 + "\n"
            table += f"Commercial Use:     {license_info.allow_commercial_use.value}\n"
            table += f"Derivatives:        {license_info.allow_derivatives.value}\n"
            table += f"Different License:  {license_info.allow_different_license.value}\n"
            table += f"No Credit Required: {license_info.allow_no_credit.value}\n"
            
            if license_info.license_name:
                table += f"License Name:       {license_info.license_name}\n"
                
            return table
    
    def export_compliance_report(self) -> Dict[str, Any]:
        """
        Export comprehensive compliance report.
        
        Returns:
            Complete compliance report for audit purposes
        """
        return {
            'report_metadata': {
                'generated_at': time.time(),
                'total_models_processed': len(self.license_cache),
                'compliance_warnings_count': len(self.compliance_warnings)
            },
            'license_cache': {
                str(model_id): license_info.to_dict() 
                for model_id, license_info in self.license_cache.items()
            },
            'compliance_warnings': self.compliance_warnings,
            'summary': self.get_license_summary(
                [{'id': k, **v.to_dict()['license_fields']} 
                 for k, v in self.license_cache.items()]
            )
        }