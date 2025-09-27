/**
 * Shared TypeScript types for the NextGen Fusion Commercial Solar Platform
 * These types are used across all services and the frontend
 */

// Base entity interface
export interface BaseEntity {
  id: string;
  created_at: Date;
  updated_at: Date;
  created_by?: string;
  updated_by?: string;
}

// Project domain models
export interface Project extends BaseEntity {
  name: string;
  description?: string;
  status: ProjectStatus;
  location: Location;
  customer_id: string;
  system_size_kw: number;
  estimated_annual_production_kwh?: number;
  project_type: ProjectType;
  phase: ProjectPhase;
  metadata?: Record<string, any>;
}

export enum ProjectStatus {
  DRAFT = 'draft',
  ACTIVE = 'active',
  ON_HOLD = 'on_hold',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled'
}

export enum ProjectType {
  RESIDENTIAL = 'residential',
  COMMERCIAL = 'commercial',
  UTILITY = 'utility',
  COMMUNITY = 'community'
}

export enum ProjectPhase {
  LEAD = 'lead',
  DESIGN = 'design',
  PERMITTING = 'permitting',
  PROCUREMENT = 'procurement',
  INSTALLATION = 'installation',
  COMMISSIONING = 'commissioning',
  OPERATIONS = 'operations'
}

// Location and geographic data
export interface Location {
  address: string;
  city: string;
  state_province: string;
  country: CountryCode;
  postal_code: string;
  latitude: number;
  longitude: number;
  timezone?: string;
}

export enum CountryCode {
  ZA = 'ZA', // South Africa
  AU = 'AU', // Australia
  US = 'US'  // United States
}

// Design domain models
export interface Design extends BaseEntity {
  project_id: string;
  version: number;
  name: string;
  description?: string;
  status: DesignStatus;
  layout_data: LayoutData;
  system_specifications: SystemSpecifications;
  performance_estimates: PerformanceEstimates;
  bill_of_materials?: BillOfMaterials[];
}

export enum DesignStatus {
  DRAFT = 'draft',
  UNDER_REVIEW = 'under_review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  ARCHIVED = 'archived'
}

export interface LayoutData {
  modules: ModuleLayout[];
  inverters: InverterLayout[];
  dc_combiner_boxes?: DCCombinerLayout[];
  ac_disconnect?: ACDisconnectLayout;
  meter_location?: MeterLocation;
  setbacks: Setbacks;
}

export interface ModuleLayout {
  id: string;
  module_type_id: string;
  position: Position3D;
  orientation: Orientation;
  tilt_angle: number;
  azimuth: number;
  shading_factor?: number;
}

export interface InverterLayout {
  id: string;
  inverter_type_id: string;
  position: Position3D;
  dc_inputs: string[];
  ac_output_id: string;
}

export interface DCCombinerLayout {
  id: string;
  position: Position3D;
  inputs: string[];
  output_id: string;
}

export interface ACDisconnectLayout {
  id: string;
  position: Position3D;
  type: 'main' | 'emergency';
}

export interface MeterLocation {
  position: Position3D;
  type: 'production' | 'consumption' | 'net';
}

export interface Setbacks {
  roof_edge: number;
  fire_setback: number;
  walkway_width: number;
  equipment_access: number;
}

export interface SensitivityAnalysis {
  parameters: SensitivityParameter[];
  results: SensitivityResult[];
}

export interface SensitivityParameter {
  name: string;
  base_value: number;
  min_value: number;
  max_value: number;
  step: number;
}

export interface SensitivityResult {
  parameter: string;
  value: number;
  npv_impact: number;
  irr_impact: number;
}

export interface Position3D {
  x: number;
  y: number;
  z: number;
}

export interface Orientation {
  rotation_x: number;
  rotation_y: number;
  rotation_z: number;
}

// System specifications
export interface SystemSpecifications {
  total_dc_capacity_kw: number;
  total_ac_capacity_kw: number;
  module_count: number;
  inverter_count: number;
  dc_ac_ratio: number;
  estimated_annual_production_kwh: number;
  performance_ratio: number;
}

