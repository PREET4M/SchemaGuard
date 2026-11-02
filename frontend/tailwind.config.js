/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          bg: '#F7F8FA',
          surface: '#FFFFFF',
          'surface-2': '#F1F4F8',
          border: '#E5E9F0',
          primary: '#2563EB',
          'primary-dark': '#1D4ED8',
          cyan: '#0891B2',
          text: '#171C26',
          'text-2': '#647084',
          muted: '#929BA9',
          success: '#159B67',
          warning: '#D99A22',
          error: '#DC4B4B',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'SF Mono',
          'ui-monospace',
          'Menlo',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'monospace',
        ],
      },
      borderRadius: {
        DEFAULT: '8px',
        md: '8px',
        lg: '10px',
        xl: '12px',
        '2xl': '16px',
      },
      boxShadow: {
        card: '0 2px 12px -2px rgba(23,28,38,0.06), 0 1px 3px rgba(23,28,38,0.03)',
        'card-hover': '0 8px 24px -4px rgba(23,28,38,0.08), 0 2px 6px rgba(23,28,38,0.04)',
        nav: '0 1px 0 0 rgba(229,233,240,0.8)',
      },
      keyframes: {
        'fade-in': { '0%': { opacity: '0', transform: 'translateY(10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out forwards',
      },
    },
  },
  plugins: [],
};

