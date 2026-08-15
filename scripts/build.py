#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import mistune

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CONTENT_ROOT = ROOT / "content"
DOCS_ROOT = CONTENT_ROOT / "documents"
GUIDES_ROOT = CONTENT_ROOT / "guides"
MEDIA_ROOT = CONTENT_ROOT / "media"
SITE = ROOT / "site"
SITE_TITLE = "Technocratic State of Arx"

SITE_CONFIG: dict = {}
GUIDES: list[dict] = []
MEDIA: list[dict] = []

TYPE_PRESETS = [
    ("constitution", "Constitution", ["Constitution"], "The foundational law of Arx."),
    ("laws", "Laws", ["Law"], "Enacted laws and generally applicable legal rules."),
    ("policies", "Policies & Procedures", ["Policy", "Procedure", "Guideline"], "Policies, procedures and administrative standards."),
    ("rulings", "Justice Rulings", ["Justice Ruling"], "Published rulings and formal interpretations."),
    ("treaties", "Treaties & Agreements", ["Treaty", "Agreement"], "Treaties, diplomatic instruments and public agreements."),
]
ARCHIVE_STATUSES = ["Legacy / Under Review", "Superseded", "Repealed", "Historical"]
STATUS_LABELS = {
    "current": "Current",
    "legacy / under review": "Legacy / Under Review",
    "superseded": "Superseded",
    "repealed": "Repealed",
    "draft": "Draft",
    "historical": "Historical",
}

ICONS = {
    "constitution": '<svg viewBox="0 0 24 24"><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Z"/><path d="M8 4v13a3 3 0 0 0 3 3"/><path d="M9 8h6M9 11h6"/></svg>',
    "laws": '<svg viewBox="0 0 24 24"><path d="m14 6 4 4M8 12l6-6 4 4-6 6M5 19l4-4M3 21l3-3M13 18h8"/></svg>',
    "policies": '<svg viewBox="0 0 24 24"><path d="M4 6h6l2 2h8v11H4z"/><path d="M4 6V4h6l2 2"/></svg>',
    "rulings": '<svg viewBox="0 0 24 24"><path d="M12 4v14M7 6h10M6 6l-3 6h6L6 6Zm12 0-3 6h6l-3-6Z"/><path d="M8 20h8"/></svg>',
    "treaties": '<svg viewBox="0 0 24 24"><path d="m8 12 3 3a2 2 0 0 0 3 0l4-4M3 9l4-4 5 3M21 9l-4-4-5 3"/><path d="m5 11 4 4m10-4-4 4M9 15l2 2m4-2-2 2"/></svg>',
    "archive": '<svg viewBox="0 0 24 24"><path d="M4 7h16v13H4zM3 4h18v3H3z"/><path d="M9 11h6"/></svg>',
    "doc": '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 16h6"/></svg>',
    "search": '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>',
    "download": '<svg viewBox="0 0 24 24"><path d="M12 3v12m-4-4 4 4 4-4M5 19h14"/></svg>',
    "book": '<svg viewBox="0 0 24 24"><path d="M3 5a5 5 0 0 1 5-2l4 2v16l-4-2a5 5 0 0 0-5 2V5Zm18 0a5 5 0 0 0-5-2l-4 2v16l4-2a5 5 0 0 1 5 2V5Z"/></svg>',
    "people": '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-4 2-7 6-7s6 3 6 7"/><circle cx="17" cy="9" r="2"/><path d="M16 14c3 0 5 2 5 5"/></svg>',
    "guide": '<svg viewBox="0 0 24 24"><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Z"/><path d="M8 4v13a3 3 0 0 0 3 3"/><path d="m10 9 2 2 4-4"/></svg>',
    "image": '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m4 18 5-5 3 3 2-2 6 4"/></svg>',
    "map": '<svg viewBox="0 0 24 24"><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z"/><path d="M9 3v15M15 6v15"/></svg>',
    "arrow": '<svg viewBox="0 0 24 24"><path d="M5 12h14M14 7l5 5-5 5"/></svg>',
    "external": '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9"/><path d="M18 13v6H5V6h6"/></svg>',
}

MD = mistune.create_markdown(escape=False, plugins=["table"])


def esc(v):
    return html.escape(str(v or ""), quote=True)


def date_label(v):
    if not v:
        return ""
    try:
        dt = datetime.strptime(v, "%Y-%m-%d")
        return f"{dt.day} {dt.strftime('%b %Y')}"
    except Exception:
        return str(v)


def slugify(value: str) -> str:
    value = value.strip().lower().replace(".", "-")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def status_key(v):
    return (v or "").strip().lower()


def status_label(v):
    return STATUS_LABELS.get(status_key(v), str(v or "Record"))


def status_class(v):
    s = status_key(v)
    return {
        "current": "current",
        "legacy / under review": "legacy",
        "superseded": "superseded",
        "repealed": "repealed",
        "draft": "draft",
        "historical": "historical",
    }.get(s, "record")


def icon(key):
    return ICONS.get(key, ICONS["doc"])


