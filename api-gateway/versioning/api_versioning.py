"""API Versioning System for NextGen Fusion Platform

Provides comprehensive API versioning support including:
- Version routing (v1/v2/v3)
- Backward compatibility management
- Version deprecation handling
- Content negotiation
- Version-specific middleware
- Migration assistance
"""

import re
import logging
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.routing import APIRoute, APIRouter
from fastapi.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field
import semver

logger = logging.getLogger(__name__)


class VersionStatus(Enum):
    """API version status"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"
    BETA = "beta"
    ALPHA = "alpha"


class VersionExtractionMethod(Enum):
    """Methods for extracting version from requests"""
    URL_PATH = "url_path"  # /v1/users
    HEADER = "header"  # Accept: application/vnd.api+json;version=1
    QUERY_PARAM = "query_param"  # ?version=1
    SUBDOMAIN = "subdomain"  # v1.api.example.com


@dataclass
class VersionInfo:
    """Information about an API version"""
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    description: str = ""
    breaking_changes: List[str] = field(default_factory=list)
    migration_guide_url: Optional[str] = None
    
    @property
    def is_deprecated(self) -> bool:
        """Check if version is deprecated"""
        return self.status in [VersionStatus.DEPRECATED, VersionStatus.SUNSET]
    
    @property
    def is_active(self) -> bool:
        """Check if version is active"""
        return self.status == VersionStatus.ACTIVE
    
    @property
    def days_until_sunset(self) -> Optional[int]:
        """Calculate days until sunset"""
        if not self.sunset_date:
            return None
        delta = self.sunset_date - datetime.now()
        return max(0, delta.days)


@dataclass
class VersioningConfig:
    """Configuration for API versioning"""
    default_version: str = "1.0.0"
    latest_version: str = "2.0.0"
    extraction_methods: List[VersionExtractionMethod] = field(
        default_factory=lambda: [VersionExtractionMethod.URL_PATH, VersionExtractionMethod.HEADER]
    )
    
    # Header configuration
    version_header: str = "API-Version"
    accept_header_pattern: str = r"application/vnd\.api\+json;version=([\d\.]+)"
    
    # URL path configuration
    url_version_pattern: str = r"/v(\d+(?:\.\d+)?)/"
    version_prefix: str = "v"
    
    # Query parameter configuration
    version_query_param: str = "version"
    
    # Deprecation settings
    deprecation_warning_header: str = "Sunset"
    deprecation_info_header: str = "Deprecation"
    link_header: str = "Link"
    
    # Version validation
    strict_versioning: bool = True
    allow_beta_versions: bool = False
    require_exact_match: bool = False


class VersionRegistry:
    """Registry for managing API versions"""
    
    def __init__(self):
        self.versions: Dict[str, VersionInfo] = {}
        self.routers: Dict[str, APIRouter] = {}
        self.middleware: Dict[str, List[Callable]] = {}
    
    def register_version(
        self, 
        version: str, 
        info: VersionInfo, 
        router: APIRouter = None
    ) -> None:
        """Register a new API version"""
        self.versions[version] = info
        if router:
            self.routers[version] = router
        self.middleware[version] = []
        logger.info(f"Registered API version {version} with status {info.status.value}")
    
    def add_middleware(self, version: str, middleware: Callable) -> None:
        """Add middleware for a specific version"""
        if version not in self.middleware:
            self.middleware[version] = []
        self.middleware[version].append(middleware)
    
    def get_version_info(self, version: str) -> Optional[VersionInfo]:
        """Get version information"""
        return self.versions.get(version)
    
    def get_router(self, version: str) -> Optional[APIRouter]:
        """Get router for a version"""
        return self.routers.get(version)
    
    def get_active_versions(self) -> List[str]:
        """Get list of active versions"""
        return [
            version for version, info in self.versions.items()
            if info.is_active
        ]
    
    def get_deprecated_versions(self) -> List[str]:
        """Get list of deprecated versions"""
        return [
            version for version, info in self.versions.items()
            if info.is_deprecated
        ]
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest active version"""
        active_versions = self.get_active_versions()
        if not active_versions:
            return None
        
        # Sort versions using semantic versioning
        try:
            sorted_versions = sorted(active_versions, key=semver.VersionInfo.parse, reverse=True)
            return sorted_versions[0]
        except ValueError:
            # Fallback to string sorting if semver parsing fails
            return sorted(active_versions, reverse=True)[0]


