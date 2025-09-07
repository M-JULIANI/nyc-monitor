import React, { useState, useEffect, useRef } from 'react';
import { usePerformanceMonitor } from '../hooks/usePerformanceMonitor';
import { addPerformanceListener, removePerformanceListener, performanceMetrics } from '../contexts/AlertStatsContext';

interface PerformanceMetric {
  endpoint: string;
  method: string;
  roundTripTime: number;
  cached: boolean;
  alertCount?: number;
  timestamp: number;
}

interface PerformancePanelProps {}

const PerformancePanel: React.FC<PerformancePanelProps> = () => {
  const { stats, isRecording, startRecording, stopRecording, clearMetrics } = usePerformanceMonitor();
  const [isExpanded, setIsExpanded] = useState(false);
  const [apiMetrics, setApiMetrics] = useState<PerformanceMetric[]>([]);
  
  // Dragging state
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 }); // Will be set on first render
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isInitialized, setIsInitialized] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Initialize position to bottom-right corner
  useEffect(() => {
    if (!isInitialized && panelRef.current) {
      const panelRect = panelRef.current.getBoundingClientRect();
      setPosition({
        x: window.innerWidth - panelRect.width - 16,
        y: window.innerHeight - panelRect.height - 16,
      });
      setIsInitialized(true);
    }
  }, [isInitialized]);

  // Listen to performance metrics from existing API calls
  useEffect(() => {
    const handleMetric = (metric: PerformanceMetric) => {
      setApiMetrics(prev => [metric, ...prev.slice(0, 99)]);
    };

    addPerformanceListener(handleMetric);
    // Initialize with existing metrics
    setApiMetrics([...performanceMetrics]);

    return () => {
      removePerformanceListener(handleMetric);
    };
  }, []);

  // Drag handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!panelRef.current) return;
    
    const rect = panelRef.current.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    setIsDragging(true);
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging) return;
    
    const newX = e.clientX - dragOffset.x;
    const newY = e.clientY - dragOffset.y;
    
    // Keep panel within viewport bounds
    const maxX = window.innerWidth - (panelRef.current?.offsetWidth || 0);
    const maxY = window.innerHeight - (panelRef.current?.offsetHeight || 0);
    
    setPosition({
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY)),
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Global mouse events for dragging
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = 'none'; // Prevent text selection while dragging
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.userSelect = '';
      };
    }
  }, [isDragging, dragOffset]);

  const formatTime = (ms: number) => {
    return `${ms.toFixed(1)}ms`;
  };

  const getCacheColor = (cached: boolean) => {
    return cached ? 'text-green-400' : 'text-orange-400';
  };

  // Calculate API stats from our tracked metrics
  const apiStats = {
    totalRequests: apiMetrics.length,
    avgRoundTripTime: apiMetrics.length > 0 
      ? apiMetrics.reduce((sum, m) => sum + m.roundTripTime, 0) / apiMetrics.length 
      : 0,
    cacheHitRate: apiMetrics.length > 0 
      ? (apiMetrics.filter(m => m.cached).length / apiMetrics.length) * 100 
      : 0,
  };

  const getFPSColor = (fps: number) => {
    if (fps >= 58) return 'text-green-400';
    if (fps >= 45) return 'text-yellow-400';
    if (fps >= 30) return 'text-orange-400';
    return 'text-red-400';
  };

  return (
    <div 
      ref={panelRef}
      className={`fixed z-50 bg-gray-900/95 backdrop-blur-sm border rounded-lg shadow-xl text-white text-xs font-mono max-w-md transition-all duration-75 ${
        isDragging 
          ? 'border-blue-400 shadow-2xl scale-105' 
          : 'border-gray-600'
      }`}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        cursor: isDragging ? 'grabbing' : 'default',
        opacity: isInitialized ? 1 : 0, // Fade in once positioned
      }}
    >
      {/* Header - Draggable */}
      <div 
        className="flex items-center justify-between p-3 border-b border-gray-600 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-gray-500'}`} />
          <span className="font-semibold">Performance Monitor</span>
          {/* Drag handle indicator */}
          <div className="flex flex-col gap-0.5 ml-1 opacity-50">
            <div className="w-1 h-0.5 bg-gray-400 rounded"></div>
            <div className="w-1 h-0.5 bg-gray-400 rounded"></div>
            <div className="w-1 h-0.5 bg-gray-400 rounded"></div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            onMouseDown={(e) => e.stopPropagation()} // Prevent drag when clicking buttons
            className={`px-2 py-1 rounded text-xs ${
              isRecording 
                ? 'bg-red-600 hover:bg-red-700' 
                : 'bg-green-600 hover:bg-green-700'
            }`}
          >
            {isRecording ? 'Stop' : 'Start'}
          </button>
          <button
            onClick={() => {
              clearMetrics();
              setApiMetrics([]);
            }}
            onMouseDown={(e) => e.stopPropagation()}
            className="px-2 py-1 bg-gray-600 hover:bg-gray-700 rounded text-xs"
          >
            Clear
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            onMouseDown={(e) => e.stopPropagation()}
            className="px-2 py-1 bg-gray-600 hover:bg-gray-700 rounded text-xs"
          >
            {isExpanded ? '−' : '+'}
          </button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="p-3 grid grid-cols-2 gap-3">
        <div>
          <div className="text-gray-400">API Requests</div>
          <div className="font-bold">{apiStats.totalRequests}</div>
        </div>
        <div>
          <div className="text-gray-400">Avg Response</div>
          <div className="font-bold">{formatTime(apiStats.avgRoundTripTime)}</div>
        </div>
        <div>
          <div className="text-gray-400">Cache Hit</div>
          <div className="font-bold text-green-400">{apiStats.cacheHitRate.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-gray-400">FPS</div>
          <div className={`font-bold ${getFPSColor(stats.currentFPS)}`}>
            {stats.currentFPS}
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <>
          {/* Recent Requests */}
          <div className="border-t border-gray-600 p-3">
            <div className="text-gray-400 mb-2">Recent API Requests ({apiMetrics.length})</div>
            <div className="max-h-40 overflow-y-auto space-y-1">
              {apiMetrics.slice(0, 10).map((metric, index) => (
                <div key={`${metric.endpoint}-${metric.timestamp}-${index}`} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className={`w-1 h-1 rounded-full ${getCacheColor(metric.cached)}`} />
                    <span className="truncate">{metric.endpoint.split('?')[0]}</span>
                    <span className="text-green-400">200</span>
                  </div>
                  <div className="flex items-center gap-2 text-right">
                    {metric.alertCount && (
                      <span className="text-blue-400">{metric.alertCount}a</span>
                    )}
                    <span>{formatTime(metric.roundTripTime)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* FPS History */}
          {stats.frameRates.length > 0 && (
            <div className="border-t border-gray-600 p-3">
              <div className="text-gray-400 mb-2">
                FPS History (Avg: {stats.avgFPS.toFixed(1)})
              </div>
              <div className="flex items-end h-8 gap-1">
                {stats.frameRates.slice(0, 20).map((frame, index) => (
                  <div
                    key={index}
                    className={`w-1 ${getFPSColor(frame.fps)} bg-current opacity-75`}
                    style={{ height: `${Math.min((frame.fps / 60) * 100, 100)}%` }}
                    title={`${frame.fps} FPS`}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Endpoint Summary */}
          {apiMetrics.length > 0 && (
            <div className="border-t border-gray-600 p-3">
              <div className="text-gray-400 mb-2">Endpoint Summary</div>
              <div className="space-y-1">
                {Object.entries(
                  apiMetrics.reduce((acc, metric) => {
                    const endpoint = metric.endpoint.split('?')[0];
                    if (!acc[endpoint]) {
                      acc[endpoint] = { count: 0, totalTime: 0, cached: 0 };
                    }
                    acc[endpoint].count++;
                    acc[endpoint].totalTime += metric.roundTripTime;
                    if (metric.cached) acc[endpoint].cached++;
                    return acc;
                  }, {} as Record<string, { count: number; totalTime: number; cached: number }>)
                ).map(([endpoint, data]) => (
                  <div key={endpoint} className="flex justify-between">
                    <span className="truncate flex-1">{endpoint.split('/').pop()}</span>
                    <span className="text-gray-400">
                      {data.count}x • {formatTime(data.totalTime / data.count)} • 
                      {((data.cached / data.count) * 100).toFixed(0)}% cached
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PerformancePanel;
