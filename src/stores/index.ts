// Export all stores
export { useAuthStore, type User, type AuthState } from './authStore';
export { 
  useProjectStore, 
  type Project, 
  type ProjectMetrics, 
  type ProjectState 
} from './projectStore';
export { 
  useUIStore, 
  type Theme, 
  type Language, 
  type Currency, 
  type Notification, 
  type Modal, 
  type UIState 
} from './uiStore';