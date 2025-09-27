#!/usr/bin/env node

/**
 * NextGen Fusion Commercial Solar Platform
 * Auth0 Migration Utility Script
 * 
 * This script handles the migration from custom JWT authentication to Auth0
 * including user data migration, role mapping, and configuration setup.
 */

const fs = require('fs')
const path = require('path')
const { Client } = require('pg')
const axios = require('axios')
require('dotenv').config()

// Configuration
const CONFIG = {
  // Database configuration
  database: {
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    database: process.env.DB_NAME || 'nextgen_fusion',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD
  },
  
  // Auth0 configuration
  auth0: {
    domain: process.env.AUTH0_DOMAIN,
    clientId: process.env.AUTH0_CLIENT_ID,
    clientSecret: process.env.AUTH0_CLIENT_SECRET,
    audience: process.env.AUTH0_AUDIENCE,
    managementApiAudience: `https://${process.env.AUTH0_DOMAIN}/api/v2/`
  },
  
  // Migration settings
  migration: {
    batchSize: 100,
    dryRun: process.env.DRY_RUN === 'true',
    skipExisting: process.env.SKIP_EXISTING === 'true',
    logLevel: process.env.LOG_LEVEL || 'info'
  }
}

// Logger utility
class Logger {
  static levels = { error: 0, warn: 1, info: 2, debug: 3 }
  
  static log(level, message, data = null) {
    const currentLevel = this.levels[CONFIG.migration.logLevel] || 2
    if (this.levels[level] <= currentLevel) {
      const timestamp = new Date().toISOString()
      const logMessage = `[${timestamp}] [${level.toUpperCase()}] ${message}`
      
      if (level === 'error') {
        console.error(logMessage, data || '')
      } else {
        console.log(logMessage, data ? JSON.stringify(data, null, 2) : '')
      }
    }
  }
  
  static error(message, data) { this.log('error', message, data) }
  static warn(message, data) { this.log('warn', message, data) }
  static info(message, data) { this.log('info', message, data) }
  static debug(message, data) { this.log('debug', message, data) }
}

// Auth0 Management API client
class Auth0Client {
  constructor() {
    this.accessToken = null
    this.tokenExpiry = null
  }
  
  async getAccessToken() {
    if (this.accessToken && this.tokenExpiry && Date.now() < this.tokenExpiry) {
      return this.accessToken
    }
    
    try {
      const response = await axios.post(`https://${CONFIG.auth0.domain}/oauth/token`, {
        client_id: CONFIG.auth0.clientId,
        client_secret: CONFIG.auth0.clientSecret,
        audience: CONFIG.auth0.managementApiAudience,
        grant_type: 'client_credentials'
      })
      
      this.accessToken = response.data.access_token
      this.tokenExpiry = Date.now() + (response.data.expires_in * 1000) - 60000 // 1 minute buffer
      
      Logger.debug('Auth0 access token obtained')
      return this.accessToken
    } catch (error) {
      Logger.error('Failed to get Auth0 access token', error.response?.data || error.message)
      throw error
    }
  }
  
  async makeRequest(method, endpoint, data = null) {
    const token = await this.getAccessToken()
    const url = `https://${CONFIG.auth0.domain}/api/v2${endpoint}`
    
    try {
      const response = await axios({
        method,
        url,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        data
      })
      
      return response.data
    } catch (error) {
      Logger.error(`Auth0 API request failed: ${method} ${endpoint}`, error.response?.data || error.message)
      throw error
    }
  }
  
  async createUser(userData) {
    return this.makeRequest('POST', '/users', userData)
  }
  
  async updateUser(userId, userData) {
    return this.makeRequest('PATCH', `/users/${userId}`, userData)
  }
  
  async getUserByEmail(email) {
    try {
      const users = await this.makeRequest('GET', `/users-by-email?email=${encodeURIComponent(email)}`)
      return users.length > 0 ? users[0] : null
    } catch (error) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }
  
  async assignRolesToUser(userId, roleIds) {
    return this.makeRequest('POST', `/users/${userId}/roles`, { roles: roleIds })
  }
  
  async createRole(roleData) {
    return this.makeRequest('POST', '/roles', roleData)
  }
  
  async getRoles() {
    return this.makeRequest('GET', '/roles')
  }
  
  async createOrganization(orgData) {
    return this.makeRequest('POST', '/organizations', orgData)
  }
  
