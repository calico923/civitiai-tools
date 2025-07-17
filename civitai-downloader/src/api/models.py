"""Data models for CivitAI API responses."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class SearchQuery:
    """Model search query parameters."""
    query: Optional[str] = None
    model_types: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    base_model: Optional[str] = None
    username: Optional[str] = None
    sort_order: str = "Highest Rated"
    nsfw: Optional[bool] = None
    limit: int = 20
    page: int = 1
    cursor: Optional[str] = None


@dataclass
class ModelStats:
    """Model statistics."""
    download_count: int = 0
    favorite_count: int = 0
    comment_count: int = 0
    rating_count: int = 0
    rating: float = 0.0


@dataclass
class ImageData:
    """Model image information."""
    id: str
    url: str
    width: int = 0
    height: int = 0
    hash: Optional[str] = None
    nsfw: bool = False
    meta: Optional[Dict[str, Any]] = None


@dataclass
class FileInfo:
    """Model file information."""
    id: str
    name: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    hashes: Dict[str, str] = field(default_factory=dict)
    download_url: str = ""
    size_kb: Optional[int] = None
    format: Optional[str] = None
    fp: Optional[str] = None
    size: Optional[str] = None


@dataclass
class VersionSummary:
    """Model version summary."""
    id: str
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trained_words: List[str] = field(default_factory=list)
    base_model: Optional[str] = None
    files: List[FileInfo] = field(default_factory=list)


@dataclass
class ModelSummary:
    """Model summary for search results."""
    id: str
    name: str
    type: str
    description: Optional[str] = None
    creator: Optional[str] = None
    stats: Optional[ModelStats] = None
    thumbnail_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    nsfw: bool = False
    allow_no_credit: bool = True
    allow_commercial_use: bool = True
    allow_derivatives: bool = True
    allow_different_license: bool = True


@dataclass
class VersionDetails:
    """Detailed model version information."""
    id: str
    name: str
    description: Optional[str] = None
    base_model: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trained_words: List[str] = field(default_factory=list)
    files: List[FileInfo] = field(default_factory=list)
    images: List[ImageData] = field(default_factory=list)
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    stats: Optional[ModelStats] = None


@dataclass
class ModelDetails:
    """Detailed model information."""
    id: str
    name: str
    description: Optional[str] = None
    type: str = ""
    creator: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    versions: List[VersionDetails] = field(default_factory=list)
    images: List[ImageData] = field(default_factory=list)
    stats: Optional[ModelStats] = None
    nsfw: bool = False
    allow_no_credit: bool = True
    allow_commercial_use: bool = True
    allow_derivatives: bool = True
    allow_different_license: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class APIResponse:
    """Generic API response wrapper."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 200
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResponse:
    """Search API response."""
    items: List[ModelSummary]
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_items: int = 0
    current_page: int = 1
    total_pages: int = 1
    page_size: int = 20
    next_cursor: Optional[str] = None