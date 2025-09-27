"""Database Connection Pool Optimization for NextGen Fusion Platform

Enhances the existing connection pool manager with:
- Dynamic pool sizing based on load
- Connection health monitoring
- Performance metrics collection
- Automatic failover and recovery
- Load balancing for read replicas
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import psutil
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import DisconnectionError, TimeoutError

from .connection_pool import ConnectionPoolManager, PoolConfig, DatabaseType, PoolStrategy
from .service_config import ServiceType

logger = logging.getLogger(__name__)


class LoadLevel(Enum):
    """System load levels for dynamic pool sizing"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PoolMetrics:
    """Connection pool performance metrics"""
    pool_size: int = 0
    checked_out: int = 0
    overflow: int = 0
    checked_in: int = 0
    total_connections: int = 0
    
    # Performance metrics
    avg_checkout_time: float = 0.0
    max_checkout_time: float = 0.0
    connection_errors: int = 0
    timeouts: int = 0
    
    # Health metrics
    healthy_connections: int = 0
    stale_connections: int = 0
    last_health_check: Optional[datetime] = None
    
    # Load metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_queries: int = 0
    
    @property
    def utilization_ratio(self) -> float:
        """Calculate pool utilization ratio"""
        if self.pool_size == 0:
            return 0.0
        return self.checked_out / self.pool_size
    
    @property
    def error_ratio(self) -> float:
        """Calculate error ratio"""
        total_operations = self.checked_out + self.connection_errors
        if total_operations == 0:
            return 0.0
        return self.connection_errors / total_operations


@dataclass
class DynamicPoolConfig:
    """Configuration for dynamic pool sizing"""
    # Base pool settings
    min_pool_size: int = 5
    max_pool_size: int = 50
    target_utilization: float = 0.7
    
    # Scaling thresholds
    scale_up_threshold: float = 0.8
    scale_down_threshold: float = 0.5
    scale_up_increment: int = 2
    scale_down_increment: int = 1
    
    # Timing settings
    monitoring_interval: int = 30  # seconds
    scale_cooldown: int = 60  # seconds
    health_check_interval: int = 120  # seconds
    
    # Performance thresholds
    max_checkout_time: float = 5.0  # seconds
    max_error_ratio: float = 0.05  # 5%
    stale_connection_threshold: int = 300  # seconds


