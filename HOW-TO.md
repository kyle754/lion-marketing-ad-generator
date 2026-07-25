# How to make Lion Marketing ads on a Mac

This tool takes campaign copy from a spreadsheet and puts it into every selected design and size.
The finished PNGs are ready for paid social, display campaigns, review, or Canva handoff.

## The normal workflow

1. Double-click **Lion Ad Generator.command**.
2. Choose **Edit ad copy**.
3. Add or update rows in `1-COPY/ads.csv`, then save it as a CSV.
4. Return to the launcher and choose **Make a quick preview**.
5. Open `3-OUTPUT` and check the first ad in all sizes.
6. Choose **Generate every ad**.

The launcher finds Chrome automatically. Your source copy and ads stay on your Mac.

## Copy: `1-COPY/ads.csv`

Each row is one campaign message. The starter columns are:

| Column | What it controls |
|---|---|
| `designs` | `all`, or selected designs such as `Bold,Report` |
| `name` | Short internal name used in output filenames |
| `eyebrow` | Small category line above the headline |
| `hook` | Main headline |
| `body` | Supporting copy |
| `cta` | Button text |
| `stat` | Short proof point, such as `3×` |
| `stat_label` | Explanation of the proof point |

You can add columns. A column called `offer` becomes `{{OFFER}}` inside a template. Keep the
`designs` column so each row can choose its layouts.

When saving from Excel or Numbers, keep the file in CSV format. If asked about character encoding,
choose UTF-8.

## Brand: `1-COPY/brand.csv`

This file controls reusable values such as `{{PRIMARY}}`, `{{ACCENT}}`, and `{{LOGO}}`.

- Put the approved Lion Marketing colors in the color rows.
- Copy the official logo into `assets/`.
- Change `LOGO_FILE` to its relative path, for example `assets/lion-logo.png`.
- PNG, JPG, and SVG logo files work.

## Copy guardrails: `1-COPY/limits.csv`

Guardrails flag copy that may be too short or too long for a design. Ads still render. Review
`3-OUTPUT/copy-check.csv` when it appears.

## Designs: `2-TEMPLATES/`

Templates are normal HTML files with placeholders such as:

```html
<div class="hook">{{HOOK}}</div>
<div class="body">{{BODY}}</div>
<div class="cta">{{CTA}}</div>
```

The filename sets the design and output sizes:

- `Bold 1200x628.html` means design `Bold`, size 1200×628.
- `Bold 1080x1080 1080x1350.html` renders one template at both sizes.

Keep important portrait content inside the centered 1080×1080 safe area so Meta placements have
room to crop.

## Troubleshooting

- **Launcher will not open:** Control-click the `.command` file, choose **Open**, and confirm.
- **“Python not found”:** Install Python 3 from python.org, then reopen the launcher.
- **“Browser not found”:** Install Chrome, Edge, or Chromium in the Applications folder.
- **Spreadsheet opens strangely:** Import the CSV as UTF-8 with commas as separators.
- **Wrong logo or color:** Update `1-COPY/brand.csv`, then generate again.
- **Text overflows:** Shorten the flagged copy or adjust that design’s font size.
