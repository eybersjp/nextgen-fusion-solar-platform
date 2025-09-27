-- Performance Optimization: Add Strategic Database Indexes
-- Migration: 2025_01_27_1200-add_performance_indexes
-- Description: Add performance indexes to critical tables for improved query performance

-- ============================================================================
-- SOLAR DESIGNS TABLE INDEXES
-- ============================================================================

-- Composite index for project-based design queries with status filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_designs_project_status_active 
ON solar_designs (project_id, status, is_active) 
WHERE deleted_at IS NULL;

-- Index for capacity-based searches and filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_designs_capacity_range 
ON solar_designs (system_capacity_kw) 
WHERE system_capacity_kw IS NOT NULL AND deleted_at IS NULL;

-- Index for design version queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_designs_version_created 
ON solar_designs (version, created_at) 
WHERE deleted_at IS NULL;

-- Index for performance-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_designs_performance 
ON solar_designs (capacity_factor, performance_ratio) 
WHERE capacity_factor IS NOT NULL AND performance_ratio IS NOT NULL AND deleted_at IS NULL;

-- Index for cost analysis queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_designs_cost_analysis 
ON solar_designs (estimated_cost, cost_per_watt) 
WHERE estimated_cost IS NOT NULL AND deleted_at IS NULL;

-- ============================================================================
-- SOLAR COMPONENTS TABLE INDEXES
-- ============================================================================

-- Composite index for design-based component queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_components_design_type 
ON solar_components (design_id, component_type) 
WHERE deleted_at IS NULL;

-- Index for manufacturer and model searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_components_manufacturer_model 
ON solar_components (manufacturer, model) 
WHERE manufacturer IS NOT NULL AND model IS NOT NULL AND deleted_at IS NULL;

-- Index for component cost analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_components_cost 
ON solar_components (component_type, unit_cost) 
WHERE unit_cost IS NOT NULL AND deleted_at IS NULL;

-- Index for quantity-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_components_quantity 
ON solar_components (component_type, quantity) 
WHERE deleted_at IS NULL;

-- ============================================================================
-- PROJECTS TABLE INDEXES
-- ============================================================================

-- Composite index for owner-based project queries with status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_owner_status_type 
ON projects (owner_id, status, project_type) 
WHERE deleted_at IS NULL;

-- Geographic index for location-based searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_location 
ON projects (site_country, site_state, site_city) 
WHERE site_country IS NOT NULL AND deleted_at IS NULL;

-- Index for capacity and budget range queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_capacity_budget 
ON projects (target_capacity_kw, budget_amount) 
WHERE target_capacity_kw IS NOT NULL AND deleted_at IS NULL;

-- Index for timeline-based queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_timeline 
ON projects (start_date, target_completion_date, status) 
WHERE start_date IS NOT NULL AND deleted_at IS NULL;

