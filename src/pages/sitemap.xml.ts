import type { APIRoute } from "astro";
import { allPages, allPosts } from "../lib/content";
import { site } from "../site";

export const GET: APIRoute = async () => {
  const posts = await allPosts();
  const pages = await allPages();
  const urls = [
    "",
    "arkiv/",
    "fotoalbum/",
    "sok/",
    ...posts.map((post) => `${post.data.slug}/`),
    ...pages
      .filter((page) => page.data.slug !== "fotoalbum")
      .map((page) => `${page.data.slug}/`),
  ];
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (path) => `  <url><loc>${site.url}/${path}</loc></url>`,
  )
  .join("\n")}
</urlset>
`;
  return new Response(body, {
    headers: { "Content-Type": "application/xml; charset=utf-8" },
  });
};
