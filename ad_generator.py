#!/usr/bin/env python3
"""Lion Marketing batch ad generator.

Merges CSV copy and brand tokens into HTML templates, then asks a local
Chrome/Edge installation to capture each finished ad as a PNG.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COPY_DIR = ROOT / "1-COPY"
TEMPLATE_DIR = ROOT / "2-TEMPLATES"
OUTPUT_DIR = ROOT / "3-OUTPUT"
TEMP_DIR = ROOT / ".tmp"
SIZE_RE = re.compile(r"(\d+)x(\d+)")


@dataclass(frozen=True)
class Size:
    width: int
    height: int

    @property
    def name(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass(frozen=True)
class Template:
    path: Path
    design: str
    sizes: tuple[Size, ...]


def fail(message: str) -> "NoReturn":
    print(f"\nERROR: {message}\n", file=sys.stderr)
    raise SystemExit(1)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): (value or "") for key, value in row.items() if key is not None}
            for row in csv.DictReader(handle)
        ]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def find_browser(explicit: str = "") -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path
        fail(f"Browser not found at: {path}")

    system = platform.system()
    candidates: list[Path] = []
    if system == "Darwin":
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    elif system == "Windows":
        for base in filter(None, [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]):
            candidates.extend([
                Path(base) / "Google/Chrome/Application/chrome.exe",
                Path(base) / "Microsoft/Edge/Application/msedge.exe",
            ])
    else:
        for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
            found = shutil.which(command)
            if found:
                candidates.append(Path(found))

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    fail("Google Chrome, Microsoft Edge, or Chromium is required. Install one and try again.")


def discover_templates() -> list[Template]:
    templates: list[Template] = []
    for path in sorted(TEMPLATE_DIR.glob("*.html")):
        matches = SIZE_RE.findall(path.stem)
        sizes = tuple(Size(int(width), int(height)) for width, height in matches)
        if not sizes:
            sizes = (Size(1200, 628),)
        design = SIZE_RE.sub("", path.stem)
        design = re.sub(r"[\s_-]{2,}", " ", design).strip(" -_") or path.stem
        templates.append(Template(path, design, sizes))
    return templates


def replace_token(source: str, name: str, value: str) -> str:
    pattern = re.compile(r"\{\{\s*" + re.escape(name) + r"\s*\}\}", re.IGNORECASE)
    return pattern.sub(lambda _: value, source)


def slug(value: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-").lower()[:28].rstrip("-")
    return result or "ad"


def load_brand_tokens() -> dict[str, str]:
    tokens = {
        row.get("token", ""): row.get("value", "")
        for row in read_csv(COPY_DIR / "brand.csv")
        if row.get("token")
    }
    logo_file = tokens.get("LOGO_FILE", "")
    if logo_file:
        logo_path = Path(logo_file).expanduser()
        if not logo_path.is_absolute():
            logo_path = ROOT / logo_path
        if logo_path.exists():
            tokens["LOGO"] = (
                f"<img class='brand-logo' src='{logo_path.resolve().as_uri()}' "
                "alt='Lion Marketing logo'>"
            )
        else:
            print(f"WARNING: LOGO_FILE not found: {logo_path}", file=sys.stderr)
            tokens["LOGO"] = "<strong class='brand-wordmark'>LION MARKETING</strong>"
    else:
        tokens["LOGO"] = "<strong class='brand-wordmark'>LION MARKETING</strong>"
    return tokens


def load_limits() -> dict[str, tuple[int, int]]:
    limits: dict[str, tuple[int, int]] = {}
    for row in read_csv(COPY_DIR / "limits.csv"):
        field = row.get("field", "").strip().lower()
        if not field:
            continue
        try:
            limits[field] = (int(row.get("min", "0")), int(row.get("max", "0")))
        except ValueError:
            fail(f"Invalid min/max in 1-COPY/limits.csv for field '{field}'.")
    return limits


def render_html(
    template: Template,
    ad: dict[str, str],
    variable_columns: list[str],
    brand_tokens: dict[str, str],
) -> str:
    source = template.path.read_text(encoding="utf-8-sig")
    for name, value in brand_tokens.items():
        source = replace_token(source, name, str(value))
    for name in variable_columns:
        source = replace_token(source, name, html.escape(ad.get(name, ""), quote=False))
    return source


def capture(browser: Path, html_path: Path, png_path: Path, size: Size) -> None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.unlink(missing_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix="chrome-profile-", dir=TEMP_DIR))
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--metrics-recording-only",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile_dir}",
        f"--screenshot={png_path}",
        f"--window-size={size.width},{size.height}",
        "--default-background-color=00000000",
        html_path.resolve().as_uri(),
    ]
    process: subprocess.Popen[str] | None = None
    details = ""
    success = False
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=(platform.system() != "Windows"),
        )
        deadline = time.monotonic() + 15
        previous_size = -1
        stable_checks = 0
        while time.monotonic() < deadline:
            if png_path.exists():
                current_size = png_path.stat().st_size
                stable_checks = stable_checks + 1 if current_size == previous_size and current_size > 0 else 0
                previous_size = current_size
                if stable_checks >= 2:
                    success = True
                    break
            if process.poll() is not None:
                success = png_path.exists() and png_path.stat().st_size > 0
                break
            time.sleep(0.1)
    finally:
        if process and process.poll() is None:
            try:
                if platform.system() == "Windows":
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        if process:
            try:
                stdout, stderr = process.communicate(timeout=1)
                details = (stderr or stdout or "").strip()
            except subprocess.TimeoutExpired:
                process.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)
    if not success:
        fail(f"Chrome could not render {png_path.name} within 15 seconds. {details}")


def open_output_folder() -> None:
    try:
        if platform.system() == "Darwin":
            subprocess.Popen(["open", str(OUTPUT_DIR)])
        elif platform.system() == "Windows":
            os.startfile(OUTPUT_DIR)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
    except (OSError, subprocess.SubprocessError):
        pass


def generate(args: argparse.Namespace) -> int:
    ads_path = COPY_DIR / "ads.csv"
    if not ads_path.exists():
        fail("Missing 1-COPY/ads.csv.")
    templates = discover_templates()
    if not templates:
        fail("No HTML templates found in 2-TEMPLATES/.")
    ads = read_csv(ads_path)
    if not ads:
        fail("1-COPY/ads.csv has no rows.")

    browser = find_browser(args.chrome_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    all_designs = list(dict.fromkeys(template.design for template in templates))
    variable_columns = [
        column for column in ads[0].keys()
        if column.lower() not in {"designs", "name"}
    ]
    brand_tokens = load_brand_tokens()
    limits = load_limits()

    print(f"Browser  : {browser.name}")
    print(f"Brand    : {brand_tokens.get('BRAND_NAME', 'Lion Marketing')}")
    print(f"Designs  : {', '.join(all_designs)}")
    print(f"Variables: {', '.join(variable_columns)}\n")

    if args.preview_row:
        index = max(0, min(args.preview_row - 1, len(ads) - 1))
        design = args.preview_design or all_designs[0]
        choices = [template for template in templates if template.design.lower() == design.lower()]
        if not choices:
            choices = templates
        template = choices[0]
        size = template.sizes[0]
        preview_html = TEMP_DIR / "preview.html"
        preview_png = TEMP_DIR / "preview.png"
        preview_html.write_text(
            render_html(template, ads[index], variable_columns, brand_tokens),
            encoding="utf-8",
        )
        capture(browser, preview_html, preview_png, size)
        print(f"PREVIEW {template.design} [{size.name}] row {index + 1}")
        print(f"Saved: {preview_png}")
        return 0

    selected_ads = ads[:1] if args.proof else ads
    manifest: list[dict[str, object]] = []
    canva_rows: list[dict[str, object]] = []
    copy_issues: list[dict[str, object]] = []
    rendered = 0

    for row_number, ad in enumerate(selected_ads, start=1):
        selection = ad.get("designs", "all").strip() or "all"
        use_designs = all_designs if selection.lower() == "all" else [
            item.strip() for item in selection.split(",") if item.strip()
        ]

        for column in variable_columns:
            guardrail = limits.get(column.lower())
            if guardrail:
                length = len(ad.get(column, ""))
                minimum, maximum = guardrail
                if length < minimum or length > maximum:
                    copy_issues.append({
                        "row": row_number,
                        "field": column,
                        "length": length,
                        "min": minimum,
                        "max": maximum,
                        "text": ad.get(column, ""),
                    })

        canva_row: dict[str, object] = {
            column: ad.get(column, "") for column in variable_columns
        }
        canva_row["designs"] = "|".join(use_designs)
        canva_rows.append(canva_row)

        first_value = ad.get(variable_columns[0], "") if variable_columns else "ad"
        label = slug(ad.get("name", "") or first_value)
        for design in use_designs:
            design_templates = [
                template for template in templates
                if template.design.lower() == design.lower()
            ]
            if not design_templates:
                print(f"WARNING: row {row_number}: no template for design '{design}'.")
                continue
            for template in design_templates:
                rendered_source = render_html(template, ad, variable_columns, brand_tokens)
                for size in template.sizes:
                    base = f"{row_number:03d}_{slug(design)}_{label}"
                    html_path = TEMP_DIR / f"{base}_{size.name}.html"
                    png_path = OUTPUT_DIR / size.name / f"{base}.png"
                    html_path.write_text(rendered_source, encoding="utf-8")
                    capture(browser, html_path, png_path, size)
                    rendered += 1
                    manifest_row: dict[str, object] = {
                        "file": f"{size.name}/{base}.png",
                        "size": size.name,
                        "design": design,
                        "row": row_number,
                    }
                    manifest_row.update({column: ad.get(column, "") for column in variable_columns})
                    manifest.append(manifest_row)
        print(f"  row {row_number}/{len(selected_ads)} done")

    manifest_fields = ["file", "size", "design", "row", *variable_columns]
    write_csv(OUTPUT_DIR / "manifest.csv", manifest, manifest_fields)
    write_csv(OUTPUT_DIR / "canva_bulkcreate.csv", canva_rows, [*variable_columns, "designs"])
    copy_check = OUTPUT_DIR / "copy-check.csv"
    if copy_issues:
        write_csv(copy_check, copy_issues, ["row", "field", "length", "min", "max", "text"])
    else:
        copy_check.unlink(missing_ok=True)

    print(f"\nDone. {rendered} images created in 3-OUTPUT.")
    if copy_issues:
        print(f"Heads up: {len(copy_issues)} copy field(s) are outside the length guardrails.")
        print("See 3-OUTPUT/copy-check.csv for the exact rows.")
    if not args.no_open:
        open_output_folder()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Lion Marketing ad images from CSV copy.")
    parser.add_argument("--proof", action="store_true", help="Render only the first CSV row.")
    parser.add_argument("--preview-row", type=int, default=0, help="Render one row to .tmp/preview.png.")
    parser.add_argument("--preview-design", default="", help="Design name for preview mode.")
    parser.add_argument("--chrome-path", default="", help="Optional path to Chrome, Edge, or Chromium.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the output folder when done.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(generate(parse_args()))