// Performance estimates
export interface PerformanceEstimates {
  p50_annual_kwh: number;
  p90_annual_kwh: number;
  p99_annual_kwh: number;
  monthly_production: MonthlyProduction[];
  degradation_rate_percent: number;
  system_losses_percent: number;
}

export interface MonthlyProduction {
  month: number;
  production_kwh: number;
  irradiance_kwh_m2: number;
}

// Bill of Materials
export interface BillOfMaterials {
  category: BOMCategory;
  items: BOMItem[];
}

export enum BOMCategory {
  MODULES = 'modules',
  INVERTERS = 'inverters',
  RACKING = 'racking',
  ELECTRICAL = 'electrical',
  MONITORING = 'monitoring',
  SAFETY = 'safety',
  LABOR = 'labor'
}

export interface BOMItem {
  id: string;
  name: string;
  manufacturer: string;
  model: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  specifications?: Record<string, any>;
}

// Compliance domain models
export interface ComplianceFinding extends BaseEntity {
  project_id: string;
  design_id?: string;
  rule_id: string;
  severity: ComplianceSeverity;
  status: ComplianceStatus;
  description: string;
  recommendation?: string;
  auto_fixable: boolean;
  metadata?: Record<string, any>;
}

export enum ComplianceSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

export enum ComplianceStatus {
  OPEN = 'open',
  ACKNOWLEDGED = 'acknowledged',
  RESOLVED = 'resolved',
  WAIVED = 'waived'
}

// Finance domain models
export interface FinancialModel extends BaseEntity {
  project_id: string;
  model_type: FinancialModelType;
  assumptions: FinancialAssumptions;
  cash_flows: CashFlow[];
  metrics: FinancialMetrics;
  sensitivity_analysis?: SensitivityAnalysis;
}

export enum FinancialModelType {
  CASH_PURCHASE = 'cash_purchase',
  LOAN = 'loan',
  LEASE = 'lease',
  PPA = 'ppa'
}

export interface FinancialAssumptions {
  system_cost_per_watt: number;
  electricity_rate_escalation: number;
  discount_rate: number;
  analysis_period_years: number;
  degradation_rate: number;
  o_m_cost_per_kw_year: number;
  insurance_rate: number;
  property_tax_rate?: number;
}

export interface CashFlow {
  year: number;
  energy_production_kwh: number;
  energy_value: number;
  o_m_costs: number;
  insurance_costs: number;
  tax_benefits?: number;
  net_cash_flow: number;
}

export interface FinancialMetrics {
  npv: number;
  irr: number;
  payback_period_years: number;
  lcoe: number;
  total_savings_25_years: number;
}

// Plugin system types
export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  license: string;
  entry_point: string;
  dependencies: PluginDependency[];
  permissions: PluginPermission[];
  extension_points: ExtensionPoint[];
  configuration_schema?: Record<string, any>;
}

export interface PluginDependency {
  name: string;
  version: string;
  optional: boolean;
}

export enum PluginPermission {
  READ_projects = 'read_projects',
  write_projects = 'write_projects',
  read_designs = 'read_designs',
  write_designs = 'write_designs',
  access_external_apis = 'access_external_apis',
  file_system_access = 'file_system_access'
}

export enum ExtensionPoint {
  design_validation = 'design_validation',
  performance_calculation = 'performance_calculation',
  compliance_check = 'compliance_check',
  cost_estimation = 'cost_estimation',
  report_generation = 'report_generation'
}

// API response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  pagination?: PaginationInfo;
}

export interface PaginationInfo {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

// User and authentication types
export interface User extends BaseEntity {
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  organization_id?: string;
  preferences?: UserPreferences;
  last_login?: Date;
}

export enum UserRole {
  ADMIN = 'admin',
  MANAGER = 'manager',
  DESIGNER = 'designer',
  SALES = 'sales',
  INSTALLER = 'installer',
  VIEWER = 'viewer'
}

export interface UserPreferences {
  theme: 'light' | 'dark';
  language: string;
  timezone: string;
  units: 'metric' | 'imperial';
  currency: string;
}

// Error types
export interface ValidationError {
  field: string;
  message: string;
  code: string;
}

export interface ServiceError {
  code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: Date;
}