/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // iOS-style fonts (SF Pro fallback to Inter)
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          '"SF Pro Text"',
          'Inter',
          '"Segoe UI"',
          'system-ui',
          'Roboto',
          'sans-serif',
        ],
      },
      // Apple Blue + soft greys
      colors: {
        primary: {
          50:  "#eef4ff",
          100: "#dce7ff",
          200: "#bccfff",
          300: "#8fadff",
          400: "#5f86ff",
          500: "#3b6cf7",  // основной (как iOS)
          600: "#2554e0",
          700: "#1f44b8",
          800: "#1d3a93",
          900: "#1d3478",
        },
        // Тёплый серый (как macOS/iOS Big Sur)
        gray: {
          50:  "#fafafa",
          100: "#f4f4f5",
          200: "#e4e4e7",
          300: "#d4d4d8",
          400: "#a1a1aa",
          500: "#71717a",
          600: "#52525b",
          700: "#3f3f46",
          800: "#27272a",
          900: "#18181b",
        },
        // Системные акценты (iOS)
        success: { 50: "#ecfdf5", 500: "#10b981", 600: "#059669" },
        warning: { 50: "#fffbeb", 500: "#f59e0b", 600: "#d97706" },
        danger:  { 50: "#fef2f2", 500: "#ef4444", 600: "#dc2626" },
        ios: {
          blue:   "#007aff",
          purple: "#af52de",
          pink:   "#ff2d92",
          red:    "#ff3b30",
          orange: "#ff9500",
          yellow: "#ffcc00",
          green:  "#34c759",
          teal:   "#5ac8fa",
          indigo: "#5856d6",
        },
      },
      // Большие скругления как в iOS
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
        '4xl': '1.5rem',
      },
      // Soft shadows (как Apple)
      boxShadow: {
        'soft':   '0 1px 2px 0 rgb(0 0 0 / 0.04), 0 1px 3px 0 rgb(0 0 0 / 0.06)',
        'card':   '0 1px 3px 0 rgb(0 0 0 / 0.05), 0 4px 12px -2px rgb(0 0 0 / 0.04)',
        'lifted': '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 10px 25px -5px rgb(0 0 0 / 0.06)',
        'modal':  '0 20px 60px -10px rgb(0 0 0 / 0.20), 0 8px 24px -4px rgb(0 0 0 / 0.10)',
      },
      // Spring-like animations
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
        'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      keyframes: {
        'slide-up':   { '0%': { transform: 'translateY(8px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
        'fade-in':    { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        'scale-in':   { '0%': { transform: 'scale(0.96)', opacity: '0' }, '100%': { transform: 'scale(1)', opacity: '1' } },
      },
      animation: {
        'slide-up': 'slide-up 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'fade-in':  'fade-in 0.2s ease-out',
        'scale-in': 'scale-in 0.2s cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
};
