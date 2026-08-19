/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // App background
        bg: {
          base:    '#04040f',
          card:    'rgba(255,255,255,0.024)',
          'card-hover': 'rgba(255,255,255,0.038)',
        },
        // Brand
        brand: {
          blue:    '#3b82f6',
          purple:  '#8b5cf6',
          green:   '#10b981',
          amber:   '#f59e0b',
          red:     '#ef4444',
        },
        // Text
        text: {
          primary:   '#f1f5f9',
          secondary: '#94a3b8',
          muted:     '#475569',
          disabled:  '#334155',
        },
        // Border
        border: {
          subtle:  'rgba(255,255,255,0.062)',
          DEFAULT: 'rgba(255,255,255,0.09)',
          focus:   'rgba(59,130,246,0.42)',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.67rem', { lineHeight: '1rem' }],
        'xs':  ['0.75rem', { lineHeight: '1.1rem' }],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
        '4xl': '1.5rem',
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'pulse-slow':  'pulse 3s ease-in-out infinite',
        'fade-in':     'fadeIn 0.3s ease-out',
        'slide-up':    'slideUp 0.35s ease-out',
        'spin-slow':   'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 },                     to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(12px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
      },
      boxShadow: {
        'glow-blue':   '0 0 24px rgba(59,130,246,0.18)',
        'glow-purple': '0 0 24px rgba(139,92,246,0.15)',
        'card':        '0 4px 24px rgba(0,0,0,0.28)',
        'card-hover':  '0 8px 40px rgba(0,0,0,0.38)',
      },
    },
  },
  plugins: [],
}