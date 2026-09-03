import { defineConfig } from "astro/config";

// Astro 5 static site. Content lives in Markdown so Martin can edit without TypeScript.
export default defineConfig({
  site: "https://www.skogenskonung.com",
  trailingSlash: "always",
  compressHTML: true,
  build: {
    inlineStylesheets: "auto",
  },
});
