"""Correlation ID System for NextGen Fusion Platform

Provides comprehensive request tracing across microservices including:
- Automatic correlation ID generation and propagation
- Request/response logging with correlation context
- Distributed tracing integration
- Performance monitoring
- Error tracking and debugging
- Service dependency mapping
"""

import uuid
import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from contextvars import ContextVar
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import BaseHTTPMiddleware as StarletteBaseHTTPMiddleware
import httpx
import json
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor

# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
parent_span_id_var: ContextVar[Optional[str]] = ContextVar('parent_span_id', default=None)

logger = logging.getLogger(__name__)


class TraceLevel(Enum):
    """Trace detail levels"""
    MINIMAL = "minimal"  # Only correlation IDs
    STANDARD = "standard"  # IDs + basic timing
    DETAILED = "detailed"  # IDs + timing + headers
    FULL = "full"  # Everything including request/response bodies


class SpanType(Enum):
    """Types of spans in distributed tracing"""
    HTTP_REQUEST = "http_request"
    DATABASE_QUERY = "database_query"
    CACHE_OPERATION = "cache_operation"
    EXTERNAL_API = "external_api"
    BUSINESS_LOGIC = "business_logic"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"


@dataclass
class TraceSpan:
    """Represents a single span in distributed tracing"""
    span_id: str
    parent_span_id: Optional[str]
    correlation_id: str
    operation_name: str
    span_type: SpanType
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "started"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    def finish(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark span as finished"""
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        if error:
            self.error = error
            self.status = "error"
    
    def add_tag(self, key: str, value: Any) -> None:
        """Add a tag to the span"""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info", **kwargs) -> None:
        """Add a log entry to the span"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.logs.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for serialization"""
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "correlation_id": self.correlation_id,
            "operation_name": self.operation_name,
            "span_type": self.span_type.value,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
            "error": self.error
        }