class VersionExtractor:
    """Extracts version information from requests"""
    
    def __init__(self, config: VersioningConfig):
        self.config = config
        self.url_pattern = re.compile(config.url_version_pattern)
        self.accept_pattern = re.compile(config.accept_header_pattern)
    
    def extract_version(self, request: Request) -> Optional[str]:
        """Extract version from request using configured methods"""
        for method in self.config.extraction_methods:
            version = None
            
            if method == VersionExtractionMethod.URL_PATH:
                version = self._extract_from_url(request)
            elif method == VersionExtractionMethod.HEADER:
                version = self._extract_from_header(request)
            elif method == VersionExtractionMethod.QUERY_PARAM:
                version = self._extract_from_query(request)
            elif method == VersionExtractionMethod.SUBDOMAIN:
                version = self._extract_from_subdomain(request)
            
            if version:
                return self._normalize_version(version)
        
        return None
    
    def _extract_from_url(self, request: Request) -> Optional[str]:
        """Extract version from URL path"""
        match = self.url_pattern.search(str(request.url.path))
        return match.group(1) if match else None
    
    def _extract_from_header(self, request: Request) -> Optional[str]:
        """Extract version from headers"""
        # Check API-Version header
        version_header = request.headers.get(self.config.version_header)
        if version_header:
            return version_header
        
        # Check Accept header with version parameter
        accept_header = request.headers.get("accept", "")
        match = self.accept_pattern.search(accept_header)
        return match.group(1) if match else None
    
    def _extract_from_query(self, request: Request) -> Optional[str]:
        """Extract version from query parameters"""
        return request.query_params.get(self.config.version_query_param)
    
    def _extract_from_subdomain(self, request: Request) -> Optional[str]:
        """Extract version from subdomain"""
        host = request.headers.get("host", "")
        if host.startswith(f"{self.config.version_prefix}"):
            parts = host.split(".")
            if parts[0].startswith(self.config.version_prefix):
                return parts[0][len(self.config.version_prefix):]
        return None
    
    def _normalize_version(self, version: str) -> str:
        """Normalize version string"""
        # Remove 'v' prefix if present
        if version.startswith('v'):
            version = version[1:]
        
        # Ensure semantic versioning format
        if '.' not in version:
            version = f"{version}.0.0"
        elif version.count('.') == 1:
            version = f"{version}.0"
        
        return version


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware for handling API versioning"""
    
    def __init__(
        self, 
        app: FastAPI, 
        registry: VersionRegistry, 
        config: VersioningConfig
    ):
        super().__init__(app)
        self.registry = registry
        self.config = config
        self.extractor = VersionExtractor(config)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with version handling"""
        # Extract version from request
        requested_version = self.extractor.extract_version(request)
        
        # Use default version if none specified
        if not requested_version:
            requested_version = self.config.default_version
        
        # Validate version
        version_info = self.registry.get_version_info(requested_version)
        if not version_info:
            if self.config.strict_versioning:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported API version: {requested_version}"
                )
            else:
                # Fallback to latest version
                requested_version = self.registry.get_latest_version() or self.config.latest_version
                version_info = self.registry.get_version_info(requested_version)
        
        # Check if version is sunset
        if version_info and version_info.status == VersionStatus.SUNSET:
            raise HTTPException(
                status_code=410,
                detail=f"API version {requested_version} has been sunset"
            )
        
        # Add version to request state
        request.state.api_version = requested_version
        request.state.version_info = version_info
        
        # Apply version-specific middleware
        if requested_version in self.registry.middleware:
            for middleware in self.registry.middleware[requested_version]:
                request = await middleware(request)
        
        # Process request
        response = await call_next(request)
        
        # Add version headers to response
        self._add_version_headers(response, version_info)
        
        return response
    
    def _add_version_headers(self, response: Response, version_info: Optional[VersionInfo]) -> None:
        """Add version-related headers to response"""
        if not version_info:
            return
        
        # Add current version header
        response.headers[self.config.version_header] = version_info.version
        
        # Add deprecation headers if applicable
        if version_info.is_deprecated:
            if version_info.sunset_date:
                response.headers[self.config.deprecation_warning_header] = \
                    version_info.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            if version_info.deprecation_date:
                response.headers[self.config.deprecation_info_header] = \
                    version_info.deprecation_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            # Add link to migration guide
            if version_info.migration_guide_url:
                response.headers[self.config.link_header] = \
                    f'<{version_info.migration_guide_url}>; rel="migration-guide"'
        
        # Add latest version link
        latest_version = self.registry.get_latest_version()
        if latest_version and latest_version != version_info.version:
            response.headers["X-Latest-Version"] = latest_version


