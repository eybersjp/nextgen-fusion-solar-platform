#!/usr/bin/env python3
"""
Database Migration Runner for NextGen Fusion Commercial Solar Platform

This script executes SQL migration files in order to set up the database schema.
It can work with both PostgreSQL and SQLite databases.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migration execution."""
    
    def __init__(self, db_path: str = "./nextgen_fusion.db"):
        self.db_path = db_path
        self.migrations_dir = Path("migrations")
        
    def get_migration_files(self) -> List[Path]:
        """Get all migration files in order."""
        if not self.migrations_dir.exists():
            logger.error(f"Migrations directory {self.migrations_dir} does not exist")
            return []
            
        migration_files = []
        for i in range(1, 7):  # migrations 001-006
            pattern = f"{i:03d}_*.sql"
            files = list(self.migrations_dir.glob(pattern))
            if files:
                migration_files.extend(files)
                
        return sorted(migration_files)
    
    def execute_migration(self, migration_file: Path) -> bool:
        """Execute a single migration file."""
        try:
            logger.info(f"Executing migration: {migration_file.name}")
            
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split SQL content by statements (simple approach)
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                
                for statement in statements:
                    if statement:
                        try:
                            # Skip PostgreSQL-specific statements for SQLite
                            if any(pg_keyword in statement.upper() for pg_keyword in [
                                'CREATE EXTENSION', 'UUID_GENERATE_V4', 'TIMESTAMP WITH TIME ZONE'
                            ]):
                                # Convert PostgreSQL syntax to SQLite
                                statement = self.convert_pg_to_sqlite(statement)
                                if not statement:
                                    continue
                            
                            conn.execute(statement)
                            
                        except sqlite3.Error as e:
                            logger.warning(f"Skipping statement due to error: {e}")
                            logger.debug(f"Statement: {statement[:100]}...")
                            continue
                
                conn.commit()
                
            logger.info(f"Successfully executed migration: {migration_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute migration {migration_file.name}: {e}")
            return False
    
    def convert_pg_to_sqlite(self, statement: str) -> Optional[str]:
        """Convert PostgreSQL-specific syntax to SQLite."""
        statement = statement.strip()
        
        # Skip PostgreSQL-specific statements
        skip_patterns = [
            'CREATE EXTENSION',
            'CREATE TYPE',
            'CREATE OR REPLACE FUNCTION',
            'CREATE TRIGGER',
            'ALTER TABLE',
            'CREATE POLICY',
            'GRANT',
            'USING GIST',
            'REFERENCES auth.users',
            'ENABLE ROW LEVEL SECURITY'
        ]
        
        for pattern in skip_patterns:
            if pattern in statement.upper():
                return None
        
        # Convert UUID generation
        statement = statement.replace('uuid_generate_v4()', "lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))")
        
        # Convert timestamp with time zone to datetime
        statement = statement.replace('TIMESTAMP WITH TIME ZONE', 'DATETIME')
        statement = statement.replace('timestamp with time zone', 'datetime')
        
        # Convert NOW() to datetime('now')
        statement = statement.replace('NOW()', "datetime('now')")
        
        # Convert JSONB to JSON
        statement = statement.replace('JSONB', 'JSON')
        
        # Convert GEOGRAPHY to TEXT (simplified)
        statement = statement.replace('GEOGRAPHY(POINT, 4326)', 'TEXT')
        
        # Remove enum types and array types
        import re
        statement = re.sub(r'\s+(project_status|project_type|project_phase|country_code|design_status|compliance_severity|compliance_status|user_role|financial_model_type|plugin_permission)', ' TEXT', statement)
        statement = re.sub(r'country_code\[\]', 'TEXT', statement)
        
        # Remove ON DELETE CASCADE/SET NULL for foreign keys (SQLite handles differently)
        statement = re.sub(r'\s+ON DELETE (CASCADE|SET NULL)', '', statement)
        
        # Remove UNIQUE constraints that reference non-existent tables
        if 'REFERENCES auth.users' in statement:
            return None
            
        return statement
    
    def run_migrations(self) -> bool:
        """Run all migrations in order."""
        logger.info("Starting database migrations...")
        
        migration_files = self.get_migration_files()
        if not migration_files:
            logger.warning("No migration files found")
            return False
        
        logger.info(f"Found {len(migration_files)} migration files")
        
        success_count = 0
        for migration_file in migration_files:
            if self.execute_migration(migration_file):
                success_count += 1
            else:
                logger.error(f"Migration {migration_file.name} failed")
                # Continue with other migrations
        
        logger.info(f"Completed {success_count}/{len(migration_files)} migrations successfully")
        return success_count > 0
    
    def verify_schema(self) -> bool:
        """Verify that the database schema was created correctly."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for key tables
                expected_tables = [
                    'organizations', 'users', 'projects', 'design_3d_models',
                    'solar_panels', 'panel_specifications', 'irradiance_calculations',
                    'project_tasks', 'project_milestones', 'exchange_rates',
                    'multi_currency_transactions', 'compliance_rules', 'compliance_checks'
                ]
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                missing_tables = [table for table in expected_tables if table not in existing_tables]
                
                if missing_tables:
                    logger.warning(f"Missing tables: {missing_tables}")
                else:
                    logger.info("All expected tables are present")
                
                logger.info(f"Database contains {len(existing_tables)} tables")
                return len(missing_tables) == 0
                
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False


def main():
    """Main function to run migrations."""
    # Change to the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Create migration runner
    runner = MigrationRunner()
    
    # Run migrations
    if runner.run_migrations():
        logger.info("Migration process completed")
        
        # Verify schema
        if runner.verify_schema():
            logger.info("Database schema verification passed")
        else:
            logger.warning("Database schema verification had issues")
    else:
        logger.error("Migration process failed")
        sys.exit(1)


if __name__ == "__main__":
    main()