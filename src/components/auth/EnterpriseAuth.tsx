import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../ui/Button';
import { Building2, Shield, Users, CheckCircle } from 'lucide-react';

interface EnterpriseConnection {
  id: string;
  name: string;
  domain: string;
  strategy: 'saml' | 'oidc' | 'ad';
  enabled: boolean;
  metadata?: {
    ssoUrl?: string;
    certificate?: string;
    issuer?: string;
  };
}

interface EnterpriseAuthProps {
  domain?: string;
  onConnectionSelect?: (connection: EnterpriseConnection) => void;
}

export const EnterpriseAuth: React.FC<EnterpriseAuthProps> = ({
  domain,
  onConnectionSelect
}) => {
  const { loginWithRedirect } = useAuth();
  const [connections, setConnections] = useState<EnterpriseConnection[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<string | null>(null);

  // Mock enterprise connections - in production, fetch from Auth0 Management API
  useEffect(() => {
    const mockConnections: EnterpriseConnection[] = [
      {
        id: 'saml-acme-corp',
        name: 'ACME Corporation',
        domain: 'acme.com',
        strategy: 'saml',
        enabled: true,
        metadata: {
          ssoUrl: 'https://acme.com/sso/saml',
          issuer: 'acme-corp'
        }
      },
      {
        id: 'oidc-tech-solutions',
        name: 'Tech Solutions Inc',
        domain: 'techsolutions.com',
        strategy: 'oidc',
        enabled: true
      },
      {
        id: 'ad-global-enterprise',
        name: 'Global Enterprise',
        domain: 'global-enterprise.com',
        strategy: 'ad',
        enabled: true
      }
    ];

    // Filter connections by domain if provided
    const filteredConnections = domain
      ? mockConnections.filter(conn => conn.domain === domain)
      : mockConnections;

    setConnections(filteredConnections);
  }, [domain]);

  const handleEnterpriseLogin = async (connection: EnterpriseConnection) => {
    setLoading(true);
    setSelectedConnection(connection.id);

    try {
      await loginWithRedirect({
        connection: connection.id,
        organization: connection.domain,
        prompt: 'login'
      });
      
      onConnectionSelect?.(connection);
    } catch (error) {
      console.error('Enterprise login failed:', error);
    } finally {
      setLoading(false);
      setSelectedConnection(null);
    }
  };

  const getStrategyIcon = (strategy: string) => {
    switch (strategy) {
      case 'saml':
        return <Shield className="h-5 w-5" />;
      case 'oidc':
        return <CheckCircle className="h-5 w-5" />;
      case 'ad':
        return <Users className="h-5 w-5" />;
      default:
        return <Building2 className="h-5 w-5" />;
    }
  };

  const getStrategyLabel = (strategy: string) => {
    switch (strategy) {
      case 'saml':
        return 'SAML SSO';
      case 'oidc':
        return 'OpenID Connect';
      case 'ad':
        return 'Active Directory';
      default:
        return 'Enterprise';
    }
  };

  if (connections.length === 0) {
    return (
      <div className="text-center py-8">
        <Building2 className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">
          No Enterprise Connections
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          {domain
            ? `No enterprise connections found for ${domain}`
            : 'No enterprise connections configured'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-center">
        <Building2 className="mx-auto h-8 w-8 text-blue-600" />
        <h2 className="mt-2 text-lg font-medium text-gray-900">
          Enterprise Sign-In
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Sign in with your organization's identity provider
        </p>
      </div>

      <div className="space-y-3">
        {connections.map((connection) => (
          <div
            key={connection.id}
            className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0 text-blue-600">
                  {getStrategyIcon(connection.strategy)}
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-900">
                    {connection.name}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {getStrategyLabel(connection.strategy)} • {connection.domain}
                  </p>
                </div>
              </div>
              
              <Button
                onClick={() => handleEnterpriseLogin(connection)}
                disabled={loading || !connection.enabled}
                loading={loading && selectedConnection === connection.id}
                size="sm"
              >
                {loading && selectedConnection === connection.id
                  ? 'Connecting...'
                  : 'Sign In'
                }
              </Button>
            </div>
            
            {!connection.enabled && (
              <div className="mt-2 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                Connection temporarily disabled
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="text-xs text-gray-500 text-center">
        Having trouble? Contact your IT administrator for assistance.
      </div>
    </div>
  );
};

export default EnterpriseAuth;