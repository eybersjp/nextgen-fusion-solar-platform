-- Database Performance Analysis Script
-- Phase 1 Enhancement: Identify optimization opportunities

-- 1. Analyze table sizes and row counts
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation,
    most_common_vals,
    most_common_freqs
FROM pg_stats 
WHERE schemaname = 'public'
ORDER BY tablename, attname;

-- 2. Check for missing indexes on foreign keys
SELECT 
    t.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public'
  AND NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE tablename = t.table_name 
    AND indexdef LIKE '%' || kcu.column_name || '%'
  );

-- 3. Identify slow queries (requires pg_stat_statements extension)
-- SELECT 
--     query,
--     calls,
--     total_time,
--     mean_time,
--     rows
-- FROM pg_stat_statements 
-- WHERE query NOT LIKE '%pg_stat_statements%'
-- ORDER BY mean_time DESC 
-- LIMIT 20;

-- 4. Check table bloat and suggest VACUUM/REINDEX
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    CASE 
        WHEN n_live_tup > 0 THEN 
            ROUND((n_dead_tup::float / n_live_tup::float) * 100, 2)
        ELSE 0 
    END AS dead_tuple_percentage
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY dead_tuple_percentage DESC;

-- 5. Analyze JSONB column usage for GIN index opportunities
SELECT 
    t.table_name,
    c.column_name,
    c.data_type
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public' 
  AND c.data_type = 'jsonb'
  AND NOT EXISTS (
    SELECT 1 FROM pg_indexes 
    WHERE tablename = t.table_name 
    AND indexdef LIKE '%GIN%' 
    AND indexdef LIKE '%' || c.column_name || '%'
  );

-- 6. Check for unused indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
  AND idx_tup_read = 0 
  AND idx_tup_fetch = 0
ORDER BY tablename, indexname;

-- 7. Recommended additional indexes based on common query patterns

-- For projects table - composite indexes for common filters
-- CREATE INDEX CONCURRENTLY idx_projects_status_priority ON projects(status, project_priority);
-- CREATE INDEX CONCURRENTLY idx_projects_dates_range ON projects(estimated_start_date, estimated_completion_date) WHERE estimated_start_date IS NOT NULL;
-- CREATE INDEX CONCURRENTLY idx_projects_budget_currency ON projects(currency_code, budget_allocated) WHERE budget_allocated IS NOT NULL;

-- For design_3d_models - workflow state indexes
-- CREATE INDEX CONCURRENTLY idx_design_workflow ON design_3d_models(design_stage, approval_status);
-- CREATE INDEX CONCURRENTLY idx_design_project_version ON design_3d_models(project_id, design_version);

-- For compliance_validations - reporting indexes
-- CREATE INDEX CONCURRENTLY idx_compliance_project_status ON compliance_validations(project_id, validation_status);
-- CREATE INDEX CONCURRENTLY idx_compliance_rule_status ON compliance_validations(rule_id, validation_status, validated_at);

-- For multi_currency_transactions - financial reporting
-- CREATE INDEX CONCURRENTLY idx_currency_transactions_date_type ON multi_currency_transactions(transaction_date, transaction_type);
-- CREATE INDEX CONCURRENTLY idx_currency_transactions_project_currency ON multi_currency_transactions(project_id, original_currency);

-- For users - authentication and session management
-- CREATE INDEX CONCURRENTLY idx_users_login_activity ON users(last_login_at, is_active) WHERE last_login_at IS NOT NULL;
-- CREATE INDEX CONCURRENTLY idx_users_department_role ON users(department, role) WHERE department IS NOT NULL;

-- 8. Partitioning recommendations for large tables
-- Consider partitioning for:
-- - compliance_validations (by validated_at date)
-- - multi_currency_transactions (by transaction_date)
-- - currency_conversion_logs (by converted_at date)

-- 9. JSONB optimization queries
-- For compliance_rules.validation_logic
-- CREATE INDEX CONCURRENTLY idx_compliance_rules_logic_category ON compliance_rules USING GIN ((validation_logic->'category'));

-- For projects.risk_assessment
-- CREATE INDEX CONCURRENTLY idx_projects_risk_level ON projects USING GIN ((risk_assessment->'level'));

-- For users.notification_preferences
-- CREATE INDEX CONCURRENTLY idx_users_notifications ON users USING GIN (notification_preferences);