class VersionedAPIRouter(APIRouter):
    """Router with built-in versioning support"""
    
    def __init__(self, version: str, *args, **kwargs):
        self.version = version
        super().__init__(*args, **kwargs)
    
    def add_api_route(self, path: str, *args, **kwargs):
        """Add route with version prefix"""
        versioned_path = f"/v{self.version.split('.')[0]}{path}"
        super().add_api_route(versioned_path, *args, **kwargs)


class APIVersionManager:
    """Main API version management class"""
    
    def __init__(self, app: FastAPI, config: VersioningConfig = None):
        self.app = app
        self.config = config or VersioningConfig()
        self.registry = VersionRegistry()
        self.middleware = None
    
    def setup_versioning(self) -> None:
        """Setup versioning middleware and routes"""
        self.middleware = VersioningMiddleware(self.app, self.registry, self.config)
        self.app.add_middleware(VersioningMiddleware, 
                               registry=self.registry, 
                               config=self.config)
        
        # Add version info endpoint
        self._add_version_endpoints()
    
    def register_version(
        self, 
        version: str, 
        status: VersionStatus = VersionStatus.ACTIVE,
        description: str = "",
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None,
        breaking_changes: List[str] = None,
        migration_guide_url: Optional[str] = None
    ) -> VersionedAPIRouter:
        """Register a new API version"""
        version_info = VersionInfo(
            version=version,
            status=status,
            release_date=datetime.now(),
            deprecation_date=deprecation_date,
            sunset_date=sunset_date,
            description=description,
            breaking_changes=breaking_changes or [],
            migration_guide_url=migration_guide_url
        )
        
        router = VersionedAPIRouter(version, prefix=f"/v{version.split('.')[0]}")
        self.registry.register_version(version, version_info, router)
        
        # Include router in main app
        self.app.include_router(router)
        
        return router
    
    def deprecate_version(
        self, 
        version: str, 
        sunset_date: Optional[datetime] = None,
        migration_guide_url: Optional[str] = None
    ) -> None:
        """Mark a version as deprecated"""
        version_info = self.registry.get_version_info(version)
        if version_info:
            version_info.status = VersionStatus.DEPRECATED
            version_info.deprecation_date = datetime.now()
            if sunset_date:
                version_info.sunset_date = sunset_date
            if migration_guide_url:
                version_info.migration_guide_url = migration_guide_url
            
            logger.info(f"Deprecated API version {version}")
    
    def sunset_version(self, version: str) -> None:
        """Mark a version as sunset (no longer available)"""
        version_info = self.registry.get_version_info(version)
        if version_info:
            version_info.status = VersionStatus.SUNSET
            logger.info(f"Sunset API version {version}")
    
    def _add_version_endpoints(self) -> None:
        """Add version information endpoints"""
        
        @self.app.get("/versions", tags=["versioning"])
        async def get_versions():
            """Get all available API versions"""
            return {
                "versions": {
                    version: {
                        "status": info.status.value,
                        "release_date": info.release_date.isoformat(),
                        "deprecation_date": info.deprecation_date.isoformat() if info.deprecation_date else None,
                        "sunset_date": info.sunset_date.isoformat() if info.sunset_date else None,
                        "description": info.description,
                        "breaking_changes": info.breaking_changes,
                        "migration_guide_url": info.migration_guide_url,
                        "days_until_sunset": info.days_until_sunset
                    }
                    for version, info in self.registry.versions.items()
                },
                "default_version": self.config.default_version,
                "latest_version": self.registry.get_latest_version()
            }
        
        @self.app.get("/versions/{version}", tags=["versioning"])
        async def get_version_info(version: str):
            """Get information about a specific version"""
            info = self.registry.get_version_info(version)
            if not info:
                raise HTTPException(status_code=404, detail="Version not found")
            
            return {
                "version": version,
                "status": info.status.value,
                "release_date": info.release_date.isoformat(),
                "deprecation_date": info.deprecation_date.isoformat() if info.deprecation_date else None,
                "sunset_date": info.sunset_date.isoformat() if info.sunset_date else None,
                "description": info.description,
                "breaking_changes": info.breaking_changes,
                "migration_guide_url": info.migration_guide_url,
                "days_until_sunset": info.days_until_sunset
            }


