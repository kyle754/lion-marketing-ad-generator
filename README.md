# Lion Marketing Ad Studio

A private, local app for creating batches of on-brand advertising images. Add copy variations,
manage brand settings and HTML templates, preview combinations, generate every selected size, and
review the finished PNG library from one responsive interface.

The app runs on macOS, Windows, and Linux with Python 3 plus Chrome, Edge, or Chromium. There are no
Python packages to install, no account to create, and campaign data never leaves the computer.

## Open the app on a Mac

1. Install Google Chrome and Python 3 if they are not already installed.
2. Download or clone this repository.
3. Double-click **Lion Ad Generator.command**.
4. Keep the small Terminal window open while using the app in your browser.

If macOS blocks the launcher the first time, Control-click it, choose **Open**, then confirm.
Opening the launcher again simply returns to the already-running app.

## The five-step workflow

### 1. Ad copy

- Add, duplicate, and remove copy variations.
- Edit every template variable in a responsive card—no wide spreadsheet required.
- See character guidance and potential output count as you work.
- Import or export CSV when a spreadsheet workflow is useful.
- Changes autosave to `1-COPY/ads.csv`.

### 2. Brand

- Upload a PNG, JPG, SVG, or WebP logo.
- Edit approved colors with visual swatches and hex values.
- Manage advanced reusable tokens.
- Adjust copy-length guidance.
- See the brand update in a live visual panel.

### 3. Templates

- See every available design, source file, and output size.
- Add an HTML template from the app.
- Remove obsolete template files with confirmation.
- Jump directly from a design card to its preview.

### 4. Preview and generate

- Choose any copy variation and design for a quick preview.
- Generate a one-row proof before committing to a full campaign.
- Render the full matrix in the background.
- Follow image-by-image progress without locking the interface.

### 5. Finished ads

- Browse a responsive output gallery.
- Filter by size and design.
- Open a full-size quick view.
- Download one PNG or the full campaign as a ZIP.
- Open the native output folder from the app.

## What the renderer produces

```text
3-OUTPUT/
  1200x628/               Finished landscape ads
  1080x1080/              Finished square ads
  1080x1350/              Finished portrait ads
  manifest.csv            Every image plus its source copy
  canva_bulkcreate.csv    Copy formatted for Canva Bulk Create
  copy-check.csv          Created only when copy is outside guidance
```

## Project map

```text
Lion Ad Generator.command        Double-click Mac app launcher
Ad Generator.bat                 Windows app launcher
app_server.py                    Private localhost app API
app/
  index.html                     Accessible five-step interface
  styles.css                     Responsive design system
  app.js                         Editing, preview, progress, and gallery behavior
ad_generator.py                  Cross-platform rendering engine
RUN.command / RUN.bat            Direct full generation without the app
PREVIEW (...).command / .bat     Direct first-row proof
1-COPY/
  ads.csv                        One row per ad variation
  brand.csv                      Brand name, colors, and logo
  limits.csv                     Character guidance
2-TEMPLATES/                     HTML designs; sizes are encoded in filenames
assets/                          Logo and other template images
3-OUTPUT/                        Generated locally and ignored by Git
```

## Command-line options

The app is the recommended interface, but the original direct workflow remains available:

```bash
python3 app_server.py --open
python3 ad_generator.py
python3 ad_generator.py --proof
python3 ad_generator.py --preview-row 2 --preview-design Bold
```

## Template model

- Every column in `ads.csv` becomes a case-insensitive `{{PLACEHOLDER}}`.
- Every token in `brand.csv` is available to every template.
- Any `.html` file in `2-TEMPLATES` becomes a design.
- Sizes come from filenames such as `Bold 1200x628.html`.
- A `designs` cell can be `all` or a comma-separated list such as `Bold,Report`.

The included Lion Marketing logo and colors are starter assets. Replace them with the approved
brand kit before production use.

See [HOW-TO.md](HOW-TO.md) for the plain-language operating guide and
[CANVA_HANDOFF.md](CANVA_HANDOFF.md) for the Canva workflow.
