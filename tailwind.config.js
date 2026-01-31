/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./dashboard/**/*.{html,js}",
    "./src/**/*.{html,js}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Apple-inspired dark theme
        'bg-primary': '#000000',
        'bg-secondary': '#121212',
        'bg-card': '#1d1d1f',
        'bg-elevated': '#2c2c2e',
        'bg-hover': '#3a3a3c',
        'text-primary': '#f5f5f7',
        'text-secondary': '#a1a1a6',
        'text-muted': '#86868b',
        'accent': '#0a84ff',
        'success': '#34c759',
        'warning': '#ff9f0a',
        'danger': '#ff453a',
        'teal': '#5ac8fa',
        'purple-custom': '#af52de',
        'pnl-positive': '#30d158',
        'pnl-negative': '#ff6961',
        'border-color': '#38383a',
        'border-subtle': '#2c2c2e'
      },
      fontFamily: {
        'sans': ['-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', 'Inter', 'sans-serif'],
        'mono': ['SF Mono', 'Menlo', 'Monaco', 'JetBrains Mono', 'monospace']
      },
      backdropBlur: {
        '20': '20px',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        }
      }
    },
  },
  plugins: [],
}