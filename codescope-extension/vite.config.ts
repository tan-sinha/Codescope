import fs from 'node:fs';
import path from 'node:path';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { crx } from '@crxjs/vite-plugin';
import manifest from './manifest.json';

// Strip `crossorigin` from <link rel="stylesheet"> in the built sidepanel HTML.
// crxjs adds it automatically; Chrome extensions don't need it and it can silently
// prevent the stylesheet from applying on some Chrome builds.
function fixSidepanelCss(): Plugin {
  return {
    name: 'fix-sidepanel-css',
    apply: 'build',
    closeBundle() {
      const htmlPath = path.resolve(__dirname, 'dist/sidepanel/index.html');
      if (!fs.existsSync(htmlPath)) return;
      const original = fs.readFileSync(htmlPath, 'utf-8');
      const fixed = original.replace(
        /<link([^>]*?)crossorigin([^>]*?)>/g,
        '<link$1$2>'
      );
      if (fixed !== original) {
        fs.writeFileSync(htmlPath, fixed);
        console.log('[fix-sidepanel-css] removed crossorigin from link tags');
      }
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    crx({ manifest }),
    fixSidepanelCss(),
  ],
});
