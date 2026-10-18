/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        wh: {
          bg:       '#0a0c12',
          panel:    '#0f1219',
          card:     '#161926',
          border:   '#1e2435',
          border2:  '#252d40',
          muted:    '#8892a4',
          floor:    '#111724',
          shelf:    '#1e1b4b',
          robot:    '#06b6d4',
          packing:  '#d97706',
          charging: '#16a34a',
          obstacle: '#dc2626',
          planned:  '#1d4ed8',
          traversed:'#1e3a5f',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-slow':  'pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite',
        'robot-blink': 'robot-blink 1s ease-in-out infinite',
        'slide-in':    'slideIn 0.2s ease-out',
        'fade-in':     'fadeIn 0.3s ease-out',
      },
      keyframes: {
        'robot-blink': {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.5' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateY(-4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
