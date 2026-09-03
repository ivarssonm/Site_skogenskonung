#!/usr/bin/env python3
"""Probe WordPress API pagination and scrape key pages."""
import json
import re
import urllib.request

UA = {"User-Agent": "Skogenskonung-migration/1.0"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def get_json(url: str):
    return json.loads(get(url).decode("utf-8"))


def main() -> None:
    tests = {
        "per_page=2": "https://www.skogenskonung.com/wp-json/wp/v2/posts?per_page=2",
        "page=2": "https://www.skogenskonung.com/wp-json/wp/v2/posts?page=2",
        "rest_route": "https://www.skogenskonung.com/?rest_route=/wp/v2/posts&per_page=100",
        "pages page=2": "https://www.skogenskonung.com/wp-json/wp/v2/pages?page=2",
        "offset=10": "https://www.skogenskonung.com/wp-json/wp/v2/posts?offset=10",
        "slug om-mig pages": "https://www.skogenskonung.com/wp-json/wp/v2/pages?slug=om-mig",
    }
    for name, url in tests.items():
        print(f"=== {name} ===")
        try:
            data = get_json(url)
            if isinstance(data, list):
                print("count", len(data))
                for item in data[:3]:
                    print(" ", item.get("id"), item.get("slug"), item.get("title", {}).get("rendered"))
            else:
                print(str(data)[:300])
        except Exception as e:
            print("ERR", e)

    print("=== HOMEPAGE ===")
    html = get("https://www.skogenskonung.com/").decode("utf-8", "replace")
    print("len", len(html))
    title = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    print("title:", re.sub(r"\s+", " ", title.group(1)) if title else None)
    items = re.findall(
        r'class="[^"]*menu-item[^"]*"[\s\S]*?<a href="([^"]+)"[^>]*>(.*?)</a>',
        html,
    )
    print("menu items", len(items))
    for href, text in items[:50]:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            print(" ", text, "->", href)

    print("=== OM MIG ===")
    html = get("https://www.skogenskonung.com/om-mig/").decode("utf-8", "replace")
    print("len", len(html))
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    print("h1:", re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else None)
    for sel in ("entry-content", "post-content", "wp-block-post-content", "page-content", "type-page"):
        print(" ", sel, sel in html)

    print("=== FOTOALBUM ===")
    html = get("https://www.skogenskonung.com/fotoalbum/").decode("utf-8", "replace")
    print("len", len(html))
    folders = sorted(set(re.findall(r"wp-content/gallery/([^/\"?]+)", html)))
    print("gallery folders", folders)
    albums = re.findall(r'data-image-name="([^"]+)"', html)
    print("images", len(albums), "sample", albums[:5])
    ngg = re.findall(r'data-gallery-name="([^"]+)"', html)
    print("gallery names", ngg)
    links = re.findall(r'href="(https://www\.skogenskonung\.com/[^"]+)"', html)
    interesting = [
        u
        for u in dict.fromkeys(links)
        if any(
            x in u
            for x in (
                "foto",
                "jakt",
                "garden",
                "bastu",
                "atv",
                "bal",
                "pall",
                "ved",
                "travers",
                "carport",
                "isol",
            )
        )
    ]
    print("interesting links")
    for u in interesting[:40]:
        print(" ", u)


if __name__ == "__main__":
    main()
