-- Migration: 007_database_performance_optimization.sql
-- Phase 1 Enhancement: Database Performance Optimization
-- Adds strategic indexes and optimizations for improved query performance

-- Enable concurrent index creation to avoid blocking operations
SET maintenance_work_mem = '1GB';

-- 1. COMPOSITE INDEXES FOR COMMON QUERY PATTERNS

-- Projects table optimizations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_status_priority 
    ON projects(status, project_priority) 
    WHERE status IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_dates_range 
    ON projects(estimated_start_date, estimated_completion_date) 
    WHERE estimated_start_date IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_budget_currency 
    ON projects(currency_code, budget_allocated) 
    WHERE budget_allocated IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_manager_status 
    ON projects(project_manager_id, status) 
    WHERE project_manager_id IS NOT NULL;

-- Design workflow optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_workflow 
    ON design_3d_models(design_stage, approval_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_project_version 
    ON design_3d_models(project_id, design_version);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_approved_workflow 
    ON design_3d_models(approved_by, approved_at) 
    WHERE approved_by IS NOT NULL;

-- 2. COMPLIANCE SYSTEM OPTIMIZATIONS

-- Compliance validations for reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_project_status 
    ON compliance_validations(project_id, validation_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rule_status_date 
    ON compliance_validations(rule_id, validation_status, validated_at);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_design_status 
    ON compliance_validations(design_id, validation_status) 
    WHERE design_id IS NOT NULL;

-- Compliance rules optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_jurisdiction_category 
    ON compliance_rules(jurisdiction, category, is_active);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_type_severity 
    ON compliance_rules(rule_type, severity, is_active);

-- 3. FINANCIAL/CURRENCY OPTIMIZATIONS

-- Multi-currency transactions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_currency_transactions_date_type 
    ON multi_currency_transactions(transaction_date, transaction_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_currency_transactions_project_currency 
    ON multi_currency_transactions(project_id, original_currency);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_currency_transactions_reference 
    ON multi_currency_transactions(reference_id, transaction_type) 
    WHERE reference_id IS NOT NULL;

-- Exchange rates optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_rates_date_currencies 
    ON exchange_rates(effective_date DESC, from_currency, to_currency);

-- 4. USER AND AUTHENTICATION OPTIMIZATIONS

-- User activity and session management
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_login_activity 
    ON users(last_login_at DESC, is_active) 
    WHERE last_login_at IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_department_role 
    ON users(department, role) 
    WHERE department IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_2fa_active 
    ON users(is_2fa_enabled, is_active);

-- 5. CUSTOMER AND ORGANIZATION OPTIMIZATIONS

-- Customer segmentation and sales
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_segment_rep 
    ON customers(customer_segment, assigned_sales_rep) 
    WHERE customer_segment IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_currency_segment 
    ON customers(preferred_currency, customer_segment);

-- Organization industry analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_industry_size 
    ON organizations(industry, organization_size) 
    WHERE industry IS NOT NULL;

-- 6. ADVANCED JSONB INDEXES FOR STRUCTURED QUERIES

-- Compliance rules validation logic
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_logic_category 
    ON compliance_rules USING GIN ((validation_logic->'category'));

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_logic_type 
    ON compliance_rules USING GIN ((validation_logic->'type'));

-- Project risk assessment
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_risk_level 
    ON projects USING GIN ((risk_assessment->'level')) 
    WHERE risk_assessment IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_risk_factors 
    ON projects USING GIN ((risk_assessment->'factors')) 
    WHERE risk_assessment IS NOT NULL;

-- User notification preferences
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_notifications 
    ON users USING GIN (notification_preferences);

-- Compliance validation results
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_validation_results 
    ON compliance_validations USING GIN (validation_result) 
    WHERE validation_result IS NOT NULL;

-- 7. PARTIAL INDEXES FOR SPECIFIC USE CASES

-- Active projects only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_active_status 
    ON projects(status, updated_at) 
    WHERE status IN ('active', 'in_progress', 'planning');

-- Failed compliance validations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_failed_validations 
    ON compliance_validations(project_id, rule_id, validated_at) 
    WHERE validation_status = 'fail';

-- Pending approvals
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_pending_approvals 
    ON design_3d_models(project_id, created_at) 
    WHERE approval_status = 'pending';

-- Recent currency conversions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_currency_recent_conversions 
    ON currency_conversion_logs(converted_at DESC, from_currency, to_currency) 
    WHERE converted_at > NOW() - INTERVAL '30 days';

-- 8. TEXT SEARCH OPTIMIZATIONS

-- Full-text search on project descriptions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_description_fts 
    ON projects USING GIN (to_tsvector('english', description)) 
    WHERE description IS NOT NULL;

-- Full-text search on compliance rule names and descriptions
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_rules_fts 
    ON compliance_rules USING GIN (
        to_tsvector('english', name || ' ' || COALESCE(description, ''))
    );

-- 9. COVERING INDEXES FOR READ-HEAVY QUERIES

-- Project summary data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_summary_covering 
    ON projects(id, name, status, project_priority, estimated_completion_date, budget_allocated);

-- User profile data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_profile_covering 
    ON users(id, email, first_name, last_name, role, department, is_active);

-- Design summary data
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_design_summary_covering 
    ON design_3d_models(id, project_id, name, design_stage, approval_status, created_at);

-- 10. STATISTICS AND MAINTENANCE

-- Update table statistics for better query planning
ANALYZE projects;
ANALYZE design_3d_models;
ANALYZE compliance_validations;
ANALYZE compliance_rules;
ANALYZE multi_currency_transactions;
ANALYZE users;
ANALYZE customers;
ANALYZE organizations;

-- Reset maintenance_work_mem
RESET maintenance_work_mem;

-- Create a view for database performance monitoring
CREATE OR REPLACE VIEW v_database_performance_summary AS
SELECT 
    'table_sizes' as metric_type,
    schemaname,
    tablename as object_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_stat_get_live_tuples(c.oid) as live_tuples,
    pg_stat_get_dead_tuples(c.oid) as dead_tuples
FROM pg_stat_user_tables 
JOIN pg_class c ON c.relname = tablename
WHERE schemaname = 'public'
UNION ALL
SELECT 
    'index_usage' as metric_type,
    schemaname,
    indexname as object_name,
    pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size,
    idx_tup_read as live_tuples,
    idx_tup_fetch as dead_tuples
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY metric_type, size DESC;

COMMIT;

-- Performance optimization notes:
-- 1. All indexes created with CONCURRENTLY to avoid blocking
-- 2. Partial indexes used where appropriate to reduce size
-- 3. JSONB GIN indexes for structured JSON queries
-- 4. Covering indexes for read-heavy operations
-- 5. Full-text search indexes for content search
-- 6. Composite indexes aligned with common query patterns