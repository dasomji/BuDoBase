import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'node:path';

export default defineConfig({
  base: '/static/frontend/',
  plugins: [react(), tailwindcss()],
  build: {
    outDir: resolve(__dirname, '../budo_app/static/frontend'),
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: resolve(__dirname, 'src/main.jsx'),
      output: {
        entryFileNames: 'app.js',
        assetFileNames: assetInfo =>
          assetInfo.names?.some(name => name.endsWith('.css'))
            ? 'app.css'
            : 'assets/[name]-[hash][extname]',
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test-setup.js',
  },
});