  async getOrganizations() {
    return this.makeRequest('GET', '/organizations')
  }
}

// Database client
class DatabaseClient {
  constructor() {
    this.client = new Client(CONFIG.database)
  }
  
  async connect() {
    await this.client.connect()
    Logger.info('Connected to database')
  }
  
  async disconnect() {
    await this.client.end()
    Logger.info('Disconnected from database')
  }
  
  async query(text, params = []) {
    try {
      const result = await this.client.query(text, params)
      return result
    } catch (error) {
      Logger.error('Database query failed', { query: text, error: error.message })
      throw error
    }
  }
  
  async runMigrationScript() {
    const migrationPath = path.join(__dirname, '..', 'migrations', 'auth0-migration.sql')
    
    if (!fs.existsSync(migrationPath)) {
      throw new Error(`Migration script not found: ${migrationPath}`)
    }
    
    const migrationSQL = fs.readFileSync(migrationPath, 'utf8')
    
    Logger.info('Running Auth0 migration script')
    await this.query(migrationSQL)
    Logger.info('Migration script completed successfully')
  }
  
  async getLegacyUsers(limit = CONFIG.migration.batchSize, offset = 0) {
    const query = `
      SELECT 
        u.id,
        u.email,
        u.first_name,
        u.last_name,
        u.phone,
        u.organization,
        u.is_active,
        u.created_at,
        u.is_migrated,
        u.auth0_user_id,
        array_agg(DISTINCT r.name) as roles,
        array_agg(DISTINCT p.name) as permissions
      FROM users u
      LEFT JOIN user_roles ur ON u.id = ur.user_id
      LEFT JOIN roles r ON ur.role_id = r.id
      LEFT JOIN role_permissions rp ON r.id = rp.role_id
      LEFT JOIN permissions p ON rp.permission_id = p.id
      WHERE u.is_migrated = FALSE OR u.is_migrated IS NULL
      GROUP BY u.id, u.email, u.first_name, u.last_name, u.phone, u.organization, u.is_active, u.created_at, u.is_migrated, u.auth0_user_id
      ORDER BY u.created_at
      LIMIT $1 OFFSET $2
    `
    
    const result = await this.query(query, [limit, offset])
    return result.rows
  }
  
  async markUserAsMigrated(userId, auth0UserId) {
    const query = `
      UPDATE users 
      SET 
        is_migrated = TRUE,
        auth0_user_id = $2,
        migrated_at = NOW()
      WHERE id = $1
    `
    
    await this.query(query, [userId, auth0UserId])
  }
  
  async createUserMapping(legacyUserId, auth0UserId, email, rollbackData) {
    const query = `
      INSERT INTO auth0_user_mapping (
        legacy_user_id,
        auth0_user_id,
        email,
        migration_status,
        migrated_at,
        rollback_data
      ) VALUES ($1, $2, $3, 'completed', NOW(), $4)
      ON CONFLICT (auth0_user_id) DO UPDATE SET
        migration_status = 'completed',
        migrated_at = NOW()
    `
    
    await this.query(query, [legacyUserId, auth0UserId, email, JSON.stringify(rollbackData)])
  }
  
  async getMigrationStats() {
    const query = `
      SELECT 
        COUNT(*) as total_users,
        COUNT(*) FILTER (WHERE is_migrated = TRUE) as migrated_users,
        COUNT(*) FILTER (WHERE is_migrated = FALSE OR is_migrated IS NULL) as pending_users
      FROM users
    `
    
    const result = await this.query(query)
    return result.rows[0]
  }
}

// Migration orchestrator
class MigrationOrchestrator {
  constructor() {
    this.auth0Client = new Auth0Client()
    this.dbClient = new DatabaseClient()
    this.stats = {
      totalProcessed: 0,
      successful: 0,
      failed: 0,
      skipped: 0
    }
  }
  
  async initialize() {
    Logger.info('Initializing Auth0 migration')
    
    // Validate configuration
    this.validateConfig()
    
    // Connect to database
    await this.dbClient.connect()
    
    // Run migration script
    if (!CONFIG.migration.dryRun) {
      await this.dbClient.runMigrationScript()
    } else {
      Logger.info('DRY RUN: Skipping migration script execution')
    }
    
    // Setup Auth0 roles and organizations
    await this.setupAuth0Configuration()
    
    Logger.info('Migration initialization completed')
  }
  
