/**
 * Plugin management routes for the API Gateway
 * Handles plugin registration, discovery, and lifecycle management
 */

import { Router, Request, Response } from 'express';
import { createClient } from '@supabase/supabase-js';
import { authMiddleware, requireRole } from '../middleware/auth.js';
import { asyncHandler } from '../middleware/error.js';
import { logger } from '../utils/logger.js';
import { PluginManifest } from '../../../shared/types.js';

const router = Router();

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL!;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

/**
 * GET /plugins
 * List all available plugins
 */
router.get('/', authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  const { category, status, organization_id } = req.query;
  
  let query = supabase
    .from('plugins')
    .select(`
      id,
      name,
      version,
      description,
      category,
      status,
      manifest,
      organization_id,
      created_at,
      updated_at
    `);
  
  // Apply filters
  if (category) {
    query = query.eq('category', category);
  }
  
  if (status) {
    query = query.eq('status', status);
  }
  
  // Filter by organization for non-admin users
  if (req.user?.role !== 'admin') {
    query = query.or(`organization_id.is.null,organization_id.eq.${req.user?.organization_id}`);
  } else if (organization_id) {
    query = query.eq('organization_id', organization_id);
  }
  
  const { data: plugins, error } = await query.order('created_at', { ascending: false });
  
  if (error) {
    logger.error('Failed to fetch plugins:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to fetch plugins'
    });
  }
  
  res.json({
    success: true,
    data: plugins
  });
}));

/**
 * GET /plugins/:id
 * Get plugin details
 */
router.get('/:id', authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  
  let query = supabase
    .from('plugins')
    .select('*')
    .eq('id', id);
  
  // Filter by organization for non-admin users
  if (req.user?.role !== 'admin') {
    query = query.or(`organization_id.is.null,organization_id.eq.${req.user?.organization_id}`);
  }
  
  const { data: plugin, error } = await query.single();
  
  if (error || !plugin) {
    return res.status(404).json({
      success: false,
      error: 'Plugin not found'
    });
  }
  
  res.json({
    success: true,
    data: plugin
  });
}));

/**
 * POST /plugins
 * Register a new plugin
 */
router.post('/', authMiddleware, requireRole(['admin', 'developer']), asyncHandler(async (req: Request, res: Response) => {
  const manifest: PluginManifest = req.body;
  
  // Validate manifest
  if (!manifest.name || !manifest.version || !manifest.entry_point) {
    return res.status(400).json({
      success: false,
      error: 'Invalid plugin manifest. Required fields: name, version, entry_point'
    });
  }
  
  // Check if plugin already exists
  const { data: existing } = await supabase
    .from('plugins')
    .select('id')
    .eq('name', manifest.name)
    .eq('version', manifest.version)
    .eq('organization_id', req.user?.organization_id || null)
    .single();
  
  if (existing) {
    return res.status(409).json({
      success: false,
      error: 'Plugin with this name and version already exists'
    });
  }
  
  // Create plugin record
  const { data: plugin, error } = await supabase
    .from('plugins')
    .insert({
      name: manifest.name,
      version: manifest.version,
      description: manifest.description,
      category: manifest.category || 'general',
      status: 'pending',
      manifest,
      organization_id: req.user?.organization_id || null,
      created_by: req.user?.id
    })
    .select()
    .single();
  
  if (error) {
    logger.error('Failed to register plugin:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to register plugin'
    });
  }
  
  logger.info(`Plugin registered: ${manifest.name}@${manifest.version} by ${req.user?.email}`);
  
  res.status(201).json({
    success: true,
    data: plugin
  });
}));

/**
 * PUT /plugins/:id/status
 * Update plugin status (approve/reject/disable)
 */
