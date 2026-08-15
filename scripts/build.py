#!/usr/bin/env python3
from __future__ import annotations
import json, html, re, shutil, subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
CONTENT = ROOT / 'content' / 'documents'
SITE = ROOT / 'site'
SITE_TITLE = 'Technocratic State of Arx'

TYPE_PRESETS = [
    ('constitution', 'Constitution', ['Constitution'], 'The foundational law of Arx.'),
    ('laws', 'Laws', ['Law'], 'Enacted laws and generally applicable legal rules.'),
    ('policies', 'Policies & Procedures', ['Policy', 'Procedure', 'Guideline'], 'Policies, procedures and administrative standards.'),
    ('rulings', 'Justice Rulings', ['Justice Ruling'], 'Published rulings and formal interpretations.'),
    ('treaties', 'Treaties & Agreements', ['Treaty', 'Agreement'], 'Treaties, diplomatic instruments and public agreements.'),
]
ARCHIVE_STATUSES = ['Legacy / Under Review', 'Superseded', 'Repealed', 'Historical']
STATUS_LABELS = {
    'current': 'Current',
    'legacy / under review': 'Legacy / Under Review',
    'superseded': 'Superseded',
    'repealed': 'Repealed',
    'draft': 'Draft',
    'historical': 'Historical',
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
    try:
        dt = datetime.strptime(v, '%Y-%m-%d')
        return f'{dt.day} {dt.strftime("%b %Y")}'
    except Exception:
        return str(v)

def status_key(v): return (v or '').strip().lower()
def status_label(v): return STATUS_LABELS.get(status_key(v), str(v or 'Record'))
def status_class(v):
    s=status_key(v)
    return {
        'current':'current', 'legacy / under review':'legacy', 'superseded':'superseded',
        'repealed':'repealed', 'draft':'draft', 'historical':'historical'
    }.get(s,'record')

def extract_pdf_text(path: Path):
    if not path or not path.exists(): return ''
    try:
        from pypdf import PdfReader
        reader=PdfReader(str(path))
        return '\n'.join((p.extract_text() or '') for p in reader.pages)
    except Exception:
        try:
            out=subprocess.check_output(['pdftotext',str(path),'-'],stderr=subprocess.DEVNULL,timeout=60)
            return out.decode('utf-8',errors='ignore')
        except Exception:
            return ''

def load_docs():
    docs=[]
    if not CONTENT.exists(): return docs
    for folder in sorted(CONTENT.iterdir()):
        if not folder.is_dir() or folder.name.startswith('_'): continue
        meta=folder/'meta.json'
        if not meta.exists(): continue
        d=json.loads(meta.read_text(encoding='utf-8'))
        if not d.get('id') or not d.get('title'): continue
        d['_folder']=folder
        d['type']=d.get('type') or 'Document'
        d['status']=d.get('status') or 'Historical'
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
    out=SITE/'documents'; out.mkdir()
    for folder in CONTENT.iterdir():
        if not folder.is_dir() or folder.name.startswith('_'): continue
        dest=out/folder.name
        shutil.copytree(folder,dest)
        for p in list(dest.rglob('*')):
            if p.is_file() and (p.name == 'meta.json' or p.suffix.lower()=='.docx'):
                p.unlink()

def base_for(rel_path):
    return '../' * (len(Path(rel_path).parts)-1)

def page_header(base, active=''):
    def n(url): return base+url
    ah=' active' if active=='home' else ''
    aj=' active' if active=='justice' else ''
    return f'''<header class="site-header"><div class="site-header-inner">
<a class="brand" href="{n('index.html')}"><span class="brand-ribbon"><img src="{n('assets/images/arx-flag.webp')}" alt="Flag of Arx"></span><span class="brand-text"><strong>ARX STATE</strong><span>OFFICIAL ARCHIVES</span></span></a>
<button class="mobile-toggle" aria-label="Toggle navigation" data-mobile-toggle>☰</button>
<nav class="main-nav" aria-label="Primary navigation"><a class="nav-link{ah}" href="{n('index.html')}">⌂&nbsp; HOME</a><a class="nav-link{aj}" href="{n('justice/index.html')}">JUSTICE ARCHIVE</a></nav>
<div class="header-search"><div class="search-shell"><input data-global-search type="search" placeholder="Search the Archive…" aria-label="Search the Archive"><button type="button" aria-label="Search" data-search-submit>⌕</button></div><div class="search-results" data-search-results></div></div>
</div></header>'''

def page_footer(base):
    return f'''<footer class="site-footer"><div class="site-footer-inner"><img class="footer-mark" src="{base}assets/images/justice-shield.png" alt=""><strong>The Arxian Justice Archive</strong><span class="footer-sep">•</span><span>Technocratic State of Arx</span></div></footer>'''

def shell(title, rel_path, content, active=''):
    base=base_for(rel_path)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="Official archive of the Technocratic State of Arx"><title>{esc(title)} | Arx</title><link rel="icon" href="{base}assets/images/arx-flag.webp"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@500;600;700&family=Roboto:wght@300;400;500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="{base}assets/css/site.css"><style>:root{{--crest-url:url('{base}assets/images/arx-state-crest.webp')}}</style></head><body data-base="{base}">{page_header(base,active)}<main class="site-main">{content}</main>{page_footer(base)}<script src="{base}assets/js/site.js" defer></script></body></html>'''

def breadcrumb(base, parts):
    chunks=[]
    for label,url in parts:
        chunks.append(f'<a href="{base}{url}">{esc(label)}</a>' if url else esc(label))
    return '<div class="breadcrumb">'+'<span>›</span>'.join(chunks)+'</div>'

def icon(key): return ICONS.get(key,ICONS['doc'])

def preset_url(types=None,statuses=None):
    params=[]
    for t in types or []: params.append(('type',t))
    for s in statuses or []: params.append(('status',s))
    q=urlencode(params,doseq=True)
    return 'archive/index.html'+(('?'+q) if q else '')

def type_icon_key(types):
    t=(types or '').lower()
    if t=='constitution': return 'constitution'
    if t=='law': return 'laws'
    if t in {'policy','procedure','guideline'}: return 'policies'
    if t=='justice ruling': return 'rulings'
    if t in {'treaty','agreement'}: return 'treaties'
    return 'archive'

def cover(d, mini=False):
    cls='document-cover-mini' if mini else ''
    type_cls=re.sub(r'[^a-z0-9]+','-',(d.get('type') or 'document').lower()).strip('-')
    return f'''<div class="{cls}"><div class="doc-cover cover-{esc(type_cls)}"><img src="PLACEHOLDER_JUSTICE" alt=""><div class="cover-id">{esc(d['id'])}</div><div class="cover-title">{esc(d.get('short_title') or d['title'])}</div></div></div>'''

def replace_asset_placeholders(s,base): return s.replace('PLACEHOLDER_JUSTICE',base+'assets/images/justice-shield-cover.png')

def write(rel_path,title,content,active=''):
    path=SITE/rel_path; path.parent.mkdir(parents=True,exist_ok=True)
    base=base_for(rel_path)
    path.write_text(shell(title,rel_path,replace_asset_placeholders(content,base),active),encoding='utf-8')

def write_redirect(rel_path,target,title='Archive'):
    path=SITE/rel_path; path.parent.mkdir(parents=True,exist_ok=True)
    safe=esc(target)
    path.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0; url={safe}"><title>{esc(title)} | Arx</title><script>location.replace({json.dumps(target)});</script></head><body><p><a href="{safe}">Continue to the Justice Archive</a></p></body></html>''',encoding='utf-8')

