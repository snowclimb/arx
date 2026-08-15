#!/usr/bin/env python3
from __future__ import annotations
import json, html, os, re, shutil, subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
CONTENT = ROOT / 'content' / 'documents'
SITE = ROOT / 'site'
SITE_TITLE = 'Technocratic State of Arx'

CATEGORIES = {
    'constitution': ('Constitution', 'The foundational law of Arx.'),
    'laws': ('Laws', 'Enacted laws and generally applicable legal rules.'),
    'policies': ('Policies & Procedures', 'Official policies, procedures and administrative framework documents.'),
    'rulings': ('Justice Rulings', 'Published rulings and formal interpretations.'),
    'treaties': ('Treaties & Agreements', 'Public treaties, diplomatic agreements and interstate accords.'),
    'archive': ('Archive', 'Superseded and historical records retained for reference.'),
}

ICONS = {
'constitution': '<svg viewBox="0 0 24 24"><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Z"/><path d="M8 4v13a3 3 0 0 0 3 3"/><path d="M9 8h6M9 11h6"/></svg>',
'laws': '<svg viewBox="0 0 24 24"><path d="m14 6 4 4M8 12l6-6 4 4-6 6M5 19l4-4M3 21l3-3M13 18h8"/></svg>',
'policies': '<svg viewBox="0 0 24 24"><path d="M4 6h6l2 2h8v11H4z"/><path d="M4 6V4h6l2 2"/></svg>',
'rulings': '<svg viewBox="0 0 24 24"><path d="M12 4v14M7 6h10M6 6l-3 6h6L6 6Zm12 0-3 6h6l-3-6Z"/><path d="M8 20h8"/></svg>',
'treaties': '<svg viewBox="0 0 24 24"><path d="m8 12 3 3a2 2 0 0 0 3 0l4-4M3 9l4-4 5 3M21 9l-4-4-5 3"/><path d="m5 11 4 4m10-4-4 4M9 15l2 2m4-2-2 2"/></svg>',
'archive': '<svg viewBox="0 0 24 24"><path d="M4 7h16v13H4zM3 4h18v3H3z"/><path d="M9 11h6"/></svg>',
'doc': '<svg viewBox="0 0 24 24"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 16h6"/></svg>',
'search': '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>',
'download': '<svg viewBox="0 0 24 24"><path d="M12 3v12m-4-4 4 4 4-4M5 19h14"/></svg>',
'book': '<svg viewBox="0 0 24 24"><path d="M3 5a5 5 0 0 1 5-2l4 2v16l-4-2a5 5 0 0 0-5 2V5Zm18 0a5 5 0 0 0-5-2l-4 2v16l4-2a5 5 0 0 1 5 2V5Z"/></svg>',
}

def esc(v): return html.escape(str(v or ''), quote=True)

def date_label(v):
    if not v: return ''
    try: return datetime.strptime(v, '%Y-%m-%d').strftime('%-d %b %Y')
    except Exception: return str(v)

def relative_age(v):
    # Static, deterministic wording; avoids stale 'x days ago' labels on a long-lived archive.
    return date_label(v)

def status_class(v):
    s = (v or '').strip().lower()
    if s == 'current': return 'current'
    if s == 'superseded': return 'superseded'
    if s == 'draft': return 'draft'
    return ''

def extract_pdf_text(path: Path):
    if not path.exists(): return ''
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return '\n'.join((p.extract_text() or '') for p in reader.pages)
    except Exception:
        try:
            out = subprocess.check_output(['pdftotext', str(path), '-'], stderr=subprocess.DEVNULL, timeout=60)
            return out.decode('utf-8', errors='ignore')
        except Exception:
            return ''