# Utility functions
def get_current_version(request: Request) -> str:
    """Get current API version from request"""
    return getattr(request.state, 'api_version', '1.0.0')


def get_version_info(request: Request) -> Optional[VersionInfo]:
    """Get version info from request"""
    return getattr(request.state, 'version_info', None)


def require_version(min_version: str):
    """Decorator to require minimum API version"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            current_version = get_current_version(request)
            
            try:
                if semver.compare(current_version, min_version) < 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint requires API version {min_version} or higher"
                    )
            except ValueError:
                # Fallback to string comparison if semver fails
                if current_version < min_version:
                    raise HTTPException(
                        status_code=400,
                        detail=f"This endpoint requires API version {min_version} or higher"
                    )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Example usage and configuration
def create_versioned_app() -> Tuple[FastAPI, APIVersionManager]:
    """Create a FastAPI app with versioning support"""
    app = FastAPI(
        title="NextGen Fusion API",
        description="Commercial Solar Platform API with versioning support",
        version="2.0.0"
    )
    
    # Configure versioning
    config = VersioningConfig(
        default_version="1.0.0",
        latest_version="2.0.0",
        extraction_methods=[
            VersionExtractionMethod.URL_PATH,
            VersionExtractionMethod.HEADER,
            VersionExtractionMethod.QUERY_PARAM
        ]
    )
    
    version_manager = APIVersionManager(app, config)
    version_manager.setup_versioning()
    
    # Register versions
    v1_router = version_manager.register_version(
        "1.0.0",
        status=VersionStatus.DEPRECATED,
        description="Legacy API version",
        deprecation_date=datetime.now() - timedelta(days=30),
        sunset_date=datetime.now() + timedelta(days=90),
        breaking_changes=[
            "User authentication changed to OAuth2",
            "Project schema updated with new fields"
        ],
        migration_guide_url="https://docs.nextgenfusion.com/migration/v1-to-v2"
    )
    
    v2_router = version_manager.register_version(
        "2.0.0",
        status=VersionStatus.ACTIVE,
        description="Current stable API version",
        breaking_changes=[
            "New authentication system",
            "Enhanced project management",
            "Improved error responses"
        ]
    )
    
    return app, version_manager