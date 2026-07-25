# How to use Lion Marketing Ad Studio

## Start the app

On a Mac, double-click **Lion Ad Generator.command**. The app opens in your browser and a small
Terminal window stays open in the background. That window is the local app—not an upload or cloud
connection. Close it when you are finished.

The app is organized into five numbered steps. On a large window they appear in the left sidebar.
On a narrow window they appear in the bottom navigation bar.

## 1. Add the ad copy

Open **Ad copy** and edit the variation cards.

- **Designs:** use `all`, or list selected designs such as `Bold,Report`.
- **Internal name:** a short label used to identify the variation.
- **Category / eyebrow:** the small text above the headline.
- **Headline:** the primary campaign hook.
- **Supporting copy:** the explanation beneath the headline.
- **Call to action:** the button text.
- **Proof point:** a short value such as `3×` or `+42%`.
- **Proof point label:** what the value means.

Use **Duplicate** to create a closely related test. Use **+ Add variation** for a blank card.
Character notes update while you type, and changes save automatically.

For a large spreadsheet, choose **Import CSV**. The first CSV row must contain column names.
Choose **Export CSV** to move the current set back into Excel or Numbers.

## 2. Set the brand

Open **Brand**.

1. Upload the approved logo.
2. Set the primary, dark, accent, ink, and muted colors.
3. Check the visual brand preview.
4. Choose **Save brand**.

The **Advanced brand tokens** section exposes every reusable value from `brand.csv`. Use it when a
template needs another shared value.

The copy-length guidance below the brand settings does not block generation. It only creates
helpful writing notes and, when needed, `3-OUTPUT/copy-check.csv`.

## 3. Manage templates

Open **Templates** to see each design and its sizes.

- Choose **Preview design** to jump to that design in the preview tool.
- Choose **+ Add template** to upload an HTML template.
- Choose **Remove** beside a source file to delete it after confirmation.
- Choose **Open folder** when you want to edit HTML directly.

Template filenames control design names and sizes:

- `Bold 1200x628.html`
- `Bold 1080x1080 1080x1350.html`

Template copy fields use double braces:

```html
<div class="hook">{{HOOK}}</div>
<div class="body">{{BODY}}</div>
<div class="cta">{{CTA}}</div>
```

## 4. Preview and generate

Open **Preview & generate**.

1. Choose a copy variation.
2. Choose a design.
3. Select **Refresh preview**.
4. Review the rendered image.

Choose **Quick proof** to render the first copy row in every design and size. Choose **Generate
all** to render the full campaign. Progress advances after every image, and the app moves to the
finished library when the job is complete.

## 5. Review finished ads

Open **Finished ads**.

- Use the first filter row for dimensions.
- Use the second filter row for designs.
- Click an image for a larger quick view.
- Use the arrow button to download one PNG.
- Choose **Download all** for a ZIP of the full output folder.
- Choose **Open folder** to work with the files in Finder.

## Troubleshooting

- **The launcher is blocked:** Control-click it, choose **Open**, and confirm.
- **The app does not open:** Confirm `python3 --version` works in Terminal.
- **Preview says renderer unavailable:** Install Chrome, Edge, or Chromium.
- **A template upload is rejected:** Use an `.html` file containing at least one `{{PLACEHOLDER}}`.
- **Text overflows:** Shorten the flagged copy or adjust that template’s typography.
- **The app is already running:** Opening the launcher again returns to the same local app.
- **You closed the browser tab:** Run the launcher again; the project data is still saved.
