export default {
  content: ['./frontend/index.html', './frontend/src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        midnight: '#080d12',
        panel: '#10181f',
        emerald: '#13d39a',
        lime: '#c4f26b',
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
      boxShadow: { glow: '0 0 38px rgba(19, 211, 154, .12)' },
    },
  },
  plugins: [],
};
