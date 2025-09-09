import React from 'react';

interface LoadingBarProps {
  progress: number; // 0-100
  label?: string;
  isVisible: boolean;
}

const LoadingBar: React.FC<LoadingBarProps> = ({ progress, label, isVisible }) => {
  if (!isVisible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-zinc-900/95 backdrop-blur-sm border-b border-zinc-700">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-zinc-300">
            {label || 'Loading...'}
          </span>
          <span className="text-xs text-zinc-400">
            {Math.round(progress)}%
          </span>
        </div>
        
        <div className="w-full bg-zinc-700 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-orange-500 to-orange-400 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
          >
            {/* Add a subtle glow effect */}
            <div className="h-full w-full rounded-full bg-gradient-to-r from-orange-400 to-orange-300 opacity-50 animate-pulse"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoadingBar;
