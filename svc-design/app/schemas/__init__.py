"""Pydantic schemas for request/response validation."""

from .base import BaseSchema, TimestampSchema, PaginationSchema
from .design import (
    SolarSystemDesign,
    SolarSystemDesignCreate,
    SolarSystemDesignUpdate,
    SolarSystemDesignResponse,
    DesignValidationResult,
    DesignOptimizationRequest,
    DesignOptimizationResult
)
from .layout import (
    PanelLayout,
    PanelLayoutCreate,
    PanelLayoutUpdate,
    PanelLayoutResponse,
    LayoutValidationResult,
    LayoutResponse,
    LayoutZoneResponse,
    LayoutModuleResponse,
    LayoutOptimizationResponse,
    LayoutTemplateResponse,
    LayoutConstraintResponse,
    LayoutGenerationRequest,
    LayoutGenerationResponse,
    LayoutAnalysisRequest,
    LayoutAnalysisResponse,
    LayoutComparisonRequest,
    LayoutComparisonResponse,
    LayoutComparisonResult,
    LayoutExportRequest,
    LayoutExportResponse,
    LayoutListResponse
)
from .shading import (
    ShadingAnalysis,
    ShadingAnalysisCreate,
    ShadingAnalysisUpdate,
    ShadingAnalysisResponse,
    ShadingResult
)
from .bom import (
    BillOfMaterials,
    BOMItem,
    BOMItemCreate,
    BOMItemUpdate,
    BOMResponse,
    CostAnalysis
)

# New authentication, project, and solar schemas
from .user import (
    UserRole,
    UserBase,
    UserCreate,
    UserUpdate,
    UserPasswordUpdate,
    UserResponse,
    UserProfile,
    UserList,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationRequest,
    UserSessionBase,
    UserSessionCreate,
    UserSessionResponse,
    UserSessionList
)
from .project import (
    ProjectStatus,
    ProjectType,
    ProjectPriority,
    ProjectBase,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectSummary,
    ProjectList,
    ProjectFilter,
    ProjectStats,
    ProjectLocationUpdate,
    ProjectTagsUpdate,
    ProjectCustomFieldsUpdate,
    ProjectStatusUpdate
)
from .solar import (
    SolarDesignStatus,
    SolarDesignType,
    ComponentType,
    CalculationType,
    CalculationStatus,
    SolarDesignBase,
    SolarDesignCreate,
    SolarDesignUpdate,
    SolarDesignResponse,
    SolarDesignSummary,
    SolarDesignList,
    SolarComponentBase,
    SolarComponentCreate,
    SolarComponentUpdate,
    SolarComponentResponse,
    SolarComponentList,
    DesignCalculationBase,
    DesignCalculationCreate,
    DesignCalculationUpdate,
    DesignCalculationResponse,
    DesignCalculationSummary,
    DesignCalculationList,
    CalculationRequest,
    CalculationResult,
    SolarDesignFilter,
    ComponentFilter
)

__all__ = [
    # Base schemas
    "BaseSchema",
    "TimestampSchema", 
    "PaginationSchema",
    
    # Design schemas
    "SolarSystemDesign",
    "SolarSystemDesignCreate",
    "SolarSystemDesignUpdate",
    "SolarSystemDesignResponse",
    "DesignValidationResult",
    "DesignOptimizationRequest",
    "DesignOptimizationResult",
    
    # Layout schemas
    "PanelLayout",
    "PanelLayoutCreate",
    "PanelLayoutUpdate",
    "PanelLayoutResponse",
    "LayoutValidationResult",
    "LayoutResponse",
    "LayoutZoneResponse",
    "LayoutModuleResponse",
    "LayoutOptimizationResponse",
    "LayoutTemplateResponse",
    "LayoutConstraintResponse",
    "LayoutGenerationRequest",
    "LayoutGenerationResponse",
    "LayoutAnalysisRequest",
    "LayoutAnalysisResponse",
    "LayoutComparisonRequest",
    "LayoutComparisonResponse",
    "LayoutComparisonResult",
    "LayoutExportRequest",
    "LayoutExportResponse",
    "LayoutListResponse",
    
    # Shading schemas
    "ShadingAnalysis",
    "ShadingAnalysisCreate",
    "ShadingAnalysisUpdate",
    "ShadingAnalysisResponse",
    "ShadingResult",
    
    # BOM schemas
    "BillOfMaterials",
    "BOMItem",
    "BOMItemCreate",
    "BOMItemUpdate",
    "BOMResponse",
    "CostAnalysis",
    
    # User schemas
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserResponse",
    "UserProfile",
    "UserList",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "EmailVerificationRequest",
    "UserSessionBase",
    "UserSessionCreate",
    "UserSessionResponse",
    "UserSessionList",
    
    # Project schemas
    "ProjectStatus",
    "ProjectType",
    "ProjectPriority",
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectSummary",
    "ProjectList",
    "ProjectFilter",
    "ProjectStats",
    "ProjectLocationUpdate",
    "ProjectTagsUpdate",
    "ProjectCustomFieldsUpdate",
    "ProjectStatusUpdate",
    
    # Solar schemas
    "SolarDesignStatus",
    "SolarDesignType",
    "ComponentType",
    "CalculationType",
    "CalculationStatus",
    "SolarDesignBase",
    "SolarDesignCreate",
    "SolarDesignUpdate",
    "SolarDesignResponse",
    "SolarDesignSummary",
    "SolarDesignList",
    "SolarComponentBase",
    "SolarComponentCreate",
    "SolarComponentUpdate",
    "SolarComponentResponse",
    "SolarComponentList",
    "DesignCalculationBase",
    "DesignCalculationCreate",
    "DesignCalculationUpdate",
    "DesignCalculationResponse",
    "DesignCalculationSummary",
    "DesignCalculationList",
    "CalculationRequest",
    "CalculationResult",
    "SolarDesignFilter",
    "ComponentFilter"
]

# Aliases for backward compatibility with API routes
DesignCreate = SolarSystemDesignCreate
DesignUpdate = SolarSystemDesignUpdate
DesignResponse = SolarSystemDesignResponse
DesignListResponse = SolarDesignList
DesignPerformanceMetrics = CalculationResult
DesignComparison = SolarDesignBase
DesignComparisonResult = CalculationResult

# Layout aliases - most are already properly named, just add missing ones
LayoutCreate = PanelLayoutCreate
LayoutUpdate = PanelLayoutUpdate
LayoutOptimization = LayoutGenerationRequest
LayoutPerformanceMetrics = LayoutAnalysisResponse
LayoutComparison = LayoutComparisonRequest
LayoutZoneCreate = LayoutZoneResponse  # Placeholder - actual create schema may differ
LayoutZoneUpdate = LayoutZoneResponse  # Placeholder - actual update schema may differ
LayoutTemplateCreate = LayoutTemplateResponse  # Placeholder - actual create schema may differ
LayoutTemplateUpdate = LayoutTemplateResponse  # Placeholder - actual update schema may differ