-- Index for geographic coordinates (for proximity searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_coordinates 
ON projects (latitude, longitude) 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND deleted_at IS NULL;

-- ============================================================================
-- USERS TABLE INDEXES
-- ============================================================================

-- Composite index for authentication queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_auth_status 
ON users (email, is_active, is_verified) 
WHERE deleted_at IS NULL;

-- Index for role-based access control
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_active 
ON users (role, is_active) 
WHERE deleted_at IS NULL;

-- Index for company-based user searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_company_role 
ON users (company, role) 
WHERE company IS NOT NULL AND deleted_at IS NULL;

-- Index for login activity tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login 
ON users (last_login_at) 
WHERE last_login_at IS NOT NULL AND deleted_at IS NULL;

-- Index for password security queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_password_changed 
ON users (password_changed_at, is_active) 
WHERE password_changed_at IS NOT NULL AND deleted_at IS NULL;

-- ============================================================================
-- USER SESSIONS TABLE INDEXES
-- ============================================================================

-- Index for session management
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_user_active 
ON user_sessions (user_id, is_active, expires_at) 
WHERE deleted_at IS NULL;

-- Index for session cleanup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_expires 
ON user_sessions (expires_at) 
WHERE expires_at IS NOT NULL;

-- Index for session token lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_token 
ON user_sessions (session_token) 
WHERE session_token IS NOT NULL AND deleted_at IS NULL;

-- ============================================================================
-- DESIGN CALCULATIONS TABLE INDEXES
-- ============================================================================

-- Composite index for design-based calculation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_calculations_design_type 
ON design_calculations (design_id, calculation_type) 
WHERE deleted_at IS NULL;

-- Index for calculation status and results
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_calculations_status 
ON design_calculations (calculation_type, status, created_at) 
WHERE deleted_at IS NULL;

-- Index for performance calculation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_calculations_performance 
ON design_calculations (design_id, created_at) 
WHERE calculation_type = 'performance' AND deleted_at IS NULL;

-- ============================================================================
-- CROSS-TABLE PERFORMANCE INDEXES
-- ============================================================================

-- Index for audit trail queries across all tables
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_created_by 
ON solar_designs (created_by, created_at) 
WHERE created_by IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_updated_by 
ON solar_designs (updated_by, updated_at) 
WHERE updated_by IS NOT NULL AND deleted_at IS NULL;

-- Similar audit indexes for projects
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_audit_created 
ON projects (created_by, created_at) 
WHERE created_by IS NOT NULL AND deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_audit_updated 
ON projects (updated_by, updated_at) 
WHERE updated_by IS NOT NULL AND deleted_at IS NULL;

-- ============================================================================
-- PARTIAL INDEXES FOR SOFT DELETE OPTIMIZATION
-- ============================================================================

-- Optimize queries that filter out deleted records
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_designs_active_only 
ON solar_designs (id, created_at) 
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_active_only 
ON projects (id, created_at) 
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active_only 
ON users (id, created_at) 
WHERE deleted_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_solar_components_active_only 
ON solar_components (id, created_at) 
WHERE deleted_at IS NULL;

-- ============================================================================
-- STATISTICS UPDATE
-- ============================================================================

-- Update table statistics for better query planning
ANALYZE solar_designs;
ANALYZE solar_components;
ANALYZE projects;
ANALYZE users;
ANALYZE user_sessions;
ANALYZE design_calculations;

-- ============================================================================
-- INDEX USAGE MONITORING VIEWS
-- ============================================================================

-- Create view to monitor index usage
CREATE OR REPLACE VIEW v_index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'LOW_USAGE'
        WHEN idx_scan < 1000 THEN 'MEDIUM_USAGE'
        ELSE 'HIGH_USAGE'
    END as usage_category
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Create view to monitor table scan ratios
CREATE OR REPLACE VIEW v_table_scan_ratios AS
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    CASE 
        WHEN (seq_scan + idx_scan) = 0 THEN 0
        ELSE ROUND((seq_scan::float / (seq_scan + idx_scan)) * 100, 2)
    END as seq_scan_ratio
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY seq_scan_ratio DESC;

-- ============================================================================
-- PERFORMANCE MONITORING FUNCTIONS
-- ============================================================================

-- Function to identify slow queries
CREATE OR REPLACE FUNCTION get_slow_queries(min_duration_ms INTEGER DEFAULT 1000)
RETURNS TABLE(
    query TEXT,
    calls BIGINT,
    total_time DOUBLE PRECISION,
    mean_time DOUBLE PRECISION,
    rows BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pg_stat_statements.query,
        pg_stat_statements.calls,
        pg_stat_statements.total_exec_time,
        pg_stat_statements.mean_exec_time,
        pg_stat_statements.rows
    FROM pg_stat_statements
    WHERE pg_stat_statements.mean_exec_time > min_duration_ms
    ORDER BY pg_stat_statements.mean_exec_time DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- Function to get index recommendations
CREATE OR REPLACE FUNCTION get_missing_indexes()
RETURNS TABLE(
    table_name TEXT,
    column_names TEXT,
    seq_scans BIGINT,
    recommendation TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.tablename::TEXT,
        'Multiple columns'::TEXT,
        t.seq_scan,
        'Consider adding composite indexes for frequently queried columns'::TEXT
    FROM pg_stat_user_tables t
    WHERE t.seq_scan > 1000
    AND t.schemaname = 'public'
    ORDER BY t.seq_scan DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Performance indexes migration completed successfully';
    RAISE NOTICE 'Added % indexes for improved query performance', 
        (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'idx_%');
END $$;