import React from 'react';
import { motion } from 'framer-motion';

export interface KpiCardProps {
  label: string;
  value: string;
  delta?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  className?: string;
}

export function KpiCard({ 
  label, 
  value, 
  delta, 
  trend = 'neutral',
  icon,
  className = '' 
}: KpiCardProps) {
  const getTrendColor = () => {
    switch (trend) {
      case 'up': return 'text-green-600';
      case 'down': return 'text-red-600';
      default: return 'text-slate';
    }
  };

  return (
    <motion.div 
      whileHover={{ scale: 1.02 }} 
      whileTap={{ scale: 0.98 }}
      className={`rounded-xl bg-white shadow-sm p-5 border border-slate/10 hover:shadow-md transition-shadow ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-slate text-sm font-medium">{label}</div>
        {icon && (
          <div className="text-slate/60">
            {icon}
          </div>
        )}
      </div>
      <div className="text-3xl font-semibold text-navy mt-1 mb-1">{value}</div>
      {delta && (
        <div className={`text-xs mt-1 font-medium ${getTrendColor()}`}>
          {delta}
        </div>
      )}
    </motion.div>
  );
}

export default KpiCard;