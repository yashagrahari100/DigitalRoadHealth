/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0B0F19',
          800: '#141A28',
          700: '#1E293B',
          600: '#334155',
        },
        accent: {
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
        },
        anomaly: {
          pothole: '#f43f5e', // Rose
          speed_breaker: '#06b6d4', // Cyan
        }
      },
      backgroundImage: {
        'glass': 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.4) 100%)',
      }
    },
  },
  plugins: [],
}
