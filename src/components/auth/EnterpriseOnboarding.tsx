import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import {
  Building2,
  Users,
  Shield,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Settings,
  Mail,
  Phone
} from 'lucide-react';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  component: React.ComponentType<any>;
}

interface EnterpriseOnboardingProps {
  onComplete?: () => void;
  onSkip?: () => void;
}

interface OrganizationInfo {
  name: string;
  domain: string;
  size: string;
  industry: string;
  adminEmail: string;
  adminPhone: string;
}

interface SecurityPreferences {
  mfaRequired: boolean;
  sessionTimeout: number;
  passwordPolicy: string;
  ssoOnly: boolean;
}

const OrganizationSetup: React.FC<{
  data: OrganizationInfo;
  onChange: (data: OrganizationInfo) => void;
}> = ({ data, onChange }) => {
  const handleChange = (field: keyof OrganizationInfo, value: string) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Building2 className="mx-auto h-12 w-12 text-blue-600" />
        <h2 className="mt-4 text-xl font-semibold text-gray-900">
          Organization Information
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Tell us about your organization to customize your experience
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <Input
          label="Organization Name"
          value={data.name}
          onChange={(e) => handleChange('name', e.target.value)}
          placeholder="ACME Corporation"
          required
        />

        <Input
          label="Domain"
          value={data.domain}
          onChange={(e) => handleChange('domain', e.target.value)}
          placeholder="acme.com"
          required
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Organization Size
          </label>
          <select
            value={data.size}
            onChange={(e) => handleChange('size', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Select size</option>
            <option value="1-10">1-10 employees</option>
            <option value="11-50">11-50 employees</option>
            <option value="51-200">51-200 employees</option>
            <option value="201-1000">201-1000 employees</option>
            <option value="1000+">1000+ employees</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Industry
          </label>
          <select
            value={data.industry}
            onChange={(e) => handleChange('industry', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          >
            <option value="">Select industry</option>
            <option value="technology">Technology</option>
            <option value="finance">Finance</option>
            <option value="healthcare">Healthcare</option>
            <option value="manufacturing">Manufacturing</option>
            <option value="retail">Retail</option>
            <option value="education">Education</option>
            <option value="other">Other</option>
          </select>
        </div>

        <Input
          label="Administrator Email"
          type="email"
          value={data.adminEmail}
          onChange={(e) => handleChange('adminEmail', e.target.value)}
          placeholder="admin@acme.com"
          required
        />

        <Input
          label="Administrator Phone"
          type="tel"
          value={data.adminPhone}
          onChange={(e) => handleChange('adminPhone', e.target.value)}
          placeholder="+1 (555) 123-4567"
        />
      </div>
    </div>
  );
};

const SecuritySetup: React.FC<{
  data: SecurityPreferences;
  onChange: (data: SecurityPreferences) => void;
}> = ({ data, onChange }) => {
  const handleChange = (field: keyof SecurityPreferences, value: any) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Shield className="mx-auto h-12 w-12 text-green-600" />
        <h2 className="mt-4 text-xl font-semibold text-gray-900">
          Security Preferences
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Configure security settings for your organization
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
          <div>
            <h3 className="text-sm font-medium text-gray-900">
              Multi-Factor Authentication
            </h3>
            <p className="text-xs text-gray-500">
              Require MFA for all users
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={data.mfaRequired}
              onChange={(e) => handleChange('mfaRequired', e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        <div className="p-4 border border-gray-200 rounded-lg">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Session Timeout (minutes)
          </label>
          <select
            value={data.sessionTimeout}
            onChange={(e) => handleChange('sessionTimeout', parseInt(e.target.value))}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={30}>30 minutes</option>
            <option value={60}>1 hour</option>
            <option value={120}>2 hours</option>
            <option value={240}>4 hours</option>
            <option value={480}>8 hours</option>
          </select>
        </div>

        <div className="p-4 border border-gray-200 rounded-lg">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Password Policy
          </label>
          <select
            value={data.passwordPolicy}
            onChange={(e) => handleChange('passwordPolicy', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="basic">Basic (8+ characters)</option>
            <option value="standard">Standard (8+ chars, mixed case, numbers)</option>
            <option value="strong">Strong (12+ chars, mixed case, numbers, symbols)</option>
          </select>
        </div>

        <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
          <div>
            <h3 className="text-sm font-medium text-gray-900">
              SSO Only Access
            </h3>
            <p className="text-xs text-gray-500">
              Disable password-based login
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={data.ssoOnly}
              onChange={(e) => handleChange('ssoOnly', e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>
      </div>
    </div>
  );
};

const CompletionStep: React.FC = () => {
  return (
    <div className="text-center space-y-6">
      <CheckCircle className="mx-auto h-16 w-16 text-green-600" />
      <div>
        <h2 className="text-xl font-semibold text-gray-900">
          Setup Complete!
        </h2>
        <p className="mt-2 text-sm text-gray-600">
          Your enterprise account has been configured successfully.
        </p>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-green-900 mb-2">
          What's Next?
        </h3>
        <ul className="text-xs text-green-700 space-y-1">
          <li>• Your IT administrator will receive setup instructions</li>
          <li>• Users can now sign in with their enterprise credentials</li>
          <li>• Access the admin panel to manage users and permissions</li>
        </ul>
      </div>

      <div className="text-xs text-gray-500">
        Need help? Contact our support team at support@nextgenfusion.com
      </div>
    </div>
  );
};

export const EnterpriseOnboarding: React.FC<EnterpriseOnboardingProps> = ({
  onComplete,
  onSkip
}) => {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [organizationData, setOrganizationData] = useState<OrganizationInfo>({
    name: '',
    domain: '',
    size: '',
    industry: '',
    adminEmail: user?.email || '',
    adminPhone: ''
  });
  const [securityData, setSecurityData] = useState<SecurityPreferences>({
    mfaRequired: true,
    sessionTimeout: 60,
    passwordPolicy: 'standard',
    ssoOnly: false
  });

  const steps: OnboardingStep[] = [
    {
      id: 'organization',
      title: 'Organization',
      description: 'Basic information',
      component: OrganizationSetup
    },
    {
      id: 'security',
      title: 'Security',
      description: 'Security preferences',
      component: SecuritySetup
    },
    {
      id: 'complete',
      title: 'Complete',
      description: 'Setup finished',
      component: CompletionStep
    }
  ];

  const currentStepData = steps[currentStep];
  const isLastStep = currentStep === steps.length - 1;
  const isFirstStep = currentStep === 0;

  const handleNext = () => {
    if (isLastStep) {
      onComplete?.();
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (isFirstStep) {
      return;
    }
    setCurrentStep(currentStep - 1);
  };

  const isStepValid = () => {
    switch (currentStep) {
      case 0:
        return (
          organizationData.name &&
          organizationData.domain &&
          organizationData.size &&
          organizationData.industry &&
          organizationData.adminEmail
        );
      case 1:
        return true; // Security step is always valid (has defaults)
      case 2:
        return true; // Completion step
      default:
        return false;
    }
  };

  const renderStepContent = () => {
    const StepComponent = currentStepData.component;
    
    switch (currentStep) {
      case 0:
        return (
          <StepComponent
            data={organizationData}
            onChange={setOrganizationData}
          />
        );
      case 1:
        return (
          <StepComponent
            data={securityData}
            onChange={setSecurityData}
          />
        );
      case 2:
        return <StepComponent />;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex items-center ${
                index < steps.length - 1 ? 'flex-1' : ''
              }`}
            >
              <div className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index <= currentStep
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {index < currentStep ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    index + 1
                  )}
                </div>
                <div className="ml-3">
                  <p
                    className={`text-sm font-medium ${
                      index <= currentStep ? 'text-gray-900' : 'text-gray-500'
                    }`}
                  >
                    {step.title}
                  </p>
                  <p className="text-xs text-gray-500">{step.description}</p>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-4 ${
                    index < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {renderStepContent()}
      </div>

      {/* Navigation */}
      <div className="mt-6 flex items-center justify-between">
        <div>
          {!isFirstStep && (
            <Button
              variant="ghost"
              onClick={handleBack}
              className="flex items-center"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          )}
        </div>

        <div className="flex items-center space-x-3">
          {!isLastStep && onSkip && (
            <Button variant="ghost" onClick={onSkip}>
              Skip Setup
            </Button>
          )}
          
          <Button
            onClick={handleNext}
            disabled={!isStepValid()}
            className="flex items-center"
          >
            {isLastStep ? 'Get Started' : 'Continue'}
            {!isLastStep && <ArrowRight className="w-4 h-4 ml-2" />}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default EnterpriseOnboarding;