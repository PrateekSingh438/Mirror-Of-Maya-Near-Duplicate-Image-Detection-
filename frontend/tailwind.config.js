/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        saffron: {
          50: '#fff8f0',
          100: '#ffe6d5',
          200: '#ffd4aa',
          300: '#ffb84d',
          400: '#ff9f1c',
          500: '#ff8700',
          600: '#e67e0d',
          700: '#d47015',
          800: '#c05a1a',
          900: '#9a4415',
        },
        indigo: {
          50: '#f6f5ff',
          100: '#ede9ff',
          200: '#ddd4ff',
          300: '#b8a9ff',
          400: '#8b7aff',
          500: '#6b5aff',
          600: '#4b0082',
          700: '#3d006b',
          800: '#2d004d',
          900: '#1a0630',
        },
        parchment: {
          50: '#fefdf9',
          100: '#fefbf3',
          200: '#fdf8ec',
          300: '#fcf3de',
          400: '#f5e6d3',
          500: '#f0dcc4',
          600: '#e8d4b8',
          700: '#dcc7a9',
          800: '#ccb896',
          900: '#b8a685',
        },
        maya: {
          dark: '#1A0D1F',
          darker: '#0D0610',
        },
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1rem' }],
        sm: ['0.875rem', { lineHeight: '1.25rem' }],
        base: ['1rem', { lineHeight: '1.5rem' }],
        lg: ['1.125rem', { lineHeight: '1.75rem' }],
        xl: ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      animation: {
        'spin-chakra': 'spin-chakra 10s linear infinite',
        'pulse-chakra': 'pulse-chakra 2.5s ease-in-out infinite',
        'pulse-inner': 'pulse-inner 3s ease-in-out infinite',
        'spin-fast': 'spin 1s linear infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s ease-in-out infinite',
      },
      keyframes: {
        'spin-chakra': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'pulse-chakra': {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.5' },
          '50%': { transform: 'scale(1.15)', opacity: '0.8' },
        },
        'pulse-inner': {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.4' },
          '50%': { transform: 'scale(0.85)', opacity: '0.6' },
        },
        'glow': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'shimmer': {
          '0%, 100%': { backgroundPosition: '200% center' },
          '50%': { backgroundPosition: '-200% center' },
        },
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '12px',
        lg: '16px',
      },
      boxShadow: {
        'saffron-glow': '0 0 20px rgba(255, 159, 28, 0.5)',
        'saffron-glow-lg': '0 0 30px rgba(255, 159, 28, 0.7)',
        'indigo-glow': '0 0 15px rgba(75, 0, 130, 0.3)',
        'gold-glow': '0 0 20px rgba(255, 215, 0, 0.4)',
      },
      backgroundImage: {
        'gradient-maya': 'linear-gradient(135deg, #4B0082 0%, #2D004D 50%, #0D0610 100%)',
        'gradient-chakra': 'radial-gradient(circle, #FF9F1C 0%, #FFD700 30%, #FF6B35 60%, transparent 80%)',
        'gradient-sacred': 'linear-gradient(135deg, #FF9F1C 0%, #4B0082 50%, #2D004D 100%)',
      },
    },
  },
  plugins: [],
}
