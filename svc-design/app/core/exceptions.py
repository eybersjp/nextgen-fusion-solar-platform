"""Custom exceptions for the Design Service.

Defines application-specific exceptions and error handling.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class DesignServiceException(Exception):
    """Base exception for Design Service."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(DesignServiceException):
    """Raised when data validation fails."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )


class NotFoundError(DesignServiceException):
    """Raised when a resource is not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ):
        if not message:
            if resource_id:
                message = f"{resource_type} with ID '{resource_id}' not found"
            else:
                message = f"{resource_type} not found"
        
        details = kwargs.get("details", {})
        details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            details=details
        )


class PermissionError(DesignServiceException):
    """Raised when user lacks permission for an operation."""
    
    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if required_permission:
            details["required_permission"] = required_permission
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            details=details
        )


class AuthenticationError(DesignServiceException):
    """Raised when authentication fails."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_FAILED",
            details=kwargs.get("details", {})
        )


class AuthorizationError(DesignServiceException):
    """Raised when authorization fails."""
    
    def __init__(
        self,
        message: str = "Authorization failed",
        required_permission: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if required_permission:
            details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_FAILED",
            details=details
        )


class ConflictError(DesignServiceException):
    """Raised when a resource conflict occurs."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        resource_type: Optional[str] = None,
        conflicting_field: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if conflicting_field:
            details["conflicting_field"] = conflicting_field
        
        super().__init__(
            message=message,
            error_code="CONFLICT",
            details=details
        )


class BusinessLogicError(DesignServiceException):
    """Raised when business logic validation fails."""
    
    def __init__(
        self,
        message: str,
        rule: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if rule:
            details["rule"] = rule
        
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details=details
        )