def load_site_config():
    p = CONTENT_ROOT / "site.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def extract_pdf_text(path: Path | None):
    if not path or not path.exists():
        return ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        try:
            out = subprocess.check_output(["pdftotext", str(path), "-"], stderr=subprocess.DEVNULL, timeout=60)
            return out.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def load_docs():
    docs = []
    if not DOCS_ROOT.exists():
        return docs
    for folder in sorted(DOCS_ROOT.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        meta = folder / "meta.json"
        if not meta.exists():
            continue
        d = json.loads(meta.read_text(encoding="utf-8"))
        if not d.get("id") or not d.get("title"):
            continue
        d["_folder"] = folder
        d["_folder_name"] = folder.name
        d["type"] = d.get("type") or "Document"
        d["status"] = d.get("status") or "Historical"
        d["slug"] = d.get("slug") or slugify(d["id"])
        d["url"] = f"justice/documents/{d['slug']}/"
        pdf = d.get("pdf") or ""
        d["_pdf_path"] = folder / pdf if pdf else None
        d["_search_text"] = extract_pdf_text(d["_pdf_path"]) if d["_pdf_path"] else ""
        docs.append(d)
    return docs


def parse_frontmatter(text: str):
    meta = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            head = text[4:end]
            body = text[end + 5 :]
            for line in head.splitlines():
                if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, body.strip()


def strip_html(s: str):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def load_guides():
    guides = []
    if not GUIDES_ROOT.exists():
        return guides
    for path in sorted(GUIDES_ROOT.glob("*.md")):
        if path.name.startswith("_"):
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta.get("title"):
            continue
        slug = meta.get("slug") or slugify(path.stem)
        rendered = MD(body)
        guides.append({
            **meta,
            "slug": slug,
            "category": meta.get("category") or "Guides",
            "order": int(meta.get("order") or 999),
            "body": body,
            "html": rendered,
            "text": strip_html(rendered),
            "url": f"guides/{slug}/",
            "_path": path,
        })
    guides.sort(key=lambda g: (g["order"], g["title"].lower()))
    return guides


def load_media():
    items = []
    supported = {
        "photo": {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"},
        "video": {".mp4", ".webm", ".mov", ".m4v"},
    }
    for kind, folder_name in [("photo", "photos"), ("video", "videos")]:
        folder = MEDIA_ROOT / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() not in supported[kind]:
                continue
            sidecar = path.with_suffix(".json")
            meta = {}
            if sidecar.exists():
                try:
                    meta = json.loads(sidecar.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
            title = meta.get("title") or path.stem.replace("-", " ").replace("_", " ").title()
            items.append({
                "kind": kind,
                "folder": folder_name,
                "filename": path.name,
                "title": title,
                "caption": meta.get("caption") or "",
                "date": meta.get("date") or "",
                "order": int(meta.get("order") or 999),
                "slug": slugify(path.stem),
                "_path": path,
            })
    items.sort(key=lambda m: (m["order"], m.get("date") or "9999", m["title"].lower()))
    return items


def copy_source(docs, media):
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(SRC / "assets", SITE / "assets")

    out = SITE / "documents"
    out.mkdir()
    for d in docs:
        folder = d["_folder"]
        dest = out / folder.name
        shutil.copytree(folder, dest)
        for p in list(dest.rglob("*")):
            if p.is_file() and (p.name == "meta.json" or p.suffix.lower() == ".docx"):
                p.unlink()

    for item in media:
        dest = SITE / "media" / item["folder"]
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item["_path"], dest / item["filename"])


def base_for(rel_path):
    return "../" * (len(Path(rel_path).parts) - 1)


def group_guides():
    grouped: dict[str, list[dict]] = {}
    for g in GUIDES:
        grouped.setdefault(g["category"], []).append(g)
    return grouped


def nav_dropdown_about(base, active):
    civmap = SITE_CONFIG.get("civmap_url", "#")
    cls = " active" if active == "about" else ""
    return f'''<div class="nav-drop" data-nav-drop>
<button class="nav-drop-button{cls}" type="button" aria-expanded="false" data-nav-drop-button>ABOUT ARX</button>
<div class="nav-drop-menu about-menu" data-nav-drop-menu>
<a href="{base}about/index.html"><strong>Overview</strong><span>What Arx is and how the nation is organised.</span></a>
<a href="{base}about/media/index.html"><strong>Media</strong><span>Photos, videos and promotional material.</span></a>
<a class="external-link" href="{esc(civmap)}" target="_blank" rel="noopener"><strong>CivMap {icon('external')}</strong><span>Open Arx on the live CivMC map.</span></a>
</div></div>'''


def nav_dropdown_guides(base, active):
    grouped = group_guides()
    cls = " active" if active == "guides" else ""
    preferred = ["Start Here", "Core Mechanics", "Economy & Industry", "Transport", "Arx"]
    cats = [c for c in preferred if c in grouped] + [c for c in grouped if c not in preferred]
    columns = []
    for category in cats:
        links = "".join(f'<a href="{base}guides/{esc(g["slug"])}/index.html">{esc(g["title"])}</a>' for g in grouped[category])
        columns.append(f'<div class="mega-column"><div class="mega-heading">{esc(category)}</div>{links}</div>')
    return f'''<div class="nav-drop guides-drop" data-nav-drop>
<button class="nav-drop-button{cls}" type="button" aria-expanded="false" data-nav-drop-button>GUIDES</button>
<div class="nav-drop-menu mega-menu" data-nav-drop-menu><div class="mega-top"><a href="{base}guides/index.html"><strong>Guides Home</strong><span>Browse the full newcomer guide and mechanic library.</span></a></div><div class="mega-grid">{''.join(columns)}</div></div></div>'''


def page_header(base, active=""):
    home_cls = " active" if active == "home" else ""
    justice_cls = " active" if active == "justice" else ""
    join_cls = " active" if active == "join" else ""
    discord = SITE_CONFIG.get("discord_url", "#")
    return f'''<header class="site-header"><div class="site-header-inner">
<a class="brand" href="{base}index.html"><span class="brand-ribbon"><img src="{base}assets/images/arx-flag.webp" alt="Flag of Arx"></span><span class="brand-text"><strong>ARX</strong><span>TECHNOCRATIC STATE</span></span></a>
<button class="mobile-toggle" aria-label="Toggle navigation" aria-expanded="false" data-mobile-toggle>☰</button>
<nav class="main-nav" aria-label="Primary navigation" data-main-nav>
<a class="nav-link{home_cls}" href="{base}index.html">HOME</a>
{nav_dropdown_about(base, active)}
{nav_dropdown_guides(base, active)}
<a class="nav-link{justice_cls}" href="{base}justice/index.html">JUSTICE ARCHIVE</a>
</nav>
<div class="header-actions" data-header-actions>
<div class="header-search"><div class="search-shell"><input data-global-search type="search" placeholder="Search Arx…" aria-label="Search the Arx website"><button type="button" aria-label="Search" data-search-submit>{icon('search')}</button></div><div class="search-results" data-search-results></div></div>
<a class="join-cta{join_cls}" href="{base}join/index.html">JOIN US</a>
</div>
</div></header>'''


def page_footer(base, section=""):
    if section == "justice":
        return f'''<footer class="site-footer"><div class="site-footer-inner"><img class="footer-mark" src="{base}assets/images/justice-shield.png" alt=""><strong>The Arxian Justice Archive</strong><span class="footer-sep">•</span><a href="{base}index.html">Technocratic State of Arx</a></div></footer>'''
    return f'''<footer class="site-footer"><div class="site-footer-inner general-footer"><img class="footer-mark arx-footer-mark" src="{base}assets/images/arx-flag.webp" alt=""><strong>Technocratic State of Arx</strong><span class="footer-spacer"></span><a href="{base}about/index.html">About</a><a href="{base}guides/index.html">Guides</a><a href="{base}justice/index.html">Justice Archive</a></div></footer>'''


def shell(title, rel_path, content, active=""):
    base = base_for(rel_path)
    section = "justice" if active == "justice" else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Official website of the Technocratic State of Arx"><title>{esc(title)} | Arx</title><link rel="icon" href="{base}assets/images/arx-flag.webp"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500;600;700&family=Roboto:wght@300;400;500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="{base}assets/css/site.css"><style>:root{{--crest-url:url('{base}assets/images/arx-state-crest.webp')}}</style></head><body data-base="{base}">{page_header(base, active)}<main class="site-main">{content}</main>{page_footer(base, section)}<script src="{base}assets/js/site.js" defer></script></body></html>'''


def breadcrumb(base, parts):
    chunks = []
    for label, url in parts:
        chunks.append(f'<a href="{base}{url}">{esc(label)}</a>' if url else esc(label))
    return '<div class="breadcrumb">' + '<span>›</span>'.join(chunks) + "</div>"


def preset_url(types=None, statuses=None):
    params = []
    for t in types or []:
        params.append(("type", t))
    for s in statuses or []:
        params.append(("status", s))
    q = urlencode(params, doseq=True)
    return "archive/index.html" + (("?" + q) if q else "")


def type_icon_key(types):
    t = (types or "").lower()
    if t == "constitution":
        return "constitution"
    if t == "law":
        return "laws"
    if t in {"policy", "procedure", "guideline"}:
        return "policies"
    if t == "justice ruling":
        return "rulings"
    if t in {"treaty", "agreement"}:
        return "treaties"
    return "archive"


def cover(d, mini=False):
    cls = "document-cover-mini" if mini else ""
    type_cls = re.sub(r"[^a-z0-9]+", "-", (d.get("type") or "document").lower()).strip("-")
    return f'''<div class="{cls}"><div class="doc-cover cover-{esc(type_cls)}"><img src="PLACEHOLDER_JUSTICE" alt=""><div class="cover-id">{esc(d['id'])}</div><div class="cover-title">{esc(d.get('short_title') or d['title'])}</div></div></div>'''


def replace_asset_placeholders(s, base):
    return s.replace("PLACEHOLDER_JUSTICE", base + "assets/images/justice-shield-cover.png")


def write(rel_path, title, content, active=""):
    path = SITE / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    base = base_for(rel_path)
    path.write_text(shell(title, rel_path, replace_asset_placeholders(content, base), active), encoding="utf-8")


def write_redirect(rel_path, target, title="Arx"):
    path = SITE / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = esc(target)
    path.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url={safe}"><title>{esc(title)} | Arx</title><script>location.replace({json.dumps(target)});</script></head><body><p><a href="{safe}">Continue</a></p></body></html>''', encoding="utf-8")


def docs_for_types(docs, types):
    return [d for d in docs if d.get("type") in types]


def find_home_hero(media):
    wanted = SITE_CONFIG.get("homepage_hero_basename", "homepage-hero")
    for item in media:
        if item["kind"] == "photo" and Path(item["filename"]).stem.lower() == str(wanted).lower():
            return f"media/{item['folder']}/{item['filename']}"
    return ""


def home_page(media):
    hero = find_home_hero(media)
    hero_style = f' style="--home-photo:url(\'{esc(hero)}\')"' if hero else ""
    discord = SITE_CONFIG.get("discord_url", "#")
    civmap = SITE_CONFIG.get("civmap_url", "#")
    return f'''<section class="home-hero{' has-photo' if hero else ''}"{hero_style}><div class="home-hero-overlay"></div><div class="container home-hero-inner"><div class="home-hero-copy"><div class="eyebrow light">Technocratic State of Arx</div><h1>Build something<br>that lasts.</h1><p>Explore Arx, learn the mechanics of CivMC, join the community, or browse the nation’s public legal archive.</p><div class="hero-actions"><a class="hero-btn primary" href="join/index.html">Join Arx {icon('arrow')}</a><a class="hero-btn ghost" href="guides/index.html">New to CivMC?</a></div></div><div class="home-hero-mark"><img src="assets/images/arx-state-crest.webp" alt="Arx state crest"></div></div></section>
<section class="home-paths"><div class="container"><div class="section-heading"><div><div class="eyebrow">Start here</div><h2>Find your way into Arx</h2></div><p>Three straightforward routes depending on what you came here to do.</p></div><div class="home-path-grid">
<a class="home-path-card join" href="join/index.html"><span class="path-icon">{icon('people')}</span><div><span class="path-kicker">Become part of Arx</span><h3>Join Us</h3><p>Meet the community, find your way to Arx and start contributing.</p></div><span class="path-arrow">{icon('arrow')}</span></a>
<a class="home-path-card guide" href="guides/index.html"><span class="path-icon">{icon('guide')}</span><div><span class="path-kicker">Learn the server</span><h3>Guides</h3><p>A newcomer-friendly route through the CivMC mechanics you actually need.</p></div><span class="path-arrow">{icon('arrow')}</span></a>
<a class="home-path-card justice" href="justice/index.html"><span class="path-icon">{icon('archive')}</span><div><span class="path-kicker">Official records</span><h3>Justice Archive</h3><p>Constitution, laws, procedures, treaties and historical records.</p></div><span class="path-arrow">{icon('arrow')}</span></a>
</div></div></section>
<section class="home-explore"><div class="container"><div class="section-heading compact"><div><div class="eyebrow">Explore</div><h2>See more of the nation</h2></div></div><div class="explore-grid"><a href="about/index.html"><span>{icon('doc')}</span><strong>About Arx</strong><small>Overview of the nation and its public institutions.</small></a><a href="about/media/index.html"><span>{icon('image')}</span><strong>Media</strong><small>Photos, videos, posters and future recruitment material.</small></a><a href="{esc(civmap)}" target="_blank" rel="noopener"><span>{icon('map')}</span><strong>CivMap {icon('external')}</strong><small>View Arx and its surroundings on the live map.</small></a></div></div></section>'''


def about_page():
    civmap = SITE_CONFIG.get("civmap_url", "#")
    return f'''<section class="general-hero about-hero"><div class="container general-hero-inner"><div><div class="eyebrow">About Arx</div><h1>A nation built around expertise and contribution.</h1><p>The Technocratic State of Arx is a player-run nation on CivMC. Its public institutions are organised around specialised departments, a constitutional framework and a strong emphasis on practical participation.</p></div><img src="../assets/images/arx-state-crest.webp" alt="Arx state crest"></div></section><div class="container about-content"><section class="about-lead"><h2>What you can find here</h2><p>This website is the public front door to Arx. It combines newcomer information, CivMC guides, media and the Arxian Justice Archive in one searchable place.</p></section><div class="about-card-grid"><a href="../join/index.html" class="about-card"><span>{icon('people')}</span><h3>Join Arx</h3><p>Learn how to enter the community and get started.</p></a><a href="../guides/index.html" class="about-card"><span>{icon('guide')}</span><h3>Learn CivMC</h3><p>Use the guided mechanic library instead of learning everything at once.</p></a><a href="../justice/index.html" class="about-card"><span>{icon('archive')}</span><h3>Justice Archive</h3><p>Browse the current Constitution and public government records.</p></a><a href="media/index.html" class="about-card"><span>{icon('image')}</span><h3>Media</h3><p>See Arx through photos, videos and promotional material.</p></a><a href="{esc(civmap)}" target="_blank" rel="noopener" class="about-card"><span>{icon('map')}</span><h3>CivMap {icon('external')}</h3><p>Open the nation-specific view on CivMap.</p></a></div></div>'''


def media_page(media):
    if media:
        cards = []
        for item in media:
            src = f"../../media/{item['folder']}/{item['filename']}"
            media_html = f'<img loading="lazy" src="{src}" alt="{esc(item["title"])}">' if item["kind"] == "photo" else f'<video controls preload="metadata"><source src="{src}"></video>'
            caption = f'<p>{esc(item["caption"])}</p>' if item.get("caption") else ""
            cards.append(f'''<article class="media-card" id="media-{esc(item['slug'])}"><div class="media-frame">{media_html}</div><div class="media-caption"><span>{esc(item['kind'].upper())}</span><h3>{esc(item['title'])}</h3>{caption}</div></article>''')
        body = f'<div class="media-grid">{"".join(cards)}</div>'
    else:
        body = '''<div class="media-empty"><div class="media-placeholder-grid"><div class="media-placeholder">PHOTO</div><div class="media-placeholder wide">ARX MEDIA</div><div class="media-placeholder">VIDEO</div><div class="media-placeholder">PHOTO</div></div><h2>Media collection being prepared</h2><p>Photos and videos added to the project media folders will appear here automatically on the next site build.</p></div>'''
    return f'''<div class="container">{breadcrumb('../../',[('Home','index.html'),('About Arx','about/index.html'),('Media',None)])}<section class="page-title-block"><div class="eyebrow">About Arx</div><h1>Media</h1><p>Photos, videos and promotional material from around Arx.</p></section>{body}</div>'''


def join_page():
    discord = SITE_CONFIG.get("discord_url", "#")
    return f'''<section class="join-hero"><div class="container join-hero-inner"><div><div class="eyebrow light">Join Arx</div><h1>Your first step is simply saying hello.</h1><p>You do not need to understand every CivMC mechanic before joining. Enter the Arx Discord, introduce yourself and the community can help you get oriented.</p><div class="hero-actions"><a class="hero-btn primary bright" href="{esc(discord)}" target="_blank" rel="noopener">Join the Arx Discord {icon('external')}</a><a class="hero-btn ghost" href="../guides/getting-started/index.html">Read the beginner guide</a></div></div><img src="../assets/images/arx-state-crest.webp" alt="Arx state crest"></div></section><div class="container join-content"><div class="join-steps"><article><span>01</span><h2>Join the Discord</h2><p>Use the invitation above and follow the current recruitment instructions there.</p></article><article><span>02</span><h2>Get oriented</h2><p>Ask for help reaching Arx, learn where you can settle and meet the people currently active.</p></article><article><span>03</span><h2>Learn the essentials</h2><p>NameLayer, Citadel and a handful of other plugins are enough to get started. The Guides section walks through them in order.</p></article><article><span>04</span><h2>Find something to do</h2><p>Build, trade, research, create media, help with infrastructure or contribute through one of Arx’s public projects and departments.</p></article></div><section class="join-bottom"><div><div class="eyebrow">Not sure yet?</div><h2>Explore before you commit.</h2><p>Read about Arx, browse the media collection or see where the nation sits on CivMap.</p></div><div class="join-bottom-links"><a href="../about/index.html">About Arx →</a><a href="../about/media/index.html">Media →</a></div></section></div>'''


def guide_card(g):
    return f'''<a class="guide-card" href="{esc(g['slug'])}/index.html"><span class="guide-card-index">{str(g['order']).zfill(2)}</span><div><span class="guide-card-category">{esc(g['category'])}</span><h3>{esc(g['title'])}</h3><p>{esc(g.get('description') or '')}</p></div><span class="guide-card-arrow">{icon('arrow')}</span></a>'''


def guides_index(guides):
    grouped = group_guides()
    preferred = ["Start Here", "Core Mechanics", "Economy & Industry", "Transport", "Arx"]
    cats = [c for c in preferred if c in grouped] + [c for c in grouped if c not in preferred]
    sections = []
    for category in cats:
        cards = "".join(guide_card(g) for g in grouped[category])
        sections.append(f'''<section class="guide-category"><div class="guide-category-head"><h2>{esc(category)}</h2><span>{len(grouped[category])} guide{'s' if len(grouped[category]) != 1 else ''}</span></div><div class="guide-card-grid">{cards}</div></section>''')
    return f'''<section class="guides-hero"><div class="container guides-hero-inner"><div><div class="eyebrow light">Arx Guides</div><h1>Learn CivMC without reading everything at once.</h1><p>A curated route through the mechanics most useful to a new resident, with direct links back to the official CivMC Wiki for the full reference.</p><a class="hero-btn primary bright" href="getting-started/index.html">Start the guide {icon('arrow')}</a></div><div class="guide-route"><span>1</span><b>Start</b><i></i><span>2</span><b>Protect</b><i></i><span>3</span><b>Build</b><i></i><span>4</span><b>Trade</b></div></div></section><div class="container guide-library"><div class="guide-library-intro"><div><div class="eyebrow">Guide library</div><h2>Browse by mechanic</h2></div><p>These pages are intentionally shorter than the server wiki. Use them for orientation, then follow the official source link when you need exact or advanced details.</p></div>{''.join(sections)}</div>'''


def guide_sidebar(current):
    grouped = group_guides()
    preferred = ["Start Here", "Core Mechanics", "Economy & Industry", "Transport", "Arx"]
    cats = [c for c in preferred if c in grouped] + [c for c in grouped if c not in preferred]
    blocks = ['<a class="guide-home-link" href="../index.html">← Guides Home</a>']
    for category in cats:
        links = "".join(f'<a class="{("current" if g["slug"] == current["slug"] else "")}" href="../{esc(g["slug"])}/index.html">{esc(g["title"])}</a>' for g in grouped[category])
        blocks.append(f'<div class="guide-side-group"><strong>{esc(category)}</strong>{links}</div>')
    return "".join(blocks)


def guide_page(g, guides):
    idx = next(i for i, item in enumerate(guides) if item["slug"] == g["slug"])
    prev_g = guides[idx - 1] if idx > 0 else None
    next_g = guides[idx + 1] if idx + 1 < len(guides) else None
    source = ""
    if g.get("source_url"):
        source = f'''<div class="guide-source"><span>Source</span><a href="{esc(g['source_url'])}" target="_blank" rel="noopener">{esc(g.get('source_label') or 'Official source')} {icon('external')}</a>{f'<small>Reviewed {esc(date_label(g.get("reviewed")))}</small>' if g.get('reviewed') else ''}</div>'''
    nav_parts = []
    if prev_g:
        nav_parts.append(f'<a class="prev" href="../{esc(prev_g["slug"])}/index.html"><span>Previous</span><strong>← {esc(prev_g["title"])}</strong></a>')
    else:
        nav_parts.append('<span></span>')
    if next_g:
        nav_parts.append(f'<a class="next" href="../{esc(next_g["slug"])}/index.html"><span>Next</span><strong>{esc(next_g["title"])} →</strong></a>')
    return f'''<div class="container">{breadcrumb('../../',[('Home','index.html'),('Guides','guides/index.html'),(g['title'],None)])}<div class="guide-layout"><aside class="guide-sidebar" data-guide-sidebar>{guide_sidebar(g)}</aside><article class="guide-article"><header><span class="guide-badge">{esc(g['category'])}</span><h1>{esc(g['title'])}</h1><p>{esc(g.get('description') or '')}</p>{source}</header><div class="guide-prose">{g['html']}</div><nav class="guide-progress">{''.join(nav_parts)}</nav></article></div></div>'''


def archive_home(docs):
    cards = []
    for key, name, types, _desc in TYPE_PRESETS:
        count = len(docs_for_types(docs, types))
        cards.append(f'''<a class="category-card" href="{esc(preset_url(types=types))}"><div class="category-top"><span class="icon-round">{icon(key)}</span><h3>{esc(name)}</h3></div><div class="category-meta"><span>{count} {'Document' if count == 1 else 'Documents'}</span><span class="arrow-circle">→</span></div></a>''')
    archive_count = sum(1 for d in docs if status_label(d.get("status")) in ARCHIVE_STATUSES)
    cards.append(f'''<a class="category-card" href="{esc(preset_url(statuses=ARCHIVE_STATUSES))}"><div class="category-top"><span class="icon-round">{icon('archive')}</span><h3>Archive</h3></div><div class="category-meta"><span>{archive_count} Records</span><span class="arrow-circle">→</span></div></a>''')
    current = next((d for d in docs if d.get("type") == "Constitution" and status_key(d.get("status")) == "current"), None)
    feature = ""
    if current:
        date = current.get("ratified") or current.get("adopted") or ""
        date_line = f'<div class="feature-meta">Ratified: {esc(date_label(date))}</div>' if date else '<div class="feature-meta">Ratification date not recorded</div>'
        pdf_rel = f"../documents/{current['_folder_name']}/{current.get('pdf')}" if current.get("pdf") else ""
        feature = f'''<div class="feature-card">{cover(current)}<div class="feature-body"><div class="feature-main-row"><div><div class="feature-kicker">Current Constitution</div><h2 class="feature-title">{esc(current['id'])}</h2><p class="feature-subtitle">{esc(current.get('short_title') or current['title'])}</p>{date_line}</div><div class="status-box"><strong>● CURRENT / ACTIVE</strong><span>Official current archive record</span></div></div><hr class="feature-divider"><div class="action-row"><a class="action-btn primary" href="documents/{current['slug']}/index.html">{ICONS['book']}<span>Read Document</span></a>{f'<a class="action-btn blue" href="{pdf_rel}" target="_blank" rel="noopener">{ICONS["search"]}<span>Open Fullscreen</span></a>' if pdf_rel else ''}{f'<a class="action-btn green-outline" href="{pdf_rel}" download>{ICONS["download"]}<span>Download PDF</span></a>' if pdf_rel else ''}</div></div></div>'''
    recent = sorted(docs, key=lambda d: d.get("last_updated") or d.get("adopted") or d.get("archive_added") or "", reverse=True)[:5]
    rows = "".join(f'''<a class="update-item" href="documents/{d['slug']}/index.html" style="text-decoration:none"><span class="update-icon">{icon(type_icon_key(d.get('type')))}</span><span class="update-id">{esc(d['id'])}</span><span>{esc(d.get('short_title') or d['title'])}</span><span class="update-age">{esc(date_label(d.get('last_updated') or d.get('adopted') or d.get('archive_added')))}</span></a>''' for d in recent) or '<div class="search-empty">No records have been added yet.</div>'
    return f'''<div class="container"><section class="archive-hero"><div class="archive-hero-inner"><img class="justice-emblem" src="../assets/images/justice-shield.png" alt="Justice emblem"><div class="hero-rule"></div><div class="archive-title"><h1>The Arxian<br>Justice Archive</h1><p>Official legal and governmental records of Arx.</p><div class="title-flourish"><i></i></div></div></div></section><section class="category-grid">{''.join(cards)}</section><section class="archive-dashboard">{feature}<div class="updates-panel"><div class="panel-heading">Recently Updated</div>{rows}<div class="panel-more"><a href="recent-changes/index.html">View All Updates&nbsp; →</a></div></div></section></div>'''


def archive_index(docs):
    all_types = sorted({d.get("type") or "Document" for d in docs})
    all_statuses = ["Current", "Legacy / Under Review", "Superseded", "Repealed", "Draft", "Historical"]
    years = sorted({(d.get("last_updated") or d.get("adopted") or d.get("effective") or d.get("ratified") or "")[:4] for d in docs if (d.get("last_updated") or d.get("adopted") or d.get("effective") or d.get("ratified") or "")[:4].isdigit()}, reverse=True)
    type_filters = "".join(f'''<label class="filter-option"><input type="checkbox" data-type-filter value="{esc(t)}"><span>{esc(t)}</span><span class="filter-count">{sum(1 for d in docs if (d.get('type') or 'Document') == t)}</span></label>''' for t in all_types)
    status_filters = "".join(f'''<label class="filter-option"><input type="checkbox" data-status-filter value="{esc(s)}"><span class="status-dot {status_class(s)}"></span><span>{esc(s)}</span><span class="filter-count">{sum(1 for d in docs if status_label(d.get('status')) == s)}</span></label>''' for s in all_statuses if any(status_label(d.get("status")) == s for d in docs))
    year_opts = '<option value="">All years</option>' + "".join(f'<option value="{y}">{y}</option>' for y in years)
    rows = []
    for d in docs:
        date = d.get("last_updated") or d.get("adopted") or d.get("effective") or d.get("ratified") or ""
        st = status_label(d.get("status"))
        search = " ".join([d["id"], d["title"], d.get("short_title", ""), d.get("summary", ""), d.get("legacy_id", ""), d.get("legacy_code", ""), " ".join(d.get("aliases") or [])]).lower()
        rows.append(f'''<a class="doc-row" data-doc-row data-id="{esc(d['id'])}" data-title="{esc((d.get('short_title') or d['title']).lower())}" data-date="{esc(date)}" data-year="{esc(date[:4] if date else '')}" data-status="{esc(st.lower())}" data-type="{esc((d.get('type') or 'Document').lower())}" data-search="{esc(search)}" href="../documents/{d['slug']}/index.html"><span class="id">{esc(d['id'])}</span><strong>{esc(d.get('short_title') or d['title'])}</strong><span class="doc-type"><span class="type-pill">{esc(d.get('type') or 'Document')}</span></span><span class="doc-status"><span class="status-pill {status_class(st)}"><span class="status-dot {status_class(st)}"></span>{esc(st.upper())}</span></span><span class="doc-date">{esc(date_label(date) or '—')}</span><span class="row-arrow">→</span></a>''')
    return f'''<div class="container">{breadcrumb('../',[('Home','../index.html'),('Justice Archive','index.html'),('Archive',None)])}</div><section class="category-hero archive-index-hero"><div class="container"><div class="category-hero-inner"><span class="category-hero-icon">{icon('archive')}</span><div><h1>Document Archive</h1><p>Search and filter all public Justice Archive records in one place.</p></div></div></div></section><div class="container"><div class="active-filter-bar" data-active-filters></div><div class="catalogue-wrap"><aside class="filter-panel"><h3>Filters</h3><div class="local-search"><input data-local-search type="search" placeholder="Search documents…"><button type="button">⌕</button></div><div class="filter-group"><div class="filter-label">Document Type</div>{type_filters}</div><div class="filter-group"><div class="filter-label">Status</div>{status_filters}</div><div class="filter-group"><div class="filter-label">Date</div><select class="sort-select" data-year-filter>{year_opts}</select></div></aside><section class="catalogue-main"><div class="catalogue-toolbar master-toolbar"><div><strong><span data-visible-count>{len(rows)}</span> records</strong><span class="catalogue-subline">Filters can be removed at any time.</span></div><select class="sort-select compact" data-sort><option value="newest">Last Updated (Newest)</option><option value="oldest">Last Updated (Oldest)</option><option value="title">Title</option><option value="id">Document ID</option></select></div><div class="catalogue-table"><div class="catalogue-head"><span>Document ID</span><span>Title</span><span>Type</span><span>Status</span><span>Date</span><span></span></div><div data-catalogue>{''.join(rows)}</div><div class="empty-state" data-empty-state style="display:{'none' if rows else 'block'}"><strong>No records match those filters.</strong>Remove a filter or try a different search term.</div></div></section></div></div>'''


def doc_file_public(d, filename):
    return f"../../../documents/{d['_folder_name']}/{filename}" if filename else ""


def warning_for(d):
    s = status_key(d.get("status"))
    if s == "legacy / under review":
        return '<div class="document-warning legacy"><strong>Legacy document - under review.</strong><span>This instrument predates the current constitutional framework and has not yet completed review for compatibility with current law.</span></div>'
    if s == "superseded":
        return '<div class="document-warning superseded"><strong>Superseded document.</strong><span>Retained for historical reference. This is not the current governing instrument.</span></div>'
    if s == "repealed":
        return '<div class="document-warning repealed"><strong>Repealed document.</strong><span>Retained for historical reference and no longer in force.</span></div>'
    if s == "historical":
        return '<div class="document-warning historical"><strong>Historical record.</strong><span>Preserved as part of the official archive. Its present legal or diplomatic effect may require separate confirmation.</span></div>'
    if s == "draft":
        return '<div class="document-warning draft"><strong>Draft document.</strong><span>This record has not been marked as an enacted or final instrument.</span></div>'
    return ""


def relationship_links(d, docs):
    ids = {x["id"]: x for x in docs}
    blocks = []
    sets = [("Supersedes", d.get("supersedes") or []), ("Superseded By", d.get("superseded_by") or []), ("Related Documents", d.get("related_documents") or [])]
    for label, values in sets:
        links = []
        for item in values:
            target = ids.get(item)
            if target:
                links.append(f'<a class="side-link" href="../{target["slug"]}/index.html"><span><strong>{esc(target["id"])}</strong>&nbsp;&nbsp;{esc(target.get("short_title") or target["title"])}</span><span>→</span></a>')
            elif item:
                links.append(f'<div class="side-link muted"><span>{esc(item)}</span></div>')
        if links:
            blocks.append(f'<div class="side-card"><h3>{esc(label)}</h3>{"".join(links)}</div>')
    return "".join(blocks)


def document_page(d, docs):
    base = "../../../"
    pdf = doc_file_public(d, d.get("pdf")) if d.get("pdf") else ""
    crumbs = breadcrumb(base, [("Home", "index.html"), ("Justice Archive", "justice/index.html"), ("Archive", "justice/archive/index.html"), (d["id"], None)])
    metas = []
    def add(label, val, formatter=lambda x: x):
        if val:
            metas.append(f'<div class="meta-cell"><span class="meta-label">{esc(label)}</span><span class="meta-value">{esc(formatter(val))}</span></div>')
    add("Type", d.get("type")); add("Status", status_label(d.get("status"))); add("Version", d.get("version")); add("Ratified", d.get("ratified"), date_label); add("Adopted", d.get("adopted"), date_label); add("Effective", d.get("effective"), date_label); add("Last Updated", d.get("last_updated"), date_label); add("Authority", d.get("authority"))
    authors = d.get("authors") or []
    if isinstance(authors, str):
        authors = [authors]
    if authors:
        add("Author" if len(authors) == 1 else "Authors", ", ".join(authors))
    actions = ""
    if pdf:
        actions = f'''<a class="action-btn blue" href="{pdf}" target="_blank" rel="noopener" data-pdf-open>{ICONS['search']}<span>Open Fullscreen</span></a><a class="action-btn primary" href="{pdf}" download data-pdf-download>{ICONS['download']}<span>Download PDF</span></a><a class="action-btn green-outline" href="#" data-google-file="{pdf}">G&nbsp; <span>Google Viewer</span></a>'''
    current_date = d.get("last_updated") or d.get("adopted") or d.get("effective") or d.get("ratified") or ""
    versions = [f'''<button class="version-row version-select active" type="button" data-version-select data-version-file="{esc(pdf)}" data-version-label="Current" data-version-key="current"><strong>{esc(d.get('version') or 'Current archive record')}</strong><span>{esc(date_label(current_date) or 'Current')}</span></button>'''] if pdf else []
    for i, v in enumerate(d.get("versions") or []):
        file = v.get("file") or ""
        if not file:
            continue
        link = doc_file_public(d, file)
        key = v.get("key") or f"v{i+1}"
        versions.append(f'''<button class="version-row version-select" type="button" data-version-select data-version-file="{esc(link)}" data-version-label="{esc(v.get('label') or 'Previous version')}" data-version-key="{esc(key)}"><strong>{esc(v.get('label') or v.get('status') or 'Previous version')}</strong><span>{esc(date_label(v.get('date')) or v.get('status') or '')}</span></button>''')
    about = d.get("summary") or "No description has been added."
    side = f'''<aside class="viewer-side"><div class="side-card"><h3>Version History</h3>{''.join(versions) if versions else '<p>No version files have been attached.</p>'}</div><div class="side-card"><h3>About This Document</h3><p>{esc(about)}</p></div>{relationship_links(d, docs)}</aside>'''
    viewer = f'''<div class="version-viewing-note" data-version-note style="display:none"></div><iframe loading="lazy" src="{pdf}#view=FitH" title="{esc(d['title'])} PDF viewer" data-viewer-frame></iframe>''' if pdf else '<div class="empty-state"><strong>No PDF attached.</strong>Add a PDF filename in this document’s meta.json file.</div>'
    return f'''<div class="container document-page">{crumbs}{warning_for(d)}<section class="document-head">{cover(d, True)}<div class="document-info"><h1>{esc(d['id'])}</h1><p class="full-title">{esc(d['title'])}</p><span class="current-badge {status_class(d.get('status'))}">{esc(status_label(d.get('status')).upper())}</span><div class="meta-strip">{''.join(metas)}</div></div></section><div class="viewer-actions">{actions}</div><section class="viewer-grid"><div class="pdf-frame">{viewer}</div>{side}</section></div>'''


def recent_page(docs):
    recent = sorted(docs, key=lambda d: d.get("last_updated") or d.get("adopted") or d.get("archive_added") or "", reverse=True)
    items = "".join(f'<a class="side-link" href="../documents/{d["slug"]}/index.html"><span><strong>{esc(d["id"])}</strong>&nbsp;&nbsp;{esc(d.get("short_title") or d["title"])}</span><span>{esc(date_label(d.get("last_updated") or d.get("adopted") or d.get("archive_added")))}</span></a>' for d in recent)
    return f'<div class="container"><div class="simple-page">{breadcrumb("../",[("Home","../index.html"),("Justice Archive","index.html"),("Recent Changes",None)])}<h1>Recent Changes</h1><div class="side-card">{items or "No records yet."}</div></div></div>'


def search_page():
    return f'''<div class="container search-page" data-search-page>{breadcrumb('../',[('Home','index.html'),('Search',None)])}<section class="search-page-hero"><div class="eyebrow">Site Search</div><h1>Search Arx</h1><form class="search-page-form" data-search-page-form><input type="search" data-search-page-input placeholder="Search guides, pages, document IDs and document text…" aria-label="Search the Arx website"><button type="submit">{ICONS['search']}<span>Search</span></button></form></section><section class="search-page-results"><div class="search-page-summary" data-search-summary>Enter a search term to search the whole Arx website.</div><div data-search-page-results></div></section></div>'''


def not_found_page():
    return '''<section class="not-found"><div class="container"><div class="not-found-mark">404</div><div class="eyebrow">Page not found</div><h1>That page is not in the Arx archive.</h1><p>The address may have changed, or the page may not have been published yet.</p><div class="hero-actions"><a class="hero-btn primary" href="index.html">Return Home</a><a class="hero-btn dark" href="guides/index.html">Browse Guides</a><a class="hero-btn dark" href="justice/index.html">Justice Archive</a></div></div></section>'''


def build_search_index(docs, guides, media):
    index = [
        {"id": "", "title": "Technocratic State of Arx", "category": "Site", "type": "Page", "status": "", "summary": "Official public website of Arx.", "text": "Arx official website about join guides justice archive media CivMC", "url": "index.html"},
        {"id": "", "title": "About Arx", "category": "About Arx", "type": "Page", "status": "", "summary": "Overview of the Technocratic State of Arx.", "text": "Arx nation technocratic departments CivMC overview media CivMap", "url": "about/index.html"},
        {"id": "", "title": "Media", "category": "About Arx", "type": "Page", "status": "", "summary": "Photos, videos and promotional material from Arx.", "text": "Arx photos videos media screenshots recruitment", "url": "about/media/index.html"},
        {"id": "", "title": "Join Arx", "category": "Join Us", "type": "Page", "status": "", "summary": "How to join the Arx community.", "text": "join Arx Discord recruitment newcomer resident community contribute", "url": "join/index.html"},
        {"id": "", "title": "Arx Guides", "category": "Guides", "type": "Collection", "status": "", "summary": "Newcomer-friendly CivMC mechanics guides.", "text": "CivMC guide mechanics NameLayer Citadel ExilePearl JukeAlert FactoryMod", "url": "guides/index.html"},
        {"id": "", "title": "The Arxian Justice Archive", "category": "Justice Archive", "type": "Page", "status": "", "summary": "Official legal and governmental records of Arx.", "text": "constitution laws policies procedures justice rulings treaties agreements archive", "url": "justice/index.html"},
        {"id": "", "title": "Document Archive", "category": "Justice Archive", "type": "Collection", "status": "", "summary": "Search and filter all public Justice Archive records.", "text": "all documents constitution law policy procedure ruling treaty agreement legacy superseded historical", "url": "justice/archive/index.html"},
    ]
    for g in guides:
        index.append({"id": "", "title": g["title"], "category": "Guides", "type": "Guide", "status": "", "summary": g.get("description", ""), "text": g.get("text", ""), "url": g["url"]})
    for d in docs:
        txt = re.sub(r"\s+", " ", d.get("_search_text", "")).strip()
        meta = " ".join(str(d.get(k) or "") for k in ["legacy_id", "legacy_code", "authority", "department", "version"]) + " " + " ".join(d.get("aliases") or [])
        index.append({"id": d["id"], "title": d["title"], "category": "Justice Archive", "type": d.get("type", ""), "status": status_label(d.get("status")), "summary": d.get("summary", ""), "text": (meta + " " + txt)[:160000], "url": d["url"]})
    for item in media:
        index.append({"id": "", "title": item["title"], "category": "Media", "type": item["kind"].title(), "status": "", "summary": item.get("caption", ""), "text": f"{item['title']} {item.get('caption','')} media Arx {item['kind']}", "url": f"about/media/#media-{item['slug']}"})
    (SITE / "assets" / "search-index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def build():
    global SITE_CONFIG, GUIDES, MEDIA
    SITE_CONFIG = load_site_config()
    docs = load_docs()
    GUIDES = load_guides()
    MEDIA = load_media()
    copy_source(docs, MEDIA)

    write("index.html", "Home", home_page(MEDIA), "home")
    write("about/index.html", "About Arx", about_page(), "about")
    write("about/media/index.html", "Media", media_page(MEDIA), "about")
    write("join/index.html", "Join Us", join_page(), "join")
    write("guides/index.html", "Guides", guides_index(GUIDES), "guides")
    for g in GUIDES:
        write(f"guides/{g['slug']}/index.html", g["title"], guide_page(g, GUIDES), "guides")

    write("justice/index.html", "The Arxian Justice Archive", archive_home(docs), "justice")
    write("justice/archive/index.html", "Document Archive", archive_index(docs), "justice")
    category_redirects = {
        "constitution": preset_url(types=["Constitution"]).replace("archive/index.html", "../archive/index.html"),
        "laws": preset_url(types=["Law"]).replace("archive/index.html", "../archive/index.html"),
        "policies": preset_url(types=["Policy", "Procedure", "Guideline"]).replace("archive/index.html", "../archive/index.html"),
        "rulings": preset_url(types=["Justice Ruling"]).replace("archive/index.html", "../archive/index.html"),
        "treaties": preset_url(types=["Treaty", "Agreement"]).replace("archive/index.html", "../archive/index.html"),
    }
    for old, target in category_redirects.items():
        write_redirect(f"justice/{old}/index.html", target, old.title())

    for d in docs:
        write(f"justice/documents/{d['slug']}/index.html", f"{d['id']} — {d['title']}", document_page(d, docs), "justice")
        for alias in d.get("aliases") or []:
            old_slug = slugify(alias)
            if old_slug and old_slug != d["slug"]:
                write_redirect(f"justice/documents/{old_slug}/index.html", f"../{d['slug']}/index.html", d["title"])

    write("justice/recent-changes/index.html", "Recent Changes", recent_page(docs), "justice")
    write("search/index.html", "Search", search_page(), "search")
    write("404.html", "Page Not Found", not_found_page(), "")
    build_search_index(docs, GUIDES, MEDIA)
    print(f"Built {len(docs)} document(s), {len(GUIDES)} guide(s), and {len(MEDIA)} media item(s) into {SITE}")


if __name__ == "__main__":
    build()
