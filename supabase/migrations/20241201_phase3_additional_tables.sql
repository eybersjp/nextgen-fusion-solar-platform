-- Phase 3 Additional Tables Migration
-- This migration adds new tables for Phase 3 functionality

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create organizations table (referenced by projects but missing)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) CHECK (type IN ('company', 'government', 'nonprofit', 'individual')),
    registration_number VARCHAR(100),
    tax_id VARCHAR(100),
    address JSONB,
    contact_info JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create customers table (referenced by projects but missing)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    address JSONB,
    customer_type VARCHAR(50) DEFAULT 'individual' CHECK (customer_type IN ('individual', 'business')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create weather_data table for irradiance calculations
CREATE TABLE IF NOT EXISTS weather_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_coordinates JSONB NOT NULL,
    data_source VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER CHECK (month >= 1 AND month <= 12),
    daily_data JSONB,
    monthly_summary JSONB,
    annual_summary JSONB,
    data_quality_score NUMERIC(3,2) CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create cad_exports table for 3D design exports
CREATE TABLE IF NOT EXISTS cad_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID NOT NULL REFERENCES design_3d_models(id),
    export_format VARCHAR(20) NOT NULL CHECK (export_format IN ('dwg', 'dxf', 'step', 'iges', 'pdf')),
    file_path VARCHAR(500),
    file_size BIGINT,
    export_parameters JSONB,
    export_status VARCHAR(20) DEFAULT 'pending' CHECK (export_status IN ('pending', 'processing', 'completed', 'failed')),
    exported_by UUID REFERENCES users(id),
    exported_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create system_components table for detailed system design
CREATE TABLE IF NOT EXISTS system_components (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID NOT NULL REFERENCES design_3d_models(id),
    component_type VARCHAR(50) NOT NULL CHECK (component_type IN ('inverter', 'battery', 'monitoring', 'mounting', 'electrical')),
    manufacturer VARCHAR(100),
    model_number VARCHAR(100),
    specifications JSONB,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_cost NUMERIC(12,2),
    position_data JSONB,
    installation_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create project_documents table for document management
CREATE TABLE IF NOT EXISTS project_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN ('contract', 'permit', 'design', 'compliance', 'invoice', 'report', 'other')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500),
    file_size BIGINT,
    mime_type VARCHAR(100),
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create energy_calculations table for performance analysis
CREATE TABLE IF NOT EXISTS energy_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID NOT NULL REFERENCES design_3d_models(id),
    calculation_type VARCHAR(50) NOT NULL CHECK (calculation_type IN ('annual_production', 'monthly_production', 'performance_ratio', 'degradation')),
    input_parameters JSONB NOT NULL,
    calculation_results JSONB NOT NULL,
    calculation_method VARCHAR(100),
    confidence_level NUMERIC(3,2) CHECK (confidence_level >= 0 AND confidence_level <= 1),
    calculated_at TIMESTAMPTZ DEFAULT now(),
    calculated_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create project_phases table for detailed project management
CREATE TABLE IF NOT EXISTS project_phases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id),
    phase_name VARCHAR(100) NOT NULL,
    phase_order INTEGER NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'cancelled', 'on_hold')),
    completion_percentage NUMERIC(5,2) DEFAULT 0 CHECK (completion_percentage >= 0 AND completion_percentage <= 100),
    budget_allocated NUMERIC(12,2),
    budget_spent NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create compliance_templates table for reusable compliance configurations
CREATE TABLE IF NOT EXISTS compliance_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    jurisdiction VARCHAR(100) NOT NULL,
    template_type VARCHAR(50) NOT NULL CHECK (template_type IN ('residential', 'commercial', 'industrial', 'utility')),
    rule_configuration JSONB NOT NULL,
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create audit_trail table for comprehensive change tracking
CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values JSONB,
    new_values JSONB,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT now(),
    ip_address INET,
    user_agent TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_weather_data_location ON weather_data USING GIN(location_coordinates);
CREATE INDEX IF NOT EXISTS idx_cad_exports_design_id ON cad_exports(design_id);
CREATE INDEX IF NOT EXISTS idx_system_components_design_id ON system_components(design_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_project_id ON project_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_energy_calculations_design_id ON energy_calculations(design_id);
CREATE INDEX IF NOT EXISTS idx_project_phases_project_id ON project_phases(project_id);
CREATE INDEX IF NOT EXISTS idx_compliance_templates_jurisdiction ON compliance_templates(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_audit_trail_table_record ON audit_trail(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_changed_at ON audit_trail(changed_at);

-- Add updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_weather_data_updated_at BEFORE UPDATE ON weather_data FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_components_updated_at BEFORE UPDATE ON system_components FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_project_documents_updated_at BEFORE UPDATE ON project_documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_project_phases_updated_at BEFORE UPDATE ON project_phases FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_compliance_templates_updated_at BEFORE UPDATE ON compliance_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for supported currencies (if not exists)
INSERT INTO supported_currencies (code, name, symbol, decimal_places, is_active, country_code) 
VALUES 
    ('ZAR', 'South African Rand', 'R', 2, true, 'ZA'),
    ('AUD', 'Australian Dollar', 'A$', 2, true, 'AU'),
    ('USD', 'US Dollar', '$', 2, true, 'US'),
    ('EUR', 'Euro', '€', 2, true, 'EU'),
    ('GBP', 'British Pound', '£', 2, true, 'GB')
ON CONFLICT (code) DO NOTHING;

-- Insert sample compliance jurisdictions
INSERT INTO compliance_jurisdictions (code, name, jurisdiction_type, is_active)
VALUES 
    ('ZA', 'South Africa', 'country', true),
    ('AU', 'Australia', 'country', true),
    ('US', 'United States', 'country', true),
    ('EU', 'European Union', 'region', true)
ON CONFLICT (code) DO NOTHING;

-- Insert sample compliance rules
INSERT INTO compliance_rules (rule_code, name, description, jurisdiction, category, rule_type, validation_logic, effective_date)
VALUES 
    ('ZA-ELEC-001', 'Electrical Safety Standards', 'Basic electrical safety requirements for solar installations', 'ZA', 'electrical', 'mandatory', '{"type": "safety_check", "parameters": {"min_clearance": 1.5}}', '2024-01-01'),
    ('AU-STRUCT-001', 'Structural Load Requirements', 'Structural load calculations for roof-mounted systems', 'AU', 'structural', 'mandatory', '{"type": "load_calculation", "parameters": {"wind_load": 1.5, "snow_load": 0.5}}', '2024-01-01'),
    ('US-FIRE-001', 'Fire Safety Setbacks', 'Required setbacks for fire safety access', 'US', 'fire_safety', 'mandatory', '{"type": "setback_check", "parameters": {"min_setback": 3.0}}', '2024-01-01')
ON CONFLICT (rule_code) DO NOTHING;

COMMIT;