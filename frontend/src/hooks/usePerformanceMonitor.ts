import { useState, useEffect, useCallback, useRef } from 'react';

export interface PerformanceMetric {
  id: string;
  timestamp: number;
  endpoint: string;
  method: string;
  roundTripTime: number;
  alertCount?: number;
  cached: boolean;
  responseSize?: number;
  statusCode?: number;
}

export interface FrameRateMetric {
  timestamp: number;
  fps: number;
  frameTime: number;
}

export interface PerformanceStats {
  metrics: PerformanceMetric[];
  frameRates: FrameRateMetric[];
  avgRoundTripTime: number;
  totalRequests: number;
  cacheHitRate: number;
  currentFPS: number;
  avgFPS: number;
}

const MAX_METRICS = 100; // Keep last 100 requests
const MAX_FRAME_RATES = 60; // Keep last 60 FPS measurements

export const usePerformanceMonitor = () => {
  const [metrics, setMetrics] = useState<PerformanceMetric[]>([]);
  const [frameRates, setFrameRates] = useState<FrameRateMetric[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  
  // FPS tracking
  const frameCount = useRef(0);
  const lastTime = useRef(performance.now());
  const animationFrame = useRef<number>();

  // Start/stop recording
  const startRecording = useCallback(() => {
    setIsRecording(true);
  }, []);

  const stopRecording = useCallback(() => {
    setIsRecording(false);
    if (animationFrame.current) {
      cancelAnimationFrame(animationFrame.current);
    }
  }, []);

  const clearMetrics = useCallback(() => {
    setMetrics([]);
    setFrameRates([]);
  }, []);

  // Record API performance metric
  const recordMetric = useCallback((metric: Omit<PerformanceMetric, 'id' | 'timestamp'>) => {
    if (!isRecording) return;

    const newMetric: PerformanceMetric = {
      ...metric,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
    };

    setMetrics(prev => {
      const updated = [newMetric, ...prev];
      return updated.slice(0, MAX_METRICS);
    });
  }, [isRecording]);

  // FPS measurement function
  const measureFPS = useCallback(() => {
    if (!isRecording) return;

    const now = performance.now();
    frameCount.current++;

    // Calculate FPS every 500ms
    if (now - lastTime.current >= 500) {
      const fps = Math.round((frameCount.current * 1000) / (now - lastTime.current));
      const frameTime = (now - lastTime.current) / frameCount.current;

      setFrameRates(prev => {
        const newFrameRate: FrameRateMetric = {
          timestamp: now,
          fps,
          frameTime,
        };
        const updated = [newFrameRate, ...prev];
        return updated.slice(0, MAX_FRAME_RATES);
      });

      frameCount.current = 0;
      lastTime.current = now;
    }

    animationFrame.current = requestAnimationFrame(measureFPS);
  }, [isRecording]);

  // Start FPS monitoring when recording starts
  useEffect(() => {
    if (isRecording) {
      frameCount.current = 0;
      lastTime.current = performance.now();
      animationFrame.current = requestAnimationFrame(measureFPS);
    } else {
      if (animationFrame.current) {
        cancelAnimationFrame(animationFrame.current);
      }
    }

    return () => {
      if (animationFrame.current) {
        cancelAnimationFrame(animationFrame.current);
      }
    };
  }, [isRecording, measureFPS]);

  // Calculate stats
  const stats: PerformanceStats = {
    metrics,
    frameRates,
    avgRoundTripTime: metrics.length > 0 
      ? metrics.reduce((sum, m) => sum + m.roundTripTime, 0) / metrics.length 
      : 0,
    totalRequests: metrics.length,
    cacheHitRate: metrics.length > 0 
      ? (metrics.filter(m => m.cached).length / metrics.length) * 100 
      : 0,
    currentFPS: frameRates.length > 0 ? frameRates[0].fps : 0,
    avgFPS: frameRates.length > 0 
      ? frameRates.reduce((sum, f) => sum + f.fps, 0) / frameRates.length 
      : 0,
  };

  return {
    stats,
    isRecording,
    startRecording,
    stopRecording,
    clearMetrics,
    recordMetric,
  };
};