def load_docs():
    docs=[]
    for folder in sorted(CONTENT.iterdir()):
        if not folder.is_dir() or folder.name.startswith('_'): continue
        meta = folder / 'meta.json'
        if not meta.exists(): continue
        d=json.loads(meta.read_text(encoding='utf-8'))
        d['_folder']=folder
        d['category']=d.get('category','archive').lower()
        if d['category'] not in CATEGORIES: d['category']='archive'
        d['url']=f"justice/documents/{d['id'].lower()}/"
        pdf=d.get('pdf') or ''
        d['_pdf_path']=folder/pdf if pdf else None
        d['_search_text']=extract_pdf_text(d['_pdf_path']) if d['_pdf_path'] else ''
        docs.append(d)
    return docs

def copy_source():
    if SITE.exists(): shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(SRC/'assets', SITE/'assets')
    # Public document files get a stable path by document ID.
    out = SITE/'documents'; out.mkdir()
    for folder in CONTENT.iterdir():
        if not folder.is_dir() or folder.name.startswith('_'): continue
        dest=out/folder.name
        shutil.copytree(folder,dest)
        meta=dest/'meta.json'
        if meta.exists(): meta.unlink()  # metadata is rendered into pages; no need to publish internal file.

def base_for(rel_path):
    depth = len(Path(rel_path).parts)-1  # file path depth below site root
    return '../' * depth

def page_header(base, active=''):
    def n(url): return base + url
    active_home=' active' if active=='home' else ''
    active_browse=' active' if active=='browse' else ''
    return f'''<header class="site-header"><div class="site-header-inner">
<a class="brand" href="{n('index.html')}"><span class="brand-ribbon"><img src="{n('assets/images/arx-flag.webp')}" alt="Flag of Arx"></span><span class="brand-text"><strong>ARX STATE</strong><span>OFFICIAL ARCHIVES</span></span></a>
<button class="mobile-toggle" aria-label="Toggle navigation" data-mobile-toggle>☰</button>
<nav class="main-nav" aria-label="Primary navigation">
<a class="nav-link{active_home}" href="{n('index.html')}">⌂&nbsp; HOME</a>
<div class="nav-drop"><button class="nav-drop-button{active_browse}">BROWSE</button><div class="nav-drop-menu">
<a href="{n('justice/index.html')}">The Arxian Justice Archive</a>
<a href="{n('justice/constitution/index.html')}">Constitution</a><a href="{n('justice/laws/index.html')}">Laws</a><a href="{n('justice/policies/index.html')}">Policies &amp; Procedures</a><a href="{n('justice/rulings/index.html')}">Justice Rulings</a><a href="{n('justice/treaties/index.html')}">Treaties &amp; Agreements</a><a href="{n('justice/archive/index.html')}">Archive</a>
</div></div>
<a class="nav-link" href="{n('collections/index.html')}">COLLECTIONS</a>
<a class="nav-link" href="{n('about/index.html')}">ABOUT</a>
<a class="nav-link" href="{n('help/index.html')}">HELP</a>
<a class="nav-link" href="{n('contact/index.html')}">CONTACT</a>
</nav>
<div class="header-search"><div class="search-shell"><input data-global-search type="search" placeholder="Search the Archive…" aria-label="Search the Archive"><button aria-label="Search">⌕</button></div><div class="search-results" data-search-results></div></div>
</div></header>'''

def page_footer(base):
    return f'''<footer class="site-footer"><div class="site-footer-inner"><img class="footer-mark" src="{base}assets/images/justice-shield.png" alt=""><strong>The Arxian Justice Archive</strong><span class="footer-sep">•</span><span>Technocratic State of Arx</span></div></footer>'''

def shell(title, rel_path, content, active=''):
    base=base_for(rel_path)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Official archive of the Technocratic State of Arx"><title>{esc(title)} | Arx</title><link rel="icon" href="{base}assets/images/arx-flag.webp"><link rel="stylesheet" href="{base}assets/css/site.css"><style>:root{{--crest-url:url('{base}assets/images/arx-state-crest.png')}}</style></head><body data-base="{base}">{page_header(base,active)}<main class="site-main">{content}</main>{page_footer(base)}<script src="{base}assets/js/site.js"></script></body></html>'''

