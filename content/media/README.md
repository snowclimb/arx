# Arx media folder

The site automatically registers supported files placed here when `python scripts/build.py` runs.

## Photos
Put `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, or `.avif` files in `content/media/photos/`.

If you add an image called `homepage-hero.jpg` (or PNG/WebP/AVIF), the homepage will automatically use it as the large background photograph.

Optional metadata: add a JSON sidecar with the same basename, for example `philippi-overview.jpg` + `philippi-overview.json`:

```json
{
  "title": "Philippi from above",
  "caption": "Aerial view of the Arxian capital.",
  "date": "",
  "order": 10
}
```

## Videos
Put `.mp4`, `.webm`, `.mov`, or `.m4v` files in `content/media/videos/`. They are automatically shown in the Media gallery with native browser controls.

Optional metadata works the same way as photos.

For large videos, hosting them externally and embedding them later is preferable to committing very large files to GitHub.
