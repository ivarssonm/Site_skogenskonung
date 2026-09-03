#!/usr/bin/env python3
"""Export skogenskonung.com from WordPress into Astro content + local media.

Preserves post/page/comment text exactly. Rewrites media to /media/...
Comments are stored as legacy/read-only frontmatter.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Comment, NavigableString
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "export"
RAW = EXPORT / "raw"
CONTENT_POSTS = ROOT / "src" / "content" / "posts"
CONTENT_PAGES = ROOT / "src" / "content" / "pages"
CONTENT_GALLERIES = ROOT / "src" / "content" / "galleries"
MEDIA = ROOT / "public" / "media"

BASE = "https://www.skogenskonung.com"
UA = "Skogenskonung-migration/1.0 (content preservation)"
TIMEOUT = 90
RETRIES = 3

SIZE_SUFFIX = re.compile(r"-(?:\d+x\d+|scaled|rotated)(?=\.[a-zA-Z0-9]+$)")
QUERY_TS = re.compile(r"[?].*$")
SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")

GALLERY_PAGE_SLUGS = [
    "fotoalbum",
    "om-mig",
    "jakt",
    "fran-garden",
    "isolering-garage",
    "carport-2008",
    "traversbalk-i-ladugarden",
    "vedklipp-2013-2",
    "pallgafflar-2009",
    "balspjut",
    "atv-vagn",
    "knuttimrad-bastu",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def iri_to_uri(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/")
    query = urllib.parse.quote(urllib.parse.unquote(parsed.query), safe="=&%")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, parsed.fragment))


def request(url: str, binary: bool = False) -> Any:
    if url.startswith("/") and not url.startswith("//"):
        raise ValueError(f"local path, not a url: {url}")
    last_err: Exception | None = None
    encoded = iri_to_uri(url)
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(encoded, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
                if binary:
                    return data, resp.geturl(), resp.headers.get("Content-Type", "")
                return data.decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 — we retry transient errors
            last_err = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code in {400, 401, 403, 404}:
                break
            wait = min(2 ** attempt, 8)
            log(f"  retry {attempt}/{RETRIES} {url} ({exc}) wait {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Failed {url}: {last_err}")


def rest(path: str, **params: Any) -> Any:
    q = {"rest_route": path, **params}
    url = f"{BASE}/?{urllib.parse.urlencode(q, doseq=True)}"
    return json.loads(request(url))


def fetch_all(path: str, per_page: int = 100) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        log(f"  GET {path} page {page}")
        try:
            chunk = rest(path, per_page=per_page, page=page)
        except RuntimeError as exc:
            if any(code in str(exc) for code in ("400", "404")):
                log(f"  stop: {exc}")
                break
            raise
        if isinstance(chunk, dict) and chunk.get("code"):
            # out of range or forbidden
            log(f"  stop: {chunk.get('code')} {chunk.get('message')}")
            break
        if not isinstance(chunk, list) or not chunk:
            break
        # Detect query-string ignore (same first item as previous page)
        if items and chunk[0].get("id") == items[0].get("id"):
            log("  pagination ignored by server, stopping")
            break
        items.extend(chunk)
        if page >= 30:
            break
        page += 1
        time.sleep(0.3)
    return items


def strip_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    return soup.get_text(" ", strip=True)


def decode_title(html: str) -> str:
    return unescape(BeautifulSoup(html or "", "lxml").get_text()).strip()


def preferred_src(url: str) -> str:
    """Prefer original file over WP resized variants."""
    url = QUERY_TS.sub("", url or "")
    url = url.replace("http://www.skogenskonung.com", BASE)
    url = url.replace("http://skogenskonung.com", BASE)
    url = url.replace("https://skogenskonung.com", BASE)
    return SIZE_SUFFIX.sub("", url)


def local_media_path(url: str) -> Path:
    url = QUERY_TS.sub("", url)
    parsed = urllib.parse.urlparse(url)
    path = unquote_path(parsed.path)
    if "/wp-content/uploads/" in path:
        rel = path.split("/wp-content/uploads/", 1)[1]
        return MEDIA / "uploads" / rel
    if "/wp-content/gallery/" in path:
        rel = path.split("/wp-content/gallery/", 1)[1]
        # skip thumbs/cache
        return MEDIA / "galleries" / rel
    digest = hashlib.sha1(url.encode()).hexdigest()[:12]
    name = SAFE_NAME.sub("-", Path(path).name) or digest
    return MEDIA / "other" / f"{digest}-{name}"


def unquote_path(path: str) -> str:
    return urllib.parse.unquote(path)


def should_skip_gallery_file(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    name = path.name.lower()
    if "thumbs" in parts or "cache" in parts:
        return True
    if name.startswith("thumbs_"):
        return True
    return False


DOWNLOADED: dict[str, str] = {}  # remote url -> public path


def download_file(url: str) -> str | None:
    if not url or url.startswith("data:"):
        return None
    url = url.strip()
    if url.startswith("/") and not url.startswith("//"):
        return url
    url = url.replace("http://www.skogenskonung.com", BASE)
    url = url.replace("http://skogenskonung.com", BASE)
    candidates = []
    original = preferred_src(url)
    if original and original != QUERY_TS.sub("", url):
        candidates.append(original)
    candidates.append(QUERY_TS.sub("", url))
    # unique preserve order
    seen: set[str] = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)

    for candidate in uniq:
        if candidate in DOWNLOADED:
            return DOWNLOADED[candidate]
        dest = local_media_path(candidate)
        if should_skip_gallery_file(dest):
            continue
        public = "/" + dest.relative_to(ROOT / "public").as_posix()
        if dest.exists() and dest.stat().st_size > 0:
            DOWNLOADED[candidate] = public
            return public
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            data, final_url, _ctype = request(candidate, binary=True)
        except Exception as exc:  # noqa: BLE001
            log(f"    miss {candidate} ({exc})")
            continue
        if not data or len(data) < 40:
            continue
        # If we requested original but server returned a tiny html error
        if data[:15].lstrip().lower().startswith(b"<!doctype") or data[:6].lstrip().lower().startswith(b"<html"):
            continue
        dest.write_bytes(data)
        DOWNLOADED[candidate] = public
        DOWNLOADED[final_url] = public
        return public
    return None


def collect_urls_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html or "", "lxml")
    urls: list[str] = []
    for tag in soup.find_all(["img", "video", "source", "a"]):
        for attr in ("src", "href", "data-src", "poster"):
            val = tag.get(attr)
            if not val:
                continue
            if any(ext in val.lower() for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".mp4", ".mov", ".m4v", ".webm")):
                urls.append(val)
        srcset = tag.get("srcset")
        if srcset:
            for part in srcset.split(","):
                u = part.strip().split(" ")[0]
                if u:
                    urls.append(u)
    # also raw regex for gallery originals
    urls.extend(re.findall(r"https?://[^\"'\s>]+\.(?:jpe?g|png|gif|webp|mp4|mov)", html or "", flags=re.I))
    return urls


def rewrite_html(html: str, extra_gallery: list[str] | None = None) -> str:
    if not html:
        return ""
    if html.strip() in {""} or html.strip().startswith("ngg_shortcode_"):
        if extra_gallery:
            return render_gallery_html(extra_gallery)
        return ""

    soup = BeautifulSoup(html, "lxml")
    # drop WP noise
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        local = download_file(src)
        if not local:
            continue
        img["src"] = local
        if img.get("srcset"):
            del img["srcset"]
        if img.get("sizes"):
            del img["sizes"]
        img.attrs.pop("data-src", None)
        img.attrs.pop("decoding", None)
        # keep alt/title
        parent = img.find_parent("a")
        if parent and parent.get("href") and is_media_url(parent.get("href", "")):
            parent["href"] = local

    for video in soup.find_all("video"):
        src = video.get("src")
        if src:
            local = download_file(src)
            if local:
                video["src"] = local
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                local = download_file(src)
                if local:
                    source["src"] = local
        poster = video.get("poster")
        if poster:
            local = download_file(poster)
            if local:
                video["poster"] = local

    for a in soup.find_all("a"):
        href = a.get("href") or ""
        if is_media_url(href):
            local = download_file(href)
            if local:
                a["href"] = local
        else:
            a["href"] = rewrite_internal_link(href)

    # unwrap empty figure wrappers later via pretty html
    body = soup.body
    root = body if body else soup
    # If this was a full document, take children
    parts = []
    for child in list(root.children):
        if getattr(child, "name", None) in {"html", "head"}:
            continue
        parts.append(str(child))
    out = "".join(parts).strip()
    if extra_gallery and "ngg_shortcode" in (html or ""):
        out = (out + "\n" + render_gallery_html(extra_gallery)).strip()
    return out


def is_media_url(url: str) -> bool:
    if not url or (url.startswith("/") and not url.startswith("//")):
        return False
    u = url.lower()
    return any(x in u for x in ("/wp-content/uploads/", "/wp-content/gallery/")) or u.endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".m4v")
    )


def rewrite_internal_link(href: str) -> str:
    if not href:
        return href
    for prefix in (
        "https://www.skogenskonung.com",
        "http://www.skogenskonung.com",
        "https://skogenskonung.com",
        "http://skogenskonung.com",
    ):
        if href.startswith(prefix):
            path = href[len(prefix) :] or "/"
            # drop nggallery pagination etc
            path = path.split("?")[0]
            return path
    return href


def render_gallery_html(urls: list[str]) -> str:
    figs = []
    for url in urls:
        local = download_file(url)
        if not local:
            continue
        figs.append(f'<figure class="gallery-item"><img src="{local}" alt="" /></figure>')
    if not figs:
        return ""
    return '<div class="photo-gallery">\n' + "\n".join(figs) + "\n</div>"


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=88,
    )


def write_md(path: Path, front: dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep body HTML exactly after frontmatter
    text = "---\n" + dump_yaml(front).rstrip() + "\n---\n\n" + (body or "").strip() + "\n"
    path.write_text(text, encoding="utf-8")


def scrape_gallery_images(page_url: str) -> list[str]:
    """Walk NextGEN pagination and collect original image URLs."""
    found: list[str] = []
    seen_pages: set[str] = set()
    queue = [page_url]
    while queue:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        try:
            html = request(url)
        except Exception as exc:  # noqa: BLE001
            log(f"    gallery page fail {url}: {exc}")
            continue
        soup = BeautifulSoup(html, "lxml")
        for a in soup.select("a[data-src], a[href*='/wp-content/gallery/']"):
            src = a.get("data-src") or a.get("href") or ""
            src = QUERY_TS.sub("", src)
            if "/wp-content/gallery/" in src and "/thumbs/" not in src and "/cache/" not in src:
                if src not in found:
                    found.append(src)
        for img in soup.select("img[src*='/wp-content/gallery/']"):
            src = img.get("data-src") or img.get("src") or ""
            src = QUERY_TS.sub("", src)
            # try original next to cache/thumbs
            src = src.replace("/thumbs/thumbs_", "/")
            src = re.sub(r"/cache/[^/]+$", "", src)
            if "/cache/" in src:
                continue
            if "/wp-content/gallery/" in src and src not in found:
                found.append(src)
        for a in soup.select("a.page-numbers, a.prev, .ngg-navigation a"):
            href = a.get("href")
            if href and "nggallery/page/" in href:
                if href.startswith("/"):
                    href = BASE + href
                if href not in seen_pages:
                    queue.append(href)
        time.sleep(0.2)
    return found


def category_names(post: dict, cats_by_id: dict[int, dict]) -> list[str]:
    names = []
    for cid in post.get("categories") or []:
        cat = cats_by_id.get(cid)
        if not cat:
            continue
        # skip empty parent buckets
        if cat.get("count", 0) == 0:
            continue
        names.append(cat["slug"])
    return names or ["okategoriserade"]


def excerpt_from(post: dict) -> str:
    raw = strip_html(post.get("excerpt", {}).get("rendered") or "")
    raw = re.sub(r"\s*Läs mer…?\s*$", "", raw).strip()
    return raw


def comments_for(post_id: int, comments: list[dict]) -> list[dict[str, Any]]:
    out = []
    for c in comments:
        if c.get("post") != post_id:
            continue
        if c.get("status") and c["status"] != "approved":
            continue
        out.append(
            {
                "id": c["id"],
                "author": c.get("author_name") or "Anonym",
                "date": c.get("date"),
                "parent": c.get("parent") or 0,
                "content": strip_html(c.get("content", {}).get("rendered") or ""),
                "html": (c.get("content", {}).get("rendered") or "").strip(),
                "legacy": True,
            }
        )
    out.sort(key=lambda x: x["date"] or "")
    return out


def featured_path(post: dict, media_by_id: dict[int, dict]) -> str | None:
    mid = post.get("featured_media") or 0
    if not mid:
        return None
    media = media_by_id.get(mid)
    if not media:
        return None
    src = media.get("source_url")
    if not src:
        return None
    return download_file(src)


def main() -> int:
    for d in (RAW, CONTENT_POSTS, CONTENT_PAGES, CONTENT_GALLERIES, MEDIA):
        d.mkdir(parents=True, exist_ok=True)

    log("Fetching categories")
    categories = fetch_all("/wp/v2/categories")
    cats_by_id = {c["id"]: c for c in categories}
    (RAW / "categories.json").write_text(json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8")

    log("Fetching comments")
    comments = fetch_all("/wp/v2/comments")
    (RAW / "comments.json").write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  comments: {len(comments)}")

    log("Fetching pages")
    pages = fetch_all("/wp/v2/pages")
    (RAW / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  pages: {len(pages)}")

    log("Fetching posts")
    posts = fetch_all("/wp/v2/posts")
    (RAW / "posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  posts: {len(posts)}")

    log("Fetching media library")
    media = fetch_all("/wp/v2/media")
    (RAW / "media.json").write_text(json.dumps(media, ensure_ascii=False, indent=2), encoding="utf-8")
    media_by_id = {m["id"]: m for m in media}
    log(f"  media: {len(media)}")

    # Scrape live gallery pages (NextGEN does not render in REST)
    log("Scraping gallery pages")
    gallery_map: dict[str, list[str]] = {}
    for slug in GALLERY_PAGE_SLUGS:
        url = f"{BASE}/{slug}/"
        log(f"  gallery {slug}")
        imgs = scrape_gallery_images(url)
        gallery_map[slug] = imgs
        log(f"    {len(imgs)} images")
    (RAW / "galleries.json").write_text(json.dumps(gallery_map, ensure_ascii=False, indent=2), encoding="utf-8")

    # Download media library originals first
    log("Downloading media library files")
    for i, m in enumerate(media, 1):
        src = m.get("source_url")
        if src:
            download_file(src)
        if i % 25 == 0:
            log(f"  media {i}/{len(media)}")

    log("Writing posts")
    for post in posts:
        slug = post["slug"]
        html = post.get("content", {}).get("rendered") or ""
        extra = gallery_map.get(slug)
        body = rewrite_html(html, extra_gallery=extra)
        front = {
            "title": decode_title(post.get("title", {}).get("rendered") or slug),
            "slug": slug,
            "date": post.get("date"),
            "updated": post.get("modified"),
            "author": "Martin Ivarsson",
            "categories": category_names(post, cats_by_id),
            "excerpt": excerpt_from(post),
            "draft": post.get("status") != "publish",
            "wp_id": post["id"],
            "legacy_url": f"/{slug}/",
        }
        feat = featured_path(post, media_by_id)
        if feat:
            front["cover"] = feat
        cms = comments_for(post["id"], comments)
        if cms:
            front["comments"] = cms
        write_md(CONTENT_POSTS / f"{slug}.md", front, body)
        log(f"  post {slug}")

    log("Writing pages")
    page_slugs = set()
    for page in pages:
        slug = page["slug"]
        page_slugs.add(slug)
        html = page.get("content", {}).get("rendered") or ""
        extra = gallery_map.get(slug, [])
        # Always merge scraped gallery if REST only has a shortcode
        body = rewrite_html(html, extra_gallery=extra)
        if not strip_html(body) and extra:
            body = render_gallery_html(extra)
        kind = "gallery" if extra and not strip_html(html.replace("ngg_shortcode_0_placeholder", "").replace("ngg_shortcode_1_placeholder", "")) else "page"
        # more reliable: if body is only a gallery
        if extra and (not html.strip() or "ngg_shortcode" in html or "ngg-galleryoverview" in html):
            kind = "gallery"
            if "ngg-galleryoverview" in html:
                body = rewrite_html(html)  # already has thumbs; rewrite + we want originals
                # prefer originals
                body = render_gallery_html(extra)
        front = {
            "title": decode_title(page.get("title", {}).get("rendered") or slug),
            "slug": slug,
            "date": page.get("date"),
            "updated": page.get("modified"),
            "author": "Martin Ivarsson",
            "kind": kind,
            "draft": page.get("status") != "publish",
            "wp_id": page["id"],
            "legacy_url": f"/{slug}/",
            "menu_order": page.get("menu_order") or 0,
        }
        if extra:
            front["gallery"] = [download_file(u) for u in extra]
            front["gallery"] = [g for g in front["gallery"] if g]
        write_md(CONTENT_PAGES / f"{slug}.md", front, body)
        log(f"  page {slug} ({kind}, {len(extra)} imgs)")

    # Ensure gallery slugs that exist on the live site but maybe missing from REST
    for slug, imgs in gallery_map.items():
        if slug in page_slugs or slug in {p["slug"] for p in posts}:
            continue
        if not imgs and slug not in {"om-mig"}:
            continue
        # fetch live HTML for text pages (om-mig)
        try:
            live = request(f"{BASE}/{slug}/")
            soup = BeautifulSoup(live, "lxml")
            title_el = soup.select_one("h1.entry-title, .entry-title, h1")
            title = title_el.get_text(strip=True) if title_el else slug
            content_el = soup.select_one(".entry-content")
            html = str(content_el) if content_el else ""
            body = rewrite_html(html, extra_gallery=imgs)
        except Exception as exc:  # noqa: BLE001
            log(f"  live page fail {slug}: {exc}")
            title = slug
            body = render_gallery_html(imgs)
        front = {
            "title": title,
            "slug": slug,
            "author": "Martin Ivarsson",
            "kind": "gallery" if imgs and slug != "om-mig" else "page",
            "legacy_url": f"/{slug}/",
        }
        if imgs:
            front["gallery"] = [p for p in (download_file(u) for u in imgs) if p]
        write_md(CONTENT_PAGES / f"{slug}.md", front, body)
        log(f"  extra page {slug}")

    # Download any remaining gallery originals
    log("Downloading remaining gallery originals")
    all_gallery = [u for urls in gallery_map.values() for u in urls]
    for i, url in enumerate(all_gallery, 1):
        download_file(url)
        if i % 20 == 0:
            log(f"  gallery files {i}/{len(all_gallery)}")

    manifest = {
        "exported_at": datetime.now().isoformat(),
        "source": BASE,
        "posts": len(posts),
        "pages": len(pages),
        "comments": len(comments),
        "media_library": len(media),
        "downloaded_files": len(DOWNLOADED),
        "galleries": {k: len(v) for k, v in gallery_map.items()},
        "post_slugs": sorted(p["slug"] for p in posts),
        "page_slugs": sorted(p["slug"] for p in pages),
        "comment_ids": [c["id"] for c in comments],
    }
    (EXPORT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log("DONE")
    log(json.dumps({k: manifest[k] for k in ("posts", "pages", "comments", "media_library", "downloaded_files", "galleries")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