def docs_for_types(docs,types): return [d for d in docs if d.get('type') in types]

def archive_home(docs):
    cards=[]
    for key,name,types,_desc in TYPE_PRESETS:
        count=len(docs_for_types(docs,types))
        cards.append(f'''<a class="category-card" href="{esc(preset_url(types=types))}"><div class="category-top"><span class="icon-round">{icon(key)}</span><h3>{esc(name)}</h3></div><div class="category-meta"><span>{count} {'Document' if count==1 else 'Documents'}</span><span class="arrow-circle">→</span></div></a>''')
    archive_count=sum(1 for d in docs if status_label(d.get('status')) in ARCHIVE_STATUSES)
    cards.append(f'''<a class="category-card" href="{esc(preset_url(statuses=ARCHIVE_STATUSES))}"><div class="category-top"><span class="icon-round">{icon('archive')}</span><h3>Archive</h3></div><div class="category-meta"><span>{archive_count} Records</span><span class="arrow-circle">→</span></div></a>''')
    current=next((d for d in docs if d.get('type')=='Constitution' and status_key(d.get('status'))=='current'),None)
    feature=''
    if current:
        date=current.get('ratified') or current.get('adopted') or ''
        date_line=f'<div class="feature-meta">Ratified: {esc(date_label(date))}</div>' if date else '<div class="feature-meta">Ratification date not recorded</div>'
        pdf_rel=f"../documents/{current['id']}/{current.get('pdf')}" if current.get('pdf') else ''
        feature=f'''<div class="feature-card">{cover(current)}<div class="feature-body"><div class="feature-main-row"><div><div class="feature-kicker">Current Constitution</div><h2 class="feature-title">{esc(current['id'])}</h2><p class="feature-subtitle">{esc(current.get('short_title') or current['title'])}</p>{date_line}</div><div class="status-box"><strong>● CURRENT / ACTIVE</strong><span>Official current archive record</span></div></div><hr class="feature-divider"><div class="action-row"><a class="action-btn primary" href="documents/{current['id'].lower()}/index.html">{ICONS['book']}<span>Read Document</span></a>{f'<a class="action-btn blue" href="{pdf_rel}" target="_blank" rel="noopener">{ICONS["search"]}<span>Open Fullscreen</span></a>' if pdf_rel else ''}{f'<a class="action-btn green-outline" href="{pdf_rel}" download>{ICONS["download"]}<span>Download PDF</span></a>' if pdf_rel else ''}</div></div></div>'''
    recent=sorted(docs,key=lambda d:d.get('last_updated') or d.get('adopted') or d.get('archive_added') or '',reverse=True)[:5]
    rows=''.join(f'''<a class="update-item" href="documents/{d['id'].lower()}/index.html" style="text-decoration:none"><span class="update-icon">{icon(type_icon_key(d.get('type')))}</span><span class="update-id">{esc(d['id'])}</span><span>{esc(d.get('short_title') or d['title'])}</span><span class="update-age">{esc(date_label(d.get('last_updated') or d.get('adopted') or d.get('archive_added')))}</span></a>''' for d in recent) or '<div class="search-empty">No records have been added yet.</div>'
    return f'''<div class="container"><section class="archive-hero"><div class="archive-hero-inner"><img class="justice-emblem" src="../assets/images/justice-shield.png" alt="Justice emblem"><div class="hero-rule"></div><div class="archive-title"><h1>The Arxian<br>Justice Archive</h1><p>Official legal and governmental records of Arx.</p><div class="title-flourish"><i></i></div></div></div></section><section class="category-grid">{''.join(cards)}</section><section class="archive-dashboard">{feature}<div class="updates-panel"><div class="panel-heading">Recently Updated</div>{rows}<div class="panel-more"><a href="recent-changes/index.html">View All Updates&nbsp; →</a></div></div></section></div>'''

