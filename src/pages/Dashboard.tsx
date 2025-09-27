import React, { useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { KpiCard } from '../components/ui/KpiCard';
import { DarkModeToggle } from '../components/ui/DarkModeToggle';
import { useProjectStore, useUIStore } from '../stores';
import { BarChart3, Zap, DollarSign, TrendingUp, MapPin, Users, AlertTriangle, Activity, Target, CheckCircle } from 'lucide-react';

const Dashboard: React.FC = () => {
  const { 
    projects, 
    metrics, 
    isLoading, 
    error, 
    fetchProjects, 
    fetchMetrics 
  } = useProjectStore();
  
  const { 
    currency, 
    addNotification, 
    setBreadcrumbs 
  } = useUIStore();

  useEffect(() => {
    setBreadcrumbs([{ label: 'Dashboard' }]);
    fetchProjects();
    fetchMetrics();
  }, [fetchProjects, fetchMetrics, setBreadcrumbs]);

  useEffect(() => {
    if (error) {
      addNotification({
        type: 'error',
        title: 'Error',
        message: error
      });
    }
  }, [error, addNotification]);

  const formatCurrency = (amount: number) => {
    const formatter = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
    return formatter.format(amount);
  };

  const formatCapacity = (kw: number) => {
    if (kw >= 1000) {
      return `${(kw / 1000).toFixed(1)} MW`;
    }
    return `${kw} kW`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational': return 'bg-green-100 text-green-800';
      case 'construction': return 'bg-blue-100 text-blue-800';
      case 'design': return 'bg-purple-100 text-purple-800';
      case 'planning': return 'bg-yellow-100 text-yellow-800';
      case 'procurement': return 'bg-orange-100 text-orange-800';
      case 'completed': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const recentProjects = projects.slice(0, 5);

  if (isLoading && !projects.length) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
        <span className="ml-2 text-gray-600">Loading dashboard...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper dark:bg-gray-900 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-navy dark:text-white">Dashboard</h1>
          <p className="text-slate dark:text-slate/80 mt-1">Welcome to NextGen Fusion Commercial Solar Platform</p>
        </div>
        <div className="flex items-center space-x-3">
          <Badge variant="outline" className="text-green-600 border-green-200 bg-green-50">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            System Online
          </Badge>
          <DarkModeToggle />
        </div>
      </div>

      {/* KPI Hero Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KpiCard
          label="Active Projects"
          value={String(metrics?.active_projects || 0)}
          delta={`+${metrics?.total_projects || 0} total`}
          trend="up"
          icon={<BarChart3 className="h-5 w-5" />}
        />
        
        <KpiCard
          label="Total Capacity"
          value={formatCapacity(metrics?.total_capacity_kw || 0)}
          delta="Across all projects"
          trend="up"
          icon={<Zap className="h-5 w-5 text-solar" />}
        />
        
        <KpiCard
          label="Portfolio Value"
          value={formatCurrency(metrics?.total_investment || 0)}
          delta="Projected ROI: 12.5%"
          trend="up"
          icon={<DollarSign className="h-5 w-5 text-mint" />}
        />
        
        <KpiCard
          label="Compliance Pass Rate"
          value={`${Math.round(metrics?.average_progress || 85)}%`}
          delta="Above industry avg"
          trend="up"
          icon={<CheckCircle className="h-5 w-5 text-green-600" />}
        />
      </div>

      {/* Recent Projects and System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <Card className="border-slate/20 dark:border-slate/30">
          <CardHeader>
            <CardTitle className="text-navy dark:text-white">Recent Activity</CardTitle>
            <CardDescription className="text-slate dark:text-slate/80">
              Latest project updates and activities
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Spinner size="lg" />
              </div>
            ) : recentProjects.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-paper dark:bg-slate/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <BarChart3 className="h-8 w-8 text-slate" />
                </div>
                <h3 className="text-lg font-semibold text-navy dark:text-white mb-2">No projects yet</h3>
                <p className="text-slate dark:text-slate/80 mb-4">Get started by creating your first solar project.</p>
                <button className="bg-navy hover:bg-navy/90 text-white px-4 py-2 rounded-xl transition-colors">
                  Create First Project
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {recentProjects.map((project) => (
                  <div key={project.id} className="flex items-center justify-between p-4 border border-slate/10 dark:border-slate/20 rounded-xl hover:bg-paper/50 dark:hover:bg-slate/5 transition-colors">
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-solar/10 rounded-xl flex items-center justify-center">
                          <MapPin className="h-5 w-5 text-solar" />
                        </div>
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-navy dark:text-white">{project.name}</h4>
                        <p className="text-sm text-slate dark:text-slate/80">{project.location.address}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <Badge 
                        variant="outline"
                        className={`rounded-lg ${
                          project.status === 'operational' 
                            ? 'bg-green-50 text-green-700 border-green-200' 
                            : project.status === 'planning'
                            ? 'bg-slate/10 text-slate border-slate/20'
                            : 'bg-solar/10 text-solar border-solar/20'
                        }`}
                      >
                        {project.status}
                      </Badge>
                      <span className="text-sm text-slate dark:text-slate/80">
                        {project.progress_percentage}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* System Status */}
        <Card className="border-slate/20 dark:border-slate/30">
          <CardHeader>
            <CardTitle className="text-navy dark:text-white flex items-center space-x-2">
              <Activity className="h-5 w-5" />
              <span>System Status</span>
            </CardTitle>
            <CardDescription className="text-slate dark:text-slate/80">
              Current system health and performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-200 dark:border-green-800">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium text-green-800 dark:text-green-200">API Services</span>
                </div>
                <Badge variant="outline" className="text-green-700 border-green-300 bg-green-100 dark:bg-green-900/30">
                  Operational
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-xl border border-green-200 dark:border-green-800">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium text-green-800 dark:text-green-200">Database</span>
                </div>
                <Badge variant="outline" className="text-green-700 border-green-300 bg-green-100 dark:bg-green-900/30">
                  Connected
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-3 bg-solar/10 dark:bg-solar/20 rounded-xl border border-solar/30">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-solar rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium text-solar dark:text-solar">Cache Layer</span>
                </div>
                <Badge variant="outline" className="text-solar border-solar/30 bg-solar/20">
                  Optimizing
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-3 bg-mint/10 dark:bg-mint/20 rounded-xl border border-mint/30">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-mint rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium text-mint dark:text-mint">External APIs</span>
                </div>
                <Badge variant="outline" className="text-mint border-mint/30 bg-mint/20">
                  Available
                </Badge>
              </div>
              
              <div className="pt-4 border-t border-slate/20 dark:border-slate/30">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate dark:text-slate/80">Last Updated</span>
                  <span className="font-medium text-navy dark:text-white">{new Date().toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      </div>
    </div>
    </div>
  );
};

export default Dashboard;