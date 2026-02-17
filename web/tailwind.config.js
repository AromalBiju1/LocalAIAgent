/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                elyssia: {
                    bg: 'var(--bg)',
                    surface: 'var(--surface)',
                    card: 'var(--card)',
                    border: 'var(--border)',
                    hover: 'var(--highlight-dim)',

                    // Maintain pink object structure but map to new variables where possible,
                    // or just keep them for backward compatibility if used directly.
                    // But preferably we want to use the new theme.
                    pink: {
                        50: '#f0f9ff', // Sky 50
                        100: '#e0f2fe',
                        200: '#bae6fd',
                        300: '#7dd3fc',
                        400: '#38bdf8',
                        500: '#0ea5e9', // Sky 500
                        600: '#0284c7',
                        700: '#0369a1',
                        800: '#075985',
                        900: '#0c4a6e',
                    },

                    accent: 'var(--highlight)',     // Cyan Neon
                    glow: 'var(--highlight-glow)',  // Cyan Glow
                    text: 'var(--text)',
                    muted: 'var(--muted)',
                },
            },
            fontFamily: {
                mono: ['Share Tech Mono', 'JetBrains Mono', 'monospace'],
                sans: ['Rajdhani', 'Inter', 'sans-serif'],
            },
            animation: {
                'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
                'blink': 'blink 1s step-end infinite',
                'fadeIn': 'fadeIn 0.3s ease-out',
                'slideUp': 'slideUp 0.3s ease-out',
                'spin-slow': 'spin-slow 10s linear infinite',
                'glitch': 'glitch 0.3s cubic-bezier(.25, .46, .45, .94) both infinite',
            },
            keyframes: {
                'pulse-glow': {
                    '0%, 100%': { boxShadow: '0 0 5px var(--highlight-dim)' },
                    '50%': { boxShadow: '0 0 20px var(--highlight-glow)' },
                },
                'blink': {
                    '0%, 100%': { opacity: '1' },
                    '50%': { opacity: '0' },
                },
                'fadeIn': {
                    '0%': { opacity: '0', transform: 'translateY(8px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                'slideUp': {
                    '0%': { opacity: '0', transform: 'translateY(16px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                'spin-slow': {
                    'from': { transform: 'rotate(0deg)' },
                    'to': { transform: 'rotate(360deg)' },
                },
            },
            boxShadow: {
                'glow-sm': '0 0 8px var(--highlight-dim)',
                'glow': '0 0 15px var(--highlight-glow)',
                'glow-lg': '0 0 30px var(--highlight-glow)',
            },
        },
    },
    plugins: [],
};

