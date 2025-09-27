-- NextGen Fusion Commercial Solar Platform
-- Auth0 Migration Script
-- This script handles the migration from custom JWT authentication to Auth0

-- Create migration tracking table
CREATE TABLE IF NOT EXISTS auth_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rollback_script TEXT,
    notes TEXT
);

-- Create Auth0 user mapping table
CREATE TABLE IF NOT EXISTS auth0_user_mapping (
    id SERIAL PRIMARY KEY,
    legacy_user_id UUID NOT NULL,
    auth0_user_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    migration_status VARCHAR(50) DEFAULT 'pending',
    migrated_at TIMESTAMP WITH TIME ZONE,
    rollback_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_auth0_user_mapping_legacy_id ON auth0_user_mapping(legacy_user_id);
CREATE INDEX IF NOT EXISTS idx_auth0_user_mapping_auth0_id ON auth0_user_mapping(auth0_user_id);
CREATE INDEX IF NOT EXISTS idx_auth0_user_mapping_email ON auth0_user_mapping(email);
CREATE INDEX IF NOT EXISTS idx_auth0_user_mapping_status ON auth0_user_mapping(migration_status);

-- Create Auth0 roles mapping table
CREATE TABLE IF NOT EXISTS auth0_roles (
    id SERIAL PRIMARY KEY,
    auth0_role_id VARCHAR(255) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions TEXT[], -- Array of permission strings
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default Auth0 roles
INSERT INTO auth0_roles (auth0_role_id, role_name, description, permissions, is_system_role) VALUES
('rol_admin', 'Administrator', 'Full system access', ARRAY[
    'read:users', 'write:users', 'delete:users',
    'read:projects', 'write:projects', 'delete:projects',
    'read:analytics', 'write:analytics',
    'read:settings', 'write:settings',
    'read:audit_logs', 'write:audit_logs',
    'manage:system'
], TRUE),
('rol_manager', 'Manager', 'Management level access', ARRAY[
    'read:users', 'write:users',
    'read:projects', 'write:projects',
    'read:analytics', 'write:analytics',
    'read:reports', 'write:reports'
], TRUE),
('rol_user', 'User', 'Standard user access', ARRAY[
    'read:projects', 'write:projects',
    'read:reports'
], TRUE),
('rol_viewer', 'Viewer', 'Read-only access', ARRAY[
    'read:projects',
    'read:reports'
], TRUE)
ON CONFLICT (auth0_role_id) DO UPDATE SET
    role_name = EXCLUDED.role_name,
    description = EXCLUDED.description,
    permissions = EXCLUDED.permissions,
    updated_at = NOW();

-- Create Auth0 organizations table
CREATE TABLE IF NOT EXISTS auth0_organizations (
    id SERIAL PRIMARY KEY,
    auth0_org_id VARCHAR(255) NOT NULL UNIQUE,
    organization_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    connection_strategy VARCHAR(100), -- 'saml', 'oidc', 'ad', etc.
    connection_config JSONB,
    branding_config JSONB,
    is_enterprise BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create Auth0 user sessions table for tracking
CREATE TABLE IF NOT EXISTS auth0_user_sessions (
    id SERIAL PRIMARY KEY,
    auth0_user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    access_token_jti VARCHAR(255), -- JWT ID for token tracking
    refresh_token_jti VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    login_method VARCHAR(50), -- 'password', 'social', 'sso', 'mfa'
    mfa_verified BOOLEAN DEFAULT FALSE,
    session_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_end TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for session tracking
CREATE INDEX IF NOT EXISTS idx_auth0_sessions_user_id ON auth0_user_sessions(auth0_user_id);
CREATE INDEX IF NOT EXISTS idx_auth0_sessions_session_id ON auth0_user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_auth0_sessions_active ON auth0_user_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_auth0_sessions_last_activity ON auth0_user_sessions(last_activity);

-- Create Auth0 audit log table
CREATE TABLE IF NOT EXISTS auth0_audit_logs (
    id SERIAL PRIMARY KEY,
    auth0_log_id VARCHAR(255) UNIQUE,
    auth0_user_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    event_description TEXT,
    ip_address INET,
    user_agent TEXT,
    location_info JSONB, -- Country, city, etc.
    risk_assessment JSONB, -- Auth0 risk assessment data
    event_data JSONB,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_auth0_audit_user_id ON auth0_audit_logs(auth0_user_id);
CREATE INDEX IF NOT EXISTS idx_auth0_audit_event_type ON auth0_audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_auth0_audit_occurred_at ON auth0_audit_logs(occurred_at);
CREATE INDEX IF NOT EXISTS idx_auth0_audit_ip_address ON auth0_audit_logs(ip_address);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_auth0_user_mapping_updated_at
    BEFORE UPDATE ON auth0_user_mapping
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_auth0_roles_updated_at
    BEFORE UPDATE ON auth0_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_auth0_organizations_updated_at
    BEFORE UPDATE ON auth0_organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function to migrate user data
CREATE OR REPLACE FUNCTION migrate_user_to_auth0(
    p_legacy_user_id UUID,
    p_auth0_user_id VARCHAR(255),
    p_email VARCHAR(255)
) RETURNS BOOLEAN AS $$
DECLARE
    v_existing_mapping INTEGER;
    v_rollback_data JSONB;
BEGIN
    -- Check if mapping already exists
    SELECT COUNT(*) INTO v_existing_mapping
    FROM auth0_user_mapping
    WHERE legacy_user_id = p_legacy_user_id OR auth0_user_id = p_auth0_user_id;
    
    IF v_existing_mapping > 0 THEN
        RAISE NOTICE 'User mapping already exists for legacy_user_id: % or auth0_user_id: %', p_legacy_user_id, p_auth0_user_id;
        RETURN FALSE;
    END IF;
    
    -- Prepare rollback data (store original user data)
    SELECT jsonb_build_object(
        'user_id', u.id,
        'email', u.email,
        'roles', array_agg(DISTINCT r.name),
        'permissions', array_agg(DISTINCT p.name),
        'profile_data', jsonb_build_object(
            'first_name', u.first_name,
            'last_name', u.last_name,
            'phone', u.phone,
            'organization', u.organization
        )
    ) INTO v_rollback_data
    FROM users u
    LEFT JOIN user_roles ur ON u.id = ur.user_id
    LEFT JOIN roles r ON ur.role_id = r.id
    LEFT JOIN role_permissions rp ON r.id = rp.role_id
    LEFT JOIN permissions p ON rp.permission_id = p.id
    WHERE u.id = p_legacy_user_id
    GROUP BY u.id, u.email, u.first_name, u.last_name, u.phone, u.organization;
    
    -- Insert mapping record
    INSERT INTO auth0_user_mapping (
        legacy_user_id,
        auth0_user_id,
        email,
        migration_status,
        migrated_at,
        rollback_data
    ) VALUES (
        p_legacy_user_id,
        p_auth0_user_id,
        p_email,
        'completed',
        NOW(),
        v_rollback_data
    );
    
    -- Mark legacy user as migrated (don't delete, keep for rollback)
    UPDATE users 
    SET 
        is_migrated = TRUE,
        auth0_user_id = p_auth0_user_id,
        migrated_at = NOW()
    WHERE id = p_legacy_user_id;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error migrating user %: %', p_legacy_user_id, SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Create function to rollback user migration
CREATE OR REPLACE FUNCTION rollback_user_migration(
    p_auth0_user_id VARCHAR(255)
) RETURNS BOOLEAN AS $$
DECLARE
    v_mapping_record RECORD;
BEGIN
    -- Get mapping record
    SELECT * INTO v_mapping_record
    FROM auth0_user_mapping
    WHERE auth0_user_id = p_auth0_user_id;
    
    IF NOT FOUND THEN
        RAISE NOTICE 'No mapping found for auth0_user_id: %', p_auth0_user_id;
        RETURN FALSE;
    END IF;
    
    -- Restore legacy user status
    UPDATE users 
    SET 
        is_migrated = FALSE,
        auth0_user_id = NULL,
        migrated_at = NULL
    WHERE id = v_mapping_record.legacy_user_id;
    
    -- Update mapping status
    UPDATE auth0_user_mapping
    SET 
        migration_status = 'rolled_back',
        updated_at = NOW()
    WHERE auth0_user_id = p_auth0_user_id;
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error rolling back user migration %: %', p_auth0_user_id, SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    v_cleaned_count INTEGER;
BEGIN
    -- Mark sessions as inactive if they haven't been active for more than 24 hours
    UPDATE auth0_user_sessions
    SET 
        is_active = FALSE,
        session_end = NOW()
    WHERE 
        is_active = TRUE 
        AND last_activity < NOW() - INTERVAL '24 hours';
    
    GET DIAGNOSTICS v_cleaned_count = ROW_COUNT;
    
    -- Delete old inactive sessions (older than 30 days)
    DELETE FROM auth0_user_sessions
    WHERE 
        is_active = FALSE 
        AND session_end < NOW() - INTERVAL '30 days';
    
    RETURN v_cleaned_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to log Auth0 events
CREATE OR REPLACE FUNCTION log_auth0_event(
    p_auth0_log_id VARCHAR(255),
    p_auth0_user_id VARCHAR(255),
    p_event_type VARCHAR(100),
    p_event_description TEXT,
    p_ip_address INET,
    p_user_agent TEXT,
    p_location_info JSONB DEFAULT NULL,
    p_risk_assessment JSONB DEFAULT NULL,
    p_event_data JSONB DEFAULT NULL,
    p_occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) RETURNS BOOLEAN AS $$
BEGIN
    INSERT INTO auth0_audit_logs (
        auth0_log_id,
        auth0_user_id,
        event_type,
        event_description,
        ip_address,
        user_agent,
        location_info,
        risk_assessment,
        event_data,
        occurred_at
    ) VALUES (
        p_auth0_log_id,
        p_auth0_user_id,
        p_event_type,
        p_event_description,
        p_ip_address,
        p_user_agent,
        p_location_info,
        p_risk_assessment,
        p_event_data,
        p_occurred_at
    )
    ON CONFLICT (auth0_log_id) DO UPDATE SET
        processed_at = NOW();
    
    RETURN TRUE;
    
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error logging Auth0 event %: %', p_auth0_log_id, SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- Add migration columns to existing users table (if not exists)
DO $$
BEGIN
    -- Add migration tracking columns to users table
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_migrated') THEN
        ALTER TABLE users ADD COLUMN is_migrated BOOLEAN DEFAULT FALSE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'auth0_user_id') THEN
        ALTER TABLE users ADD COLUMN auth0_user_id VARCHAR(255) UNIQUE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'migrated_at') THEN
        ALTER TABLE users ADD COLUMN migrated_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Create index on auth0_user_id
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_users_auth0_user_id') THEN
        CREATE INDEX idx_users_auth0_user_id ON users(auth0_user_id) WHERE auth0_user_id IS NOT NULL;
    END IF;
END
$$;

-- Create view for migration status
CREATE OR REPLACE VIEW migration_status_view AS
SELECT 
    'Total Users' as metric,
    COUNT(*) as count
FROM users
UNION ALL
SELECT 
    'Migrated Users' as metric,
    COUNT(*) as count
FROM users
WHERE is_migrated = TRUE
UNION ALL
SELECT 
    'Pending Migration' as metric,
    COUNT(*) as count
FROM users
WHERE is_migrated = FALSE
UNION ALL
SELECT 
    'Active Auth0 Sessions' as metric,
    COUNT(*) as count
FROM auth0_user_sessions
WHERE is_active = TRUE
UNION ALL
SELECT 
    'Auth0 Organizations' as metric,
    COUNT(*) as count
FROM auth0_organizations
WHERE is_active = TRUE;

-- Grant permissions to application roles
GRANT SELECT, INSERT, UPDATE ON auth0_user_mapping TO authenticated;
GRANT SELECT ON auth0_roles TO authenticated;
GRANT SELECT ON auth0_organizations TO authenticated;
GRANT SELECT, INSERT, UPDATE ON auth0_user_sessions TO authenticated;
GRANT SELECT, INSERT ON auth0_audit_logs TO authenticated;
GRANT SELECT ON migration_status_view TO authenticated;

-- Grant permissions to anon role for public access
GRANT SELECT ON auth0_roles TO anon;

-- Record this migration
INSERT INTO auth_migrations (migration_name, notes) VALUES (
    'auth0_initial_setup',
    'Initial Auth0 migration setup with user mapping, roles, organizations, sessions, and audit logging'
) ON CONFLICT (migration_name) DO NOTHING;

-- Create RLS policies
ALTER TABLE auth0_user_mapping ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth0_user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth0_audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy for user mapping - users can only see their own mapping
CREATE POLICY "Users can view their own Auth0 mapping" ON auth0_user_mapping
    FOR SELECT USING (
        auth0_user_id = auth.jwt() ->> 'sub'
    );

-- Policy for user sessions - users can only see their own sessions
CREATE POLICY "Users can view their own sessions" ON auth0_user_sessions
    FOR SELECT USING (
        auth0_user_id = auth.jwt() ->> 'sub'
    );

-- Policy for audit logs - users can only see their own logs
CREATE POLICY "Users can view their own audit logs" ON auth0_audit_logs
    FOR SELECT USING (
        auth0_user_id = auth.jwt() ->> 'sub'
    );

-- Admin policies
CREATE POLICY "Admins can view all Auth0 data" ON auth0_user_mapping
    FOR ALL USING (
        auth.jwt() ->> 'https://nextgenfusion.com/roles' LIKE '%admin%'
    );

CREATE POLICY "Admins can view all sessions" ON auth0_user_sessions
    FOR ALL USING (
        auth.jwt() ->> 'https://nextgenfusion.com/roles' LIKE '%admin%'
    );

CREATE POLICY "Admins can view all audit logs" ON auth0_audit_logs
    FOR ALL USING (
        auth.jwt() ->> 'https://nextgenfusion.com/roles' LIKE '%admin%'
    );

COMMIT;