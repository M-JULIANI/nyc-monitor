/**
 * Utility functions for development mode detection
 */

export const isDevelopmentMode = (): boolean => {
  // Check multiple indicators for development mode
  return (
    process.env.NODE_ENV === 'development' ||
    import.meta.env.DEV ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname.includes('codespaces') ||
    window.location.hostname.includes('gitpod') ||
    window.location.port === '3000' || // Vite default port
    window.location.search.includes('debug=true')
  );
};
