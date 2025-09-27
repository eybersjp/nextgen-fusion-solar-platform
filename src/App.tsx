import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
// import Design3D from "./pages/Design3D";
import { useUIStore } from "./stores";
import Auth0Provider from "./components/auth/Auth0Provider";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import LoginButton from "./components/auth/LoginButton";

// Placeholder components for other routes
const Projects = () => <div className="text-center text-xl">Projects - Coming Soon</div>;
const Compliance = () => <div className="text-center text-xl">Compliance - Coming Soon</div>;
const Finance = () => <div className="text-center text-xl">Finance - Coming Soon</div>;
const Procurement = () => <div className="text-center text-xl">Procurement - Coming Soon</div>;
const Operations = () => <div className="text-center text-xl">Operations - Coming Soon</div>;
const Team = () => <div className="text-center text-xl">Team - Coming Soon</div>;
const Support = () => <div className="text-center text-xl">Support - Coming Soon</div>;
const Settings = () => <div className="text-center text-xl">Settings - Coming Soon</div>;

// Login page component
const LoginPage = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="max-w-md w-full space-y-8 p-8">
      <div className="text-center">
        <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
          Sign in to NextGen Fusion
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Commercial Solar Platform
        </p>
      </div>
      <div className="mt-8 space-y-6">
        <LoginButton className="w-full justify-center" />
      </div>
    </div>
  </div>
);

// Auth callback handler
const AuthCallback = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p className="mt-4 text-gray-600">Completing authentication...</p>
    </div>
  </div>
);

function AppContent() {
  const { setCurrentPage } = useUIStore();

  useEffect(() => {
    // Set current page based on pathname
    const path = window.location.pathname;
    if (path === '/') {
      setCurrentPage('dashboard');
    } else {
      setCurrentPage(path.slice(1)); // Remove leading slash
    }
  }, [setCurrentPage]);

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/callback" element={<AuthCallback />} />
      
      {/* Protected routes */}
      <Route path="/" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/home" element={
        <ProtectedRoute>
          <Layout>
            <Home />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/projects" element={
        <ProtectedRoute requiredPermissions={['read:projects']}>
          <Layout>
            <Projects />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/design" element={
        <ProtectedRoute requiredPermissions={['read:projects']}>
          <Layout>
            <div className="text-center text-xl">3D Design - Coming Soon</div>
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/compliance" element={
        <ProtectedRoute requiredPermissions={['read:compliance']}>
          <Layout>
            <Compliance />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/finance" element={
        <ProtectedRoute requiredRoles={['Admin', 'Manager']} requiredPermissions={['read:finance']}>
          <Layout>
            <Finance />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/procurement" element={
        <ProtectedRoute requiredPermissions={['read:procurement']}>
          <Layout>
            <Procurement />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/operations" element={
        <ProtectedRoute requiredPermissions={['read:operations']}>
          <Layout>
            <Operations />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/team" element={
        <ProtectedRoute requiredRoles={['Admin', 'Manager']}>
          <Layout>
            <Team />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/support" element={
        <ProtectedRoute>
          <Layout>
            <Support />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/settings" element={
        <ProtectedRoute>
          <Layout>
            <Settings />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="*" element={
        <div className="text-center text-xl text-gray-500 mt-8">Page Not Found</div>
      } />
    </Routes>
  );
}

export default function App() {
  return (
    <Router>
      <Auth0Provider>
        <AppContent />
      </Auth0Provider>
    </Router>
  );
}
