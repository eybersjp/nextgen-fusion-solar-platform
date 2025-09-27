-- Phase 3: Update existing tables to support new features
-- This migration adds new columns to existing tables for Phase 3 functionality

-- Update projects table to support Phase 3 features
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS project_manager_id UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS estimated_start_date DATE,
ADD COLUMN IF NOT EXISTS estimated_completion_date DATE,
ADD COLUMN IF NOT EXISTS actual_start_date DATE,
ADD COLUMN IF NOT EXISTS actual_completion_date DATE,
ADD COLUMN IF NOT EXISTS project_priority VARCHAR(20) DEFAULT 'medium' CHECK (project_priority IN ('low', 'medium', 'high', 'critical')),
ADD COLUMN IF NOT EXISTS budget_allocated NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS budget_spent NUMERIC(12,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS currency_code VARCHAR(3) DEFAULT 'USD' REFERENCES supported_currencies(code),
ADD COLUMN IF NOT EXISTS project_tags TEXT[],
ADD COLUMN IF NOT EXISTS risk_assessment JSONB,
ADD COLUMN IF NOT EXISTS compliance_status VARCHAR(20) DEFAULT 'pending' CHECK (compliance_status IN ('pending', 'in_review', 'approved', 'rejected', 'conditional'));

-- Update users table to support Phase 3 features
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS preferred_currency VARCHAR(3) DEFAULT 'USD' REFERENCES supported_currencies(code),
ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC',
ADD COLUMN IF NOT EXISTS language_preference VARCHAR(10) DEFAULT 'en',
ADD COLUMN IF NOT EXISTS notification_preferences JSONB DEFAULT '{"email": true, "sms": false, "push": true}',
ADD COLUMN IF NOT EXISTS user_permissions JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_2fa_enabled BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS department VARCHAR(100),
ADD COLUMN IF NOT EXISTS job_title VARCHAR(100);

-- Update design_3d_models table to support additional features
ALTER TABLE design_3d_models 
ADD COLUMN IF NOT EXISTS design_version VARCHAR(20) DEFAULT '1.0',
ADD COLUMN IF NOT EXISTS design_stage VARCHAR(20) DEFAULT 'draft' CHECK (design_stage IN ('draft', 'review', 'approved', 'final')),
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'rejected', 'revision_required')),
ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS revision_notes TEXT,
ADD COLUMN IF NOT EXISTS design_complexity VARCHAR(20) DEFAULT 'medium' CHECK (design_complexity IN ('simple', 'medium', 'complex')),
ADD COLUMN IF NOT EXISTS estimated_installation_time INTEGER; -- in hours

-- Update organizations table to support Phase 3 features
ALTER TABLE organizations 
ADD COLUMN IF NOT EXISTS default_currency VARCHAR(3) DEFAULT 'USD' REFERENCES supported_currencies(code),
ADD COLUMN IF NOT EXISTS billing_address JSONB,
ADD COLUMN IF NOT EXISTS payment_terms INTEGER DEFAULT 30, -- days
ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS organization_size VARCHAR(20) CHECK (organization_size IN ('small', 'medium', 'large', 'enterprise')),
ADD COLUMN IF NOT EXISTS industry VARCHAR(100),
ADD COLUMN IF NOT EXISTS website VARCHAR(255),
ADD COLUMN IF NOT EXISTS linkedin_profile VARCHAR(255);

-- Update customers table to support Phase 3 features
ALTER TABLE customers 
ADD COLUMN IF NOT EXISTS preferred_currency VARCHAR(3) DEFAULT 'USD' REFERENCES supported_currencies(code),
ADD COLUMN IF NOT EXISTS communication_preferences JSONB DEFAULT '{"email": true, "phone": false, "sms": false}',
ADD COLUMN IF NOT EXISTS customer_segment VARCHAR(50),
ADD COLUMN IF NOT EXISTS lead_source VARCHAR(100),
ADD COLUMN IF NOT EXISTS credit_score INTEGER,
ADD COLUMN IF NOT EXISTS payment_history JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS notes TEXT,
ADD COLUMN IF NOT EXISTS assigned_sales_rep UUID REFERENCES users(id);

-- Create indexes for better performance on new columns
CREATE INDEX IF NOT EXISTS idx_projects_manager ON projects(project_manager_id);
CREATE INDEX IF NOT EXISTS idx_projects_currency ON projects(currency_code);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(compliance_status);
CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects(project_priority);
CREATE INDEX IF NOT EXISTS idx_projects_dates ON projects(estimated_start_date, estimated_completion_date);

CREATE INDEX IF NOT EXISTS idx_users_currency ON users(preferred_currency);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login_at);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);

CREATE INDEX IF NOT EXISTS idx_design_3d_models_version ON design_3d_models(design_version);
CREATE INDEX IF NOT EXISTS idx_design_3d_models_stage ON design_3d_models(design_stage);
CREATE INDEX IF NOT EXISTS idx_design_3d_models_approval ON design_3d_models(approval_status);
CREATE INDEX IF NOT EXISTS idx_design_3d_models_approved_by ON design_3d_models(approved_by);

CREATE INDEX IF NOT EXISTS idx_organizations_currency ON organizations(default_currency);
CREATE INDEX IF NOT EXISTS idx_organizations_size ON organizations(organization_size);
CREATE INDEX IF NOT EXISTS idx_organizations_industry ON organizations(industry);

CREATE INDEX IF NOT EXISTS idx_customers_currency ON customers(preferred_currency);
CREATE INDEX IF NOT EXISTS idx_customers_segment ON customers(customer_segment);
CREATE INDEX IF NOT EXISTS idx_customers_sales_rep ON customers(assigned_sales_rep);

-- Update existing records with default values where appropriate
UPDATE projects SET currency_code = 'USD' WHERE currency_code IS NULL;
UPDATE projects SET project_priority = 'medium' WHERE project_priority IS NULL;
UPDATE projects SET compliance_status = 'pending' WHERE compliance_status IS NULL;
UPDATE projects SET budget_spent = 0 WHERE budget_spent IS NULL;

UPDATE users SET preferred_currency = 'USD' WHERE preferred_currency IS NULL;
UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL;
UPDATE users SET language_preference = 'en' WHERE language_preference IS NULL;
UPDATE users SET notification_preferences = '{"email": true, "sms": false, "push": true}' WHERE notification_preferences IS NULL;
UPDATE users SET user_permissions = '{}' WHERE user_permissions IS NULL;
UPDATE users SET login_count = 0 WHERE login_count IS NULL;
UPDATE users SET is_2fa_enabled = false WHERE is_2fa_enabled IS NULL;

UPDATE design_3d_models SET design_version = '1.0' WHERE design_version IS NULL;
UPDATE design_3d_models SET design_stage = 'draft' WHERE design_stage IS NULL;
UPDATE design_3d_models SET approval_status = 'pending' WHERE approval_status IS NULL;
UPDATE design_3d_models SET design_complexity = 'medium' WHERE design_complexity IS NULL;

UPDATE organizations SET default_currency = 'USD' WHERE default_currency IS NULL;
UPDATE organizations SET payment_terms = 30 WHERE payment_terms IS NULL;

UPDATE customers SET preferred_currency = 'USD' WHERE preferred_currency IS NULL;
UPDATE customers SET communication_preferences = '{"email": true, "phone": false, "sms": false}' WHERE communication_preferences IS NULL;
UPDATE customers SET payment_history = '{}' WHERE payment_history IS NULL;

COMMIT;