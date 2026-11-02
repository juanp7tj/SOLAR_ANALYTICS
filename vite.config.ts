import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  root: 'frontend',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    allowedHosts: ['3000-it2wdur24j0jly701k6yj-70b0567a.us3.manus.computer'],
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  build: {
    outDir: '../static',
    emptyOutDir: true,
    sourcemap: false,
  },
});
