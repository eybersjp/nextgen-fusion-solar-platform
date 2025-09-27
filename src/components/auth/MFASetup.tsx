import React, { useState, useEffect } from 'react'
import { useAuth } from '@auth0/auth0-react'
import { Shield, Smartphone, Mail, Key, Check, AlertCircle, Copy, QrCode } from 'lucide-react'
import { cn } from '../../utils/cn'

interface MFAMethod {
  id: string
  type: 'sms' | 'email' | 'totp' | 'webauthn'
  name: string
  description: string
  icon: React.ComponentType<any>
  enabled: boolean
  primary: boolean
}

interface MFASetupProps {
  onComplete?: () => void
  onSkip?: () => void
  required?: boolean
}

const MFASetup: React.FC<MFASetupProps> = ({ onComplete, onSkip, required = false }) => {
  const { user, isAuthenticated } = useAuth()
  const [currentStep, setCurrentStep] = useState<'select' | 'setup' | 'verify' | 'complete'>('select')
  const [selectedMethod, setSelectedMethod] = useState<MFAMethod | null>(null)
  const [verificationCode, setVerificationCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [qrCodeUrl, setQrCodeUrl] = useState('')
  const [totpSecret, setTotpSecret] = useState('')

  const mfaMethods: MFAMethod[] = [
    {
      id: 'totp',
      type: 'totp',
      name: 'Authenticator App',
      description: 'Use Google Authenticator, Authy, or similar apps',
      icon: Smartphone,
      enabled: false,
      primary: false
    },
    {
      id: 'sms',
      type: 'sms',
      name: 'SMS Text Message',
      description: 'Receive codes via text message',
      icon: Mail,
      enabled: false,
      primary: false
    },
    {
      id: 'email',
      type: 'email',
      name: 'Email',
      description: 'Receive codes via email',
      icon: Mail,
      enabled: false,
      primary: false
    },
    {
      id: 'webauthn',
      type: 'webauthn',
      name: 'Security Key',
      description: 'Use hardware security keys or biometrics',
      icon: Key,
      enabled: false,
      primary: false
    }
  ]

  const [methods, setMethods] = useState<MFAMethod[]>(mfaMethods)

  useEffect(() => {
    // Load existing MFA methods for the user
    loadUserMFAMethods()
  }, [user])

  const loadUserMFAMethods = async () => {
    if (!isAuthenticated || !user) return

    try {
      // Mock API call to get user's MFA methods
      const response = await fetch('/api/auth/mfa/methods', {
        headers: {
          'Authorization': `Bearer ${await getAccessToken()}`
        }
      })

      if (response.ok) {
        const userMethods = await response.json()
        setMethods(prev => prev.map(method => {
          const userMethod = userMethods.find((um: any) => um.type === method.type)
          return userMethod ? { ...method, enabled: true, primary: userMethod.primary } : method
        }))
      }
    } catch (error) {
      console.error('Error loading MFA methods:', error)
    }
  }

  const getAccessToken = async () => {
    // Mock function - in real implementation, get from Auth0
    return 'mock-access-token'
  }

  const handleMethodSelect = (method: MFAMethod) => {
    setSelectedMethod(method)
    setCurrentStep('setup')
    setError('')

    if (method.type === 'totp') {
      generateTOTPSecret()
    }
  }

  const generateTOTPSecret = () => {
    // Mock TOTP secret generation
    const secret = 'JBSWY3DPEHPK3PXP' // Mock secret
    const qrUrl = `otpauth://totp/NextGen%20Fusion:${user?.email}?secret=${secret}&issuer=NextGen%20Fusion`
    
    setTotpSecret(secret)
    setQrCodeUrl(qrUrl)
  }

  const handleSetupMethod = async () => {
    if (!selectedMethod) return

    setIsLoading(true)
    setError('')

    try {
      // Mock API call to setup MFA method
      const response = await fetch('/api/auth/mfa/setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getAccessToken()}`
        },
        body: JSON.stringify({
          type: selectedMethod.type,
          phoneNumber: selectedMethod.type === 'sms' ? '+1234567890' : undefined,
          secret: selectedMethod.type === 'totp' ? totpSecret : undefined
        })
      })

      if (response.ok) {
        setCurrentStep('verify')
      } else {
        throw new Error('Failed to setup MFA method')
      }
    } catch (error) {
      setError('Failed to setup MFA method. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyCode = async () => {
    if (!verificationCode || !selectedMethod) return

    setIsLoading(true)
    setError('')

    try {
      // Mock API call to verify MFA code
      const response = await fetch('/api/auth/mfa/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getAccessToken()}`
        },
        body: JSON.stringify({
          type: selectedMethod.type,
          code: verificationCode
        })
      })

      if (response.ok) {
        const result = await response.json()
        setBackupCodes(result.backupCodes || [])
        
        // Update methods state
        setMethods(prev => prev.map(method => 
          method.id === selectedMethod.id 
            ? { ...method, enabled: true, primary: true }
            : { ...method, primary: false }
        ))
        
        setCurrentStep('complete')
      } else {
        throw new Error('Invalid verification code')
      }
    } catch (error) {
      setError('Invalid verification code. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const handleComplete = () => {
    onComplete?.()
  }

  const handleSkip = () => {
    if (!required) {
      onSkip?.()
    }
  }

  const renderMethodSelection = () => (
    <div className="space-y-6">
      <div className="text-center">
        <Shield className="mx-auto h-12 w-12 text-blue-600" />
        <h2 className="mt-4 text-2xl font-bold text-gray-900">Secure Your Account</h2>
        <p className="mt-2 text-gray-600">
          Add an extra layer of security with multi-factor authentication
        </p>
      </div>

      <div className="space-y-3">
        {methods.map((method) => {
          const IconComponent = method.icon
          return (
            <button
              key={method.id}
              onClick={() => handleMethodSelect(method)}
              disabled={method.enabled}
              className={cn(
                "w-full p-4 border rounded-lg text-left transition-colors",
                method.enabled
                  ? "border-green-200 bg-green-50 cursor-not-allowed"
                  : "border-gray-200 hover:border-blue-300 hover:bg-blue-50 cursor-pointer"
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <IconComponent className={cn(
                    "h-6 w-6",
                    method.enabled ? "text-green-600" : "text-gray-600"
                  )} />
                  <div>
                    <h3 className="font-medium text-gray-900">{method.name}</h3>
                    <p className="text-sm text-gray-500">{method.description}</p>
                  </div>
                </div>
                {method.enabled && (
                  <div className="flex items-center space-x-2">
                    {method.primary && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        Primary
                      </span>
                    )}
                    <Check className="h-5 w-5 text-green-600" />
                  </div>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {!required && (
        <div className="text-center">
          <button
            onClick={handleSkip}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            Skip for now
          </button>
        </div>
      )}
    </div>
  )

  const renderSetup = () => {
    if (!selectedMethod) return null

    return (
      <div className="space-y-6">
        <div className="text-center">
          <selectedMethod.icon className="mx-auto h-12 w-12 text-blue-600" />
          <h2 className="mt-4 text-2xl font-bold text-gray-900">
            Setup {selectedMethod.name}
          </h2>
        </div>

        {selectedMethod.type === 'totp' && (
          <div className="space-y-4">
            <div className="text-center">
              <div className="bg-white p-4 border rounded-lg inline-block">
                <QrCode className="h-32 w-32 text-gray-400" />
                <p className="text-xs text-gray-500 mt-2">QR Code Placeholder</p>
              </div>
            </div>
            
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Manual Entry Key
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={totpSecret}
                  readOnly
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-sm font-mono"
                />
                <button
                  onClick={() => copyToClipboard(totpSecret)}
                  className="p-2 text-gray-500 hover:text-gray-700"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Instructions:</h4>
              <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                <li>Install an authenticator app (Google Authenticator, Authy, etc.)</li>
                <li>Scan the QR code or enter the key manually</li>
                <li>Enter the 6-digit code from your app below</li>
              </ol>
            </div>
          </div>
        )}

        {selectedMethod.type === 'sms' && (
          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-blue-800">
                We'll send verification codes to your phone number: +1 (234) 567-8900
              </p>
            </div>
          </div>
        )}

        {selectedMethod.type === 'email' && (
          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-blue-800">
                We'll send verification codes to: {user?.email}
              </p>
            </div>
          </div>
        )}

        <div className="flex space-x-3">
          <button
            onClick={() => setCurrentStep('select')}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Back
          </button>
          <button
            onClick={handleSetupMethod}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Setting up...' : 'Continue'}
          </button>
        </div>

        {error && (
          <div className="flex items-center space-x-2 text-red-600 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}
      </div>
    )
  }

  const renderVerification = () => (
    <div className="space-y-6">
      <div className="text-center">
        <Shield className="mx-auto h-12 w-12 text-blue-600" />
        <h2 className="mt-4 text-2xl font-bold text-gray-900">Verify Your Code</h2>
        <p className="mt-2 text-gray-600">
          Enter the verification code from your {selectedMethod?.name}
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Verification Code
          </label>
          <input
            type="text"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-center text-2xl font-mono tracking-widest"
            maxLength={6}
          />
        </div>

        <div className="flex space-x-3">
          <button
            onClick={() => setCurrentStep('setup')}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            Back
          </button>
          <button
            onClick={handleVerifyCode}
            disabled={isLoading || verificationCode.length !== 6}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Verifying...' : 'Verify'}
          </button>
        </div>

        {error && (
          <div className="flex items-center space-x-2 text-red-600 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  )

  const renderComplete = () => (
    <div className="space-y-6">
      <div className="text-center">
        <div className="mx-auto h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
          <Check className="h-6 w-6 text-green-600" />
        </div>
        <h2 className="mt-4 text-2xl font-bold text-gray-900">MFA Setup Complete!</h2>
        <p className="mt-2 text-gray-600">
          Your account is now protected with multi-factor authentication
        </p>
      </div>

      {backupCodes.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="font-medium text-yellow-900 mb-2">Backup Codes</h3>
          <p className="text-sm text-yellow-800 mb-3">
            Save these backup codes in a secure location. You can use them to access your account if you lose your primary MFA method.
          </p>
          <div className="grid grid-cols-2 gap-2 font-mono text-sm">
            {backupCodes.map((code, index) => (
              <div key={index} className="bg-white p-2 rounded border text-center">
                {code}
              </div>
            ))}
          </div>
          <button
            onClick={() => copyToClipboard(backupCodes.join('\n'))}
            className="mt-3 text-sm text-yellow-700 hover:text-yellow-900 flex items-center space-x-1"
          >
            <Copy className="h-4 w-4" />
            <span>Copy all codes</span>
          </button>
        </div>
      )}

      <button
        onClick={handleComplete}
        className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
      >
        Continue to Dashboard
      </button>
    </div>
  )

  return (
    <div className="max-w-md mx-auto bg-white rounded-lg shadow-lg p-6">
      {currentStep === 'select' && renderMethodSelection()}
      {currentStep === 'setup' && renderSetup()}
      {currentStep === 'verify' && renderVerification()}
      {currentStep === 'complete' && renderComplete()}
    </div>
  )
}

export default MFASetup