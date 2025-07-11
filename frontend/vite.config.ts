import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Optimize dependency pre-bundling for faster dev server startup
  optimizeDeps: {
    include: [
      "react",
      "react-dom",
      "react-router-dom",
      "axios",
      "@react-oauth/google",
      "@tanstack/react-query",
      "recharts",
    ],
    // Exclude large dependencies that work better as separate chunks
    exclude: ["mapbox-gl"],
  },
  server: {
    port: 3000,
    host: true, // needed for docker
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    // Modern build target for better performance
    target: "es2020",
    // Optimize CSS code splitting
    cssCodeSplit: true,
    // Ensure proper chunking for better caching
    rollupOptions: {
      output: {
        // Better chunk splitting strategy
        manualChunks: {
          // Core React dependencies
          "react-vendor": ["react", "react-dom"],
          // Routing
          router: ["react-router-dom"],
          // Large UI library
          mui: ["@mui/material", "@mui/icons-material", "@emotion/react", "@emotion/styled"],
          // Map library (large)
          mapbox: ["mapbox-gl", "react-map-gl"],
          // Data/HTTP utilities
          utils: ["axios", "@react-oauth/google", "@tanstack/react-query"],
          // Charting library
          charts: ["recharts"],
        },
        chunkFileNames: "assets/js/[name]-[hash].js",
        entryFileNames: "assets/js/[name]-[hash].js",
      },
    },
    // Optimize minification
    minify: "esbuild",
    // Set reasonable chunk size limit
    chunkSizeWarningLimit: 1000,
  },
});
