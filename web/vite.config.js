import { defineConfig } from 'vite'

export default defineConfig({
  // runonweb se distribuye como .ts con `import type`: el optimizador de deps de Vite 8 no lo
  // parsea y tumba `npm run dev`. Excluido, Vite lo transpila como fuente propia.
  optimizeDeps: { exclude: ['runonweb'] },
  build: {
    rollupOptions: { input: ['index.html', 'bench.html', 'voice.html'] },
  },
})