def breadcrumb(base, parts):
    chunks=[]
    for label,url in parts:
        if url: chunks.append(f'<a href="{base}{url}">{esc(label)}</a>')
        else: chunks.append(esc(label))
    return '<div class="breadcrumb">' + '<span>›</span>'.join(chunks) + '</div>'

def icon(category): return ICONS.get(category, ICONS['doc'])

def cover(d, mini=False):
    cls='document-cover-mini' if mini else ''
    return f'''<div class="{cls}"><div class="doc-cover"><img src="PLACEHOLDER_JUSTICE" alt=""><div class="cover-id">{esc(d['id'])}</div><div class="cover-title">{esc(d.get('short_title') or d['title'])}</div></div></div>'''

def replace_asset_placeholders(s, base):
    return s.replace('PLACEHOLDER_JUSTICE', base+'assets/images/justice-shield.png')

def write(rel_path, title, content, active=''):
    path=SITE/rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    base=base_for(rel_path)
    content=replace_asset_placeholders(content, base)
    path.write_text(shell(title,rel_path,content,active),encoding='utf-8')

def category_counts(docs):
    return {k: sum(1 for d in docs if d['category']==k) for k in CATEGORIES}

def status_for_feature(d):
    if (d.get('status') or '').lower()=='current': return 'CURRENT / ACTIVE'
    return (d.get('status') or 'Record').upper()

def archive_home(docs):
    counts=category_counts(docs)
    base='../'
    cards=''.join(f'''<a class="category-card" href="{cat}/index.html"><div class="category-top"><span class="icon-round">{icon(cat)}</span><h3>{esc(CATEGORIES[cat][0])}</h3></div><div class="category-meta"><span>{counts[cat]} {'Document' if counts[cat]==1 else 'Documents'}</span><span class="arrow-circle">→</span></div></a>''' for cat in ['constitution','laws','policies','rulings','treaties','archive'])
    current = next((d for d in docs if d['category']=='constitution' and (d.get('status') or '').lower()=='current'), docs[0] if docs else None)
    feature=''
    if current:
        date = current.get('ratified') or current.get('adopted') or ''
        date_line = f'<div class="feature-meta">Ratified: {esc(date_label(date))}</div>' if date else '<div class="feature-meta">Ratification date not recorded</div>'
        pdf_rel=f"../documents/{current['id']}/{current.get('pdf')}" if current.get('pdf') else ''
        feature=f'''<div class="feature-card">{cover(current)}<div class="feature-body"><div class="feature-main-row"><div><div class="feature-kicker">Current Constitution</div><h2 class="feature-title">{esc(current['id'])}</h2><p class="feature-subtitle">{esc(current.get('short_title') or current['title'])}</p>{date_line}</div><div class="status-box"><strong>● {esc(status_for_feature(current))}</strong><span>Official current archive record</span></div></div><hr class="feature-divider"><div class="action-row"><a class="action-btn primary" href="documents/{current['id'].lower()}/index.html">{ICONS['book']}<span>Read Online</span></a>{f'<a class="action-btn blue" href="{pdf_rel}" target="_blank">{ICONS["download"]}<span>View PDF</span></a>' if pdf_rel else ''}{f'<a class="action-btn green-outline" href="#" data-google-file="{pdf_rel}">{ICONS["search"]}<span>Google Viewer</span></a>' if pdf_rel else ''}</div></div></div>'''
    recent=sorted(docs, key=lambda d: d.get('last_updated') or d.get('archive_added') or '', reverse=True)[:5]
    update_rows=''.join(f'''<a class="update-item" href="documents/{d['id'].lower()}/index.html" style="text-decoration:none"><span class="update-icon">{icon(d['category'])}</span><span class="update-id">{esc(d['id'])}</span><span>{esc(d.get('short_title') or d['title'])}</span><span class="update-age">{esc(relative_age(d.get('last_updated') or d.get('archive_added')))}</span></a>''' for d in recent)
    if not recent: update_rows='<div class="search-empty">No records have been added yet.</div>'
    return f'''<div class="container"><section class="archive-hero"><div class="archive-hero-inner"><img class="justice-emblem" src="../assets/images/justice-shield.png" alt="Justice emblem"><div class="hero-rule"></div><div class="archive-title"><h1>The Arxian<br>Justice Archive</h1><p>Official legal and governmental records of Arx.</p><div class="title-flourish"><i></i></div></div></div></section><section class="category-grid">{cards}</section><section class="archive-dashboard">{feature}<div class="updates-panel"><div class="panel-heading">Recently Updated</div>{update_rows}<div class="panel-more"><a href="recent-changes/index.html">View All Updates&nbsp; →</a></div></div></section></div>'''

