/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#ea580c', // orange-600
        accent: '#fbbf24', // orange-300
        critical: '#dc2626', // red-600
        high: '#ea580c', // orange-600
        medium: '#f59e42', // orange-400
        low: '#65a30d', // green-600
        card: '#f3f4f6', // gray-100
        background: '#f9fafb', // gray-50
        border: '#e5e7eb', // gray-200
        text: {
          primary: '#111827', // gray-900
          secondary: '#374151', // gray-700
          muted: '#6b7280' // gray-500
        }
      },
      spacing: {
        '128': '32rem',
      },
      borderRadius: {
        'xl': '0.5rem',
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 8px 25px -5px rgba(0, 0, 0, 0.3)',
      }
    },
  },
  plugins: [],
} 