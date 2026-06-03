/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      spacing: {
        '2': 'var(--space-2, 0.5rem)',
        '2.5': 'var(--space-2-5, 0.625rem)',
        '3': 'var(--space-3, 0.75rem)',
        '3.5': 'var(--space-3-5, 0.875rem)',
        '4': 'var(--space-4, 1rem)',
        '5': 'var(--space-5, 1.25rem)',
        '6': 'var(--space-6, 1.5rem)',
        '8': 'var(--space-8, 2rem)',
        '10': 'var(--space-10, 2.5rem)',
        '12': 'var(--space-12, 3rem)',
        '16': 'var(--space-16, 4rem)',
      },
      colors: {
        accent: {
          50: 'rgb(var(--accent-50) / <alpha-value>)',
          100: 'rgb(var(--accent-100) / <alpha-value>)',
          200: 'rgb(var(--accent-200) / <alpha-value>)',
          300: 'rgb(var(--accent-300) / <alpha-value>)',
          400: 'rgb(var(--accent-400) / <alpha-value>)',
          500: 'rgb(var(--accent-500) / <alpha-value>)',
          600: 'rgb(var(--accent-600) / <alpha-value>)',
          700: 'rgb(var(--accent-700) / <alpha-value>)',
          800: 'rgb(var(--accent-800) / <alpha-value>)',
          900: 'rgb(var(--accent-900) / <alpha-value>)',
        }
      }
    },
  },
  plugins: [],
}