def home_page():
    return '''<div class="container"><section class="state-home-hero"><div class="state-home-copy"><div class="eyebrow">Technocratic State of Arx</div><h1>Arx</h1><p>Official public information and records. The Arxian Justice Archive is the first active collection on the wider Arx website.</p></div></section><a class="home-entry" href="justice/index.html"><img src="assets/images/justice-shield.png" alt="Justice emblem"><div><h2>The Arxian Justice Archive</h2><p>Constitution, laws, policies, rulings, treaties and historical records.</p></div><span class="arrow-circle" style="margin-left:auto">→</span></a></div>'''

def category_page(cat, docs):
    name, desc=CATEGORIES[cat]
    relevant=[d for d in docs if d['category']==cat]
    types=sorted(set((d.get('type') or 'Document') for d in relevant))
    status_counts={s:sum(1 for d in relevant if (d.get('status') or '').lower()==s) for s in ['current','superseded','draft']}
    rows=[]
    for d in relevant:
        date=d.get('last_updated') or d.get('adopted') or d.get('archive_added') or ''
        st=(d.get('status') or '').lower()
        rows.append(f'''<a class="doc-row" data-doc-row data-id="{esc(d['id'])}" data-title="{esc((d.get('short_title') or d['title']).lower())}" data-date="{esc(date)}" data-status="{esc(st)}" data-type="{esc((d.get('type') or 'document').lower())}" data-search="{esc((d['id']+' '+d['title']+' '+d.get('summary','')).lower())}" href="../documents/{d['id'].lower()}/index.html"><span class="id">{esc(d['id'])}</span><strong>{esc(d.get('short_title') or d['title'])}</strong><span class="doc-type"><span class="type-pill">{esc(d.get('type') or 'Document')}</span></span><span class="doc-status"><span class="status-pill {status_class(d.get('status'))}"><span class="dot {'grey' if st=='superseded' else 'gold' if st=='draft' else ''}"></span>{esc((d.get('status') or 'Record').upper())}</span></span><span class="doc-date">{esc(date_label(date) or '—')}</span><span class="row-arrow">→</span></a>''')
    type_filters=''.join(f'''<label class="filter-option"><input type="checkbox" data-type-filter value="{esc(t)}">{esc(t)}<span class="filter-count">{sum(1 for d in relevant if (d.get('type') or 'Document')==t)}</span></label>''' for t in types) or '<div class="filter-option">No document types yet.</div>'
    rows_html=''.join(rows)
    content=f'''<div class="container">{breadcrumb('../',[('Home','../index.html'),(name,None)])}</div><section class="category-hero"><div class="container"><div class="category-hero-inner"><span class="category-hero-icon">{icon(cat)}</span><div><h1>{esc(name)}</h1><p>{esc(desc)}</p></div></div></div></section><div class="container"><div class="catalogue-wrap"><aside class="filter-panel"><h3>Filters</h3><div class="local-search"><input data-local-search type="search" placeholder="Search {esc(name.lower())}…"><button>⌕</button></div><div class="filter-group"><div class="filter-label">Status</div><div class="filter-option"><span class="dot"></span>Current<span class="filter-count">{status_counts['current']}</span></div><div class="filter-option"><span class="dot grey"></span>Superseded<span class="filter-count">{status_counts['superseded']}</span></div><div class="filter-option"><span class="dot gold"></span>Draft<span class="filter-count">{status_counts['draft']}</span></div></div><div class="filter-group"><div class="filter-label">Document Type</div>{type_filters}</div><div class="filter-group"><div class="filter-label">Sort By</div><select class="sort-select" data-sort><option value="newest">Last Updated (Newest)</option><option value="oldest">Last Updated (Oldest)</option><option value="title">Title</option><option value="id">Document ID</option></select></div></aside><section class="catalogue-main"><div class="catalogue-toolbar"><div class="status-tabs"><button class="status-tab active" data-status-tab="all">☷&nbsp; All</button><button class="status-tab" data-status-tab="current"><span class="dot"></span>Current</button><button class="status-tab" data-status-tab="superseded"><span class="dot grey"></span>Superseded</button><button class="status-tab" data-status-tab="draft"><span class="dot gold"></span>Draft</button></div><div class="view-switch"><button>▦</button><button class="active">☷</button></div></div><div class="catalogue-table"><div class="catalogue-head"><span>Document ID</span><span>Title</span><span>Type</span><span>Status</span><span>Last Updated</span><span></span></div><div data-catalogue>{rows_html}</div><div class="empty-state" data-empty-state style="display:{'none' if rows else 'block'}"><strong>No records in this collection yet.</strong>Documents added to this category will appear here automatically.</div><div class="catalogue-foot"><span>Showing <b data-visible-count>{len(rows)}</b> of {len(rows)} documents</span><span></span></div></div></section></div></div>'''
    return content

