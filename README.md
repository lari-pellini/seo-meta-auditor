# seo-meta-auditor

[![CI](https://github.com/lari-pellini/seo-meta-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/lari-pellini/seo-meta-auditor/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

A tiny, **zero-dependency** Python CLI that checks the on-page SEO basics of any HTML file or URL — the stuff that's easy to forget when you publish a landing page in a hurry.

> 🇧🇷 [Leia em português](#-português)

## What it checks

| Check | Fails / warns when… |
| --- | --- |
| `title` | missing, or outside 30–60 characters |
| `meta-description` | missing, or outside 70–160 characters |
| `h1` | no `<h1>`, or more than one |
| `heading-order` | heading levels skip (e.g. `h1` → `h4`) |
| `lang` | `<html>` has no `lang` attribute |
| `viewport` | no `<meta name="viewport">` |
| `canonical` | no `<link rel="canonical">` |
| `open-graph` | `og:title`, `og:description` or `og:image` missing |
| `img-alt` | any `<img>` without an `alt` attribute (`alt=""` is fine for decorative images) |
| `robots` | `<meta name="robots">` contains `noindex` |
| `structured-data` | JSON-LD is missing, invalid, or declares no `@type`; reports types including nested objects and `@graph` entries |
| `hreflang` | Lists language alternates and warns when `x-default` is missing or a language tag looks invalid |

The score is simple on purpose: pass = 1 point, warning = ½, fail = 0.

## Usage

```bash
python3 seo_audit.py examples/bad.html
python3 seo_audit.py https://example.com
python3 seo_audit.py https://example.com --json > report.json
```

```
SEO audit for examples/bad.html

⚠️  title             Title is short (4 chars, aim for 30-60).
❌ meta-description  Meta description is missing.
⚠️  h1                Found 2 <h1> tags; one clear main heading is easier to scan.
⚠️  heading-order     Heading levels skip: h1 -> h4 ('Promoções')
❌ lang              <html> has no lang attribute.
...
Score: 30/100
```

The command exits with code `1` when any check **fails**, so you can drop it into a CI pipeline and block a deploy that ships a page without a title or alt texts.

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

## Ideas / roadmap

- [x] Check `hreflang` alternates
- [x] Detect JSON-LD structured data (`Product`, `Article`, `FAQPage`)
- [ ] Crawl a `sitemap.xml` and audit every URL
- [ ] HTML report output

Contributions are very welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the issues labelled **good first issue**.

---

## 🇧🇷 Português

CLI em Python, **sem dependências**, que confere o básico de SEO on-page de um arquivo HTML ou URL: tamanho do título e da meta description, `h1`, ordem dos headings, `lang`, viewport, canonical, Open Graph, `alt` das imagens, `noindex`, marcação JSON-LD e links alternativos `hreflang`.

```bash
python3 seo_audit.py minha-landing.html
python3 seo_audit.py https://meusite.com.br --json
```

Retorna código de saída `1` quando algum item falha — dá para usar no CI e impedir que uma página vá ao ar sem título ou sem texto alternativo nas imagens. Contribuições são bem-vindas!

## License

MIT © Larissa Pellini
