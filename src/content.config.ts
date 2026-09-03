import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const commentSchema = z.object({
  id: z.number(),
  author: z.string(),
  date: z.string(),
  parent: z.number().default(0),
  content: z.string(),
  html: z.string().optional(),
  legacy: z.boolean().default(true),
});

const posts = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/posts" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    date: z.string(),
    updated: z.string().optional(),
    author: z.string().default("Martin Ivarsson"),
    categories: z.array(z.string()).default([]),
    excerpt: z.string().default(""),
    draft: z.boolean().default(false),
    cover: z.string().optional(),
    wp_id: z.number().optional(),
    legacy_url: z.string().optional(),
    comments: z.array(commentSchema).default([]),
  }),
});

const pages = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/pages" }),
  schema: z.object({
    title: z.string(),
    slug: z.string(),
    date: z.string().optional(),
    updated: z.string().optional(),
    author: z.string().default("Martin Ivarsson"),
    kind: z.enum(["page", "gallery"]).default("page"),
    draft: z.boolean().default(false),
    wp_id: z.number().optional(),
    legacy_url: z.string().optional(),
    menu_order: z.number().default(0),
    gallery: z.array(z.string()).default([]),
    excerpt: z.string().optional(),
  }),
});

export const collections = { posts, pages };
