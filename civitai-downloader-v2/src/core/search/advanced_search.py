#!/usr/bin/env python3
"""
Advanced Search Parameters System.
Implements requirements 10-12: Advanced filtering, categories, and unofficial API management.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
try:
    import dateutil.parser
except ImportError:
    # Fallback if dateutil is not available
    dateutil = None
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import re

logger = logging.getLogger(__name__)


class NSFWFilter(Enum):
    """NSFW content filtering options per requirement 10.3."""
    INCLUDE_ALL = "all"
    SFW_ONLY = "false"
    NSFW_ONLY = "true"
    MATURE = "mature"


class NSFWLevel(Enum):
    """Detailed NSFW level filtering per user feedback (Phase C-3)."""
    SFW = "sfw"           # Safe for work content only
    NSFW = "nsfw"         # Include NSFW content
    ALL = "all"           # Include all content regardless of NSFW status


class ModelQuality(Enum):
    """Model quality filters per requirement 10.4."""
    ALL = "all"
    VERIFIED = "verified"
    FEATURED = "featured"
    VERIFIED_AND_FEATURED = "verified_featured"


class CommercialUse(Enum):
    """Commercial use filtering per requirement 10.5 and pre-investigation findings."""
    ALL = "all"
    # Commercial use levels as array per pre-investigation: Image, Rent, RentCivit, Sell
    IMAGE_ALLOWED = "Image"  # Generated images commercial use
    RENT_ALLOWED = "Rent"    # Model rental allowed
    RENTCIVIT_ALLOWED = "RentCivit"  # CivitAI rental allowed
    SELL_ALLOWED = "Sell"    # Model selling allowed
    NON_COMMERCIAL_ONLY = "non_commercial"


class FileFormat(Enum):
    """File format preferences per requirement 10.6."""
    SAFETENSORS_ONLY = "safetensors"
    PICKLE_ALLOWED = "pickle"
    ALL_FORMATS = "all"


class ModelCategory(Enum):
    """Model categories per requirement 11.1 (15 categories)."""
    CHARACTER = "character"
    STYLE = "style"
    CONCEPT = "concept"
    BACKGROUND = "background"
    POSES = "poses"
    VEHICLE = "vehicle"
    CLOTHING = "clothing"
    ACTION = "action"
    ANIMAL = "animal"
    ASSETS = "assets"
    BASE_MODEL = "base model"
    BUILDINGS = "buildings"
    CELEBRITY = "celebrity"
    OBJECTS = "objects"
    TOOL = "tool"


class SortOption(Enum):
    """Official sort options."""
    HIGHEST_RATED = "Highest Rated"
    MOST_DOWNLOADED = "Most Downloaded"
    NEWEST = "Newest"
    OLDEST = "Oldest"
    MOST_LIKED = "Most Liked"
    MOST_DISCUSSED = "Most Discussed"
    MOST_COLLECTED = "Most Collected"
    MOST_IMAGES = "Most Images"


class CustomSortMetric(Enum):
    """Custom sort metrics per requirement 11.3."""
    TIPPED_AMOUNT = "metrics.tippedAmountCount:desc"
    COMMENT_COUNT = "metrics.commentCount:desc"
    FAVORITE_COUNT = "metrics.favoriteCount:desc"
    RATING_COUNT = "metrics.ratingCount:desc"
    DOWNLOAD_COUNT = "stats.downloadCount:desc"
    GENERATION_COUNT = "stats.generationCount:desc"


class SortByField(Enum):
    """Advanced sortBy fields per pre-investigation findings."""
    # Metrics fields
    TIPPED_AMOUNT = "metrics.tippedAmountCount"
    COMMENT_COUNT = "metrics.commentCount"
    FAVORITE_COUNT = "metrics.favoriteCount"
    RATING_COUNT = "metrics.ratingCount"
    THUMBS_UP_COUNT = "metrics.thumbsUpCount"
    
    # Stats fields  
    DOWNLOAD_COUNT = "stats.downloadCount"
    GENERATION_COUNT = "stats.generationCount"
    
    # Model fields
    PUBLISHED_AT = "publishedAt"
    UPDATED_AT = "updatedAt"


class SortDirection(Enum):
    """Sort direction for sortBy parameter."""
    DESC = "desc"
    ASC = "asc"


class RiskLevel(Enum):
    """API feature risk levels per requirement 12.2."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DateRange:
    """Date range filtering per requirement 10.2."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def to_api_params(self) -> Dict[str, str]:
        """Convert to API parameters."""
        params = {}
        if self.start_date:
            params['period'] = 'AllTime'  # Custom date ranges use AllTime
            # Convert to ISO format for API
            params['periodStartDate'] = self.start_date.isoformat()
        if self.end_date:
            params['periodEndDate'] = self.end_date.isoformat()
        return params
    
    def validate(self) -> List[str]:
        """Validate date range."""
        errors = []
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                errors.append("Start date must be before end date")
            if self.start_date > datetime.now():
                errors.append("Start date cannot be in the future")
        return errors


class DateFilterType(Enum):
    """Type of date filtering per Phase B-1."""
    PUBLISHED = "published"
    UPDATED = "updated"


@dataclass
class FlexibleDateRange:
    """
    Flexible date range filtering for Phase B-1.
    Supports both published and updated date filtering with multiple input formats.
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    filter_type: DateFilterType = DateFilterType.PUBLISHED
    
    def __post_init__(self):
        """Validate dates after initialization."""
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("Start date must be before end date")
    
    @classmethod
    def from_string_dates(cls, start_str: Optional[str] = None, end_str: Optional[str] = None, 
                         filter_type: DateFilterType = DateFilterType.PUBLISHED) -> 'FlexibleDateRange':
        """
        Create FlexibleDateRange from string dates.
        
        Supports formats:
        - ISO dates: "2024-07-18", "2024-07-18T12:00:00"
        - Relative periods: "30days", "3months", "1year"
        """
        start_date = None
        end_date = None
        
        if start_str:
            start_date = cls._parse_date_string(start_str)
        
        if end_str:
            end_date = cls._parse_date_string(end_str)
            
        return cls(start_date=start_date, end_date=end_date, filter_type=filter_type)
    
    @classmethod
    def from_relative_period(cls, period_str: str, filter_type: DateFilterType = DateFilterType.PUBLISHED) -> 'FlexibleDateRange':
        """
        Create date range from relative period like "30days", "3months", "1year".
        """
        now = datetime.now()
        
        # Parse relative period
        if period_str.endswith('days'):
            days = int(period_str[:-4])
            start_date = now - timedelta(days=days)
        elif period_str.endswith('months'):
            months = int(period_str[:-6])
            start_date = now - timedelta(days=months * 30)  # Approximate
        elif period_str.endswith('year') or period_str.endswith('years'):
            years = int(period_str.rstrip('syear'))
            start_date = now - timedelta(days=years * 365)  # Approximate
        else:
            raise ValueError(f"Unsupported period format: {period_str}")
            
        return cls(start_date=start_date, end_date=now, filter_type=filter_type)
    
    @staticmethod
    def _parse_date_string(date_str: str) -> datetime:
        """Parse various date string formats."""
        # Try with dateutil if available
        if dateutil:
            try:
                return dateutil.parser.parse(date_str)
            except Exception:
                pass
        
        # Fallback to common formats
        formats = [
            '%Y-%m-%d',           # 2024-07-18
            '%Y-%m-%dT%H:%M:%S',  # 2024-07-18T12:00:00
            '%Y-%m-%d %H:%M:%S',  # 2024-07-18 12:00:00
            '%Y/%m/%d',           # 2024/07/18
            '%m/%d/%Y',           # 07/18/2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        raise ValueError(f"Unable to parse date: {date_str}")
    
    def to_api_params(self) -> Dict[str, str]:
        """Convert to CivitAI API parameters."""
        params = {}
        
        if self.start_date or self.end_date:
            # Use AllTime period for custom date ranges
            params['period'] = 'AllTime'
            
            if self.start_date:
                params['periodStartDate'] = self.start_date.isoformat()
            
            if self.end_date:
                params['periodEndDate'] = self.end_date.isoformat()
        
        return params
    
    def validate(self) -> List[str]:
        """Validate date range."""
        errors = []
        
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                errors.append("Start date must be before end date")
        
        if self.start_date and self.start_date > datetime.now():
            errors.append("Start date cannot be in the future")
            
        if self.end_date and self.end_date > datetime.now():
            errors.append("End date cannot be in the future")
            
        return errors


@dataclass  
class RatingFilter:
    """
    Rating/Likes filtering system for Phase B-2.
    Based on thumbsUpCount since traditional rating system is discontinued.
    """
    min_thumbs_up: Optional[int] = None
    max_thumbs_up: Optional[int] = None
    min_thumbs_down: Optional[int] = None
    max_thumbs_down: Optional[int] = None
    min_like_ratio: Optional[float] = None  # thumbsUp / (thumbsUp + thumbsDown)
    max_like_ratio: Optional[float] = None
    min_total_interactions: Optional[int] = None  # thumbsUp + thumbsDown
    
    def __post_init__(self):
        """Validate rating filter values."""
        if self.min_like_ratio is not None:
            if not 0.0 <= self.min_like_ratio <= 1.0:
                raise ValueError("min_like_ratio must be between 0.0 and 1.0")
        if self.max_like_ratio is not None:
            if not 0.0 <= self.max_like_ratio <= 1.0:
                raise ValueError("max_like_ratio must be between 0.0 and 1.0")
        if self.min_like_ratio is not None and self.max_like_ratio is not None:
            if self.min_like_ratio > self.max_like_ratio:
                raise ValueError("min_like_ratio must be <= max_like_ratio")
    
    def matches_model(self, model_data: Dict[str, Any]) -> bool:
        """Check if model matches rating filter criteria."""
        stats = model_data.get('stats', {})
        thumbs_up = stats.get('thumbsUpCount', 0)
        thumbs_down = stats.get('thumbsDownCount', 0)
        total_interactions = thumbs_up + thumbs_down
        
        # Check thumbs up range
        if self.min_thumbs_up is not None and thumbs_up < self.min_thumbs_up:
            return False
        if self.max_thumbs_up is not None and thumbs_up > self.max_thumbs_up:
            return False
            
        # Check thumbs down range
        if self.min_thumbs_down is not None and thumbs_down < self.min_thumbs_down:
            return False
        if self.max_thumbs_down is not None and thumbs_down > self.max_thumbs_down:
            return False
            
        # Check total interactions
        if self.min_total_interactions is not None and total_interactions < self.min_total_interactions:
            return False
            
        # Check like ratio
        if total_interactions > 0:
            like_ratio = thumbs_up / total_interactions
            if self.min_like_ratio is not None and like_ratio < self.min_like_ratio:
                return False
            if self.max_like_ratio is not None and like_ratio > self.max_like_ratio:
                return False
        elif self.min_like_ratio is not None and self.min_like_ratio > 0:
            # If no interactions but minimum ratio required, exclude
            return False
            
        return True
    
    def to_api_params(self) -> Dict[str, Any]:
        """
        Convert to API parameters. 
        Note: CivitAI API doesn't support thumbs filtering directly,
        so this is primarily for post-processing filtering.
        """
        params = {}
        # API doesn't support thumbs filtering, but we can use sort by likes
        if self.min_thumbs_up is not None and self.min_thumbs_up > 0:
            # Suggest using "Most Liked" sort for better results
            params['_suggested_sort'] = 'Most Liked'
        return params
    
    def validate(self) -> List[str]:
        """Validate rating filter parameters."""
        errors = []
        
        if self.min_thumbs_up is not None and self.min_thumbs_up < 0:
            errors.append("min_thumbs_up must be non-negative")
        if self.max_thumbs_up is not None and self.max_thumbs_up < 0:
            errors.append("max_thumbs_up must be non-negative")
        if self.min_thumbs_down is not None and self.min_thumbs_down < 0:
            errors.append("min_thumbs_down must be non-negative")
        if self.max_thumbs_down is not None and self.max_thumbs_down < 0:
            errors.append("max_thumbs_down must be non-negative")
        if self.min_total_interactions is not None and self.min_total_interactions < 0:
            errors.append("min_total_interactions must be non-negative")
            
        if (self.min_thumbs_up is not None and self.max_thumbs_up is not None 
            and self.min_thumbs_up > self.max_thumbs_up):
            errors.append("min_thumbs_up must be <= max_thumbs_up")
        if (self.min_thumbs_down is not None and self.max_thumbs_down is not None 
            and self.min_thumbs_down > self.max_thumbs_down):
            errors.append("min_thumbs_down must be <= max_thumbs_down")
            
        return errors


@dataclass
class DownloadRange:
    """Download count range per requirement 10.1."""
    min_downloads: Optional[int] = None
    max_downloads: Optional[int] = None
    
    def to_filter(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply download range filter."""
        if not self.min_downloads and not self.max_downloads:
            return models
        
        filtered = []
        for model in models:
            download_count = model.get('stats', {}).get('downloadCount', 0)
            
            if self.min_downloads and download_count < self.min_downloads:
                continue
            if self.max_downloads and download_count > self.max_downloads:
                continue
                
            filtered.append(model)
        
        return filtered
    
    def validate(self) -> List[str]:
        """Validate download range."""
        errors = []
        if self.min_downloads is not None and self.min_downloads < 0:
            errors.append("Minimum downloads must be non-negative")
        if self.max_downloads is not None and self.max_downloads < 0:
            errors.append("Maximum downloads must be non-negative")
        if (self.min_downloads is not None and self.max_downloads is not None 
            and self.min_downloads > self.max_downloads):
            errors.append("Minimum downloads must be less than maximum downloads")
        return errors


@dataclass
class AdvancedSearchParams:
    """
    Advanced search parameters implementing requirements 10-11.
    Comprehensive filtering and sorting capabilities.
    """
    # Basic search parameters
    query: Optional[str] = None
    username: Optional[str] = None
    model_types: Optional[List[str]] = None
    
    # Advanced filtering (Requirement 10)
    download_range: Optional[DownloadRange] = None
    date_range: Optional[DateRange] = None
    
    # Phase B-1: Flexible date filtering
    published_date_range: Optional[FlexibleDateRange] = None
    updated_date_range: Optional[FlexibleDateRange] = None
    
    # Phase B-2: Rating/Likes filtering
    rating_filter: Optional[RatingFilter] = None
    
    nsfw_filter: NSFWFilter = NSFWFilter.INCLUDE_ALL
    nsfw_level: Optional[NSFWLevel] = None  # Phase C-3: NSFW level filtering
    quality_filter: ModelQuality = ModelQuality.ALL
    commercial_filter: CommercialUse = CommercialUse.ALL
    file_format: FileFormat = FileFormat.SAFETENSORS_ONLY
    
    # Category and tag filtering (Requirement 11)
    categories: Optional[List[ModelCategory]] = None
    tags: Optional[List[str]] = None
    base_model: Optional[str] = None
    
    # Sorting (Requirement 11.3)
    sort_option: Optional[SortOption] = None
    custom_sort: Optional[CustomSortMetric] = None
    sort_fallback: bool = True
    
    # Advanced sortBy system (Phase A-3)
    sort_by_field: Optional[SortByField] = None
    sort_by_direction: SortDirection = SortDirection.DESC
    
    # Search parameters
    limit: int = 100
    page: int = 1
    cursor: Optional[str] = None
    
    def __post_init__(self):
        """Validate parameters after initialization."""
        if self.categories is None:
            self.categories = []
        if self.tags is None:
            self.tags = []
        if self.model_types is None:
            self.model_types = []
    
    def validate(self) -> List[str]:
        """Validate all search parameters."""
        errors = []
        
        # Validate ranges
        if self.download_range:
            errors.extend(self.download_range.validate())
        
        if self.date_range:
            errors.extend(self.date_range.validate())
        
        # Phase B-1: Validate date filtering
        if self.published_date_range:
            errors.extend(self.published_date_range.validate())
        if self.updated_date_range:
            errors.extend(self.updated_date_range.validate())
        
        # Phase B-2: Validate rating filtering
        if self.rating_filter:
            errors.extend(self.rating_filter.validate())
        
        # Validate limits
        if self.limit <= 0:
            errors.append("Limit must be positive")
        if self.limit > 200:  # API limit per requirement 13.3
            errors.append("Limit cannot exceed 200")
        
        if self.page <= 0:
            errors.append("Page must be positive")
        
        return errors
    
    def to_api_params(self) -> Dict[str, Any]:
        """Convert to CivitAI API parameters."""
        params = {}
        
        # Basic parameters - FIXED: Keep query and tags separate per pre-investigation
        if self.query and self.query.strip():  # Only add query if not empty
            # Query should remain as query parameter, not converted to tags
            # This allows proper distinction between search queries and tag filtering
            params['query'] = self.query.strip()
        if self.username:
            params['username'] = self.username
        if self.model_types:
            # CivitAI API expects types as array
            params['types'] = self.model_types if isinstance(self.model_types, list) else [self.model_types]
        
        # Pagination - FIXED: Cannot use page with query parameter
        params['limit'] = min(self.limit, 200)  # Enforce API limit
        if self.cursor:
            params['cursor'] = self.cursor
        elif not self.query:  # Only use page if no query parameter
            params['page'] = self.page
        
        # Date range
        if self.date_range:
            params.update(self.date_range.to_api_params())
        
        # Phase B-1: Flexible date filtering (prioritize over legacy date_range)
        if self.published_date_range:
            params.update(self.published_date_range.to_api_params())
        elif self.updated_date_range:
            # Note: CivitAI API currently only supports published date filtering
            # Updated date filtering would require additional API support
            params.update(self.updated_date_range.to_api_params())
        
        # NSFW filtering - prioritize nsfw_level over nsfw_filter
        if self.nsfw_level:
            if self.nsfw_level == NSFWLevel.SFW:
                params['nsfw'] = 'false'
            elif self.nsfw_level == NSFWLevel.NSFW:
                params['nsfw'] = 'true'
            elif self.nsfw_level == NSFWLevel.ALL:
                # Don't include nsfw parameter to include both SFW and NSFW
                pass  # Don't set nsfw parameter
        elif self.nsfw_filter != NSFWFilter.INCLUDE_ALL:
            params['nsfw'] = self.nsfw_filter.value
        
        # Quality filters
        if self.quality_filter == ModelQuality.VERIFIED:
            params['verified'] = True
        elif self.quality_filter == ModelQuality.FEATURED:
            params['featured'] = True
        elif self.quality_filter == ModelQuality.VERIFIED_AND_FEATURED:
            params['verified'] = True
            params['featured'] = True
        
        # Commercial use - CRITICAL FIX: Handle as array per pre-investigation findings
        if self.commercial_filter and self.commercial_filter != CommercialUse.ALL:
            if self.commercial_filter == CommercialUse.NON_COMMERCIAL_ONLY:
                # For non-commercial only, exclude all commercial use types
                params['allowCommercialUse'] = []
            elif self.commercial_filter in [CommercialUse.IMAGE_ALLOWED, 
                                           CommercialUse.RENT_ALLOWED,
                                           CommercialUse.RENTCIVIT_ALLOWED, 
                                           CommercialUse.SELL_ALLOWED]:
                # For specific commercial use level, filter by that level
                params['allowCommercialUse'] = [self.commercial_filter.value]
            # Note: For ALL, we don't add the parameter to include all commercial use levels
        
        # Tags - CivitAI API expects tags as array
        if self.tags:
            params['tags'] = self.tags if isinstance(self.tags, list) else [self.tags]
        
        # Categories - FIXED: Proper category parameter handling per pre-investigation  
        if self.categories:
            # Categories are separate from tags and use 'category' parameter
            # Format: single category or comma-separated multiple categories
            params['category'] = ','.join([cat.value for cat in self.categories]) if len(self.categories) > 1 else self.categories[0].value
        
        # Base model
        if self.base_model:
            params['baseModels'] = [self.base_model]
        
        # Sorting - Phase A-3: Support advanced sortBy parameter
        if self.sort_by_field:
            # Advanced sortBy format: models_v9:field:direction
            params['sortBy'] = f"models_v9:{self.sort_by_field.value}:{self.sort_by_direction.value}"
        elif self.custom_sort:
            params['sort'] = self.custom_sort.value
        elif self.sort_option:
            params['sort'] = self.sort_option.value
        
        return params


@dataclass
class APIFeature:
    """API feature configuration per requirement 12."""
    name: str
    official: bool
    risk_level: RiskLevel
    enabled: bool = False
    success_rate: float = 0.0
    usage_count: int = 0
    error_count: int = 0
    last_used: Optional[float] = None
    description: str = ""
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        total = self.usage_count + self.error_count
        if total == 0:
            return 0.0
        return self.usage_count / total
    
    def should_retry(self) -> bool:
        """Determine if feature should be retried based on success rate."""
        success_rate = self.get_success_rate()
        total_attempts = self.usage_count + self.error_count
        
        # Don't retry high-risk features with low success rates
        if self.risk_level == RiskLevel.HIGH and success_rate < 0.5 and total_attempts >= 5:
            return False
        
        # Don't retry critical risk features with any failures
        if self.risk_level == RiskLevel.CRITICAL and self.error_count > 0:
            return False
        
        return True


class BaseModelDetector:
    """
    Base model detection system per requirement 11.6.
    Supports 50+ base models with dynamic detection.
    """
    
    def __init__(self):
        """Initialize base model detector."""
        self.known_models = self._initialize_known_models()
        self.detected_models: Set[str] = set()
        self.model_patterns = self._compile_patterns()
    
    def _initialize_known_models(self) -> Set[str]:
        """Initialize known base models per requirement 11.6."""
        return {
            # Popular models explicitly mentioned
            "Illustrious", "NoobAI", "Pony", "SDXL 1.0", "SDXL 1.0 Base",
            
            # Stable Diffusion variants
            "SD 1.4", "SD 1.5", "SD 2.0", "SD 2.1", "SD XL", "SDXL",
            "SDXL Base", "SDXL Refiner", "SDXL Turbo", "SD3", "SD3 Medium",
            
            # NoobAI variants
            "NoobAI XL", "NoobAI v1.0", "NoobAI-XL", "Noob SDXL",
            
            # Pony variants
            "Pony Diffusion", "Pony XL", "PonyDiffusion", "Pony v6",
            
            # Anime/Asian models
            "AnimeLibertai", "Waifu Diffusion", "AnythingV3", "AnythingV4", "AnythingV5",
            "CounterfeitV2.5", "AbyssOrangeMix", "PastelMix", "MeinaV11",
            
            # Realistic models
            "ChilloutMix", "Realistic Vision", "DreamShaper", "epiCRealism",
            "Photorealistic", "juggernautXL", "RealityCheckXL",
            
            # Art styles
            "OpenJourney", "Midjourney", "DiscoDiffusion", "VanGogh", "Arcane",
            
            # Technical variants
            "ControlNet", "IP-Adapter", "LCM", "Turbo", "Lightning",
            
            # Community models
            "CivitAI", "RunwayML", "CompVis", "Stability", "HuggingFace"
        }
    
    def _compile_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for model detection."""
        patterns = [
            re.compile(r'SD\s*(?:XL|3|2\.1|2\.0|1\.5|1\.4)', re.IGNORECASE),
            re.compile(r'Stable\s+Diffusion\s+(?:XL|3|2\.1|2\.0|1\.5|1\.4)', re.IGNORECASE),
            re.compile(r'NoobAI(?:\s*XL|v[\d\.]+)?', re.IGNORECASE),
            re.compile(r'Pony(?:\s*Diffusion|\s*XL|v\d+)?', re.IGNORECASE),
            re.compile(r'Illustrious(?:\s*XL)?', re.IGNORECASE),
            re.compile(r'Anime(?:Liberty|[\w\s]*)', re.IGNORECASE),
            re.compile(r'Realistic(?:\s*Vision)?', re.IGNORECASE),
            re.compile(r'Dream(?:\s*Shaper)?', re.IGNORECASE),
        ]
        return patterns
    
    def detect_base_model(self, model_data: Dict[str, Any]) -> Optional[str]:
        """
        Detect base model from model data per requirement 11.6.
        
        Args:
            model_data: Model information from API
            
        Returns:
            Detected base model name or None
        """
        # Check explicit base model field
        if 'baseModel' in model_data:
            return model_data['baseModel']
        
        # Search in model name
        model_name = model_data.get('name', '')
        detected = self._search_for_base_model(model_name)
        if detected:
            return detected
        
        # Search in description
        description = model_data.get('description', '')
        detected = self._search_for_base_model(description)
        if detected:
            return detected
        
        # Search in tags
        tags = model_data.get('tags', [])
        for tag in tags:
            tag_name = tag.get('name', '') if isinstance(tag, dict) else str(tag)
            detected = self._search_for_base_model(tag_name)
            if detected:
                return detected
        
        # Search in versions
        versions = model_data.get('modelVersions', [])
        for version in versions:
            version_name = version.get('name', '')
            detected = self._search_for_base_model(version_name)
            if detected:
                return detected
            
            # Check version description
            version_desc = version.get('description', '')
            detected = self._search_for_base_model(version_desc)
            if detected:
                return detected
        
        return None
    
    def _search_for_base_model(self, text: str) -> Optional[str]:
        """Search for base model in text."""
        if not text:
            return None
        
        # Check known models first
        text_lower = text.lower()
        for model in self.known_models:
            if model.lower() in text_lower:
                self.detected_models.add(model)
                return model
        
        # Check patterns
        for pattern in self.model_patterns:
            match = pattern.search(text)
            if match:
                detected_model = match.group(0)
                self.detected_models.add(detected_model)
                return detected_model
        
        return None
    
    def get_all_detected_models(self) -> List[str]:
        """Get all detected models."""
        return sorted(list(self.known_models.union(self.detected_models)))


class UnofficialAPIManager:
    """
    Unofficial API feature management per requirement 12.
    Handles risk assessment, feature detection, and fallback mechanisms.
    """
    
    def __init__(self):
        """Initialize unofficial API manager."""
        self.features: Dict[str, APIFeature] = self._initialize_features()
        self.usage_stats: Dict[str, Dict[str, int]] = {
            'official': {'success': 0, 'failure': 0},
            'unofficial': {'success': 0, 'failure': 0}
        }
        self.feature_detection_enabled = True
        self.official_priority_mode = True
    
    def _initialize_features(self) -> Dict[str, APIFeature]:
        """Initialize API features per requirement 12.1."""
        return {
            # Official features (low risk)
            'basic_search': APIFeature(
                name='basic_search',
                official=True,
                risk_level=RiskLevel.LOW,
                enabled=True,
                description='Basic model search functionality'
            ),
            'pagination': APIFeature(
                name='pagination',
                official=True,
                risk_level=RiskLevel.LOW,
                enabled=True,
                description='Standard pagination support'
            ),
            'model_details': APIFeature(
                name='model_details',
                official=True,
                risk_level=RiskLevel.LOW,
                enabled=True,
                description='Model detail retrieval'
            ),
            
            # Semi-official features (medium risk)
            'advanced_sorting': APIFeature(
                name='advanced_sorting',
                official=False,
                risk_level=RiskLevel.MEDIUM,
                enabled=False,
                description='Advanced sorting by metrics'
            ),
            'custom_date_ranges': APIFeature(
                name='custom_date_ranges',
                official=False,
                risk_level=RiskLevel.MEDIUM,
                enabled=False,
                description='Custom date range filtering'
            ),
            'bulk_operations': APIFeature(
                name='bulk_operations',
                official=False,
                risk_level=RiskLevel.HIGH,
                enabled=False,
                description='Bulk API operations (not recommended)'
            ),
            
            # Experimental features (high risk)
            'undocumented_endpoints': APIFeature(
                name='undocumented_endpoints',
                official=False,
                risk_level=RiskLevel.HIGH,
                enabled=False,
                description='Undocumented API endpoints'
            ),
            'rate_limit_bypass': APIFeature(
                name='rate_limit_bypass',
                official=False,
                risk_level=RiskLevel.CRITICAL,
                enabled=False,
                description='Rate limit bypass techniques (dangerous)'
            )
        }
    
    def enable_feature(self, feature_name: str, force: bool = False) -> bool:
        """
        Enable API feature per requirement 12.1.
        
        Args:
            feature_name: Name of feature to enable
            force: Force enable even high-risk features
            
        Returns:
            True if feature was enabled
        """
        if feature_name not in self.features:
            logger.warning(f"Unknown API feature: {feature_name}")
            return False
        
        feature = self.features[feature_name]
        
        # Check risk level and official priority mode
        if self.official_priority_mode and not feature.official:
            logger.info(f"Feature {feature_name} disabled due to official priority mode")
            return False
        
        if not force and feature.risk_level == RiskLevel.CRITICAL:
            logger.warning(f"Critical risk feature {feature_name} requires force enable")
            return False
        
        if not force and feature.risk_level == RiskLevel.HIGH and not feature.should_retry():
            logger.warning(f"High risk feature {feature_name} has poor success rate")
            return False
        
        feature.enabled = True
        logger.info(f"Enabled API feature: {feature_name} (risk: {feature.risk_level.value})")
        return True
    
    def record_feature_usage(self, feature_name: str, success: bool, 
                           response_time: Optional[float] = None) -> None:
        """Record feature usage statistics."""
        if feature_name not in self.features:
            return
        
        feature = self.features[feature_name]
        feature.last_used = time.time()
        
        if success:
            feature.usage_count += 1
            category = 'official' if feature.official else 'unofficial'
            self.usage_stats[category]['success'] += 1
        else:
            feature.error_count += 1
            category = 'official' if feature.official else 'unofficial'
            self.usage_stats[category]['failure'] += 1
        
        # Auto-disable if too many failures
        if feature.get_success_rate() < 0.3 and feature.error_count > 5:
            if feature.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                feature.enabled = False
                logger.warning(f"Auto-disabled feature {feature_name} due to high failure rate")
    
    def get_fallback_strategy(self, failed_feature: str) -> List[str]:
        """
        Get fallback strategy per requirement 12.4.
        Implements gradual degradation: extended -> official -> basic
        """
        fallback_chains = {
            'advanced_sorting': ['basic_sorting', 'no_sorting'],
            'custom_date_ranges': ['period_filtering', 'no_date_filter'],
            'bulk_operations': ['batch_processing', 'individual_requests'],
            'undocumented_endpoints': ['official_endpoints'],
            'rate_limit_bypass': []  # No fallback for critical features
        }
        
        return fallback_chains.get(failed_feature, ['basic_search'])
    
    def detect_api_capabilities(self, api_response: Dict[str, Any]) -> Set[str]:
        """
        Detect available API capabilities per requirement 12.3.
        
        Args:
            api_response: Sample API response to analyze
            
        Returns:
            Set of detected capabilities
        """
        if not self.feature_detection_enabled:
            return set()
        
        detected = set()
        
        # Analyze response structure
        if 'metadata' in api_response:
            detected.add('metadata_support')
        
        if 'totalPages' in api_response:
            detected.add('pagination_metadata')
        
        if 'nextCursor' in api_response:
            detected.add('cursor_pagination')
        
        # Check for model data fields
        items = api_response.get('items', [])
        if items:
            model = items[0]
            
            if 'stats' in model and 'metrics' in model:
                detected.add('detailed_statistics')
            
            if 'allowCommercialUse' in model:
                detected.add('license_filtering')
            
            if 'nsfw' in model:
                detected.add('nsfw_classification')
            
            if 'tags' in model and isinstance(model['tags'], list):
                detected.add('tag_system')
        
        # Update feature availability
        for capability in detected:
            if capability in self.features:
                self.features[capability].enabled = True
        
        logger.info(f"Detected API capabilities: {detected}")
        return detected
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics per requirement 12.6."""
        total_official = (self.usage_stats['official']['success'] + 
                         self.usage_stats['official']['failure'])
        total_unofficial = (self.usage_stats['unofficial']['success'] + 
                           self.usage_stats['unofficial']['failure'])
        
        feature_stats = {}
        for name, feature in self.features.items():
            total_uses = feature.usage_count + feature.error_count
            feature_stats[name] = {
                'enabled': feature.enabled,
                'official': feature.official,
                'risk_level': feature.risk_level.value,
                'usage_count': feature.usage_count,
                'error_count': feature.error_count,
                'success_rate': feature.get_success_rate(),
                'total_uses': total_uses,
                'last_used': feature.last_used
            }
        
        return {
            'official_features': {
                'success_count': self.usage_stats['official']['success'],
                'failure_count': self.usage_stats['official']['failure'],
                'success_rate': (self.usage_stats['official']['success'] / total_official 
                               if total_official > 0 else 0)
            },
            'unofficial_features': {
                'success_count': self.usage_stats['unofficial']['success'],
                'failure_count': self.usage_stats['unofficial']['failure'],
                'success_rate': (self.usage_stats['unofficial']['success'] / total_unofficial 
                               if total_unofficial > 0 else 0)
            },
            'feature_details': feature_stats,
            'configuration': {
                'official_priority_mode': self.official_priority_mode,
                'feature_detection_enabled': self.feature_detection_enabled
            }
        }