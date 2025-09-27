import React from 'react';
import { LogIn, LogOut, User, Loader2 } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

interface LoginButtonProps {
  className?: string;
  showText?: boolean;
  variant?: 'primary' | 'secondary' | 'outline';
}

const LoginButton: React.FC<LoginButtonProps> = ({ 
  className = '', 
  showText = true, 
  variant = 'primary' 
}) => {
  const { isAuthenticated, isLoading, login, logout, user } = useAuth();

  const baseClasses = 'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
    outline: 'border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-blue-500'
  };

  const buttonClasses = `${baseClasses} ${variantClasses[variant]} ${className}`;

  if (isLoading) {
    return (
      <button disabled className={buttonClasses}>
        <Loader2 className="h-4 w-4 animate-spin" />
        {showText && <span>Loading...</span>}
      </button>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex items-center gap-3">
        {user && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            {user.picture ? (
              <img 
                src={user.picture} 
                alt={user.name} 
                className="h-8 w-8 rounded-full"
              />
            ) : (
              <User className="h-8 w-8 p-1 bg-gray-200 rounded-full" />
            )}
            {showText && (
              <div className="hidden md:block">
                <div className="font-medium">{user.name}</div>
                <div className="text-xs text-gray-500">{user.email}</div>
              </div>
            )}
          </div>
        )}
        <button
          onClick={() => logout()}
          className={buttonClasses}
          title="Sign Out"
        >
          <LogOut className="h-4 w-4" />
          {showText && <span>Sign Out</span>}
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => login()}
      className={buttonClasses}
      title="Sign In"
    >
      <LogIn className="h-4 w-4" />
      {showText && <span>Sign In</span>}
    </button>
  );
};

export default LoginButton;