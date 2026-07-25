# Lion Marketing Ad Generator

A local batch-production tool for turning campaign copy and reusable HTML designs into finished
PNG ads. One CSV row can produce every selected design in 1200×628, 1080×1080, and 1080×1350.

The project runs on macOS, Windows, and Linux with Python 3 plus Chrome, Edge, or Chromium. It has
no Python packages to install, no cloud service, no account, and no campaign data leaves the
computer.

## Fastest start on a Mac

1. Install Google Chrome and make sure `python3 --version` works in Terminal.
2. Double-click **Lion Ad Generator.command**.
3. Choose **Edit ad copy**, update the CSV in Numbers or Excel, and save it as CSV.
4. Choose **Make a quick preview**.
5. Choose **Generate every ad** when the preview looks right.

If macOS blocks the launcher the first time, Control-click it, choose **Open**, then confirm.
You can also double-click **RUN.command** to generate immediately.

## What the tool produces

```text
3-OUTPUT/
  1200x628/               Finished landscape ads
  1080x1080/              Finished square ads
  1080x1350/              Finished portrait ads
  manifest.csv            Every image plus its source copy
  canva_bulkcreate.csv    Copy formatted for Canva Bulk Create
  copy-check.csv          Only created when copy is outside a guardrail
```

## Folder map

```text
Lion Ad Generator.command        Mac menu for editing, previewing, and generating
RUN.command                      Mac one-click full generation
PREVIEW (first row only).command Mac one-click proof
RUN.bat                          Windows launcher
ad_generator.py                  Cross-platform rendering engine
1-COPY/
  ads.csv                        One row per ad
  brand.csv                      Brand name, colors, and logo
  limits.csv                     Character guardrails
2-TEMPLATES/                     HTML designs; sizes are encoded in filenames
assets/                          Logo and other template images
3-OUTPUT/                        Generated locally and ignored by Git
```

## Command-line use

```bash
python3 ad_generator.py
python3 ad_generator.py --proof
python3 ad_generator.py --preview-row 2 --preview-design Bold
```

Run `python3 ad_generator.py --help` for all options.

## How it stays reusable

- Columns in `ads.csv` automatically become template placeholders.
- Every `brand.csv` token is available to templates.
- Any `.html` file in `2-TEMPLATES` becomes a design.
- Sizes are read from filenames such as `Bold 1200x628.html`.
- The `designs` cell can be `all` or a comma-separated list such as `Bold,Report`.

The included Lion Marketing logo is a clean starter mark created for this repository. Replace it
with the official company logo and update the colors in `1-COPY/brand.csv` before production use.

See [HOW-TO.md](HOW-TO.md) for the plain-language operating guide and
[CANVA_HANDOFF.md](CANVA_HANDOFF.md) for the Canva workflow.