class OptimizedConnectionPoolManager(ConnectionPoolManager):
    """Enhanced connection pool manager with optimization features"""
    
    def __init__(self, config: PoolConfig, dynamic_config: DynamicPoolConfig = None):
        super().__init__(config)
        self.dynamic_config = dynamic_config or DynamicPoolConfig()
        self.metrics: Dict[str, PoolMetrics] = {}
        self.last_scale_time: Dict[str, datetime] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Connection timing tracking
        self.checkout_times: Dict[str, List[float]] = {}
        self.connection_health: Dict[str, Dict[str, Any]] = {}
    
    async def initialize_monitoring(self) -> None:
        """Initialize monitoring tasks"""
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Pool monitoring initialized")
    
    async def shutdown_monitoring(self) -> None:
        """Shutdown monitoring tasks"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.health_check_task:
            self.health_check_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            self.monitoring_task, 
            self.health_check_task, 
            return_exceptions=True
        )
        logger.info("Pool monitoring shutdown")
    
    def _setup_engine_events(self, engine: Engine, engine_key: str) -> None:
        """Setup enhanced event listeners for performance monitoring"""
        super()._setup_engine_events(engine, engine_key)
        
        # Initialize metrics for this engine
        self.metrics[engine_key] = PoolMetrics()
        self.checkout_times[engine_key] = []
        self.connection_health[engine_key] = {}
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Track new connections"""
            connection_id = id(dbapi_connection)
            self.connection_health[engine_key][connection_id] = {
                'created_at': datetime.now(),
                'last_used': datetime.now(),
                'query_count': 0,
                'error_count': 0
            }
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Track connection checkout with timing"""
            connection_record.checkout_time = time.time()
            connection_id = id(dbapi_connection)
            
            if connection_id in self.connection_health[engine_key]:
                self.connection_health[engine_key][connection_id]['last_used'] = datetime.now()
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Track connection checkin and calculate checkout duration"""
            if hasattr(connection_record, 'checkout_time'):
                checkout_duration = time.time() - connection_record.checkout_time
                self.checkout_times[engine_key].append(checkout_duration)
                
                # Keep only recent checkout times (last 100)
                if len(self.checkout_times[engine_key]) > 100:
                    self.checkout_times[engine_key] = self.checkout_times[engine_key][-100:]
        
        @event.listens_for(engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Track connection errors"""
            self.metrics[engine_key].connection_errors += 1
            connection_id = id(dbapi_connection)
            
            if connection_id in self.connection_health[engine_key]:
                self.connection_health[engine_key][connection_id]['error_count'] += 1
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop for dynamic pool management"""
        while True:
            try:
                await asyncio.sleep(self.dynamic_config.monitoring_interval)
                await self._update_metrics()
                await self._evaluate_scaling()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    async def _health_check_loop(self) -> None:
        """Health check loop for connection validation"""
        while True:
            try:
                await asyncio.sleep(self.dynamic_config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _update_metrics(self) -> None:
        """Update performance metrics for all engines"""
        for engine_key, engine in self.engines.items():
            if engine_key not in self.metrics:
                continue
            
            metrics = self.metrics[engine_key]
            
            # Update pool statistics
            pool = engine.pool
            metrics.pool_size = pool.size()
            metrics.checked_out = pool.checkedout()
            metrics.overflow = pool.overflow()
            metrics.checked_in = pool.checkedin()
            metrics.total_connections = metrics.checked_out + metrics.checked_in
            
            # Update performance metrics
            checkout_times = self.checkout_times.get(engine_key, [])
            if checkout_times:
                metrics.avg_checkout_time = sum(checkout_times) / len(checkout_times)
                metrics.max_checkout_time = max(checkout_times)
            
            # Update system metrics
            metrics.cpu_usage = psutil.cpu_percent()
            metrics.memory_usage = psutil.virtual_memory().percent
            
            # Update health metrics
            healthy_count = 0
            stale_count = 0
            current_time = datetime.now()
            
            for conn_id, health_info in self.connection_health[engine_key].items():
                last_used = health_info['last_used']
                if (current_time - last_used).total_seconds() > self.dynamic_config.stale_connection_threshold:
                    stale_count += 1
                else:
                    healthy_count += 1
            
            metrics.healthy_connections = healthy_count
            metrics.stale_connections = stale_count
            metrics.last_health_check = current_time
    
    async def _evaluate_scaling(self) -> None:
        """Evaluate if pool scaling is needed"""
        current_time = datetime.now()
        
        for engine_key, metrics in self.metrics.items():
            # Check cooldown period
            last_scale = self.last_scale_time.get(engine_key)
            if last_scale and (current_time - last_scale).total_seconds() < self.dynamic_config.scale_cooldown:
                continue
            
            utilization = metrics.utilization_ratio
            error_ratio = metrics.error_ratio
            
            # Determine if scaling is needed
            should_scale_up = (
                utilization > self.dynamic_config.scale_up_threshold or
                metrics.avg_checkout_time > self.dynamic_config.max_checkout_time or
                error_ratio > self.dynamic_config.max_error_ratio
            )
            
            should_scale_down = (
                utilization < self.dynamic_config.scale_down_threshold and
                metrics.avg_checkout_time < self.dynamic_config.max_checkout_time / 2 and
                error_ratio < self.dynamic_config.max_error_ratio / 2
            )
            
            if should_scale_up and metrics.pool_size < self.dynamic_config.max_pool_size:
                await self._scale_pool_up(engine_key)
                self.last_scale_time[engine_key] = current_time
            elif should_scale_down and metrics.pool_size > self.dynamic_config.min_pool_size:
                await self._scale_pool_down(engine_key)
                self.last_scale_time[engine_key] = current_time
    
    async def _scale_pool_up(self, engine_key: str) -> None:
        """Scale pool up"""
        engine = self.engines.get(engine_key)
        if not engine:
            return
        
        current_size = engine.pool.size()
        new_size = min(
            current_size + self.dynamic_config.scale_up_increment,
            self.dynamic_config.max_pool_size
        )
        
        # Recreate pool with new size
        await self._resize_pool(engine_key, new_size)
        
        logger.info(f"Scaled up pool {engine_key} from {current_size} to {new_size}")
    
    async def _scale_pool_down(self, engine_key: str) -> None:
        """Scale pool down"""
        engine = self.engines.get(engine_key)
        if not engine:
            return
        
        current_size = engine.pool.size()
        new_size = max(
            current_size - self.dynamic_config.scale_down_increment,
            self.dynamic_config.min_pool_size
        )
        
        # Recreate pool with new size
        await self._resize_pool(engine_key, new_size)
        
        logger.info(f"Scaled down pool {engine_key} from {current_size} to {new_size}")
    
    async def _resize_pool(self, engine_key: str, new_size: int) -> None:
        """Resize connection pool"""
        engine = self.engines.get(engine_key)
        if not engine:
            return
        
        try:
            # Dispose current pool
            engine.dispose()
            
            # Update pool size in config
            if hasattr(engine.pool, '_pool_size'):
                engine.pool._pool_size = new_size
            
            # Force pool recreation on next connection
            engine.pool.recreate()
            
        except Exception as e:
            logger.error(f"Error resizing pool {engine_key}: {e}")
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections"""
        for engine_key, engine in self.engines.items():
            try:
                # Test connection with simple query
                async with self.get_async_session(engine_key) as session:
                    await session.execute(text("SELECT 1"))
                
                # Clean up stale connections
                await self._cleanup_stale_connections(engine_key)
                
            except Exception as e:
                logger.error(f"Health check failed for {engine_key}: {e}")
                self.metrics[engine_key].connection_errors += 1
    
    async def _cleanup_stale_connections(self, engine_key: str) -> None:
        """Clean up stale connections"""
        current_time = datetime.now()
        stale_connections = []
        
        for conn_id, health_info in self.connection_health[engine_key].items():
            last_used = health_info['last_used']
            if (current_time - last_used).total_seconds() > self.dynamic_config.stale_connection_threshold:
                stale_connections.append(conn_id)
        
        # Remove stale connection tracking
        for conn_id in stale_connections:
            del self.connection_health[engine_key][conn_id]
        
        if stale_connections:
            logger.info(f"Cleaned up {len(stale_connections)} stale connections for {engine_key}")
    
    def get_detailed_metrics(self, engine_key: str = None) -> Dict[str, Any]:
        """Get detailed metrics for engines"""
        if engine_key:
            return {
                'metrics': self.metrics.get(engine_key, PoolMetrics()).__dict__,
                'checkout_times': self.checkout_times.get(engine_key, []),
                'connection_health': len(self.connection_health.get(engine_key, {}))
            }
        
        return {
            engine_key: {
                'metrics': metrics.__dict__,
                'checkout_times': self.checkout_times.get(engine_key, []),
                'connection_health': len(self.connection_health.get(engine_key, {}))
            }
            for engine_key, metrics in self.metrics.items()
        }
    
    def get_load_level(self) -> LoadLevel:
        """Determine current system load level"""
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        
        # Calculate average pool utilization
        total_utilization = 0
        active_pools = 0
        
        for metrics in self.metrics.values():
            if metrics.pool_size > 0:
                total_utilization += metrics.utilization_ratio
                active_pools += 1
        
        avg_utilization = total_utilization / max(active_pools, 1)
        
        # Determine load level
        if cpu_usage > 90 or memory_usage > 90 or avg_utilization > 0.9:
            return LoadLevel.CRITICAL
        elif cpu_usage > 70 or memory_usage > 70 or avg_utilization > 0.7:
            return LoadLevel.HIGH
        elif cpu_usage > 50 or memory_usage > 50 or avg_utilization > 0.5:
            return LoadLevel.MEDIUM
        else:
            return LoadLevel.LOW


# Factory functions for optimized pool managers
def create_optimized_pool_manager(
    service_type: ServiceType,
    database_url: str,
    multi_tenant: bool = True,
    dynamic_config: DynamicPoolConfig = None
) -> OptimizedConnectionPoolManager:
    """Create an optimized pool manager for a service"""
    
    # Service-specific optimizations
    service_optimizations = {
        ServiceType.DESIGN: DynamicPoolConfig(
            min_pool_size=10,
            max_pool_size=100,
            target_utilization=0.8,
            scale_up_increment=5,
            max_checkout_time=10.0
        ),
        ServiceType.CURRENCY: DynamicPoolConfig(
            min_pool_size=3,
            max_pool_size=20,
            target_utilization=0.6,
            scale_up_increment=2,
            max_checkout_time=2.0
        ),
        ServiceType.COMPLIANCE: DynamicPoolConfig(
            min_pool_size=5,
            max_pool_size=50,
            target_utilization=0.7,
            scale_up_increment=3,
            max_checkout_time=5.0
        ),
        ServiceType.PROJECT: DynamicPoolConfig(
            min_pool_size=5,
            max_pool_size=40,
            target_utilization=0.7,
            scale_up_increment=3,
            max_checkout_time=5.0
        ),
        ServiceType.API_GATEWAY: DynamicPoolConfig(
            min_pool_size=8,
            max_pool_size=60,
            target_utilization=0.75,
            scale_up_increment=4,
            max_checkout_time=3.0
        )
    }
    
    # Use service-specific config or provided config
    if dynamic_config is None:
        dynamic_config = service_optimizations.get(service_type, DynamicPoolConfig())
    
    # Create base pool config
    pool_config = PoolConfig(
        database_url=database_url,
        multi_tenant=multi_tenant,
        pool_size=dynamic_config.min_pool_size,
        max_overflow=dynamic_config.max_pool_size - dynamic_config.min_pool_size,
        pool_timeout=dynamic_config.max_checkout_time,
        pool_recycle=3600,  # 1 hour
        pool_pre_ping=True,
        strategy=PoolStrategy.TENANT_ISOLATED if multi_tenant else PoolStrategy.SHARED
    )
    
    return OptimizedConnectionPoolManager(pool_config, dynamic_config)


# Global optimized pool manager registry
optimized_pool_managers: Dict[str, OptimizedConnectionPoolManager] = {}


async def initialize_optimized_pools(
    service_configs: Dict[str, Tuple[ServiceType, str, bool]]
) -> None:
    """Initialize optimized pool managers for multiple services"""
    for service_name, (service_type, database_url, multi_tenant) in service_configs.items():
        manager = create_optimized_pool_manager(service_type, database_url, multi_tenant)
        await manager.initialize_monitoring()
        optimized_pool_managers[service_name] = manager
        logger.info(f"Initialized optimized pool manager for {service_name}")


async def shutdown_optimized_pools() -> None:
    """Shutdown all optimized pool managers"""
    for service_name, manager in optimized_pool_managers.items():
        await manager.shutdown_monitoring()
        await manager.close_all_engines()
        logger.info(f"Shutdown optimized pool manager for {service_name}")
    
    optimized_pool_managers.clear()


def get_optimized_pool_manager(service_name: str) -> Optional[OptimizedConnectionPoolManager]:
    """Get optimized pool manager by service name"""
    return optimized_pool_managers.get(service_name)


async def get_system_performance_report() -> Dict[str, Any]:
    """Generate comprehensive system performance report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'system_metrics': {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        },
        'pool_managers': {}
    }
    
    for service_name, manager in optimized_pool_managers.items():
        load_level = manager.get_load_level()
        detailed_metrics = manager.get_detailed_metrics()
        
        report['pool_managers'][service_name] = {
            'load_level': load_level.value,
            'metrics': detailed_metrics
        }
    
    return report