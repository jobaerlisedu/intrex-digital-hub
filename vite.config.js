import { defineConfig } from 'vite';
import path from 'path';

const BASE = path.resolve('.');

export default defineConfig({
  root: path.join(BASE, 'static_src'),
  base: '/static/dist/',
  build: {
    outDir: path.join(BASE, 'static/dist'),
    manifest: 'manifest.json',
    emptyOutDir: true,
    rollupOptions: {
      input: path.join(BASE, 'static_src/js/main.js'),
      output: {
        entryFileNames: 'js/[name].js',
        chunkFileNames: 'js/[name].js',
        assetFileNames: 'assets/[name][extname]',
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    cors: true,
  },
});