def home_page():
    return '''<div class="container"><section class="state-home-hero"><div class="state-home-copy"><div class="eyebrow">Technocratic State of Arx</div><h1>Arx</h1><p>Official public information and records. The Arxian Justice Archive is the first active collection on the wider Arx website.</p></div></section><a class="home-entry" href="justice/index.html"><img src="assets/images/justice-shield.png" alt="Justice emblem"><div><h2>The Arxian Justice Archive</h2><p>Constitution, laws, policies, rulings, treaties and historical records.</p></div><span class="arrow-circle" style="margin-left:auto">→</span></a></div>'''

def archive_index(docs):
    all_types=sorted({d.get('type') or 'Document' for d in docs})
    all_statuses=['Current','Legacy / Under Review','Superseded','Repealed','Draft','Historical']
    years=sorted({(d.get('last_updated') or d.get('adopted') or d.get('effective') or d.get('ratified') or '')[:4] for d in docs if (d.get('last_updated') or d.get('adopted') or d.get('effective') or d.get('ratified') or '')[:4].isdigit()},reverse=True)
    type_filters=''.join(f'''<label class="filter-option"><input type="checkbox" data-type-filter value="{esc(t)}"><span>{esc(t)}</span><span class="filter-count">{sum(1 for d in docs if (d.get('type') or 'Document')==t)}</span></label>''' for t in all_types)
    status_filters=''.join(f'''<label class="filter-option"><input type="checkbox" data-status-filter value="{esc(s)}"><span class="status-dot {status_class(s)}"></span><span>{esc(s)}</span><span class="filter-count">{sum(1 for d in docs if status_label(d.get('status'))==s)}</span></label>''' for s in all_statuses if any(status_label(d.get('status'))==s for d in docs))
    year_opts='<option value="">All years</option>'+''.join(f'<option value="{y}">{y}</option>' for y in years)
    rows=[]
    for d in docs:
        date=d.get('last_updated') or d.get('adopted') or d.get('effective') or d.get('ratified') or ''
        st=status_label(d.get('status'))
        search=' '.join([d['id'],d['title'],d.get('short_title',''),d.get('summary',''),d.get('legacy_id',''),d.get('legacy_code','')]).lower()
        rows.append(f'''<a class="doc-row" data-doc-row data-id="{esc(d['id'])}" data-title="{esc((d.get('short_title') or d['title']).lower())}" data-date="{esc(date)}" data-year="{esc(date[:4] if date else '')}" data-status="{esc(st.lower())}" data-type="{esc((d.get('type') or 'Document').lower())}" data-search="{esc(search)}" href="../documents/{d['id'].lower()}/index.html"><span class="id">{esc(d['id'])}</span><strong>{esc(d.get('short_title') or d['title'])}</strong><span class="doc-type"><span class="type-pill">{esc(d.get('type') or 'Document')}</span></span><span class="doc-status"><span class="status-pill {status_class(st)}"><span class="status-dot {status_class(st)}"></span>{esc(st.upper())}</span></span><span class="doc-date">{esc(date_label(date) or '—')}</span><span class="row-arrow">→</span></a>''')
    return f'''<div class="container">{breadcrumb('../',[('Home','../index.html'),('Justice Archive','index.html'),('Archive',None)])}</div><section class="category-hero archive-index-hero"><div class="container"><div class="category-hero-inner"><span class="category-hero-icon">{icon('archive')}</span><div><h1>Document Archive</h1><p>Search and filter all public Justice Archive records in one place.</p></div></div></div></section><div class="container"><div class="active-filter-bar" data-active-filters></div><div class="catalogue-wrap"><aside class="filter-panel"><h3>Filters</h3><div class="local-search"><input data-local-search type="search" placeholder="Search documents…"><button type="button">⌕</button></div><div class="filter-group"><div class="filter-label">Document Type</div>{type_filters}</div><div class="filter-group"><div class="filter-label">Status</div>{status_filters}</div><div class="filter-group"><div class="filter-label">Date</div><select class="sort-select" data-year-filter>{year_opts}</select></div></aside><section class="catalogue-main"><div class="catalogue-toolbar master-toolbar"><div><strong><span data-visible-count>{len(rows)}</span> records</strong><span class="catalogue-subline">Filters can be removed at any time.</span></div><select class="sort-select compact" data-sort><option value="newest">Last Updated (Newest)</option><option value="oldest">Last Updated (Oldest)</option><option value="title">Title</option><option value="id">Document ID</option></select></div><div class="catalogue-table"><div class="catalogue-head"><span>Document ID</span><span>Title</span><span>Type</span><span>Status</span><span>Date</span><span></span></div><div data-catalogue>{''.join(rows)}</div><div class="empty-state" data-empty-state style="display:{'none' if rows else 'block'}"><strong>No records match those filters.</strong>Remove a filter or try a different search term.</div></div></section></div></div>'''

