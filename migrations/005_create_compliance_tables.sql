-- Migration: 005_create_compliance_tables.sql
-- Phase 3: Create compliance tables for validation engine

-- Create compliance_rules table
CREATE TABLE compliance_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    jurisdiction VARCHAR(100) NOT NULL, -- Country/State/Region
    category VARCHAR(50) NOT NULL CHECK (category IN ('electrical', 'structural', 'fire_safety', 'zoning', 'environmental', 'building_code')),
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('mandatory', 'recommended', 'conditional')),
    validation_logic JSONB NOT NULL, -- Rule engine logic
    parameters JSONB DEFAULT '{}'::jsonb,
    severity VARCHAR(20) DEFAULT 'error' CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    effective_date DATE NOT NULL,
    expiry_date DATE,
    version VARCHAR(20) DEFAULT '1.0',
    source_document VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT valid_rule_dates CHECK (expiry_date IS NULL OR expiry_date > effective_date)
);

CREATE TRIGGER update_compliance_rules_updated_at
    BEFORE UPDATE ON compliance_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create compliance_validations table
CREATE TABLE compliance_validations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    design_id UUID REFERENCES design_3d_models(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES compliance_rules(id) ON DELETE CASCADE,
    validation_status VARCHAR(20) NOT NULL CHECK (validation_status IN ('pass', 'fail', 'warning', 'not_applicable', 'pending')),
    validation_result JSONB, -- Detailed results and measurements
    error_message TEXT,
    recommendations TEXT,
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validated_by UUID REFERENCES users(id),
    validation_method VARCHAR(50) DEFAULT 'automatic' CHECK (validation_method IN ('automatic', 'manual', 'hybrid')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create compliance_reports table
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('preliminary', 'final', 'amendment', 'inspection')),
    jurisdiction VARCHAR(100) NOT NULL,
    overall_status VARCHAR(20) NOT NULL CHECK (overall_status IN ('compliant', 'non_compliant', 'conditional', 'pending')),
    total_rules_checked INTEGER NOT NULL DEFAULT 0,
    rules_passed INTEGER NOT NULL DEFAULT 0,
    rules_failed INTEGER NOT NULL DEFAULT 0,
    rules_warning INTEGER NOT NULL DEFAULT 0,
    compliance_percentage DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN total_rules_checked > 0 THEN 
                ROUND((rules_passed::DECIMAL / total_rules_checked::DECIMAL) * 100, 2)
            ELSE 0
        END
    ) STORED,
    report_data JSONB, -- Full report content
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    generated_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES users(id),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_compliance_reports_updated_at
    BEFORE UPDATE ON compliance_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create compliance_exemptions table
CREATE TABLE compliance_exemptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES compliance_rules(id) ON DELETE CASCADE,
    exemption_type VARCHAR(50) NOT NULL CHECK (exemption_type IN ('variance', 'waiver', 'alternative_compliance', 'grandfathered')),
    justification TEXT NOT NULL,
    supporting_documents JSONB DEFAULT '[]'::jsonb,
    granted_by VARCHAR(200), -- Authority/Agency
    granted_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied', 'expired', 'revoked')),
    conditions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, rule_id)
);

CREATE TRIGGER update_compliance_exemptions_updated_at
    BEFORE UPDATE ON compliance_exemptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create compliance_jurisdictions table
CREATE TABLE compliance_jurisdictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    jurisdiction_type VARCHAR(50) NOT NULL CHECK (jurisdiction_type IN ('country', 'state', 'province', 'city', 'county', 'region')),
    parent_jurisdiction_id UUID REFERENCES compliance_jurisdictions(id),
    contact_info JSONB,
    website_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_compliance_jurisdictions_updated_at
    BEFORE UPDATE ON compliance_jurisdictions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default jurisdictions
INSERT INTO compliance_jurisdictions (code, name, jurisdiction_type) VALUES
('ZA', 'South Africa', 'country'),
('AU', 'Australia', 'country'),
('US', 'United States', 'country'),
('EU', 'European Union', 'region'),
('GB', 'United Kingdom', 'country');

-- Create compliance_rule_sets table for grouping rules
CREATE TABLE compliance_rule_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    jurisdiction_id UUID NOT NULL REFERENCES compliance_jurisdictions(id),
    category VARCHAR(50) NOT NULL,
    version VARCHAR(20) DEFAULT '1.0',
    effective_date DATE NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_compliance_rule_sets_updated_at
    BEFORE UPDATE ON compliance_rule_sets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create junction table for rule sets and rules
CREATE TABLE compliance_rule_set_rules (
    rule_set_id UUID NOT NULL REFERENCES compliance_rule_sets(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES compliance_rules(id) ON DELETE CASCADE,
    is_required BOOLEAN DEFAULT true,
    weight DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (rule_set_id, rule_id)
);

-- Create indexes for performance
CREATE INDEX idx_compliance_rules_jurisdiction ON compliance_rules(jurisdiction);
CREATE INDEX idx_compliance_rules_category ON compliance_rules(category);
CREATE INDEX idx_compliance_rules_active ON compliance_rules(is_active);
CREATE INDEX idx_compliance_rules_effective_date ON compliance_rules(effective_date);
CREATE INDEX idx_compliance_rules_code ON compliance_rules(rule_code);

CREATE INDEX idx_compliance_validations_project_id ON compliance_validations(project_id);
CREATE INDEX idx_compliance_validations_design_id ON compliance_validations(design_id);
CREATE INDEX idx_compliance_validations_rule_id ON compliance_validations(rule_id);
CREATE INDEX idx_compliance_validations_status ON compliance_validations(validation_status);
CREATE INDEX idx_compliance_validations_validated_at ON compliance_validations(validated_at DESC);

CREATE INDEX idx_compliance_reports_project_id ON compliance_reports(project_id);
CREATE INDEX idx_compliance_reports_status ON compliance_reports(overall_status);
CREATE INDEX idx_compliance_reports_generated_at ON compliance_reports(generated_at DESC);
CREATE INDEX idx_compliance_reports_jurisdiction ON compliance_reports(jurisdiction);

CREATE INDEX idx_compliance_exemptions_project_id ON compliance_exemptions(project_id);
CREATE INDEX idx_compliance_exemptions_rule_id ON compliance_exemptions(rule_id);
CREATE INDEX idx_compliance_exemptions_status ON compliance_exemptions(status);

CREATE INDEX idx_compliance_jurisdictions_type ON compliance_jurisdictions(jurisdiction_type);
CREATE INDEX idx_compliance_jurisdictions_parent ON compliance_jurisdictions(parent_jurisdiction_id);
CREATE INDEX idx_compliance_jurisdictions_active ON compliance_jurisdictions(is_active);

-- JSONB indexes for better query performance
CREATE INDEX idx_compliance_rules_validation_logic_gin ON compliance_rules USING GIN (validation_logic);
CREATE INDEX idx_compliance_validations_result_gin ON compliance_validations USING GIN (validation_result);