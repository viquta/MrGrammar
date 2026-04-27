import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	build: {
		target: 'es2022',
		sourcemap: false,
		cssCodeSplit: true,
		modulePreload: {
			polyfill: false
		},
		chunkSizeWarningLimit: 700,
		rollupOptions: {
			output: {
				manualChunks(id) {
					if (!id.includes('node_modules')) {
						return undefined;
					}
					if (id.includes('svelte') || id.includes('@sveltejs')) {
						return 'vendor-svelte';
					}
					return 'vendor';
				}
			}
		}
	}
});