def doc_file_public(d, filename): return f"../../../documents/{d['id']}/{filename}" if filename else ''

def warning_for(d):
    s=status_key(d.get('status'))
    if s=='legacy / under review':
        return '<div class="document-warning legacy"><strong>Legacy document - under review.</strong><span>This instrument predates the current constitutional framework and has not yet completed review for compatibility with current law.</span></div>'
    if s=='superseded':
        return '<div class="document-warning superseded"><strong>Superseded document.</strong><span>Retained for historical reference. This is not the current governing instrument.</span></div>'
    if s=='repealed':
        return '<div class="document-warning repealed"><strong>Repealed document.</strong><span>Retained for historical reference and no longer in force.</span></div>'
    if s=='historical':
        return '<div class="document-warning historical"><strong>Historical record.</strong><span>Preserved as part of the official archive. Its present legal or diplomatic effect may require separate confirmation.</span></div>'
    if s=='draft':
        return '<div class="document-warning draft"><strong>Draft document.</strong><span>This record has not been marked as an enacted or final instrument.</span></div>'
    return ''

def relationship_links(d,docs):
    ids={x['id']:x for x in docs}
    blocks=[]
    sets=[('Supersedes',d.get('supersedes') or []),('Superseded By',d.get('superseded_by') or []),('Related Documents',d.get('related_documents') or d.get('related') or [])]
    for label,vals in sets:
        links=[]
        for rid in vals:
            r=ids.get(rid)
            if r:
                links.append(f'<a class="side-link" href="../{r["id"].lower()}/index.html"><span><strong>{esc(r["id"])}</strong>&nbsp;&nbsp;{esc(r.get("short_title") or r["title"])}</span><span>→</span></a>')
            else:
                links.append(f'<div class="side-link"><span>{esc(rid)}</span></div>')
        if links: blocks.append(f'<div class="side-card"><h3>{esc(label)}</h3>{"".join(links)}</div>')
    return ''.join(blocks)

