/** @type {import('tailwindcss').Config} */

// Semantische Farben kommen aus CSS-Variablen (src/assets/global.css),
// damit Hell/Dunkel ohne dark:-Varianten in jeder Komponente funktioniert.
const themed = (name) => `rgb(var(--c-${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Flächen & Text (themeabhängig)
        app: themed('app'),
        surface: themed('surface'),
        raised: themed('raised'),
        line: themed('line'),
        fg: themed('fg'),
        muted: themed('muted'),
        subtle: themed('subtle'),
        // Cyan als Text – im Hellmodus dunkler für ausreichenden Kontrast
        brand: themed('brand'),

        // K.I.T.-Brand (fest)
        navy: {
          DEFAULT: '#0A1628',
          800: '#0A1628',
          900: '#060E1B',
        },
        // Tailwinds cyan-500 (#06B6D4) und blue-500 (#3B82F6) entsprechen bereits den Brand-Farben
        accent: {
          DEFAULT: '#FF6B35',
          400: '#FF8C5C',
          500: '#FF6B35',
          600: '#E4541F',
        },
        presence: {
          available: '#22C55E',
          busy: '#EF4444',
          away: '#F59E0B',
          dnd: '#6B7280',
          offline: '#4B5563',
        },
      },
      fontFamily: {
        sans: ['"Inter Variable"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono Variable"', 'ui-monospace', 'monospace'],
        brand: ['"Montserrat Variable"', '"Inter Variable"', 'sans-serif'],
      },
      keyframes: {
        'pulse-ring': {
          '0%': { transform: 'scale(0.95)', opacity: '0.7' },
          '70%, 100%': { transform: 'scale(1.4)', opacity: '0' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(110%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        'pulse-ring': 'pulse-ring 1.6s cubic-bezier(0.215, 0.61, 0.355, 1) infinite',
        'pulse-soft': 'pulse-soft 1.4s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 0.3s ease-out',
        'fade-in': 'fade-in 0.25s ease-out',
      },
    },
  },
  plugins: [],
}
