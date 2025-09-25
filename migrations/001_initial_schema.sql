-- NextGen Fusion Commercial Solar Platform - Initial Database Schema
-- This migration creates the core tables for the solar platform

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
CREATE TYPE project_status AS ENUM ('draft', 'active', 'on_hold', 'completed', 'cancelled');
CREATE TYPE project_type AS ENUM ('residential', 'commercial', 'utility', 'community');
CREATE TYPE project_phase AS ENUM ('lead', 'design', 'permitting', 'procurement', 'installation', 'commissioning', 'operations');
CREATE TYPE country_code AS ENUM ('ZA', 'AU', 'US');
CREATE TYPE design_status AS ENUM ('draft', 'under_review', 'approved', 'rejected', 'archived');
CREATE TYPE compliance_severity AS ENUM ('info', 'warning', 'error', 'critical');
CREATE TYPE compliance_status AS ENUM ('open', 'acknowledged', 'resolved', 'waived');
CREATE TYPE user_role AS ENUM ('admin', 'manager', 'designer', 'sales', 'installer', 'viewer');
CREATE TYPE financial_model_type AS ENUM ('cash_purchase', 'loan', 'lease', 'ppa');
CREATE TYPE plugin_permission AS ENUM ('read_projects', 'write_projects', 'read_designs', 'write_designs', 'access_external_apis', 'file_system_access');

-- Organizations table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    website VARCHAR(255),
    logo_url VARCHAR(500),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    updated_by UUID
);

-- Users table (extends Supabase auth.users)
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    preferences JSONB DEFAULT '{}',
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state_province VARCHAR(100),
    country country_code NOT NULL,
    postal_code VARCHAR(20),
    customer_type project_type,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status project_status NOT NULL DEFAULT 'draft',
    project_type project_type NOT NULL,
    phase project_phase NOT NULL DEFAULT 'lead',
    system_size_kw DECIMAL(10,3),
    estimated_annual_production_kwh DECIMAL(12,2),
    
    -- Location data
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state_province VARCHAR(100) NOT NULL,
    country country_code NOT NULL,
    postal_code VARCHAR(20),
    location GEOGRAPHY(POINT, 4326), -- PostGIS point for lat/lng
    timezone VARCHAR(50),
    
    -- Metadata and tracking
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Designs table
CREATE TABLE designs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status design_status NOT NULL DEFAULT 'draft',
    
    -- Layout and system data (stored as JSONB for flexibility)
    layout_data JSONB NOT NULL DEFAULT '{}',
    system_specifications JSONB NOT NULL DEFAULT '{}',
    performance_estimates JSONB NOT NULL DEFAULT '{}',
    bill_of_materials JSONB DEFAULT '{}',
    
    -- Metadata and tracking
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    
    UNIQUE(project_id, version)
);

-- Compliance findings table
CREATE TABLE compliance_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    design_id UUID REFERENCES designs(id) ON DELETE CASCADE,
    rule_id VARCHAR(100) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    country_pack country_code NOT NULL,
    severity compliance_severity NOT NULL,
    status compliance_status NOT NULL DEFAULT 'open',
    description TEXT NOT NULL,
    recommendation TEXT,
    auto_fixable BOOLEAN DEFAULT FALSE,
    
    -- Metadata and tracking
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Financial models table
CREATE TABLE financial_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    model_type financial_model_type NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Financial data (stored as JSONB for flexibility)
    assumptions JSONB NOT NULL DEFAULT '{}',
    cash_flows JSONB NOT NULL DEFAULT '[]',
    metrics JSONB NOT NULL DEFAULT '{}',
    sensitivity_analysis JSONB DEFAULT '{}',
    
    -- Metadata and tracking
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);

-- Plugin registry table
CREATE TABLE plugins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plugin_id VARCHAR(100) UNIQUE NOT NULL, -- from manifest
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    author VARCHAR(255),
    license VARCHAR(100),
    
    -- Plugin configuration
    manifest JSONB NOT NULL,
    configuration JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT TRUE,
    
    -- Installation tracking
    installed_by UUID REFERENCES users(id),
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(plugin_id, version)
);

-- Plugin permissions table
CREATE TABLE plugin_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plugin_id UUID NOT NULL REFERENCES plugins(id) ON DELETE CASCADE,
    permission plugin_permission NOT NULL,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(plugin_id, permission)
);