def document_page(d,docs):
    base='../../../'
    pdf=doc_file_public(d,d.get('pdf')) if d.get('pdf') else ''
    crumbs=breadcrumb(base,[('Home','index.html'),('Justice Archive','justice/index.html'),('Archive','justice/archive/index.html'),(d['id'],None)])
    metas=[]
    def add(label,val,formatter=lambda x:x):
        if val: metas.append(f'<div class="meta-cell"><span class="meta-label">{esc(label)}</span><span class="meta-value">{esc(formatter(val))}</span></div>')
    add('Type',d.get('type')); add('Status',status_label(d.get('status'))); add('Version',d.get('version')); add('Legacy ID',d.get('legacy_id')); add('Legacy Code',d.get('legacy_code')); add('Ratified',d.get('ratified'),date_label); add('Adopted',d.get('adopted'),date_label); add('Effective',d.get('effective'),date_label); add('Last Updated',d.get('last_updated'),date_label); add('Authority',d.get('authority'))
    authors=d.get('authors') or []
    if isinstance(authors,str): authors=[authors]
    if authors: add('Author' if len(authors)==1 else 'Authors',', '.join(authors))
    actions=''
    if pdf:
        actions=f'''<a class="action-btn blue" href="{pdf}" target="_blank" rel="noopener" data-pdf-open>{ICONS['search']}<span>Open Fullscreen</span></a><a class="action-btn primary" href="{pdf}" download data-pdf-download>{ICONS['download']}<span>Download PDF</span></a><a class="action-btn green-outline" href="#" data-google-file="{pdf}">G&nbsp; <span>Google Viewer</span></a>'''
    current_date=d.get('last_updated') or d.get('adopted') or d.get('effective') or d.get('ratified') or ''
    versions=[f'''<button class="version-row version-select active" type="button" data-version-select data-version-file="{esc(pdf)}" data-version-label="Current" data-version-key="current"><strong>{esc(d.get('version') or 'Current archive record')}</strong><span>{esc(date_label(current_date) or 'Current')}</span></button>'''] if pdf else []
    for i,v in enumerate(d.get('versions') or []):
        file=v.get('file') or ''
        if not file: continue
        link=doc_file_public(d,file)
        key=v.get('key') or f'v{i+1}'
        versions.append(f'''<button class="version-row version-select" type="button" data-version-select data-version-file="{esc(link)}" data-version-label="{esc(v.get('label') or 'Previous version')}" data-version-key="{esc(key)}"><strong>{esc(v.get('label') or v.get('status') or 'Previous version')}</strong><span>{esc(date_label(v.get('date')) or v.get('status') or '')}</span></button>''')
    about=d.get('summary') or 'No description has been added.'
    side=f'''<aside class="viewer-side"><div class="side-card"><h3>Version History</h3>{''.join(versions) if versions else '<p>No version files have been attached.</p>'}</div><div class="side-card"><h3>About This Document</h3><p>{esc(about)}</p></div>{relationship_links(d,docs)}</aside>'''
    viewer=f'''<div class="version-viewing-note" data-version-note style="display:none"></div><iframe loading="lazy" src="{pdf}#view=FitH" title="{esc(d['title'])} PDF viewer" data-viewer-frame></iframe>''' if pdf else '<div class="empty-state"><strong>No PDF attached.</strong>Add a PDF filename in this document’s meta.json file.</div>'
    return f'''<div class="container document-page">{crumbs}{warning_for(d)}<section class="document-head">{cover(d,True)}<div class="document-info"><h1>{esc(d['id'])}</h1><p class="full-title">{esc(d['title'])}</p><span class="current-badge {status_class(d.get('status'))}">{esc(status_label(d.get('status')).upper())}</span><div class="meta-strip">{''.join(metas)}</div></div></section><div class="viewer-actions">{actions}</div><section class="viewer-grid"><div class="pdf-frame">{viewer}</div>{side}</section></div>'''

