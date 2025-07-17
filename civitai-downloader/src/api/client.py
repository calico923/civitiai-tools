"""CivitAI API client with cross-platform support."""

import json
import os
import time
from typing import Dict, List, Optional, Iterator, Any, Union
from urllib.parse import quote_plus
import requests

from .exceptions import (
    APIError, NetworkError, RateLimitError, 
    AuthenticationError, ValidationError
)
from .models import (
    SearchQuery, ModelSummary, ModelDetails, VersionDetails,
    SearchResponse, APIResponse, ModelStats, ImageData, FileInfo
)
from .rate_limiter import RateLimiter


class CivitAIClient:
    """CivitAI API client with rate limiting and error handling."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        calls_per_second: float = 0.5,
        timeout: int = 30
    ):
        """
        Initialize CivitAI API client.
        
        Args:
            api_key: CivitAI API key (if None, will try to get from environment)
            calls_per_second: Rate limit (default: 0.5 = one call every 2 seconds)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("CIVITAI_API_KEY")
        self.base_url = "https://civitai.com/api/v1"
        self.timeout = timeout
        
        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CivitAI-Downloader/1.0",
            "Accept": "application/json"
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
        
        # Rate limiting
        self.rate_limiter = RateLimiter(calls_per_second)
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with rate limiting and error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: URL parameters
            **kwargs: Additional arguments for requests
            
        Returns:
            Response object
            
        Raises:
            NetworkError: For network-related issues
            APIError: For API-specific errors
            RateLimitError: For rate limit issues
            AuthenticationError: For auth issues
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Build URL
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout,
                **kwargs
            )
            
            # Handle HTTP errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key or authentication required")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif response.status_code >= 400:
                error_msg = f"API error {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    pass
                raise APIError(error_msg, response.status_code, response.text)
            
            response.raise_for_status()
            
            # Ensure UTF-8 encoding
            if response.encoding is None:
                response.encoding = 'utf-8'
            
            return response
            
        except requests.exceptions.Timeout:
            raise NetworkError(f"Request timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise NetworkError("Connection error - check your internet connection")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error: {str(e)}")
    
    def _parse_json_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Parse JSON response with error handling.
        
        Args:
            response: Response object
            
        Returns:
            Parsed JSON data
            
        Raises:
            APIError: For JSON parsing errors
        """
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise APIError(f"Invalid JSON response: {str(e)}")
    
    def search_models(
        self,
        query: Optional[str] = None,
        model_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        base_model: Optional[str] = None,
        username: Optional[str] = None,
        sort: str = "Highest Rated",
        limit: int = 20,
        page: int = 1,
        cursor: Optional[str] = None,
        nsfw: Optional[bool] = None
    ) -> SearchResponse:
        """
        Search for models.
        
        Args:
            query: Search query string
            model_types: List of model types (e.g., ["Checkpoint", "LORA"])
            tags: List of tags to filter by
            base_model: Base model to filter by
            username: Username to filter by
            sort: Sort order ("Highest Rated", "Most Downloaded", "Newest")
            limit: Number of results per page (max 100)
            page: Page number
            cursor: Cursor for pagination
            nsfw: NSFW filter (True, False, or None for all)
            
        Returns:
            SearchResponse object with results and metadata
        """
        # Build parameters
        params = {
            "limit": min(limit, 100),  # API max is 100
            "sort": sort
        }
        
        if query:
            params["query"] = query
        else:
            params["page"] = page
        
        if model_types:
            params["types"] = model_types
        
        if tags:
            # For multiple tags, use the first one in the tag parameter
            # Client-side filtering will be needed for multiple tags
            params["tag"] = tags[0]
        
        if base_model:
            # Note: API doesn't support baseModel parameter directly
            # This will be handled by client-side filtering
            pass
        
        if username:
            params["username"] = username
        
        if cursor:
            params["cursor"] = cursor
        
        if nsfw is not None:
            params["nsfw"] = str(nsfw).lower()
        
        # Make request
        response = self._make_request("GET", "/models", params=params)
        data = self._parse_json_response(response)
        
        # Parse response
        items = []
        for item_data in data.get("items", []):
            # Convert to ModelSummary
            model = self._parse_model_summary(item_data)
            items.append(model)
        
        metadata = data.get("metadata", {})
        
        return SearchResponse(
            items=items,
            metadata=metadata,
            total_items=metadata.get("totalItems", len(items)),
            current_page=metadata.get("currentPage", page),
            total_pages=metadata.get("totalPages", 1),
            page_size=metadata.get("pageSize", limit),
            next_cursor=metadata.get("nextCursor")
        )
    
    def search_with_cursor_pagination(
        self,
        query: Optional[str] = None,
        model_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        username: Optional[str] = None,
        sort: str = "Highest Rated",
        limit: int = 100,
        max_pages: int = 50,
        nsfw: Optional[bool] = None
    ) -> Iterator[ModelSummary]:
        """
        Search models with cursor-based pagination for large result sets.
        
        Args:
            query: Search query string
            model_types: List of model types
            tags: List of tags to filter by
            username: Username to filter by
            sort: Sort order
            limit: Results per API call
            max_pages: Maximum pages to fetch (safety limit)
            nsfw: NSFW filter
            
        Yields:
            ModelSummary objects
        """
        cursor = None
        page_count = 0
        
        while page_count < max_pages:
            page_count += 1
            
            try:
                response = self.search_models(
                    query=query,
                    model_types=model_types,
                    tags=tags,
                    username=username,
                    sort=sort,
                    limit=limit,
                    cursor=cursor,
                    nsfw=nsfw
                )
                
                if not response.items:
                    break
                
                for model in response.items:
                    yield model
                
                # Check for next cursor
                if not response.next_cursor:
                    break
                
                cursor = response.next_cursor
                
            except APIError as e:
                print(f"API error during pagination (page {page_count}): {e}")
                break
            except Exception as e:
                print(f"Unexpected error during pagination (page {page_count}): {e}")
                break
    
    def get_all_models(
        self,
        query: Optional[str] = None,
        model_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        username: Optional[str] = None,
        sort: str = "Highest Rated",
        max_results: int = 1000,
        nsfw: Optional[bool] = None
    ) -> List[ModelSummary]:
        """
        Get all models matching criteria using cursor pagination.
        
        Args:
            query: Search query string
            model_types: List of model types
            tags: List of tags to filter by
            username: Username to filter by
            sort: Sort order
            max_results: Maximum total results to return
            nsfw: NSFW filter
            
        Returns:
            List of all matching models
        """
        models = []
        
        for model in self.search_with_cursor_pagination(
            query=query,
            model_types=model_types,
            tags=tags,
            username=username,
            sort=sort,
            limit=100,  # Use max API limit for efficiency
            max_pages=max_results // 100 + 1,
            nsfw=nsfw
        ):
            models.append(model)
            if len(models) >= max_results:
                break
        
        return models
    
    def get_model(self, model_id: Union[int, str]) -> ModelDetails:
        """
        Get detailed model information.
        
        Args:
            model_id: Model ID
            
        Returns:
            ModelDetails object
        """
        response = self._make_request("GET", f"/models/{model_id}")
        data = self._parse_json_response(response)
        
        return self._parse_model_details(data)
    
    def get_model_version(self, version_id: Union[int, str]) -> VersionDetails:
        """
        Get detailed model version information.
        
        Args:
            version_id: Version ID
            
        Returns:
            VersionDetails object
        """
        response = self._make_request("GET", f"/model-versions/{version_id}")
        data = self._parse_json_response(response)
        
        return self._parse_version_details(data)
    
    def download_file(
        self, 
        url: str, 
        destination: str,
        chunk_size: int = 8192
    ) -> Iterator[Dict[str, Any]]:
        """
        Download file with progress tracking.
        
        Args:
            url: Download URL
            destination: Local file path
            chunk_size: Download chunk size in bytes
            
        Yields:
            Progress information dictionaries
        """
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        progress = {
                            "downloaded": downloaded,
                            "total": total_size,
                            "percentage": (downloaded / total_size * 100) if total_size > 0 else 0,
                            "chunk_size": len(chunk)
                        }
                        yield progress
                        
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Download failed: {str(e)}")
    
    def _parse_model_summary(self, data: Dict[str, Any]) -> ModelSummary:
        """Parse model summary from API response with robust handling."""
        # Handle stats with fallback
        stats_data = data.get("stats", {})
        stats = None
        if stats_data:
            stats = ModelStats(
                download_count=stats_data.get("downloadCount", 0),
                favorite_count=stats_data.get("favoriteCount", 0),
                comment_count=stats_data.get("commentCount", 0),
                rating_count=stats_data.get("ratingCount", 0),
                rating=float(stats_data.get("rating", 0.0))
            )
        
        # Handle creator with fallback
        creator_data = data.get("creator")
        creator_name = None
        if isinstance(creator_data, dict):
            creator_name = creator_data.get("username")
        elif isinstance(creator_data, str):
            creator_name = creator_data
        
        # Handle tags with robust parsing
        tags = []
        tags_data = data.get("tags", [])
        if isinstance(tags_data, list):
            for tag in tags_data:
                if isinstance(tag, dict) and "name" in tag:
                    tags.append(tag["name"])
                elif isinstance(tag, str):
                    tags.append(tag)
        
        # Handle images with fallback
        thumbnail_url = None
        images_data = data.get("images", [])
        if isinstance(images_data, list) and len(images_data) > 0:
            first_image = images_data[0]
            if isinstance(first_image, dict):
                thumbnail_url = first_image.get("url")
        
        return ModelSummary(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            type=data.get("type", ""),
            description=data.get("description"),
            creator=creator_name,
            stats=stats,
            thumbnail_url=thumbnail_url,
            tags=tags,
            nsfw=bool(data.get("nsfw", False)),
            allow_no_credit=bool(data.get("allowNoCredit", True)),
            allow_commercial_use=bool(data.get("allowCommercialUse", True)),
            allow_derivatives=bool(data.get("allowDerivatives", True)),
            allow_different_license=bool(data.get("allowDifferentLicense", True))
        )
    
    def _parse_model_details(self, data: Dict[str, Any]) -> ModelDetails:
        """Parse detailed model information from API response with robust handling."""
        # Handle stats with fallback
        stats_data = data.get("stats", {})
        stats = None
        if stats_data:
            stats = ModelStats(
                download_count=stats_data.get("downloadCount", 0),
                favorite_count=stats_data.get("favoriteCount", 0),
                comment_count=stats_data.get("commentCount", 0),
                rating_count=stats_data.get("ratingCount", 0),
                rating=float(stats_data.get("rating", 0.0))
            )
        
        # Handle creator with fallback
        creator_data = data.get("creator")
        creator_name = None
        if isinstance(creator_data, dict):
            creator_name = creator_data.get("username")
        elif isinstance(creator_data, str):
            creator_name = creator_data
        
        # Handle tags with robust parsing
        tags = []
        tags_data = data.get("tags", [])
        if isinstance(tags_data, list):
            for tag in tags_data:
                if isinstance(tag, dict) and "name" in tag:
                    tags.append(tag["name"])
                elif isinstance(tag, str):
                    tags.append(tag)
        
        # Parse versions with error handling
        versions = []
        for version_data in data.get("modelVersions", []):
            try:
                version = self._parse_version_details(version_data)
                versions.append(version)
            except Exception as e:
                print(f"Warning: Failed to parse version {version_data.get('id', 'unknown')}: {e}")
                continue
        
        # Parse images with error handling
        images = []
        for img_data in data.get("images", []):
            try:
                image = ImageData(
                    id=str(img_data.get("id", "")),
                    url=img_data.get("url", ""),
                    width=int(img_data.get("width", 0)),
                    height=int(img_data.get("height", 0)),
                    hash=img_data.get("hash"),
                    nsfw=bool(img_data.get("nsfw", False)),
                    meta=img_data.get("meta")
                )
                images.append(image)
            except Exception as e:
                print(f"Warning: Failed to parse image {img_data.get('id', 'unknown')}: {e}")
                continue
        
        return ModelDetails(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            description=data.get("description"),
            type=data.get("type", ""),
            creator=creator_name,
            tags=tags,
            versions=versions,
            images=images,
            stats=stats,
            nsfw=bool(data.get("nsfw", False)),
            allow_no_credit=bool(data.get("allowNoCredit", True)),
            allow_commercial_use=bool(data.get("allowCommercialUse", True)),
            allow_derivatives=bool(data.get("allowDerivatives", True)),
            allow_different_license=bool(data.get("allowDifferentLicense", True))
        )
    
    def _parse_version_details(self, data: Dict[str, Any]) -> VersionDetails:
        """Parse version details from API response with robust handling."""
        # Parse files with error handling
        files = []
        for file_data in data.get("files", []):
            try:
                file_info = FileInfo(
                    id=str(file_data.get("id", "")),
                    name=file_data.get("name", ""),
                    type=file_data.get("type", ""),
                    metadata=file_data.get("metadata", {}) if file_data.get("metadata") else {},
                    hashes=file_data.get("hashes", {}) if file_data.get("hashes") else {},
                    download_url=file_data.get("downloadUrl", ""),
                    size_kb=file_data.get("sizeKB") if file_data.get("sizeKB") is not None else None,
                    format=file_data.get("format"),
                    fp=file_data.get("fp"),
                    size=file_data.get("size")
                )
                files.append(file_info)
            except Exception as e:
                print(f"Warning: Failed to parse file {file_data.get('id', 'unknown')}: {e}")
                continue
        
        # Parse images with error handling
        images = []
        for img_data in data.get("images", []):
            try:
                image = ImageData(
                    id=str(img_data.get("id", "")),
                    url=img_data.get("url", ""),
                    width=int(img_data.get("width", 0)),
                    height=int(img_data.get("height", 0)),
                    hash=img_data.get("hash"),
                    nsfw=bool(img_data.get("nsfw", False)),
                    meta=img_data.get("meta")
                )
                images.append(image)
            except Exception as e:
                print(f"Warning: Failed to parse image {img_data.get('id', 'unknown')}: {e}")
                continue
        
        # Handle stats with fallback
        stats_data = data.get("stats", {})
        stats = None
        if stats_data:
            try:
                stats = ModelStats(
                    download_count=stats_data.get("downloadCount", 0),
                    favorite_count=stats_data.get("favoriteCount", 0),
                    comment_count=stats_data.get("commentCount", 0),
                    rating_count=stats_data.get("ratingCount", 0),
                    rating=float(stats_data.get("rating", 0.0))
                )
            except Exception as e:
                print(f"Warning: Failed to parse stats: {e}")
        
        # Handle trained words safely
        trained_words = data.get("trainedWords", [])
        if not isinstance(trained_words, list):
            trained_words = []
        
        return VersionDetails(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            description=data.get("description"),
            base_model=data.get("baseModel"),
            trained_words=trained_words,
            files=files,
            images=images,
            download_url=files[0].download_url if files else None,
            file_size=files[0].size_kb if files else None,
            stats=stats
        )
    
    def get_rate_limiter_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return self.rate_limiter.get_stats()