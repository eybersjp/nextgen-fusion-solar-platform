import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';
export type Language = 'en' | 'afr' | 'es' | 'pt';
export type Currency = 'USD' | 'ZAR' | 'AUD';

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface Modal {
  id: string;
  type: string;
  props?: Record<string, any>;
  onClose?: () => void;
}

export interface UIState {
  // Theme and appearance
  theme: Theme;
  language: Language;
  currency: Currency;
  
  // Layout state
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  
  // Loading states
  globalLoading: boolean;
  loadingMessage?: string;
  
  // Notifications
  notifications: Notification[];
  
  // Modals
  modals: Modal[];
  
  // Page state
  currentPage: string;
  breadcrumbs: Array<{ label: string; href?: string }>;
  
  // Actions
  setTheme: (theme: Theme) => void;
  setLanguage: (language: Language) => void;
  setCurrency: (currency: Currency) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebarCollapsed: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setGlobalLoading: (loading: boolean, message?: string) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markNotificationRead: (id: string) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  openModal: (modal: Omit<Modal, 'id'>) => void;
  closeModal: (id: string) => void;
  closeAllModals: () => void;
  setCurrentPage: (page: string) => void;
  setBreadcrumbs: (breadcrumbs: Array<{ label: string; href?: string }>) => void;
}

// Helper function to generate unique IDs
const generateId = () => Math.random().toString(36).substr(2, 9);

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'system',
      language: 'en',
      currency: 'USD',
      sidebarOpen: true,
      sidebarCollapsed: false,
      globalLoading: false,
      loadingMessage: undefined,
      notifications: [],
      modals: [],
      currentPage: '',
      breadcrumbs: [],

      // Theme and appearance actions
      setTheme: (theme) => {
        set({ theme });
        // Apply theme to document
        const root = document.documentElement;
        if (theme === 'dark') {
          root.classList.add('dark');
        } else if (theme === 'light') {
          root.classList.remove('dark');
        } else {
          // System theme
          const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
          if (prefersDark) {
            root.classList.add('dark');
          } else {
            root.classList.remove('dark');
          }
        }
      },
      
      setLanguage: (language) => set({ language }),
      setCurrency: (currency) => set({ currency }),

      // Layout actions
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      // Loading actions
      setGlobalLoading: (loading, message) => set({ globalLoading: loading, loadingMessage: message }),

      // Notification actions
      addNotification: (notification) => {
        const newNotification: Notification = {
          ...notification,
          id: generateId(),
          timestamp: Date.now(),
          read: false,
        };
        
        set((state) => ({
          notifications: [newNotification, ...state.notifications].slice(0, 50), // Keep max 50 notifications
        }));
        
        // Auto-remove success notifications after 5 seconds
        if (notification.type === 'success') {
          setTimeout(() => {
            get().removeNotification(newNotification.id);
          }, 5000);
        }
      },
      
      markNotificationRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map(n => 
            n.id === id ? { ...n, read: true } : n
          ),
        }));
      },
      
      removeNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id),
        }));
      },
      
      clearNotifications: () => set({ notifications: [] }),

      // Modal actions
      openModal: (modal) => {
        const newModal: Modal = {
          ...modal,
          id: generateId(),
        };
        
        set((state) => ({
          modals: [...state.modals, newModal],
        }));
      },
      
      closeModal: (id) => {
        const modal = get().modals.find(m => m.id === id);
        if (modal?.onClose) {
          modal.onClose();
        }
        
        set((state) => ({
          modals: state.modals.filter(m => m.id !== id),
        }));
      },
      
      closeAllModals: () => {
        const { modals } = get();
        modals.forEach(modal => {
          if (modal.onClose) {
            modal.onClose();
          }
        });
        
        set({ modals: [] });
      },

      // Page state actions
      setCurrentPage: (page) => set({ currentPage: page }),
      setBreadcrumbs: (breadcrumbs) => set({ breadcrumbs }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        language: state.language,
        currency: state.currency,
        sidebarCollapsed: state.sidebarCollapsed,
      }),
    }
  )
);

// Initialize theme on store creation
if (typeof window !== 'undefined') {
  const store = useUIStore.getState();
  store.setTheme(store.theme);
  
  // Listen for system theme changes
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', () => {
    const currentTheme = useUIStore.getState().theme;
    if (currentTheme === 'system') {
      useUIStore.getState().setTheme('system');
    }
  });
}