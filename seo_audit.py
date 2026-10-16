#!/usr/bin/env python3
"""seo-meta-auditor: a zero-dependency on-page SEO checker.

Usage:
    python seo_audit.py page.html
    python seo_audit.py https://example.com --json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

TITLE_RANGE = (30, 60)
DESCRIPTION_RANGE = (70, 160)
OPEN_GRAPH_TAGS = ("og:title", "og:description", "og:image")
USER_AGENT = "seo-meta-auditor/1.0 (+https://github.com/lari-pellini/seo-meta-auditor)"


@dataclass
class Check:
    id: str
    status: str  # "pass" | "warn" | "fail"
    message: str


class PageParser(HTMLParser):
    """Collects the bits of a page that matter for on-page SEO."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: Optional[str] = None
        self.title: Optional[str] = None
        self.meta: Dict[str, str] = {}
        self.robots: List[str] = []
        self.canonical: Optional[str] = None
        self.headings: List[Tuple[int, str]] = []
        self.images: List[Optional[str]] = []
        self._in_title = False
        self._title_parts: List[str] = []
        self._heading_level: Optional[int] = None
        self._heading_parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang") or None
        elif tag == "title" and self.title is None:
            self._in_title = True
            self._title_parts = []
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key == "robots":
                self.robots.extend(rule.strip().lower() for rule in a.get("content", "").split(","))
            if key and key not in self.meta:
                self.meta[key] = a.get("content", "").strip()
        elif tag == "link":
            if "canonical" in a.get("rel", "").lower().split():
                self.canonical = a.get("href") or None
        elif len(tag) == 2 and tag[0] == "h" and tag[1] in "123456":
            self._heading_level = int(tag[1])
            self._heading_parts = []
        elif tag == "img":
            self.images.append(a["alt"] if "alt" in a else None)

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.title = " ".join("".join(self._title_parts).split())
        elif self._heading_level is not None and tag == "h%d" % self._heading_level:
            text = " ".join("".join(self._heading_parts).split())
            self.headings.append((self._heading_level, text))
            self._heading_level = None

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        if self._heading_level is not None:
            self._heading_parts.append(data)


def _length_check(check_id: str, label: str, value: Optional[str], bounds: Tuple[int, int]) -> Check:
    if not value:
        return Check(check_id, "fail", "%s is missing." % label)
    low, high = bounds
    n = len(value)
    if n < low:
        return Check(check_id, "warn", "%s is short (%d chars, aim for %d-%d)." % (label, n, low, high))
    if n > high:
        return Check(check_id, "warn", "%s may be truncated in search results (%d chars, aim for %d-%d)." % (label, n, low, high))
    return Check(check_id, "pass", "%s length looks good (%d chars)." % (label, n))


def audit(html: str) -> List[Check]:
    page = PageParser()
    page.feed(html)
    page.close()
    checks: List[Check] = []

    checks.append(_length_check("title", "Title", page.title, TITLE_RANGE))
    checks.append(_length_check("meta-description", "Meta description", page.meta.get("description"), DESCRIPTION_RANGE))

    h1s = [text for level, text in page.headings if level == 1]
    if not h1s:
        checks.append(Check("h1", "fail", "No <h1> found."))
    elif len(h1s) > 1:
        checks.append(Check("h1", "warn", "Found %d <h1> tags; one clear main heading is easier to scan." % len(h1s)))
    else:
        checks.append(Check("h1", "pass", "One <h1>: %r." % h1s[0]))

    skips = []
    previous = 0
    for level, text in page.headings:
        if previous and level > previous + 1:
            skips.append("h%d -> h%d (%r)" % (previous, level, text))
        previous = level
    if skips:
        checks.append(Check("heading-order", "warn", "Heading levels skip: " + "; ".join(skips)))
    else:
        checks.append(Check("heading-order", "pass", "Heading levels are in order."))

    if page.lang:
        checks.append(Check("lang", "pass", "<html lang=%r> is set." % page.lang))
    else:
        checks.append(Check("lang", "fail", "<html> has no lang attribute."))

    if "viewport" in page.meta:
        checks.append(Check("viewport", "pass", "Meta viewport is set."))
    else:
        checks.append(Check("viewport", "fail", "Meta viewport is missing; the page may not be mobile-friendly."))

    if page.canonical:
        checks.append(Check("canonical", "pass", "Canonical URL: %s" % page.canonical))
    else:
        checks.append(Check("canonical", "warn", "No canonical link; duplicate URLs may compete with each other."))

    missing_og = [tag for tag in OPEN_GRAPH_TAGS if not page.meta.get(tag)]
    if missing_og:
        checks.append(Check("open-graph", "warn", "Missing Open Graph tags: " + ", ".join(missing_og)))
    else:
        checks.append(Check("open-graph", "pass", "Open Graph title, description and image are set."))

    no_alt = sum(1 for alt in page.images if alt is None)
    if no_alt:
        checks.append(Check("img-alt", "fail", "%d of %d images have no alt attribute." % (no_alt, len(page.images))))
    else:
        checks.append(Check("img-alt", "pass", "All %d images have an alt attribute." % len(page.images)))

    if "noindex" in page.robots or "none" in page.robots:
        checks.append(Check("robots", "warn", "Meta robots contains noindex or none; this page will not be indexed."))
    else:
        checks.append(Check("robots", "pass", "Page is indexable."))

    return checks


def score(checks: List[Check]) -> int:
    if not checks:
        return 0
    points = sum(1.0 if c.status == "pass" else 0.5 if c.status == "warn" else 0.0 for c in checks)
    return round(100 * points / len(checks))


def load(source: str) -> str:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=15) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    with open(source, encoding="utf-8", errors="replace") as f:
        return f.read()


ICONS = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the on-page SEO basics of an HTML file or URL.")
    parser.add_argument("source", help="path to an .html file or an http(s) URL")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)

    checks = audit(load(args.source))
    total = score(checks)
    if args.json:
        print(json.dumps({"source": args.source, "score": total, "checks": [asdict(c) for c in checks]}, indent=2, ensure_ascii=False))
    else:
        print("SEO audit for %s\n" % args.source)
        for c in checks:
            print("%s %-17s %s" % (ICONS[c.status], c.id, c.message))
        print("\nScore: %d/100" % total)
    return 1 if any(c.status == "fail" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
