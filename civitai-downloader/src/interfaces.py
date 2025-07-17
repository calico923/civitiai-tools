"""Core interfaces for the CivitAI downloader."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ModelType(Enum):
    """Supported model types."""
    CHECKPOINT = "Checkpoint"
    TEXTUAL_INVERSION = "TextualInversion"
    HYPERNETWORK = "Hypernetwork"
    AESTHETIC_GRADIENT = "AestheticGradient"
    LORA = "LORA"
    LOCON = "LoCon"
    LYCORIS = "LyCORIS"
    CONTROLNET = "Controlnet"
    POSES = "Poses"
    WILDCARDS = "Wildcards"
    OTHER = "Other"


class SortOrder(Enum):
    """Available sort orders for search."""
    HIGHEST_RATED = "Highest Rated"
    MOST_DOWNLOADED = "Most Downloaded"
    MOST_LIKED = "Most Liked"
    MOST_DISCUSSED = "Most Discussed"
    MOST_COLLECTED = "Most Collected"
    MOST_BUZZ = "Most Buzz"
    NEWEST = "Newest"


@dataclass
class ModelInfo:
    """Basic model information."""
    id: int
    name: str
    type: ModelType
    description: Optional[str]
    tags: List[str]
    creator: str
    stats: Dict[str, int]  # downloads, likes, etc.
    nsfw: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class ModelVersion:
    """Model version information."""
    id: int
    model_id: int
    name: str
    description: Optional[str]
    base_model: Optional[str]
    trained_words: List[str]
    files: List['ModelFile']
    images: List['ModelImage']
    download_url: str
    created_at: datetime


@dataclass
class ModelFile:
    """Model file information."""
    id: int
    name: str
    size_bytes: int
    format: str
    fp: Optional[str]  # precision: fp16, fp32, etc.
    hash: Optional[str]
    download_url: str
    metadata: Dict[str, Any]


@dataclass
class ModelImage:
    """Model preview image."""
    id: int
    url: str
    width: int
    height: int
    hash: Optional[str]
    nsfw: bool
    meta: Optional[Dict[str, Any]]  # generation metadata


@dataclass
class SearchParams:
    """Search parameters."""
    query: Optional[str] = None
    types: Optional[List[ModelType]] = None
    tags: Optional[List[str]] = None
    base_models: Optional[List[str]] = None
    sort: SortOrder = SortOrder.HIGHEST_RATED
    nsfw: Optional[bool] = None
    limit: int = 20
    page: int = 1


@dataclass
class DownloadProgress:
    """Download progress information."""
    file_name: str
    total_bytes: int
    downloaded_bytes: int
    percent: float
    speed_mbps: float
    eta_seconds: Optional[float]


class IAPIClient(ABC):
    """Interface for CivitAI API client."""
    
    @abstractmethod
    async def search_models(self, params: SearchParams) -> Tuple[List[ModelInfo], Optional[str]]:
        """Search for models. Returns (models, next_cursor)."""
        pass
    
    @abstractmethod
    async def get_model_details(self, model_id: int) -> ModelInfo:
        """Get detailed model information."""
        pass
    
    @abstractmethod
    async def get_model_versions(self, model_id: int) -> List[ModelVersion]:
        """Get all versions of a model."""
        pass
    
    @abstractmethod
    async def get_model_version(self, version_id: int) -> ModelVersion:
        """Get specific model version."""
        pass


class ISearchEngine(ABC):
    """Interface for model search engine."""
    
    @abstractmethod
    async def search(self, params: SearchParams) -> List[ModelInfo]:
        """Search for models with advanced filtering."""
        pass
    
    @abstractmethod
    async def filter_by_base_model(self, models: List[ModelInfo], base_models: List[str]) -> List[ModelInfo]:
        """Filter models by base model (client-side)."""
        pass


class IPreviewManager(ABC):
    """Interface for model preview manager."""
    
    @abstractmethod
    async def get_preview_images(self, model: ModelInfo, size: int = 512) -> List[ModelImage]:
        """Get preview images for a model."""
        pass
    
    @abstractmethod
    async def download_image(self, image: ModelImage, path: Path) -> None:
        """Download preview image."""
        pass
    
    @abstractmethod
    def display_model_info(self, model: ModelInfo, version: Optional[ModelVersion] = None) -> None:
        """Display model information in terminal."""
        pass


class IDownloadManager(ABC):
    """Interface for file download manager."""
    
    @abstractmethod
    async def download_file(
        self,
        url: str,
        path: Path,
        progress_callback: Optional[callable] = None
    ) -> None:
        """Download file with progress tracking."""
        pass
    
    @abstractmethod
    async def download_model(
        self,
        version: ModelVersion,
        path: Path,
        file_index: int = 0
    ) -> None:
        """Download model files."""
        pass
    
    @abstractmethod
    def can_resume(self, path: Path) -> bool:
        """Check if download can be resumed."""
        pass


class IStorageManager(ABC):
    """Interface for local storage management."""
    
    @abstractmethod
    def get_model_path(self, model: ModelInfo, version: ModelVersion) -> Path:
        """Get storage path for model."""
        pass
    
    @abstractmethod
    def save_metadata(self, model: ModelInfo, version: ModelVersion, path: Path) -> None:
        """Save model metadata."""
        pass
    
    @abstractmethod
    def get_download_history(self) -> List[Dict[str, Any]]:
        """Get download history."""
        pass
    
    @abstractmethod
    def add_to_history(self, model: ModelInfo, version: ModelVersion, path: Path) -> None:
        """Add download to history."""
        pass
    
    @abstractmethod
    def check_disk_space(self, required_bytes: int) -> bool:
        """Check if enough disk space is available."""
        pass