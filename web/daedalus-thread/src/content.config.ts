import { defineCollection, z } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
	docs: defineCollection({
		loader: docsLoader(),
		schema: docsSchema({
			extend: z.object({
				date: z.coerce.date().optional(),
				badge: z.string().optional(),
				badgeVariant: z.enum(['note', 'tip', 'success', 'caution', 'danger']).optional(),
				ignore: z.boolean().optional(),
			}),
		}),
	}),
};