  validateConfig() {
    const required = [
      'AUTH0_DOMAIN',
      'AUTH0_CLIENT_ID',
      'AUTH0_CLIENT_SECRET',
      'DB_HOST',
      'DB_NAME',
      'DB_USER',
      'DB_PASSWORD'
    ]
    
    const missing = required.filter(key => !process.env[key])
    
    if (missing.length > 0) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`)
    }
    
    Logger.info('Configuration validated')
  }
  
  async setupAuth0Configuration() {
    Logger.info('Setting up Auth0 configuration')
    
    try {
      // Create default roles in Auth0
      const existingRoles = await this.auth0Client.getRoles()
      const existingRoleNames = existingRoles.map(role => role.name)
      
      const defaultRoles = [
        {
          name: 'Administrator',
          description: 'Full system access',
          permissions: [
            'read:users', 'write:users', 'delete:users',
            'read:projects', 'write:projects', 'delete:projects',
            'read:analytics', 'write:analytics',
            'read:settings', 'write:settings',
            'manage:system'
          ]
        },
        {
          name: 'Manager',
          description: 'Management level access',
          permissions: [
            'read:users', 'write:users',
            'read:projects', 'write:projects',
            'read:analytics', 'write:analytics',
            'read:reports', 'write:reports'
          ]
        },
        {
          name: 'User',
          description: 'Standard user access',
          permissions: [
            'read:projects', 'write:projects',
            'read:reports'
          ]
        },
        {
          name: 'Viewer',
          description: 'Read-only access',
          permissions: [
            'read:projects',
            'read:reports'
          ]
        }
      ]
      
      for (const role of defaultRoles) {
        if (!existingRoleNames.includes(role.name)) {
          if (!CONFIG.migration.dryRun) {
            await this.auth0Client.createRole(role)
            Logger.info(`Created Auth0 role: ${role.name}`)
          } else {
            Logger.info(`DRY RUN: Would create Auth0 role: ${role.name}`)
          }
        } else {
          Logger.info(`Auth0 role already exists: ${role.name}`)
        }
      }
      
    } catch (error) {
      Logger.error('Failed to setup Auth0 configuration', error)
      throw error
    }
  }
  
  async migrateUsers() {
    Logger.info('Starting user migration')
    
    let offset = 0
    let hasMore = true
    
    while (hasMore) {
      const users = await this.dbClient.getLegacyUsers(CONFIG.migration.batchSize, offset)
      
      if (users.length === 0) {
        hasMore = false
        break
      }
      
      Logger.info(`Processing batch of ${users.length} users (offset: ${offset})`)
      
      for (const user of users) {
        await this.migrateUser(user)
      }
      
      offset += CONFIG.migration.batchSize
      
      // Add a small delay between batches to avoid rate limiting
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    Logger.info('User migration completed', this.stats)
  }
  
  async migrateUser(legacyUser) {
    try {
      this.stats.totalProcessed++
      
      // Check if user already migrated
      if (legacyUser.is_migrated && CONFIG.migration.skipExisting) {
        Logger.debug(`Skipping already migrated user: ${legacyUser.email}`)
        this.stats.skipped++
        return
      }
      
      // Check if user already exists in Auth0
      let auth0User = await this.auth0Client.getUserByEmail(legacyUser.email)
      
      if (!auth0User) {
        // Create new user in Auth0
        const userData = {
          email: legacyUser.email,
          email_verified: true,
          name: `${legacyUser.first_name || ''} ${legacyUser.last_name || ''}`.trim(),
          given_name: legacyUser.first_name,
          family_name: legacyUser.last_name,
          phone_number: legacyUser.phone,
          user_metadata: {
            organization: legacyUser.organization,
            migrated_from_legacy: true,
            migration_date: new Date().toISOString()
          },
          app_metadata: {
            roles: legacyUser.roles?.filter(r => r) || [],
            permissions: legacyUser.permissions?.filter(p => p) || [],
            legacy_user_id: legacyUser.id
          },
          connection: 'Username-Password-Authentication'
        }
        
        if (!CONFIG.migration.dryRun) {
          auth0User = await this.auth0Client.createUser(userData)
          Logger.info(`Created Auth0 user: ${legacyUser.email}`)
        } else {
          Logger.info(`DRY RUN: Would create Auth0 user: ${legacyUser.email}`)
          auth0User = { user_id: `auth0|mock_${legacyUser.id}` }
        }
      } else {
        Logger.info(`Auth0 user already exists: ${legacyUser.email}`)
        
        // Update existing user with legacy data
        const updateData = {
          user_metadata: {
            ...auth0User.user_metadata,
            organization: legacyUser.organization,
            migrated_from_legacy: true,
            migration_date: new Date().toISOString()
          },
          app_metadata: {
            ...auth0User.app_metadata,
            roles: legacyUser.roles?.filter(r => r) || [],
            permissions: legacyUser.permissions?.filter(p => p) || [],
            legacy_user_id: legacyUser.id
          }
        }
        
        if (!CONFIG.migration.dryRun) {
          await this.auth0Client.updateUser(auth0User.user_id, updateData)
          Logger.info(`Updated Auth0 user: ${legacyUser.email}`)
        } else {
          Logger.info(`DRY RUN: Would update Auth0 user: ${legacyUser.email}`)
        }
      }
      
      // Create mapping and mark as migrated
      if (!CONFIG.migration.dryRun) {
        await this.dbClient.createUserMapping(
          legacyUser.id,
          auth0User.user_id,
          legacyUser.email,
          {
            roles: legacyUser.roles,
            permissions: legacyUser.permissions,
            profile: {
              first_name: legacyUser.first_name,
              last_name: legacyUser.last_name,
              phone: legacyUser.phone,
              organization: legacyUser.organization
            }
          }
        )
        
        await this.dbClient.markUserAsMigrated(legacyUser.id, auth0User.user_id)
      }
      
      this.stats.successful++
      Logger.debug(`Successfully migrated user: ${legacyUser.email}`)
      
    } catch (error) {
      this.stats.failed++
      Logger.error(`Failed to migrate user: ${legacyUser.email}`, error.message)
    }
  }
  
  async generateReport() {
    Logger.info('Generating migration report')
    
    const dbStats = await this.dbClient.getMigrationStats()
    
    const report = {
      migration_summary: {
        total_users_in_database: parseInt(dbStats.total_users),
        migrated_users: parseInt(dbStats.migrated_users),
        pending_users: parseInt(dbStats.pending_users)
      },
      batch_processing_stats: this.stats,
      migration_config: {
        dry_run: CONFIG.migration.dryRun,
        batch_size: CONFIG.migration.batchSize,
        skip_existing: CONFIG.migration.skipExisting
      },
      timestamp: new Date().toISOString()
    }
    
    // Save report to file
    const reportPath = path.join(__dirname, '..', 'logs', `migration-report-${Date.now()}.json`)
    
    // Ensure logs directory exists
    const logsDir = path.dirname(reportPath)
    if (!fs.existsSync(logsDir)) {
      fs.mkdirSync(logsDir, { recursive: true })
    }
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
    
    Logger.info('Migration report generated', report)
    Logger.info(`Report saved to: ${reportPath}`)
    
    return report
  }
  
  async cleanup() {
    await this.dbClient.disconnect()
    Logger.info('Migration cleanup completed')
  }
  
  async run() {
    try {
      await this.initialize()
      await this.migrateUsers()
      await this.generateReport()
    } catch (error) {
      Logger.error('Migration failed', error)
      throw error
    } finally {
      await this.cleanup()
    }
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2)
  const command = args[0] || 'migrate'
  
  async function main() {
    const orchestrator = new MigrationOrchestrator()
    
    switch (command) {
      case 'migrate':
        Logger.info('Starting Auth0 migration')
        await orchestrator.run()
        break
        
      case 'setup':
        Logger.info('Setting up Auth0 configuration only')
        await orchestrator.initialize()
        await orchestrator.cleanup()
        break
        
      case 'report':
        Logger.info('Generating migration report')
        await orchestrator.initialize()
        await orchestrator.generateReport()
        await orchestrator.cleanup()
        break
        
      default:
        console.log('Usage: node auth0-migration.js [migrate|setup|report]')
        console.log('  migrate - Run full migration (default)')
        console.log('  setup   - Setup Auth0 configuration only')
        console.log('  report  - Generate migration report')
        process.exit(1)
    }
    
    Logger.info('Migration script completed successfully')
  }
  
  main().catch(error => {
    Logger.error('Migration script failed', error)
    process.exit(1)
  })
}

module.exports = {
  MigrationOrchestrator,
  Auth0Client,
  DatabaseClient,
  Logger,
  CONFIG
}