def recent_page(docs):
    recent=sorted(docs,key=lambda d:d.get('last_updated') or d.get('adopted') or d.get('archive_added') or '',reverse=True)
    items=''.join(f'<a class="side-link" href="../documents/{d["id"].lower()}/index.html"><span><strong>{esc(d["id"])}</strong>&nbsp;&nbsp;{esc(d.get("short_title") or d["title"])}</span><span>{esc(date_label(d.get("last_updated") or d.get("adopted") or d.get("archive_added")))}</span></a>' for d in recent)
    return f'<div class="container"><div class="simple-page">{breadcrumb("../",[("Home","../index.html"),("Justice Archive","index.html"),("Recent Changes",None)])}<h1>Recent Changes</h1><div class="side-card">{items or "No records yet."}</div></div></div>'

def search_page():
    return f'''<div class="container search-page" data-search-page>{breadcrumb('../',[('Home','index.html'),('Search',None)])}<section class="search-page-hero"><div class="eyebrow">Archive Search</div><h1>Search the Archive</h1><form class="search-page-form" data-search-page-form><input type="search" data-search-page-input placeholder="Search titles, document IDs and document text…" aria-label="Search archive records"><button type="submit">{ICONS['search']}<span>Search</span></button></form></section><section class="search-page-results"><div class="search-page-summary" data-search-summary>Enter a search term to find matching archive pages and documents.</div><div data-search-page-results></div></section></div>'''

def build():
    docs=load_docs(); copy_source()
    write('index.html','Home',home_page(),'home')
    write('justice/index.html','The Arxian Justice Archive',archive_home(docs),'justice')
    write('justice/archive/index.html','Document Archive',archive_index(docs),'justice')
    redirects={
        'constitution':preset_url(types=['Constitution']).replace('archive/index.html','../archive/index.html'),
        'laws':preset_url(types=['Law']).replace('archive/index.html','../archive/index.html'),
        'policies':preset_url(types=['Policy','Procedure','Guideline']).replace('archive/index.html','../archive/index.html'),
        'rulings':preset_url(types=['Justice Ruling']).replace('archive/index.html','../archive/index.html'),
        'treaties':preset_url(types=['Treaty','Agreement']).replace('archive/index.html','../archive/index.html'),
    }
    for old,target in redirects.items(): write_redirect(f'justice/{old}/index.html',target,old.title())
    for d in docs: write(f"justice/documents/{d['id'].lower()}/index.html",f"{d['id']} — {d['title']}",document_page(d,docs),'justice')
    write('justice/recent-changes/index.html','Recent Changes',recent_page(docs),'justice')
    write('search/index.html','Search the Archive',search_page())
    index=[
        {'id':'','title':'Technocratic State of Arx','category':'Site','type':'Page','status':'','summary':'Official public information and records of Arx.','text':'Arx official public information records Justice Archive','url':'index.html'},
        {'id':'','title':'The Arxian Justice Archive','category':'Justice Archive','type':'Page','status':'','summary':'Official legal and governmental records of Arx.','text':'constitution laws policies procedures justice rulings treaties agreements archive','url':'justice/index.html'},
        {'id':'','title':'Document Archive','category':'Justice Archive','type':'Collection','status':'','summary':'Search and filter all public Justice Archive records.','text':'all documents constitution law policy procedure ruling treaty agreement legacy superseded historical','url':'justice/archive/index.html'},
    ]
    for d in docs:
        txt=re.sub(r'\s+',' ',d.get('_search_text','')).strip()
        meta=' '.join(str(d.get(k) or '') for k in ['legacy_id','legacy_code','authority','department','version'])
        index.append({'id':d['id'],'title':d['title'],'category':'Justice Archive','type':d.get('type',''),'status':status_label(d.get('status')),'summary':d.get('summary',''),'text':(meta+' '+txt)[:160000],'url':d['url']})
    (SITE/'assets'/'search-index.json').write_text(json.dumps(index,ensure_ascii=False),encoding='utf-8')
    print(f'Built {len(docs)} document(s) into {SITE}')

if __name__=='__main__': build()