def doc_file_public(d, filename):
    return f"../../../documents/{d['id']}/{filename}" if filename else ''

def document_page(d, docs):
    base='../../../'
    pdf=doc_file_public(d,d.get('pdf')) if d.get('pdf') else ''
    docx=doc_file_public(d,d.get('docx')) if d.get('docx') else ''
    crumbs=breadcrumb(base,[('Home','index.html'),('Justice Archive','justice/index.html'),(CATEGORIES[d['category']][0],f"justice/{d['category']}/index.html"),(d['id'],None)])
    metas=[]
    def add(label,val,formatter=lambda x:x):
        if val: metas.append(f'<div class="meta-cell"><span class="meta-label">{esc(label)}</span><span class="meta-value">{esc(formatter(val))}</span></div>')
    add('Type',d.get('type'))
    add('Status',d.get('status'))
    add('Version',d.get('version'))
    add('Ratified',d.get('ratified'),date_label)
    add('Adopted',d.get('adopted'),date_label)
    add('Effective',d.get('effective'),date_label)
    add('Last Updated',d.get('last_updated'),date_label)
    actions=[]
    if pdf:
        actions.append(f'<a class="action-btn" href="#" data-google-file="{pdf}">G&nbsp; Google Viewer</a>')
    if docx:
        actions.append(f'<a class="action-btn" href="#" data-office-file="{docx}">▣&nbsp; Office Viewer</a>')
    if pdf:
        actions.append(f'<a class="action-btn primary" href="{pdf}" download>{ICONS["download"]}<span>Download PDF</span></a>')
    if docx:
        actions.append(f'<a class="action-btn blue" href="{docx}" download><span>Download DOCX</span></a>')
    # Current record plus explicitly supplied historical files.
    current_date=d.get('last_updated') or d.get('archive_added') or ''
    version_rows=[f'<div class="version-row"><strong>{esc(d.get("version") or "Current archive record")}</strong><span>{esc(("Added " + date_label(current_date)) if current_date and not d.get("last_updated") else (date_label(current_date) or "Current"))}</span></div>']
    for v in d.get('versions') or []:
        file=v.get('file') or ''
        link=doc_file_public(d,file) if file else '#'
        version_rows.append(f'<a class="version-row" href="{link}" target="_blank" style="text-decoration:none"><strong>{esc(v.get("label") or v.get("status") or "Previous version")}</strong><span>{esc(date_label(v.get("date")))}</span></a>')
    related=[]
    ids={x['id']:x for x in docs}
    for rid in d.get('related') or []:
        r=ids.get(rid)
        if r: related.append(f'<a class="side-link" href="../{r["id"].lower()}/index.html"><span><strong>{esc(r["id"])}</strong>&nbsp;&nbsp;{esc(r.get("short_title") or r["title"])}</span><span>→</span></a>')
    side=f'''<aside class="viewer-side"><div class="side-card"><h3>Version History</h3>{''.join(version_rows)}</div><div class="side-card"><h3>About This Document</h3><p>{esc(d.get('summary') or 'No description has been added.')}</p></div>{f'<div class="side-card"><h3>Related Documents</h3>{"".join(related)}</div>' if related else ''}</aside>'''
    viewer = f'<iframe src="{pdf}#view=FitH" title="{esc(d["title"])} PDF viewer"></iframe>' if pdf else '<div class="empty-state"><strong>No PDF attached.</strong>Add a PDF filename in this document’s meta.json file.</div>'
    return f'''<div class="container document-page">{crumbs}<section class="document-head">{cover(d,True)}<div class="document-info"><h1>{esc(d['id'])}</h1><p class="full-title">{esc(d['title'])}</p><span class="current-badge">{esc((d.get('status') or 'Record').upper())}</span><div class="meta-strip">{''.join(metas)}</div></div></section><div class="viewer-actions">{''.join(actions)}</div><section class="viewer-grid"><div class="pdf-frame">{viewer}</div>{side}</section></div>'''