-- Country compliance rules table
CREATE TABLE compliance_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id VARCHAR(100) NOT NULL,
    country country_code NOT NULL,
    jurisdiction VARCHAR(100), -- state, province, or local jurisdiction
    category VARCHAR(100) NOT NULL, -- electrical, structural, fire, etc.
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rule_text TEXT,
    severity compliance_severity NOT NULL DEFAULT 'warning',
    
    -- Rule logic (stored as JSONB for flexibility)
    conditions JSONB NOT NULL DEFAULT '{}',
    validation_logic JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    source VARCHAR(255), -- code reference, standard, etc.
    effective_date DATE,
    version VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(rule_id, country, jurisdiction)
);

-- Equipment catalog table
CREATE TABLE equipment_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL, -- module, inverter, racking, etc.
    manufacturer VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Technical specifications (stored as JSONB for flexibility)
    specifications JSONB NOT NULL DEFAULT '{}',
    
    -- Pricing and availability
    unit_price DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    availability_regions country_code[],
    
    -- Certifications and compliance
    certifications JSONB DEFAULT '{}',
    
    -- Metadata
    datasheet_url VARCHAR(500),
    image_url VARCHAR(500),
    active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(manufacturer, model)
);

-- Create indexes for performance
CREATE INDEX idx_projects_organization_id ON projects(organization_id);
CREATE INDEX idx_projects_customer_id ON projects(customer_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_location ON projects USING GIST(location);
CREATE INDEX idx_projects_country ON projects(country);

CREATE INDEX idx_designs_project_id ON designs(project_id);
CREATE INDEX idx_designs_status ON designs(status);

CREATE INDEX idx_compliance_findings_project_id ON compliance_findings(project_id);
CREATE INDEX idx_compliance_findings_design_id ON compliance_findings(design_id);
CREATE INDEX idx_compliance_findings_status ON compliance_findings(status);
CREATE INDEX idx_compliance_findings_severity ON compliance_findings(severity);

CREATE INDEX idx_financial_models_project_id ON financial_models(project_id);

CREATE INDEX idx_plugins_plugin_id ON plugins(plugin_id);
CREATE INDEX idx_plugins_enabled ON plugins(enabled);

CREATE INDEX idx_compliance_rules_country ON compliance_rules(country);
CREATE INDEX idx_compliance_rules_category ON compliance_rules(category);
CREATE INDEX idx_compliance_rules_active ON compliance_rules(active);

CREATE INDEX idx_equipment_catalog_category ON equipment_catalog(category);
CREATE INDEX idx_equipment_catalog_manufacturer ON equipment_catalog(manufacturer);
CREATE INDEX idx_equipment_catalog_active ON equipment_catalog(active);

-- Create updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_designs_updated_at BEFORE UPDATE ON designs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_compliance_findings_updated_at BEFORE UPDATE ON compliance_findings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_financial_models_updated_at BEFORE UPDATE ON financial_models FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_plugins_updated_at BEFORE UPDATE ON plugins FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_compliance_rules_updated_at BEFORE UPDATE ON compliance_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_equipment_catalog_updated_at BEFORE UPDATE ON equipment_catalog FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE designs ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE plugins ENABLE ROW LEVEL SECURITY;
ALTER TABLE plugin_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_catalog ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (organization-based access)
CREATE POLICY "Users can view their organization's data" ON organizations
    FOR SELECT USING (id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    ));

CREATE POLICY "Users can view their own profile" ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY "Users can view their organization's customers" ON customers
    FOR SELECT USING (organization_id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    ));

CREATE POLICY "Users can view their organization's projects" ON projects
    FOR SELECT USING (organization_id IN (
        SELECT organization_id FROM users WHERE id = auth.uid()
    ));

CREATE POLICY "Users can view designs for their organization's projects" ON designs
    FOR SELECT USING (project_id IN (
        SELECT id FROM projects WHERE organization_id IN (
            SELECT organization_id FROM users WHERE id = auth.uid()
        )
    ));

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant read access to anonymous users for public data
GRANT SELECT ON compliance_rules TO anon;
GRANT SELECT ON equipment_catalog TO anon;