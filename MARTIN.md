# För Martin — så skriver du ett nytt inlägg

Sajten är inte WordPress längre. Du skriver i en vanlig textfil. När sidan byggs blir det en färdig webbsida.

## Enklaste sättet

1. Öppna en terminal i projektmappen.
2. Kör:

```bash
npm run nytt-inlagg -- "Bruse i höstskogen"
```

3. Öppna filen som skapades, till exempel `src/content/posts/bruse-i-hostskogen.md`.
4. Skriv texten under strecken längst ner.
5. Lägg bilder i `public/media/uploads/new/` och peka på dem så här:

```markdown
Här kommer en bild från passet.

![Bruse i pass](/media/uploads/new/bruse.jpg)
```

6. Spara. Kör `npm run dev` och öppna adressen som skriptet skrev ut.


## Vad betyder fälten högst upp?

```yaml
title: Bruse i höstskogen
slug: bruse-i-hostskogen
date: 2026-08-16T18:00:00
author: Martin Ivarsson
categories:
  - jakt-jakt
excerpt: Kort mening som syns i listorna.
draft: false
```

- **title** — rubriken
- **slug** — adressen, t.ex. `/bruse-i-hostskogen/`
- **categories** — `jakt-jakt`, `friluftsliv-jakt` eller `okategoriserade`
- **draft: true** — filen finns men publiceras inte

## Ny sida

Kopiera en fil i `src/content/pages/` och byt `slug` och `title`. Gallerier använder `kind: gallery` och en lista med bildvägar.

## Kommentarer

Gamla kommentarer ligger kvar under inläggen, märkta *Migrerad*. Nya kommentarer går inte att skriva på sidan. Vill du spara en hälsning gör du det i själva inlägget.

## Publicera

När du är nöjd: bygg sajten (`npm run build`) och lägg upp den, eller be Eric koppla GitHub så att varje sparad ändring går ut automatiskt.
