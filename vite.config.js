import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  root: 'static_src',
  base: '/static/dist/',
  build: {
    outDir: path.resolve(__dirname, 'static/dist'),
    manifest: 'manifest.json',
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'static_src/js/main.js'),
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
