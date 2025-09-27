import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { LoginButton } from './LoginButton';
import { EnterpriseAuth } from './EnterpriseAuth';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Building2, Mail, ArrowRight, ArrowLeft } from 'lucide-react';

interface DomainConfig {
  domain: string;
  authType: 'enterprise' | 'social';
  connectionId?: string;
  displayName?: string;
}

interface DomainRouterProps {
  onAuthTypeDetected?: (authType: 'enterprise' | 'social', domain?: string) => void;
}

export const DomainRouter: React.FC<DomainRouterProps> = ({
  onAuthTypeDetected
}) => {
  const { loginWithRedirect } = useAuth();
  const [email, setEmail] = useState('');
  const [step, setStep] = useState<'email' | 'auth'>('email');
  const [authType, setAuthType] = useState<'enterprise' | 'social' | null>(null);
  const [domain, setDomain] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Mock domain configurations - in production, fetch from Auth0 Management API
  const domainConfigs: DomainConfig[] = [
    {
      domain: 'acme.com',
      authType: 'enterprise',
      connectionId: 'saml-acme-corp',
      displayName: 'ACME Corporation'
    },
    {
      domain: 'techsolutions.com',
      authType: 'enterprise',
      connectionId: 'oidc-tech-solutions',
      displayName: 'Tech Solutions Inc'
    },
    {
      domain: 'global-enterprise.com',
      authType: 'enterprise',
      connectionId: 'ad-global-enterprise',
      displayName: 'Global Enterprise'
    },
    // Add more enterprise domains as needed
  ];

  const extractDomain = (email: string): string | null => {
    const emailRegex = /^[^\s@]+@([^\s@]+\.[^\s@]+)$/;
    const match = email.match(emailRegex);
    return match ? match[1].toLowerCase() : null;
  };

  const detectAuthType = (emailDomain: string): DomainConfig | null => {
    return domainConfigs.find(config => config.domain === emailDomain) || null;
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const emailDomain = extractDomain(email);
      
      if (!emailDomain) {
        setError('Please enter a valid email address');
        setLoading(false);
        return;
      }

      const domainConfig = detectAuthType(emailDomain);
      
      if (domainConfig) {
        // Enterprise domain detected
        setAuthType('enterprise');
        setDomain(emailDomain);
        setStep('auth');
        onAuthTypeDetected?.('enterprise', emailDomain);
      } else {
        // Regular domain - use social login
        setAuthType('social');
        setDomain(emailDomain);
        setStep('auth');
        onAuthTypeDetected?.('social', emailDomain);
      }
    } catch (error) {
      setError('An error occurred while processing your email');
      console.error('Domain detection error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDirectEnterpriseLogin = async () => {
    if (!domain) return;
    
    const domainConfig = detectAuthType(domain);
    if (domainConfig?.connectionId) {
      setLoading(true);
      try {
        await loginWithRedirect({
          connection: domainConfig.connectionId,
          login_hint: email,
          prompt: 'login'
        });
      } catch (error) {
        setError('Enterprise login failed. Please try again.');
        console.error('Enterprise login error:', error);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleBack = () => {
    setStep('email');
    setAuthType(null);
    setDomain(null);
    setError(null);
  };

  const isValidEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  if (step === 'email') {
    return (
      <div className="max-w-md mx-auto">
        <div className="text-center mb-6">
          <Mail className="mx-auto h-8 w-8 text-blue-600" />
          <h2 className="mt-2 text-xl font-semibold text-gray-900">
            Welcome to NextGen Fusion
          </h2>
          <p className="mt-1 text-sm text-gray-600">
            Enter your email to get started
          </p>
        </div>

        <form onSubmit={handleEmailSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="sr-only">
              Email address
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your work email"
              required
              className="w-full"
              disabled={loading}
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
              {error}
            </div>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={!isValidEmail(email) || loading}
            loading={loading}
          >
            Continue
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            We'll detect if your organization uses single sign-on (SSO)
          </p>
        </div>
      </div>
    );
  }

  if (step === 'auth' && authType === 'enterprise') {
    const domainConfig = detectAuthType(domain!);
    
    return (
      <div className="max-w-md mx-auto">
        <div className="flex items-center mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="mr-3"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">
              Enterprise Sign-In
            </h2>
            <p className="text-sm text-gray-600">
              {email} • {domainConfig?.displayName || domain}
            </p>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <Building2 className="h-5 w-5 text-blue-600 mr-2" />
            <div>
              <p className="text-sm font-medium text-blue-900">
                Enterprise Account Detected
              </p>
              <p className="text-xs text-blue-700">
                You'll be redirected to your organization's sign-in page
              </p>
            </div>
          </div>
        </div>

        <Button
          onClick={handleDirectEnterpriseLogin}
          className="w-full mb-4"
          loading={loading}
        >
          Continue with {domainConfig?.displayName || 'Enterprise SSO'}
        </Button>

        <EnterpriseAuth domain={domain!} />
      </div>
    );
  }

  if (step === 'auth' && authType === 'social') {
    return (
      <div className="max-w-md mx-auto">
        <div className="flex items-center mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            className="mr-3"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">
              Sign In
            </h2>
            <p className="text-sm text-gray-600">
              {email}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <LoginButton
            showText={true}
            className="w-full"
            loginHint={email}
          />
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    );
  }

  return null;
};

export default DomainRouter;