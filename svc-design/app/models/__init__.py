"""Database models for the Design Service.

This module exposes all database models for easy importing.
"""

from .base import (
    Base,
    BaseModel,
    TimestampMixin,
    SoftDeleteMixin,
    AuditMixin,
    MetadataMixin,
    StatusMixin,
    QueryMixin,
    FullBaseModel,
    create_tables,
    drop_tables,
    get_table_names,
    get_model_by_tablename,
)

from .design import (
    Design,
    DesignVersion,
    DesignApproval,
    DesignComment,
    DesignAttachment,
    DesignTag,
    DesignShare,
)

from .layout import (
    Layout,
    PanelArray,
    Inverter,
    ElectricalComponent,
    CableRun,
    LayoutOptimization,
)

from .shading import (
    ShadingAnalysis,
    Obstacle,
    SolarPosition,
    ShadingResult,
    IrradianceMap,
    SunPath,
    ShadingReport,
)

from .bom import (
    BillOfMaterials,
    BOMItem,
    Component,
    Supplier,
    PriceList,
    PriceListItem,
    BOMTemplate,
)

__all__ = [
    # Base models
    "Base",
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "MetadataMixin",
    "StatusMixin",
    "QueryMixin",
    "FullBaseModel",
    "create_tables",
    "drop_tables",
    "get_table_names",
    "get_model_by_tablename",
    # Design models
    "Design",
    "DesignVersion",
    "DesignApproval",
    "DesignComment",
    "DesignAttachment",
    "DesignTag",
    "DesignShare",
    # Layout models
    "Layout",
    "PanelArray",
    "Inverter",
    "ElectricalComponent",
    "CableRun",
    "LayoutOptimization",
    # Shading models
    "ShadingAnalysis",
    "Obstacle",
    "SolarPosition",
    "ShadingResult",
    "IrradianceMap",
    "SunPath",
    "ShadingReport",
    # BOM models
    "BillOfMaterials",
    "BOMItem",
    "Component",
    "Supplier",
    "PriceList",
    "PriceListItem",
    "BOMTemplate",
]