// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://digital-transformation-center.github.io',
	base: '/daedalus-thread',
	integrations: [
		starlight({
			title: 'Daedalus Thread',
			logo: {
				light: './src/assets/daedalus_full.svg',
				dark: './src/assets/daedalus_full_dark.svg',
				replacesTitle: true,
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/Digital-Transformation-Center/daedalus-thread' }],
			sidebar: [
				{
					label: 'About',
					collapsed: true,
					items: [
						{ label: 'Project Overview', slug: 'about/overview' },
						{ label: 'Digital Thread Architecture', slug: 'about/digital-thread' },
					],
				},
				{
					label: 'Roadmap',
					collapsed: true,
					items: [
						{ label: 'Project Phases', slug: 'roadmap/phases' },
					],
				},
				{
					label: 'Research',
					collapsed: true,
					items: [
						{ label: 'Case Studies', slug: 'research/case-studies' },
					],
				},
				{
					label: 'Project Updates',
					collapsed: true,
					items: [
						{ label: 'Project Updates', slug: 'updates' },
					],
				},
			],
		}),
	],
});
