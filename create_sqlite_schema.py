#!/usr/bin/env python3
"""
SQLite Schema Creator for NextGen Fusion Commercial Solar Platform

This script creates a simplified SQLite schema based on the PostgreSQL migrations.
"""

import sqlite3
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sqlite_schema(db_path: str = "./nextgen_fusion.db"):
    """Create SQLite schema with all required tables."""
    
    schema_sql = """
    -- Organizations table
    CREATE TABLE IF NOT EXISTS organizations (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        website VARCHAR(255),
        logo_url VARCHAR(500),
        settings JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT,
        updated_by TEXT
    );

    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        role TEXT NOT NULL DEFAULT 'viewer',
        organization_id TEXT REFERENCES organizations(id),
        preferences JSON DEFAULT '{}',
        last_login DATETIME,
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now'))
    );

    -- Customers table
    CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        organization_id TEXT NOT NULL REFERENCES organizations(id),
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255),
        phone VARCHAR(50),
        address TEXT,
        city VARCHAR(100),
        state_province VARCHAR(100),
        country TEXT NOT NULL,
        postal_code VARCHAR(20),
        customer_type TEXT,
        metadata JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Projects table
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        organization_id TEXT NOT NULL REFERENCES organizations(id),
        customer_id TEXT NOT NULL REFERENCES customers(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        project_type TEXT NOT NULL,
        phase TEXT NOT NULL DEFAULT 'lead',
        system_size_kw DECIMAL(10,3),
        estimated_annual_production_kwh DECIMAL(12,2),
        address TEXT NOT NULL,
        city VARCHAR(100) NOT NULL,
        state_province VARCHAR(100) NOT NULL,
        country TEXT NOT NULL,
        postal_code VARCHAR(20),
        location TEXT,
        timezone VARCHAR(50),
        metadata JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Design 3D Models table (from migration 002)
    CREATE TABLE IF NOT EXISTS design_3d_models (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        project_id TEXT NOT NULL REFERENCES projects(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        model_data JSON NOT NULL DEFAULT '{}',
        roof_geometry JSON DEFAULT '{}',
        panel_layout JSON DEFAULT '{}',
        shading_analysis JSON DEFAULT '{}',
        version INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Solar Panels table (from migration 002)
    CREATE TABLE IF NOT EXISTS solar_panels (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        design_3d_model_id TEXT NOT NULL REFERENCES design_3d_models(id),
        panel_spec_id TEXT REFERENCES panel_specifications(id),
        position_x DECIMAL(10,3) NOT NULL,
        position_y DECIMAL(10,3) NOT NULL,
        position_z DECIMAL(10,3) NOT NULL DEFAULT 0,
        rotation_x DECIMAL(8,3) NOT NULL DEFAULT 0,
        rotation_y DECIMAL(8,3) NOT NULL DEFAULT 0,
        rotation_z DECIMAL(8,3) NOT NULL DEFAULT 0,
        tilt_angle DECIMAL(5,2) NOT NULL,
        azimuth_angle DECIMAL(5,2) NOT NULL,
        string_id INTEGER,
        panel_number INTEGER,
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now'))
    );

    -- Panel Specifications table (from migration 002)
    CREATE TABLE IF NOT EXISTS panel_specifications (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        manufacturer VARCHAR(255) NOT NULL,
        model VARCHAR(255) NOT NULL,
        power_rating_w DECIMAL(8,2) NOT NULL,
        efficiency_percent DECIMAL(5,2) NOT NULL,
        width_mm DECIMAL(8,2) NOT NULL,
        height_mm DECIMAL(8,2) NOT NULL,
        thickness_mm DECIMAL(8,2) NOT NULL,
        weight_kg DECIMAL(8,2) NOT NULL,
        temperature_coefficient DECIMAL(6,4),
        specifications JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now'))
    );

    -- Irradiance Calculations table (from migration 002)
    CREATE TABLE IF NOT EXISTS irradiance_calculations (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        design_3d_model_id TEXT NOT NULL REFERENCES design_3d_models(id),
        calculation_date DATETIME NOT NULL,
        solar_panel_id TEXT REFERENCES solar_panels(id),
        hourly_irradiance JSON NOT NULL DEFAULT '[]',
        daily_total_kwh DECIMAL(10,4),
        monthly_total_kwh DECIMAL(12,4),
        annual_total_kwh DECIMAL(12,4),
        shading_factor DECIMAL(4,3) DEFAULT 1.0,
        weather_data JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now'))
    );

    -- Project Tasks table (from migration 003)
    CREATE TABLE IF NOT EXISTS project_tasks (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        project_id TEXT NOT NULL REFERENCES projects(id),
        title VARCHAR(255) NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        priority TEXT NOT NULL DEFAULT 'medium',
        assigned_to TEXT REFERENCES users(id),
        due_date DATETIME,
        completed_at DATETIME,
        estimated_hours DECIMAL(6,2),
        actual_hours DECIMAL(6,2),
        dependencies JSON DEFAULT '[]',
        metadata JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Project Milestones table (from migration 003)
    CREATE TABLE IF NOT EXISTS project_milestones (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        project_id TEXT NOT NULL REFERENCES projects(id),
        name VARCHAR(255) NOT NULL,
        description TEXT,
        target_date DATETIME NOT NULL,
        actual_date DATETIME,
        status TEXT NOT NULL DEFAULT 'pending',
        completion_percentage DECIMAL(5,2) DEFAULT 0.00,
        deliverables JSON DEFAULT '[]',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Exchange Rates table (from migration 004)
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        from_currency VARCHAR(3) NOT NULL,
        to_currency VARCHAR(3) NOT NULL,
        rate DECIMAL(15,8) NOT NULL,
        effective_date DATETIME NOT NULL,
        source VARCHAR(100),
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now'))
    );

    -- Multi Currency Transactions table (from migration 004)
    CREATE TABLE IF NOT EXISTS multi_currency_transactions (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        project_id TEXT NOT NULL REFERENCES projects(id),
        transaction_type VARCHAR(100) NOT NULL,
        description TEXT,
        amount DECIMAL(15,2) NOT NULL,
        currency VARCHAR(3) NOT NULL,
        exchange_rate_id TEXT REFERENCES exchange_rates(id),
        amount_usd DECIMAL(15,2),
        transaction_date DATETIME NOT NULL,
        metadata JSON DEFAULT '{}',
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Compliance Rules table (from migration 005)
    CREATE TABLE IF NOT EXISTS compliance_rules (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        rule_code VARCHAR(100) UNIQUE NOT NULL,
        jurisdiction TEXT NOT NULL,
        category VARCHAR(100) NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT NOT NULL,
        rule_text TEXT,
        severity TEXT NOT NULL DEFAULT 'warning',
        validation_logic JSON NOT NULL DEFAULT '{}',
        parameters JSON DEFAULT '{}',
        effective_date DATE,
        expiry_date DATE,
        active BOOLEAN DEFAULT TRUE,
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Compliance Checks table (from migration 005)
    CREATE TABLE IF NOT EXISTS compliance_checks (
        id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
        project_id TEXT NOT NULL REFERENCES projects(id),
        design_3d_model_id TEXT REFERENCES design_3d_models(id),
        compliance_rule_id TEXT NOT NULL REFERENCES compliance_rules(id),
        check_date DATETIME NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        result TEXT,
        findings JSON DEFAULT '[]',
        recommendations JSON DEFAULT '[]',
        auto_fixable BOOLEAN DEFAULT FALSE,
        fixed_at DATETIME,
        created_at DATETIME DEFAULT (datetime('now')),
        updated_at DATETIME DEFAULT (datetime('now')),
        created_by TEXT REFERENCES users(id),
        updated_by TEXT REFERENCES users(id)
    );

    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_projects_organization_id ON projects(organization_id);
    CREATE INDEX IF NOT EXISTS idx_projects_customer_id ON projects(customer_id);
    CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
    CREATE INDEX IF NOT EXISTS idx_design_3d_models_project_id ON design_3d_models(project_id);
    CREATE INDEX IF NOT EXISTS idx_solar_panels_design_id ON solar_panels(design_3d_model_id);
    CREATE INDEX IF NOT EXISTS idx_project_tasks_project_id ON project_tasks(project_id);
    CREATE INDEX IF NOT EXISTS idx_project_milestones_project_id ON project_milestones(project_id);
    CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies ON exchange_rates(from_currency, to_currency);
    CREATE INDEX IF NOT EXISTS idx_compliance_checks_project_id ON compliance_checks(project_id);
    """
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.executescript(schema_sql)
            conn.commit()
            
        logger.info(f"Successfully created SQLite schema in {db_path}")
        
        # Verify tables were created
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
        logger.info(f"Created {len(tables)} tables: {', '.join(tables)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create schema: {e}")
        return False


if __name__ == "__main__":
    create_sqlite_schema()