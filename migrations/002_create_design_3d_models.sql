-- Migration: 002_create_design_3d_models.sql
-- Phase 3: Create 3D design models and related tables

-- Create design_3d_models table
CREATE TABLE design_3d_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    building_geometry JSONB NOT NULL,
    panel_layout JSONB NOT NULL DEFAULT '[]'::jsonb,
    simulation_parameters JSONB DEFAULT '{}'::jsonb,
    total_capacity DECIMAL(10,2),
    estimated_output DECIMAL(12,2),
    validation_status VARCHAR(50) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'valid', 'invalid', 'warning')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_design_3d_models_updated_at
    BEFORE UPDATE ON design_3d_models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create solar_panels table
CREATE TABLE solar_panels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID NOT NULL REFERENCES design_3d_models(id) ON DELETE CASCADE,
    panel_type VARCHAR(100) NOT NULL,
    power_rating DECIMAL(8,2) NOT NULL CHECK (power_rating > 0),
    position_coordinates JSONB NOT NULL,
    rotation_angles JSONB NOT NULL,
    mounting_type VARCHAR(50) DEFAULT 'roof_mounted',
    efficiency DECIMAL(5,2) CHECK (efficiency > 0 AND efficiency <= 100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create panel_specifications table
CREATE TABLE panel_specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manufacturer VARCHAR(100) NOT NULL,
    model_number VARCHAR(100) NOT NULL,
    power_rating DECIMAL(8,2) NOT NULL,
    efficiency DECIMAL(5,2) NOT NULL,
    dimensions JSONB NOT NULL, -- {length, width, thickness} in mm
    technology_type VARCHAR(50) NOT NULL,
    temperature_coefficient DECIMAL(6,4),
    warranty_years INTEGER DEFAULT 25,
    certification_standards JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(manufacturer, model_number)
);

CREATE TRIGGER update_panel_specifications_updated_at
    BEFORE UPDATE ON panel_specifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create irradiance_calculations table
CREATE TABLE irradiance_calculations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    design_id UUID NOT NULL REFERENCES design_3d_models(id) ON DELETE CASCADE,
    annual_irradiance DECIMAL(8,2),
    monthly_data JSONB, -- Array of 12 monthly values
    shading_analysis JSONB,
    performance_ratio DECIMAL(5,2) CHECK (performance_ratio >= 0 AND performance_ratio <= 1),
    calculation_method VARCHAR(50) DEFAULT 'pvlib',
    weather_data_source VARCHAR(100),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_design_3d_models_project_id ON design_3d_models(project_id);
CREATE INDEX idx_design_3d_models_status ON design_3d_models(validation_status);
CREATE INDEX idx_design_3d_models_created_at ON design_3d_models(created_at DESC);

CREATE INDEX idx_solar_panels_design_id ON solar_panels(design_id);
CREATE INDEX idx_solar_panels_type ON solar_panels(panel_type);

CREATE INDEX idx_irradiance_calculations_design_id ON irradiance_calculations(design_id);
CREATE INDEX idx_irradiance_calculations_calculated_at ON irradiance_calculations(calculated_at DESC);

-- JSONB indexes for better query performance
CREATE INDEX idx_design_3d_models_building_geometry_gin ON design_3d_models USING GIN (building_geometry);