class ExternalServiceError(DesignServiceException):
    """Raised when external service call fails."""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details["service_name"] = service_name
        if status_code:
            details["status_code"] = status_code
        
        super().__init__(
            message=f"{service_name}: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


class DatabaseError(DesignServiceException):
    """Raised when database operation fails."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details
        )


class FileStorageError(DesignServiceException):
    """Raised when file storage operation fails."""
    
    def __init__(
        self,
        message: str = "File storage operation failed",
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="FILE_STORAGE_ERROR",
            details=details
        )


class CalculationError(DesignServiceException):
    """Raised when calculation or analysis fails."""
    
    def __init__(
        self,
        message: str = "Calculation failed",
        calculation_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if calculation_type:
            details["calculation_type"] = calculation_type
        
        super().__init__(
            message=message,
            error_code="CALCULATION_ERROR",
            details=details
        )


class RateLimitError(DesignServiceException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class ConfigurationError(DesignServiceException):
    """Raised when configuration is invalid."""
    
    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details
        )


# HTTP Exception mappings
def to_http_exception(exc: DesignServiceException) -> HTTPException:
    """Convert Design Service exception to HTTP exception."""
    
    error_mappings = {
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
        "AUTHENTICATION_FAILED": status.HTTP_401_UNAUTHORIZED,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "BUSINESS_LOGIC_ERROR": status.HTTP_400_BAD_REQUEST,
        "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "FILE_STORAGE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CALCULATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "CONFIGURATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    
    status_code = error_mappings.get(
        exc.error_code,
        status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    
    detail = {
        "message": exc.message,
        "error_code": exc.error_code,
        "details": exc.details
    }
    
    return HTTPException(
        status_code=status_code,
        detail=detail
    )


# Specific Design Service exceptions
class DesignNotFoundError(NotFoundError):
    """Raised when a design is not found."""
    
    def __init__(self, design_id: str, **kwargs):
        super().__init__(
            resource_type="Design",
            resource_id=design_id,
            **kwargs
        )


class LayoutNotFoundError(NotFoundError):
    """Raised when a layout is not found."""
    
    def __init__(self, layout_id: str, **kwargs):
        super().__init__(
            resource_type="Layout",
            resource_id=layout_id,
            **kwargs
        )


class LayoutValidationError(ValidationError):
    """Raised when layout validation fails."""
    
    def __init__(self, layout_id: str, message: str, **kwargs):
        details = kwargs.get("details", {})
        details["layout_id"] = layout_id
        
        super().__init__(
            message=message,
            details=details,
            **kwargs
        )


class LayoutPermissionError(PermissionError):
    """Raised when user lacks permission for layout operation."""
    
    def __init__(self, layout_id: str, operation: str, **kwargs):
        message = f"Permission denied for {operation} operation on layout {layout_id}"
        details = kwargs.get("details", {})
        details.update({
            "layout_id": layout_id,
            "operation": operation
        })
        
        super().__init__(
            message=message,
            resource_type="Layout",
            resource_id=layout_id,
            required_permission=operation,
            details=details
        )


class LayoutBusinessLogicError(BusinessLogicError):
    """Raised when layout business logic validation fails."""
    
    def __init__(self, layout_id: str, message: str, rule: str = None, **kwargs):
        details = kwargs.get("details", {})
        details["layout_id"] = layout_id
        
        super().__init__(
            message=message,
            rule=rule or "layout_business_logic",
            details=details
        )


# Shading-specific exceptions
class ShadingNotFoundError(NotFoundError):
    """Shading analysis not found error."""
    pass


class ShadingValidationError(ValidationError):
    """Shading validation error."""
    pass


class ShadingPermissionError(PermissionError):
    """Shading permission error."""
    pass


class ShadingBusinessLogicError(BusinessLogicError):
    """Shading business logic error."""
    pass


class ShadingAnalysisNotFoundError(NotFoundError):
    """Raised when a shading analysis is not found."""
    
    def __init__(self, analysis_id: str, **kwargs):
        super().__init__(
            resource_type="ShadingAnalysis",
            resource_id=analysis_id,
            **kwargs
        )


class BOMNotFoundError(NotFoundError):
    """Raised when a BOM is not found."""
    
    def __init__(self, bom_id: str, **kwargs):
        super().__init__(
            resource_type="BillOfMaterials",
            resource_id=bom_id,
            **kwargs
        )


class BOMValidationError(ValidationError):
    """Raised when BOM validation fails."""
    
    def __init__(self, bom_id: str, message: str, **kwargs):
        details = kwargs.get("details", {})
        details["bom_id"] = bom_id
        
        super().__init__(
            message=message,
            details=details,
            **kwargs
        )


class BOMPermissionError(PermissionError):
    """Raised when user lacks permission for BOM operation."""
    
    def __init__(self, bom_id: str, operation: str, **kwargs):
        message = f"Permission denied for {operation} operation on BOM {bom_id}"
        details = kwargs.get("details", {})
        details.update({
            "bom_id": bom_id,
            "operation": operation
        })
        
        super().__init__(
            message=message,
            resource_type="BillOfMaterials",
            resource_id=bom_id,
            required_permission=operation,
            details=details
        )


class BOMBusinessLogicError(BusinessLogicError):
    """Raised when BOM business logic validation fails."""
    
    def __init__(self, bom_id: str, message: str, rule: str = None, **kwargs):
        details = kwargs.get("details", {})
        details["bom_id"] = bom_id
        
        super().__init__(
            message=message,
            rule=rule or "bom_business_logic",
            details=details
        )


class ComponentNotFoundError(NotFoundError):
    """Raised when a component is not found."""
    
    def __init__(self, component_id: str, **kwargs):
        super().__init__(
            resource_type="Component",
            resource_id=component_id,
            **kwargs
        )


class SupplierNotFoundError(NotFoundError):
    """Raised when a supplier is not found."""
    
    def __init__(self, supplier_id: str, **kwargs):
        super().__init__(
            resource_type="Supplier",
            resource_id=supplier_id,
            **kwargs
        )


class InvalidDesignStateError(BusinessLogicError):
    """Raised when design is in invalid state for operation."""
    
    def __init__(self, design_id: str, current_state: str, required_state: str, **kwargs):
        message = f"Design {design_id} is in state '{current_state}', but '{required_state}' is required"
        details = kwargs.get("details", {})
        details.update({
            "design_id": design_id,
            "current_state": current_state,
            "required_state": required_state
        })
        
        super().__init__(
            message=message,
            rule="design_state_validation",
            details=details
        )


class InvalidLayoutConfigurationError(BusinessLogicError):
    """Raised when layout configuration is invalid."""
    
    def __init__(self, layout_id: str, reason: str, **kwargs):
        message = f"Layout {layout_id} has invalid configuration: {reason}"
        details = kwargs.get("details", {})
        details.update({
            "layout_id": layout_id,
            "reason": reason
        })
        
        super().__init__(
            message=message,
            rule="layout_configuration_validation",
            details=details
        )


class ShadingAnalysisFailedError(CalculationError):
    """Raised when shading analysis calculation fails."""
    
    def __init__(self, analysis_id: str, reason: str, **kwargs):
        message = f"Shading analysis {analysis_id} failed: {reason}"
        details = kwargs.get("details", {})
        details.update({
            "analysis_id": analysis_id,
            "reason": reason
        })
        
        super().__init__(
            message=message,
            calculation_type="shading_analysis",
            details=details
        )


class BOMGenerationError(CalculationError):
    """Raised when BOM generation fails."""
    
    def __init__(self, design_id: str, reason: str, **kwargs):
        message = f"BOM generation for design {design_id} failed: {reason}"
        details = kwargs.get("details", {})
        details.update({
            "design_id": design_id,
            "reason": reason
        })
        
        super().__init__(
            message=message,
            calculation_type="bom_generation",
            details=details
        )


class WeatherDataError(ExternalServiceError):
    """Raised when weather data retrieval fails."""
    
    def __init__(self, location: str, reason: str, **kwargs):
        message = f"Weather data retrieval failed for {location}: {reason}"
        details = kwargs.get("details", {})
        details.update({
            "location": location,
            "reason": reason
        })
        
        super().__init__(
            service_name="Weather API",
            message=message,
            details=details
        )


class PricingDataError(ExternalServiceError):
    """Raised when pricing data retrieval fails."""
    
    def __init__(self, component_id: str, supplier_id: str, reason: str, **kwargs):
        message = f"Pricing data retrieval failed for component {component_id} from supplier {supplier_id}: {reason}"
        details = kwargs.get("details", {})
        details.update({
            "component_id": component_id,
            "supplier_id": supplier_id,
            "reason": reason
        })
        
        super().__init__(
            service_name="Pricing API",
            message=message,
            details=details
        )