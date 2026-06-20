import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        'aios-bg':      '#f5f1e8',
        'aios-panel':   '#fffdf8',
        'aios-ink':     '#1f1a14',
        'aios-muted':   '#6d655b',
        'aios-line':    '#d8cebf',
        'aios-accent':  '#0b6e4f',
        'aios-accent2': '#c5622d',
      },
      fontFamily: {
        serif: ['Georgia', '"Times New Roman"', 'serif'],
        mono:  ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
