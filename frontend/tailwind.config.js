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
        status: {
          connecting: '#ea580c', // orange-600 - matches primary
          connected: '#65a30d', // green-600 - matches low priority
          error: '#dc2626', // red-600 - matches critical
          warning: '#f59e42', // orange-400 - matches medium priority
        },
        text: {
          primary: '#f4f4f5', // zinc-100
          secondary: '#d4d4d8', // zinc-300
          muted: '#a1a1aa' // zinc-400
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