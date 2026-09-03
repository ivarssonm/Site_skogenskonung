export const site = {
  name: "Skogenskonung",
  tagline: "Det är inte slutet som är målet med livet utan vägen dit",
  author: "Martin Ivarsson",
  description:
    "Jakt, friluftsliv, taxar och livet på landet. Martins anteckningar från skogen sedan 2009.",
  url: "https://www.skogenskonung.com",
  locale: "sv-SE",
  nav: [
    { href: "/", label: "Hem" },
    { href: "/kategori/jakt-jakt/", label: "Jakt" },
    { href: "/kategori/friluftsliv-jakt/", label: "Friluftsliv" },
    { href: "/fotoalbum/", label: "Fotoalbum" },
    { href: "/arkiv/", label: "Arkiv" },
    { href: "/om-mig/", label: "Om mig" },
  ],
  categories: {
    "jakt-jakt": { name: "Jakt", blurb: "Drev, vak och jakthundar." },
    "friluftsliv-jakt": { name: "Friluftsliv", blurb: "Skog, fjäll och vardag ute." },
    okategoriserade: { name: "Övrigt", blurb: "Anteckningar vid sidan av." },
    friluftsliv: { name: "Friluftsliv", blurb: "Uteliv." },
    jakt: { name: "Jakt", blurb: "Jakt." },
  } as Record<string, { name: string; blurb: string }>,
};

export function categoryLabel(slug: string): string {
  return site.categories[slug]?.name ?? slug;
}
