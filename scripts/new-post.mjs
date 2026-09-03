#!/usr/bin/env node
/**
 * Skapa ett nytt inlägg som Markdown-fil.
 * Användning: npm run nytt-inlagg -- "Rubrik här"
 */
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const title = process.argv.slice(2).join(" ").trim();

if (!title) {
  console.error('Ange en rubrik: npm run nytt-inlagg -- "Hösten i skogen"');
  process.exit(1);
}

const slug = title
  .toLowerCase()
  .normalize("NFD")
  .replace(/\p{M}/gu, "")
  .replace(/å/g, "a")
  .replace(/ä/g, "a")
  .replace(/ö/g, "o")
  .replace(/[^a-z0-9]+/g, "-")
  .replace(/^-|-$/g, "");

const now = new Date();
const pad = (n) => String(n).padStart(2, "0");
const date = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}:00`;
const file = join(root, "src/content/posts", `${slug}.md`);

if (existsSync(file)) {
  console.error(`Finns redan: ${file}`);
  process.exit(1);
}

mkdirSync(dirname(file), { recursive: true });
writeFileSync(
  file,
  `---
title: ${JSON.stringify(title)}
slug: ${slug}
date: ${date}
author: Martin Ivarsson
categories:
  - okategoriserade
excerpt: ""
draft: false
---

Skriv inlägget här. Bilder lägger du i \`public/media/uploads/new/\` och pekar på med:

![Beskrivning](/media/uploads/new/filnamn.jpg)
`,
  "utf8",
);

console.log(`Skapat ${file}`);
console.log(`Adress blir /${slug}/`);