router.put('/:id/status', authMiddleware, requireRole(['admin']), asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  const { status, reason } = req.body;
  
  if (!['approved', 'rejected', 'disabled'].includes(status)) {
    return res.status(400).json({
      success: false,
      error: 'Invalid status. Must be one of: approved, rejected, disabled'
    });
  }
  
  const { data: plugin, error } = await supabase
    .from('plugins')
    .update({
      status,
      status_reason: reason,
      updated_at: new Date().toISOString()
    })
    .eq('id', id)
    .select()
    .single();
  
  if (error) {
    logger.error('Failed to update plugin status:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to update plugin status'
    });
  }
  
  if (!plugin) {
    return res.status(404).json({
      success: false,
      error: 'Plugin not found'
    });
  }
  
  logger.info(`Plugin ${plugin.name} status updated to ${status} by ${req.user?.email}`);
  
  res.json({
    success: true,
    data: plugin
  });
}));

/**
 * DELETE /plugins/:id
 * Delete a plugin
 */
router.delete('/:id', authMiddleware, requireRole(['admin']), asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  
  // Check if plugin exists and get details
  const { data: plugin, error: fetchError } = await supabase
    .from('plugins')
    .select('name, version')
    .eq('id', id)
    .single();
  
  if (fetchError || !plugin) {
    return res.status(404).json({
      success: false,
      error: 'Plugin not found'
    });
  }
  
  // Delete plugin
  const { error } = await supabase
    .from('plugins')
    .delete()
    .eq('id', id);
  
  if (error) {
    logger.error('Failed to delete plugin:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to delete plugin'
    });
  }
  
  logger.info(`Plugin deleted: ${plugin.name}@${plugin.version} by ${req.user?.email}`);
  
  res.json({
    success: true,
    message: 'Plugin deleted successfully'
  });
}));

/**
 * GET /plugins/categories
 * Get available plugin categories
 */
router.get('/categories', authMiddleware, asyncHandler(async (req: Request, res: Response) => {
  const categories = [
    { id: 'design', name: 'Design Tools', description: 'CAD, layout, and design optimization plugins' },
    { id: 'compliance', name: 'Compliance', description: 'Regulatory and standards compliance plugins' },
    { id: 'finance', name: 'Financial', description: 'Financial modeling and analysis plugins' },
    { id: 'procurement', name: 'Procurement', description: 'Equipment sourcing and procurement plugins' },
    { id: 'operations', name: 'Operations', description: 'Project management and operations plugins' },
    { id: 'analytics', name: 'Analytics', description: 'Data analysis and reporting plugins' },
    { id: 'integration', name: 'Integration', description: 'Third-party system integration plugins' },
    { id: 'utility', name: 'Utilities', description: 'General utility and helper plugins' }
  ];
  
  res.json({
    success: true,
    data: categories
  });
}));

/**
 * POST /plugins/:id/install
 * Install a plugin for an organization
 */
router.post('/:id/install', authMiddleware, requireRole(['admin', 'manager']), asyncHandler(async (req: Request, res: Response) => {
  const { id } = req.params;
  const { config } = req.body;
  
  // Check if plugin exists and is approved
  const { data: plugin, error: pluginError } = await supabase
    .from('plugins')
    .select('*')
    .eq('id', id)
    .eq('status', 'approved')
    .single();
  
  if (pluginError || !plugin) {
    return res.status(404).json({
      success: false,
      error: 'Plugin not found or not approved'
    });
  }
  
  // Check if already installed
  const { data: existing } = await supabase
    .from('plugin_installations')
    .select('id')
    .eq('plugin_id', id)
    .eq('organization_id', req.user?.organization_id)
    .single();
  
  if (existing) {
    return res.status(409).json({
      success: false,
      error: 'Plugin already installed'
    });
  }
  
  // Install plugin
  const { data: installation, error } = await supabase
    .from('plugin_installations')
    .insert({
      plugin_id: id,
      organization_id: req.user?.organization_id,
      config: config || {},
      status: 'active',
      installed_by: req.user?.id
    })
    .select()
    .single();
  
  if (error) {
    logger.error('Failed to install plugin:', error);
    return res.status(500).json({
      success: false,
      error: 'Failed to install plugin'
    });
  }
  
  logger.info(`Plugin installed: ${plugin.name}@${plugin.version} for org ${req.user?.organization_id} by ${req.user?.email}`);
  
  res.status(201).json({
    success: true,
    data: installation
  });
}));

export default router;