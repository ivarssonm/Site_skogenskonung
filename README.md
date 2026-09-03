# Skogenskonung

Statisk efterföljare till den gamla WordPress-sajten på [skogenskonung.com](https://www.skogenskonung.com).

> Det är inte slutet som är målet med livet utan vägen dit.

## Teknik

**Astro + TypeScript** för sajten, **Markdown** för innehållet. TypeScript är bra i koden, men Martins inlägg ska inte vara TypeScript — de är vanliga textfiler som byggs till HTML.

Resultatet är en statisk webbapp: inget PHP, ingen databas, inga WordPress-uppdateringar. Passar Azure Static Web Apps, Cloudflare Pages eller vilken vanlig webbserver som helst.

## Innehåll

Allt är hämtat från den levande WordPress-sajten:

- 181 blogginlägg (2009–2022)
- 12 sidor, inklusive fotoalbum
- 2 godkända kommentarer, visade som *Migrerad*
- Bilder från mediabiblioteket och NextGEN-gallerier

Gamla adresser som `/{slug}/` och `/{år}/{månad}/` är bevarade.

## Utveckling

```bash
npm install
npm run dev
```

Bygg:

```bash
npm run build
npm run preview
```

Återexportera från WordPress (om den gamla sajten fortfarande är uppe):

```bash
npm run export:wp
```

## Nya inlägg

Se [MARTIN.md](MARTIN.md). Kortversion:

```bash
npm run nytt-inlagg -- "Rubriken här"
```

## Publicera

Lägg upp mappen `dist/` efter `npm run build`, eller koppla repot till Azure Static Web Apps.

Azure-workflowen ska peka så här (redan satt i `.github/workflows/`):

- **App location:** `/`
- **Output location:** `dist`
- **API location:** tom

Pekaren mot `skogenskonung.com` byts när ni är nöjda med förhandsvisningen.
