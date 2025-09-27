import React from 'react';
import { useUIStore } from '../stores';
import { useAuth } from '../hooks/useAuth';
import { LoginButton } from './auth/LoginButton';
import { AdminOnly, ManagerOnly } from './auth/RoleGuard';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import {
  Menu,
  X,
  Home,
  BarChart3,
  Zap,
  FileText,
  DollarSign,
  ShoppingCart,
  Settings,
  Users,
  HelpCircle,
  LogOut,
  Bell,
  Search,
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  Calendar,
  ChevronDown
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const {
    sidebarOpen,
    sidebarCollapsed,
    toggleSidebar,
    toggleSidebarCollapsed,
    notifications,
    currentPage
  } = useUIStore();
  
  const { user, logout, isAuthenticated, isLoading } = useAuth();

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home, current: currentPage === 'dashboard' },
    { name: 'Projects', href: '/projects', icon: BarChart3, current: currentPage === 'projects' },
    { name: 'Design', href: '/design', icon: Zap, current: currentPage === 'design' },
    { name: 'Compliance', href: '/compliance', icon: FileText, current: currentPage === 'compliance' },
    { name: 'Finance', href: '/finance', icon: DollarSign, current: currentPage === 'finance' },
    { name: 'Procurement', href: '/procurement', icon: ShoppingCart, current: currentPage === 'procurement' },
    { name: 'Operations', href: '/operations', icon: Settings, current: currentPage === 'operations' },
  ];

  const secondaryNavigation = [
    { name: 'Team', href: '/team', icon: Users },
    { name: 'Support', href: '/support', icon: HelpCircle },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const unreadNotifications = notifications.filter(n => !n.read).length;

  const handleLogout = () => {
    logout({ logoutParams: { returnTo: window.location.origin } });
  };

  // Show loading state while Auth0 is initializing
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render layout if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <div className={`
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        ${sidebarCollapsed ? 'w-16' : 'w-64'}
        fixed inset-y-0 left-0 z-50 flex flex-col bg-white border-r border-gray-200 transition-all duration-300 ease-in-out
        lg:translate-x-0 lg:static lg:inset-0
      `}>
        {/* Sidebar header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Zap className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-gray-900">NextGen</span>
            </div>
          )}
          
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebarCollapsed}
              className="hidden lg:flex"
            >
              {sidebarCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebar}
              className="lg:hidden"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const Icon = item.icon;
            const navItem = (
              <a
                key={item.name}
                href={item.href}
                className={`
                  group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors
                  ${item.current
                    ? 'bg-blue-50 text-blue-700 border-r-2 border-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }
                `}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <Icon className={`
                  ${sidebarCollapsed ? 'mx-auto' : 'mr-3'}
                  h-5 w-5 flex-shrink-0
                  ${item.current ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}
                `} />
                {!sidebarCollapsed && item.name}
              </a>
            );
            
            // Wrap certain items with role guards
            if (item.name === 'Finance' || item.name === 'Compliance') {
              return <ManagerOnly key={item.name}>{navItem}</ManagerOnly>;
            }
            if (item.name === 'Operations') {
              return <AdminOnly key={item.name}>{navItem}</AdminOnly>;
            }
            
            return navItem;
          })}
          
          {/* Divider */}
          <div className="border-t border-gray-200 my-4"></div>
          
          {secondaryNavigation.map((item) => {
            const Icon = item.icon;
            const navItem = (
              <a
                key={item.name}
                href={item.href}
                className="group flex items-center px-2 py-2 text-sm font-medium text-gray-600 rounded-md hover:bg-gray-50 hover:text-gray-900 transition-colors"
                title={sidebarCollapsed ? item.name : undefined}
              >
                <Icon className={`
                  ${sidebarCollapsed ? 'mx-auto' : 'mr-3'}
                  h-5 w-5 flex-shrink-0 text-gray-400 group-hover:text-gray-500
                `} />
                {!sidebarCollapsed && item.name}
              </a>
            );
            
            // Wrap Settings with AdminOnly
            if (item.name === 'Settings') {
              return <AdminOnly key={item.name}>{navItem}</AdminOnly>;
            }
            
            return navItem;
          })}
        </nav>

        {/* User section */}
        <div className="border-t border-gray-200 p-4">
          {!sidebarCollapsed ? (
            <div className="flex items-center space-x-3">
              {user?.picture ? (
                <img 
                  src={user.picture} 
                  alt={user.name || 'User'}
                  className="w-8 h-8 rounded-full"
                />
              ) : (
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-gray-700">
                    {user?.name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                  </span>
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user?.name || user?.email || 'User'}
                </p>
                <p className="text-xs text-gray-500 truncate">
                  {user?.email || 'user@example.com'}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-gray-400 hover:text-gray-600"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-2">
              {user?.picture ? (
                <img 
                  src={user.picture} 
                  alt={user.name || 'User'}
                  className="w-8 h-8 rounded-full"
                />
              ) : (
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-gray-700">
                    {user?.name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                  </span>
                </div>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-gray-400 hover:text-gray-600"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top navigation */}
        <header className="bg-white border-b border-gray-200 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSidebar}
                className="lg:hidden"
              >
                <Menu className="h-5 w-5" />
              </Button>
              
              {/* Search */}
              <div className="hidden sm:block">
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-gray-400" />
                  </div>
                  <input
                    type="text"
                    placeholder="Search projects..."
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <Button variant="ghost" size="sm" className="relative">
                <Bell className="h-5 w-5" />
                {unreadNotifications > 0 && (
                  <Badge 
                    variant="destructive" 
                    className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
                  >
                    {unreadNotifications > 9 ? '9+' : unreadNotifications}
                  </Badge>
                )}
              </Button>

              {/* User menu */}
              <div className="flex items-center space-x-2">
                {user?.picture ? (
                  <img 
                    src={user.picture} 
                    alt={user.name || 'User'}
                    className="w-8 h-8 rounded-full"
                  />
                ) : (
                  <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-700">
                      {user?.name?.charAt(0) || user?.email?.charAt(0) || 'U'}
                    </span>
                  </div>
                )}
                <span className="hidden sm:block text-sm font-medium text-gray-700">
                  {user?.name || user?.email || 'User'}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="px-4 py-6 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
          onClick={toggleSidebar}
        />
      )}
    </div>
  );
};

export default Layout;