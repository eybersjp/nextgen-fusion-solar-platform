import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'planning' | 'design' | 'procurement' | 'construction' | 'operational' | 'completed';
  location: {
    address: string;
    latitude?: number;
    longitude?: number;
    country: string;
    region: string;
  };
  capacity_kw: number;
  estimated_cost: number;
  currency: 'USD' | 'ZAR' | 'AUD';
  created_at: string;
  updated_at: string;
  owner_id: string;
  team_members?: string[];
  progress_percentage: number;
  next_milestone?: string;
  compliance_status: 'pending' | 'in_review' | 'approved' | 'rejected';
}

export interface ProjectMetrics {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  total_capacity_kw: number;
  total_investment: number;
  average_progress: number;
}

export interface ProjectState {
  // State
  projects: Project[];
  currentProject: Project | null;
  metrics: ProjectMetrics | null;
  isLoading: boolean;
  error: string | null;
  filters: {
    status?: string;
    location?: string;
    search?: string;
  };

  // Actions
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (project: Omit<Project, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  updateProject: (id: string, updates: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  fetchMetrics: () => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
  setFilters: (filters: Partial<ProjectState['filters']>) => void;
  clearError: () => void;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8003';

// Helper function to get auth token
const getAuthToken = () => {
  const authStorage = localStorage.getItem('auth-storage');
  if (authStorage) {
    const parsed = JSON.parse(authStorage);
    return parsed.state?.token;
  }
  return null;
};

// Helper function for API calls
const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  return response.json();
};

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      // Initial state
      projects: [],
      currentProject: null,
      metrics: null,
      isLoading: false,
      error: null,
      filters: {},

      // Actions
      fetchProjects: async () => {
        set({ isLoading: true, error: null });
        try {
          const { filters } = get();
          const queryParams = new URLSearchParams();
          
          if (filters.status) queryParams.append('status', filters.status);
          if (filters.location) queryParams.append('location', filters.location);
          if (filters.search) queryParams.append('search', filters.search);
          
          const queryString = queryParams.toString();
          const endpoint = `/api/projects${queryString ? `?${queryString}` : ''}`;
          
          const data = await apiCall(endpoint);
          
          set({
            projects: data.projects || [],
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to fetch projects',
          });
        }
      },

      fetchProject: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          const data = await apiCall(`/api/projects/${id}`);
          
          set({
            currentProject: data.project,
            isLoading: false,
          });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to fetch project',
          });
        }
      },

      createProject: async (projectData) => {
        set({ isLoading: true, error: null });
        try {
          const data = await apiCall('/api/projects', {
            method: 'POST',
            body: JSON.stringify(projectData),
          });
          
          set((state) => ({
            projects: [...state.projects, data.project],
            isLoading: false,
          }));
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to create project',
          });
          throw error;
        }
      },

      updateProject: async (id: string, updates) => {
        set({ isLoading: true, error: null });
        try {
          const data = await apiCall(`/api/projects/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
          });
          
          set((state) => ({
            projects: state.projects.map(p => p.id === id ? data.project : p),
            currentProject: state.currentProject?.id === id ? data.project : state.currentProject,
            isLoading: false,
          }));
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to update project',
          });
          throw error;
        }
      },

      deleteProject: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          await apiCall(`/api/projects/${id}`, {
            method: 'DELETE',
          });
          
          set((state) => ({
            projects: state.projects.filter(p => p.id !== id),
            currentProject: state.currentProject?.id === id ? null : state.currentProject,
            isLoading: false,
          }));
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to delete project',
          });
          throw error;
        }
      },

      fetchMetrics: async () => {
        try {
          const data = await apiCall('/api/projects/metrics');
          set({ metrics: data.metrics });
        } catch (error) {
          console.error('Failed to fetch metrics:', error);
        }
      },

      setCurrentProject: (project) => set({ currentProject: project }),
      
      setFilters: (newFilters) => {
        set((state) => ({
          filters: { ...state.filters, ...newFilters }
        }));
        // Automatically refetch projects when filters change
        get().fetchProjects();
      },
      
      clearError: () => set({ error: null }),
    }),
    {
      name: 'project-storage',
      partialize: (state) => ({
        projects: state.projects,
        currentProject: state.currentProject,
        metrics: state.metrics,
        filters: state.filters,
      }),
    }
  )
);