@dataclass
class RequestTrace:
    """Complete trace for a request across services"""
    correlation_id: str
    request_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    spans: List[TraceSpan] = field(default_factory=list)
    services_involved: List[str] = field(default_factory=list)
    error_count: int = 0
    status: str = "in_progress"
    
    def add_span(self, span: TraceSpan) -> None:
        """Add a span to the trace"""
        self.spans.append(span)
        if span.service_name not in self.services_involved:
            self.services_involved.append(span.service_name)
        if span.error:
            self.error_count += 1
    
    def finish(self, status: str = "completed") -> None:
        """Mark trace as finished"""
        self.end_time = datetime.now()
        self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
    
    def get_critical_path(self) -> List[TraceSpan]:
        """Get the critical path (longest duration chain) through the trace"""
        # Simple implementation - can be enhanced with proper critical path analysis
        return sorted(self.spans, key=lambda s: s.duration_ms or 0, reverse=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization"""
        return {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": self.total_duration_ms,
            "spans": [span.to_dict() for span in self.spans],
            "services_involved": self.services_involved,
            "error_count": self.error_count,
            "status": self.status
        }


@dataclass
class CorrelationConfig:
    """Configuration for correlation ID system"""
    # Header names
    correlation_id_header: str = "X-Correlation-ID"
    request_id_header: str = "X-Request-ID"
    span_id_header: str = "X-Span-ID"
    parent_span_id_header: str = "X-Parent-Span-ID"
    trace_level_header: str = "X-Trace-Level"
    
    # Service identification
    service_name: str = "api-gateway"
    service_version: str = "1.0.0"
    
    # Tracing configuration
    default_trace_level: TraceLevel = TraceLevel.STANDARD
    enable_request_body_logging: bool = False
    enable_response_body_logging: bool = False
    max_body_size_bytes: int = 10240  # 10KB
    
    # Storage and retention
    trace_storage_enabled: bool = True
    trace_retention_hours: int = 24
    max_traces_in_memory: int = 10000
    
    # Performance settings
    async_logging: bool = True
    batch_size: int = 100
    flush_interval_seconds: int = 5
    
    # Sampling
    sampling_rate: float = 1.0  # 100% by default
    error_sampling_rate: float = 1.0  # Always sample errors


class TraceStorage:
    """In-memory storage for traces with cleanup"""
    
    def __init__(self, config: CorrelationConfig):
        self.config = config
        self.traces: Dict[str, RequestTrace] = {}
        self.spans: Dict[str, TraceSpan] = {}
        self.cleanup_lock = threading.Lock()
        self.last_cleanup = datetime.now()
        
        # Start cleanup task if storage is enabled
        if config.trace_storage_enabled:
            self._start_cleanup_task()
    
    def store_trace(self, trace: RequestTrace) -> None:
        """Store a complete trace"""
        if not self.config.trace_storage_enabled:
            return
        
        self.traces[trace.correlation_id] = trace
        self._maybe_cleanup()
    
    def store_span(self, span: TraceSpan) -> None:
        """Store a span"""
        if not self.config.trace_storage_enabled:
            return
        
        self.spans[span.span_id] = span
        
        # Add to trace if it exists
        if span.correlation_id in self.traces:
            self.traces[span.correlation_id].add_span(span)
    
    def get_trace(self, correlation_id: str) -> Optional[RequestTrace]:
        """Get a trace by correlation ID"""
        return self.traces.get(correlation_id)
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get a span by span ID"""
        return self.spans.get(span_id)
    
    def get_traces_by_service(self, service_name: str) -> List[RequestTrace]:
        """Get all traces involving a specific service"""
        return [
            trace for trace in self.traces.values()
            if service_name in trace.services_involved
        ]
    
    def get_error_traces(self) -> List[RequestTrace]:
        """Get all traces with errors"""
        return [
            trace for trace in self.traces.values()
            if trace.error_count > 0
        ]
    
    def get_slow_traces(self, threshold_ms: float = 1000) -> List[RequestTrace]:
        """Get traces slower than threshold"""
        return [
            trace for trace in self.traces.values()
            if trace.total_duration_ms and trace.total_duration_ms > threshold_ms
        ]
    
    def _maybe_cleanup(self) -> None:
        """Cleanup old traces if needed"""
        now = datetime.now()
        
        # Check if cleanup is needed
        if (len(self.traces) < self.config.max_traces_in_memory and 
            (now - self.last_cleanup).total_seconds() < 3600):  # 1 hour
            return
        
        with self.cleanup_lock:
            self._cleanup_old_traces()
            self.last_cleanup = now
    
    def _cleanup_old_traces(self) -> None:
        """Remove old traces based on retention policy"""
        cutoff_time = datetime.now() - timedelta(hours=self.config.trace_retention_hours)
        
        # Remove old traces
        old_correlation_ids = [
            correlation_id for correlation_id, trace in self.traces.items()
            if trace.start_time < cutoff_time
        ]
        
        for correlation_id in old_correlation_ids:
            del self.traces[correlation_id]
        
        # Remove orphaned spans
        old_span_ids = [
            span_id for span_id, span in self.spans.items()
            if span.start_time < cutoff_time
        ]
        
        for span_id in old_span_ids:
            del self.spans[span_id]
        
        logger.info(f"Cleaned up {len(old_correlation_ids)} traces and {len(old_span_ids)} spans")
    
    def _start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        def cleanup_worker():
            while True:
                time.sleep(3600)  # Run every hour
                try:
                    self._cleanup_old_traces()
                except Exception as e:
                    logger.error(f"Error in trace cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


class CorrelationIDManager:
    """Manages correlation IDs and distributed tracing"""
    
    def __init__(self, config: CorrelationConfig):
        self.config = config
        self.storage = TraceStorage(config)
        self.active_traces: Dict[str, RequestTrace] = {}
        
        # Setup logging formatter with correlation context
        self._setup_logging()
    
    def generate_correlation_id(self) -> str:
        """Generate a new correlation ID"""
        return str(uuid.uuid4())
    
    def generate_request_id(self) -> str:
        """Generate a new request ID"""
        return str(uuid.uuid4())
    
    def generate_span_id(self) -> str:
        """Generate a new span ID"""
        return str(uuid.uuid4())
    
    def start_trace(self, correlation_id: str, request_id: str) -> RequestTrace:
        """Start a new trace"""
        trace = RequestTrace(
            correlation_id=correlation_id,
            request_id=request_id,
            start_time=datetime.now()
        )
        
        self.active_traces[correlation_id] = trace
        return trace
    
    def start_span(
        self,
        operation_name: str,
        span_type: SpanType,
        correlation_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> TraceSpan:
        """Start a new span"""
        # Get correlation ID from context if not provided
        if not correlation_id:
            correlation_id = correlation_id_var.get()
        
        if not correlation_id:
            correlation_id = self.generate_correlation_id()
        
        # Get parent span ID from context if not provided
        if not parent_span_id:
            parent_span_id = span_id_var.get()
        
        span = TraceSpan(
            span_id=self.generate_span_id(),
            parent_span_id=parent_span_id,
            correlation_id=correlation_id,
            operation_name=operation_name,
            span_type=span_type,
            service_name=self.config.service_name,
            start_time=datetime.now()
        )
        
        # Set span in context
        span_id_var.set(span.span_id)
        
        # Store span
        self.storage.store_span(span)
        
        return span
    
    def finish_span(self, span: TraceSpan, status: str = "completed", error: Optional[str] = None) -> None:
        """Finish a span"""
        span.finish(status, error)
        self.storage.store_span(span)
    
    def finish_trace(self, correlation_id: str, status: str = "completed") -> None:
        """Finish a trace"""
        if correlation_id in self.active_traces:
            trace = self.active_traces[correlation_id]
            trace.finish(status)
            self.storage.store_trace(trace)
            del self.active_traces[correlation_id]
    
    def get_current_correlation_id(self) -> Optional[str]:
        """Get current correlation ID from context"""
        return correlation_id_var.get()
    
    def get_current_span_id(self) -> Optional[str]:
        """Get current span ID from context"""
        return span_id_var.get()
    
    def _setup_logging(self) -> None:
        """Setup logging with correlation context"""
        class CorrelationFormatter(logging.Formatter):
            def format(self, record):
                # Add correlation context to log record
                record.correlation_id = correlation_id_var.get() or "unknown"
                record.request_id = request_id_var.get() or "unknown"
                record.span_id = span_id_var.get() or "unknown"
                return super().format(record)
        
        # Update root logger formatter
        formatter = CorrelationFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[correlation_id=%(correlation_id)s] '
            '[request_id=%(request_id)s] '
            '[span_id=%(span_id)s] - '
            '%(message)s'
        )
        
        # Apply to all handlers
        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling correlation IDs and distributed tracing"""
    
    def __init__(self, app: FastAPI, manager: CorrelationIDManager):
        super().__init__(app)
        self.manager = manager
        self.config = manager.config
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation tracking"""
        start_time = time.time()
        
        # Extract or generate correlation ID
        correlation_id = (
            request.headers.get(self.config.correlation_id_header) or
            self.manager.generate_correlation_id()
        )
        
        # Extract or generate request ID
        request_id = (
            request.headers.get(self.config.request_id_header) or
            self.manager.generate_request_id()
        )
        
        # Extract parent span ID if present
        parent_span_id = request.headers.get(self.config.parent_span_id_header)
        
        # Set context variables
        correlation_id_var.set(correlation_id)
        request_id_var.set(request_id)
        if parent_span_id:
            parent_span_id_var.set(parent_span_id)
        
        # Start trace
        trace = self.manager.start_trace(correlation_id, request_id)
        
        # Start main request span
        span = self.manager.start_span(
            operation_name=f"{request.method} {request.url.path}",
            span_type=SpanType.HTTP_REQUEST,
            correlation_id=correlation_id,
            parent_span_id=parent_span_id
        )
        
        # Add request details to span
        span.add_tag("http.method", request.method)
        span.add_tag("http.url", str(request.url))
        span.add_tag("http.user_agent", request.headers.get("user-agent", ""))
        span.add_tag("service.name", self.config.service_name)
        span.add_tag("service.version", self.config.service_version)
        
        # Add request to state
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id
        request.state.span_id = span.span_id
        request.state.trace = trace
        request.state.span = span
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add response details to span
            span.add_tag("http.status_code", response.status_code)
            
            # Finish span with success
            self.manager.finish_span(span, "completed")
            
            # Add correlation headers to response
            response.headers[self.config.correlation_id_header] = correlation_id
            response.headers[self.config.request_id_header] = request_id
            response.headers[self.config.span_id_header] = span.span_id
            
            # Add timing header
            duration_ms = (time.time() - start_time) * 1000
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            # Add error details to span
            span.add_tag("error", True)
            span.add_log(f"Error: {str(e)}", level="error")
            
            # Finish span with error
            self.manager.finish_span(span, "error", str(e))
            
            # Finish trace with error
            self.manager.finish_trace(correlation_id, "error")
            
            raise
        
        finally:
            # Finish trace
            self.manager.finish_trace(correlation_id, "completed")


class TracedHTTPClient:
    """HTTP client with automatic correlation ID propagation"""
    
    def __init__(self, manager: CorrelationIDManager, base_url: str = ""):
        self.manager = manager
        self.config = manager.config
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)
    
    async def request(
        self,
        method: str,
        url: str,
        operation_name: Optional[str] = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with correlation tracking"""
        # Get current correlation context
        correlation_id = self.manager.get_current_correlation_id()
        current_span_id = self.manager.get_current_span_id()
        
        # Start span for external request
        span = self.manager.start_span(
            operation_name=operation_name or f"{method.upper()} {url}",
            span_type=SpanType.EXTERNAL_API,
            correlation_id=correlation_id,
            parent_span_id=current_span_id
        )
        
        # Add correlation headers
        headers = kwargs.get('headers', {})
        if correlation_id:
            headers[self.config.correlation_id_header] = correlation_id
        if current_span_id:
            headers[self.config.parent_span_id_header] = current_span_id
        headers[self.config.span_id_header] = span.span_id
        
        kwargs['headers'] = headers
        
        # Add request details to span
        span.add_tag("http.method", method.upper())
        span.add_tag("http.url", f"{self.base_url}{url}")
        span.add_tag("component", "http-client")
        
        try:
            # Make request
            response = await self.client.request(method, url, **kwargs)
            
            # Add response details
            span.add_tag("http.status_code", response.status_code)
            
            # Finish span
            self.manager.finish_span(span, "completed")
            
            return response
            
        except Exception as e:
            # Add error details
            span.add_tag("error", True)
            span.add_log(f"HTTP request failed: {str(e)}", level="error")
            
            # Finish span with error
            self.manager.finish_span(span, "error", str(e))
            
            raise
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)
    
    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()


# Utility functions and decorators
def trace_function(operation_name: str, span_type: SpanType = SpanType.BUSINESS_LOGIC):
    """Decorator to trace function execution"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            manager = get_correlation_manager()
            if not manager:
                return await func(*args, **kwargs)
            
            span = manager.start_span(operation_name, span_type)
            try:
                result = await func(*args, **kwargs)
                manager.finish_span(span, "completed")
                return result
            except Exception as e:
                manager.finish_span(span, "error", str(e))
                raise
        
        def sync_wrapper(*args, **kwargs):
            manager = get_correlation_manager()
            if not manager:
                return func(*args, **kwargs)
            
            span = manager.start_span(operation_name, span_type)
            try:
                result = func(*args, **kwargs)
                manager.finish_span(span, "completed")
                return result
            except Exception as e:
                manager.finish_span(span, "error", str(e))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Global manager instance
_correlation_manager: Optional[CorrelationIDManager] = None


def initialize_correlation_system(config: CorrelationConfig = None) -> CorrelationIDManager:
    """Initialize the correlation system"""
    global _correlation_manager
    
    if not config:
        config = CorrelationConfig()
    
    _correlation_manager = CorrelationIDManager(config)
    return _correlation_manager


def get_correlation_manager() -> Optional[CorrelationIDManager]:
    """Get the global correlation manager"""
    return _correlation_manager


def get_current_correlation_id() -> Optional[str]:
    """Get current correlation ID"""
    return correlation_id_var.get()


def get_current_request_id() -> Optional[str]:
    """Get current request ID"""
    return request_id_var.get()


def get_current_span_id() -> Optional[str]:
    """Get current span ID"""
    return span_id_var.get()


# Example usage
def setup_correlation_system(app: FastAPI, service_name: str = "api-gateway") -> CorrelationIDManager:
    """Setup correlation system for a FastAPI app"""
    config = CorrelationConfig(service_name=service_name)
    manager = initialize_correlation_system(config)
    
    # Add middleware
    app.add_middleware(CorrelationMiddleware, manager=manager)
    
    # Add tracing endpoints
    @app.get("/traces/{correlation_id}", tags=["tracing"])
    async def get_trace(correlation_id: str):
        """Get trace by correlation ID"""
        trace = manager.storage.get_trace(correlation_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return trace.to_dict()
    
    @app.get("/traces", tags=["tracing"])
    async def get_traces(
        service: Optional[str] = None,
        errors_only: bool = False,
        slow_only: bool = False,
        threshold_ms: float = 1000
    ):
        """Get traces with optional filtering"""
        if service:
            traces = manager.storage.get_traces_by_service(service)
        elif errors_only:
            traces = manager.storage.get_error_traces()
        elif slow_only:
            traces = manager.storage.get_slow_traces(threshold_ms)
        else:
            traces = list(manager.storage.traces.values())
        
        return {
            "traces": [trace.to_dict() for trace in traces[-100:]],  # Last 100 traces
            "total_count": len(traces)
        }
    
    return manager