def recent_page(docs):
    recent=sorted(docs,key=lambda d:d.get('last_updated') or d.get('archive_added') or '',reverse=True)
    items=''.join(f'<a class="side-link" href="../documents/{d["id"].lower()}/index.html"><span><strong>{esc(d["id"])}</strong>&nbsp;&nbsp;{esc(d.get("short_title") or d["title"])}</span><span>{esc(date_label(d.get("last_updated") or d.get("archive_added")))}</span></a>' for d in recent)
    return f'<div class="container"><div class="simple-page">{breadcrumb("../",[("Home","../index.html"),("Justice Archive","index.html"),("Recent Changes",None)])}<h1>Recent Changes</h1><div class="side-card">{items or "No records yet."}</div></div></div>'

def simple_page(title, text, baseprefix=''):
    return f'<div class="container"><div class="simple-page"><h1>{esc(title)}</h1><p>{esc(text)}</p></div></div>'

def build():
    docs=load_docs()
    copy_source()
    write('index.html','Home',home_page(),'home')
    write('justice/index.html','The Arxian Justice Archive',archive_home(docs),'browse')
    for cat in CATEGORIES:
        write(f'justice/{cat}/index.html',CATEGORIES[cat][0],category_page(cat,docs),'browse')
    for d in docs:
        write(f"justice/documents/{d['id'].lower()}/index.html",f"{d['id']} — {d['title']}",document_page(d,docs),'browse')
    write('justice/recent-changes/index.html','Recent Changes',recent_page(docs),'browse')
    write('collections/index.html','Collections',simple_page('Collections','The Arxian Justice Archive is the first active public collection. Additional Arx collections can be added here later.'))
    write('about/index.html','About Arx',simple_page('About Arx','The wider Arx public website is being developed. A fuller national overview can be added here when ready.'))
    write('help/index.html','Help',simple_page('Using the Archive','Use the search field or Browse menu to locate records. Document pages provide the current formatted document and available downloads.'))
    write('contact/index.html','Contact',simple_page('Contact','For corrections or questions about archive records, contact the Department of Justice through the Arx Discord.'))
    # Search index: avoid exposing every PDF word in the page itself, but make it searchable in JS.
    index=[]
    for d in docs:
        txt=re.sub(r'\s+',' ',d.get('_search_text','')).strip()
        index.append({'id':d['id'],'title':d['title'],'category':CATEGORIES[d['category']][0],'type':d.get('type',''),'status':d.get('status',''),'summary':d.get('summary',''),'text':txt[:160000],'url':d['url']})
    (SITE/'assets'/'search-index.json').write_text(json.dumps(index,ensure_ascii=False),encoding='utf-8')
    print(f'Built {len(docs)} document(s) into {SITE}')

if __name__=='__main__': build()
