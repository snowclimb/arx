# Technocratic State of Arx website — V1.2

This repository builds the public Arx website and **The Arxian Justice Archive** for GitHub Pages.

V1.2 uses a small purpose-built static generator instead of exposing repository controls in the public interface. The site is generated automatically on every push to `main`.

## Routine use

You normally only need to edit files under `content/documents/`.

### Add a new document

1. Copy the folder `content/documents/_TEMPLATE/` and rename the copy to the permanent document ID, e.g. `POL-001`.
2. Put the current PDF inside that folder as `current.pdf` (or update the `pdf` filename in `meta.json`).
3. If you have the original Word file, upload it too and set the `docx` field, e.g. `current.docx`.
4. Edit `meta.json` with the document's real metadata.
5. Commit/push the changes.

That is all. The build automatically:

- creates the document viewer page;
- adds the record to the correct category;
- updates document counts;
- updates Recent Changes;
- adds the document to full-text archive search;
- exposes Google Viewer for PDFs;
- exposes Office Viewer when a DOCX is supplied;
- provides downloads;
- creates version-history links from the metadata.

You do **not** need to manually edit a navigation file for each new record.

## Permanent document IDs

Recommended prefixes:

- `CON-###` — Constitution / constitutional documents
- `LAW-###` — laws / Acts
- `POL-###` — policies and procedures
- `JUD-###` — Justice rulings / interpretations
- `TRT-###` — treaties and agreements

Once issued, an ID should remain attached to the same legal/documentary record. Amended versions normally remain under the same ID and are listed in `versions`.

## Metadata fields

Example:

```json
{
  "id": "POL-001",
  "title": "Citizenship Procedure",
  "short_title": "Citizenship Procedure",
  "category": "policies",
  "type": "Procedure",
  "status": "Current",
  "version": "1.0",
  "adopted": "2026-08-15",
  "effective": "2026-08-15",
  "ratified": "",
  "last_updated": "2026-08-15",
  "archive_added": "2026-08-15",
  "authority": "Departmental Council",
  "summary": "Short description.",
  "pdf": "current.pdf",
  "docx": "current.docx",
  "related": ["CON-001"],
  "versions": []
}
```

Dates use `YYYY-MM-DD`. Leave an unknown field as an empty string. Empty metadata is automatically omitted from the public document page, so it can be filled in later without redesigning anything.

Allowed category values are:

- `constitution`
- `laws`
- `policies`
- `rulings`
- `treaties`
- `archive`

### Previous versions

Put old files inside the document folder, for example:

```text
content/documents/POL-001/
├── current.pdf
├── current.docx
├── meta.json
└── versions/
    ├── 2026-07-01.pdf
    └── 2026-07-01.docx
```

Then add them to `versions` in `meta.json`:

```json
"versions": [
  {
    "label": "Version 1.0",
    "date": "2026-07-01",
    "status": "Superseded",
    "file": "versions/2026-07-01.pdf",
    "notes": "Original adopted version"
  }
]
```

## CON-001 metadata

The supplied Constitution does not state its ratification/adoption date or a formal version number. Those fields are therefore intentionally blank in:

`content/documents/CON-001/meta.json`

When the correct information is known, edit that one file and commit it. The site will update automatically.

## Search

The build extracts text from each PDF using `pypdf` and creates `site/assets/search-index.json`. This allows the main archive search field to find terms contained inside the formatted PDFs while visitors continue to read the original document visually.

## Public layout

The global top navigation and footer are generated once by `scripts/build.py`, so they remain consistent across the homepage, archive, category pages and document viewer pages.

The national Arx flag remains in the global header. Justice branding is used inside the Justice Archive content rather than replacing the national site identity.

## Development

Generate the site locally with:

```bash
python scripts/build.py
```

Then serve the `site/` folder with any static web server, for example:

```bash
python -m http.server 8000 -d site
```

The GitHub Pages workflow performs the same build automatically.
