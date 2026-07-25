#!/usr/bin/env python3
"""Local, dependency-free web app for the Lion Marketing Ad Generator."""

from __future__ import annotations

import argparse
import base64
import binascii
import csv
import io
import json
import mimetypes
import platform
import re
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlopen

from ad_generator import (
    COPY_DIR,
    OUTPUT_DIR,
    ROOT,
    TEMP_DIR,
    TEMPLATE_DIR,
    discover_templates,
    find_browser,
    read_csv,
    write_csv,
)


APP_DIR = ROOT / "app"
ASSET_DIR = ROOT / "assets"
MAX_UPLOAD = 8 * 1024 * 1024
SAFE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
SAFE_TEMPLATE_EXTENSIONS = {".html", ".htm"}


class JobState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.data: dict[str, object] = {
            "status": "idle",
            "progress": 0,
            "message": "Ready to generate.",
            "logs": [],
            "started_at": None,
            "finished_at": None,
        }

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            return json.loads(json.dumps(self.data))

    def update(self, **values: object) -> None:
        with self.lock:
            self.data.update(values)

    def log(self, line: str) -> None:
        with self.lock:
            logs = list(self.data.get("logs", []))
            logs.append(line)
            self.data["logs"] = logs[-40:]


JOB = JobState()


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def safe_path(base: Path, relative: str) -> Path | None:
    try:
        candidate = (base / unquote(relative)).resolve()
        candidate.relative_to(base.resolve())
        return candidate
    except (ValueError, OSError):
        return None


def template_payload() -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for template in discover_templates():
        item = grouped.setdefault(template.design, {
            "design": template.design,
            "sizes": [],
            "files": [],
        })
        item["files"].append(template.path.name)  # type: ignore[union-attr]
        for size in template.sizes:
            if size.name not in item["sizes"]:  # type: ignore[operator]
                item["sizes"].append(size.name)  # type: ignore[union-attr]
    return list(grouped.values())


def output_payload() -> list[dict[str, object]]:
    rows = read_csv(OUTPUT_DIR / "manifest.csv")
    outputs: list[dict[str, object]] = []
    for row in rows:
        relative = row.get("file", "")
        file_path = safe_path(OUTPUT_DIR, relative)
        if not file_path or not file_path.is_file():
            continue
        item: dict[str, object] = dict(row)
        item["url"] = "/output/" + quote(relative, safe="/")
        item["modified"] = int(file_path.stat().st_mtime)
        outputs.append(item)
    return outputs


def project_payload() -> dict[str, object]:
    ads = read_csv(COPY_DIR / "ads.csv")
    brand = read_csv(COPY_DIR / "brand.csv")
    limits = read_csv(COPY_DIR / "limits.csv")
    columns = list(ads[0].keys()) if ads else [
        "designs", "name", "eyebrow", "hook", "body", "cta", "stat", "stat_label"
    ]
    browser_ready = True
    browser_message = "Chrome is ready."
    try:
        find_browser()
    except SystemExit:
        browser_ready = False
        browser_message = "Install Chrome, Edge, or Chromium before generating."
    brand_map = {row.get("token", ""): row.get("value", "") for row in brand}
    logo_file = brand_map.get("LOGO_FILE", "")
    logo_url = ""
    if logo_file:
        logo_path = safe_path(ROOT, logo_file)
        if logo_path and logo_path.is_file():
            logo_url = "/project-file/" + quote(logo_file, safe="/")
    return {
        "ads": ads,
        "columns": columns,
        "brand": brand,
        "limits": limits,
        "templates": template_payload(),
        "outputs": output_payload(),
        "job": JOB.snapshot(),
        "browser": {"ready": browser_ready, "message": browser_message},
        "logo_url": logo_url,
    }


def decode_upload(payload: dict[str, object], extensions: set[str]) -> tuple[str, bytes]:
    name = Path(str(payload.get("name", ""))).name
    extension = Path(name).suffix.lower()
    if not name or extension not in extensions:
        raise ValueError("Unsupported file type.")
    encoded = str(payload.get("data", ""))
    if "," in encoded:
        encoded = encoded.split(",", 1)[1]
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("The uploaded file could not be read.") from error
    if not content or len(content) > MAX_UPLOAD:
        raise ValueError("File must be smaller than 8 MB.")
    return name, content


def set_brand_value(token: str, value: str) -> list[dict[str, str]]:
    rows = read_csv(COPY_DIR / "brand.csv")
    found = False
    for row in rows:
        if row.get("token", "").upper() == token.upper():
            row["value"] = value
            found = True
    if not found:
        rows.append({"token": token, "value": value})
    write_csv(COPY_DIR / "brand.csv", rows, ["token", "value"])
    return rows


def run_generation(proof: bool) -> None:
    ads = read_csv(COPY_DIR / "ads.csv")
    selected_ads = ads[:1] if proof else ads
    templates = discover_templates()
    all_designs = list(dict.fromkeys(template.design for template in templates))
    total_images = 0
    for ad in selected_ads:
        selection = ad.get("designs", "all").strip() or "all"
        designs = all_designs if selection.lower() == "all" else [
            item.strip() for item in selection.split(",") if item.strip()
        ]
        total_images += sum(
            len(template.sizes)
            for template in templates
            if template.design.lower() in {design.lower() for design in designs}
        )
    total_images = max(1, total_images)
    JOB.update(
        status="running",
        progress=2,
        message="Preparing the renderer…",
        logs=[],
        started_at=int(time.time()),
        finished_at=None,
    )
    command = [sys.executable, "-u", str(ROOT / "ad_generator.py"), "--no-open"]
    if proof:
        command.append("--proof")
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            JOB.log(line)
            image_match = re.search(r"image\s+(\d+)\s+done", line, re.IGNORECASE)
            match = re.search(r"row\s+(\d+)/(\d+)\s+done", line, re.IGNORECASE)
            if image_match:
                current_image = int(image_match.group(1))
                JOB.update(
                    progress=min(96, int(current_image / total_images * 94) + 2),
                    message=f"Rendered image {current_image} of {total_images}.",
                )
            elif match:
                current = int(match.group(1))
                JOB.update(message=f"Finished copy variation {current} of {len(selected_ads)}.")
            elif line.startswith("Browser"):
                JOB.update(message="Chrome is rendering your designs…")
        code = process.wait()
        if code == 0:
            count = len(output_payload())
            JOB.update(
                status="complete",
                progress=100,
                message=f"Finished — {count} ad images are ready.",
                finished_at=int(time.time()),
            )
        else:
            logs = JOB.snapshot().get("logs", [])
            message = str(logs[-1]) if logs else "Generation failed."
            JOB.update(status="error", progress=0, message=message, finished_at=int(time.time()))
    except Exception as error:  # noqa: BLE001 - surfaced to the local user
        JOB.update(status="error", progress=0, message=str(error), finished_at=int(time.time()))


class AppHandler(BaseHTTPRequestHandler):
    server_version = "LionAdApp/1.0"

    def log_message(self, format: str, *args: object) -> None:
        if getattr(self.server, "quiet", False):
            return
        super().log_message(format, *args)

    def send_bytes(
        self,
        content: bytes,
        content_type: str,
        status: int = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        self.send_bytes(json_bytes(payload), "application/json; charset=utf-8", status)

    def send_file(self, path: Path, download_name: str = "") -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        headers = {}
        if download_name:
            headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
        self.send_bytes(path.read_bytes(), content_type, headers=headers)

    def read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_UPLOAD + 1024 * 1024:
            raise ValueError("Invalid request size.")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected an object.")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/":
            self.send_file(APP_DIR / "index.html")
        elif route.startswith("/static/"):
            path = safe_path(APP_DIR, route.removeprefix("/static/"))
            self.send_file(path) if path else self.send_error(HTTPStatus.BAD_REQUEST)
        elif route == "/api/project":
            self.send_json(project_payload())
        elif route == "/api/job":
            self.send_json(JOB.snapshot())
        elif route == "/api/outputs":
            self.send_json({"outputs": output_payload()})
        elif route == "/api/outputs.zip":
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in OUTPUT_DIR.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(OUTPUT_DIR))
            self.send_bytes(
                buffer.getvalue(),
                "application/zip",
                headers={"Content-Disposition": 'attachment; filename="lion-marketing-ads.zip"'},
            )
        elif route.startswith("/output/"):
            path = safe_path(OUTPUT_DIR, route.removeprefix("/output/"))
            self.send_file(path) if path else self.send_error(HTTPStatus.BAD_REQUEST)
        elif route.startswith("/project-file/"):
            path = safe_path(ROOT, route.removeprefix("/project-file/"))
            self.send_file(path) if path else self.send_error(HTTPStatus.BAD_REQUEST)
        elif route == "/preview.png":
            self.send_file(TEMP_DIR / "preview.png")
        elif route == "/download/ads.csv":
            self.send_file(COPY_DIR / "ads.csv", "lion-marketing-ad-copy.csv")
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        try:
            payload = self.read_json()
            if route == "/api/save-ads":
                rows = payload.get("rows", [])
                columns = payload.get("columns", [])
                if not isinstance(rows, list) or not isinstance(columns, list) or not columns:
                    raise ValueError("Copy rows or columns are missing.")
                safe_columns = [str(column).strip() for column in columns if str(column).strip()]
                safe_rows = [
                    {column: str(row.get(column, "")) for column in safe_columns}
                    for row in rows if isinstance(row, dict)
                ]
                write_csv(COPY_DIR / "ads.csv", safe_rows, safe_columns)
                self.send_json({"ok": True, "rows": safe_rows, "columns": safe_columns})
            elif route == "/api/save-brand":
                rows = payload.get("rows", [])
                if not isinstance(rows, list):
                    raise ValueError("Brand settings are missing.")
                safe_rows = [
                    {"token": str(row.get("token", "")), "value": str(row.get("value", ""))}
                    for row in rows if isinstance(row, dict) and row.get("token")
                ]
                write_csv(COPY_DIR / "brand.csv", safe_rows, ["token", "value"])
                self.send_json({"ok": True, "rows": safe_rows})
            elif route == "/api/save-limits":
                rows = payload.get("rows", [])
                if not isinstance(rows, list):
                    raise ValueError("Copy limits are missing.")
                safe_rows = [
                    {
                        "field": str(row.get("field", "")),
                        "min": str(row.get("min", "0")),
                        "max": str(row.get("max", "0")),
                    }
                    for row in rows if isinstance(row, dict) and row.get("field")
                ]
                write_csv(COPY_DIR / "limits.csv", safe_rows, ["field", "min", "max"])
                self.send_json({"ok": True, "rows": safe_rows})
            elif route == "/api/upload-logo":
                name, content = decode_upload(payload, SAFE_IMAGE_EXTENSIONS)
                ASSET_DIR.mkdir(parents=True, exist_ok=True)
                destination = ASSET_DIR / name
                destination.write_bytes(content)
                rows = set_brand_value("LOGO_FILE", f"assets/{name}")
                self.send_json({
                    "ok": True,
                    "brand": rows,
                    "logo_url": "/project-file/" + quote(f"assets/{name}", safe="/"),
                })
            elif route == "/api/upload-template":
                name, content = decode_upload(payload, SAFE_TEMPLATE_EXTENSIONS)
                if b"{{" not in content or b"}}" not in content:
                    raise ValueError("Template needs at least one {{PLACEHOLDER}}.")
                TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
                (TEMPLATE_DIR / name).write_bytes(content)
                self.send_json({"ok": True, "templates": template_payload()})
            elif route == "/api/import-ads":
                _, content = decode_upload(payload, {".csv"})
                text = content.decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(text))
                if not reader.fieldnames:
                    raise ValueError("CSV needs a header row.")
                columns = [str(name) for name in reader.fieldnames]
                rows = [
                    {column: str(row.get(column, "") or "") for column in columns}
                    for row in reader
                ]
                if not rows:
                    raise ValueError("CSV needs at least one copy row.")
                write_csv(COPY_DIR / "ads.csv", rows, columns)
                self.send_json({"ok": True, "rows": rows, "columns": columns})
            elif route == "/api/delete-template":
                name = Path(str(payload.get("name", ""))).name
                path = safe_path(TEMPLATE_DIR, name)
                if not path or not path.is_file() or path.suffix.lower() not in SAFE_TEMPLATE_EXTENSIONS:
                    raise ValueError("Template file was not found.")
                path.unlink()
                self.send_json({"ok": True, "templates": template_payload()})
            elif route == "/api/preview":
                row = max(1, int(payload.get("row", 1)))
                design = str(payload.get("design", ""))
                command = [
                    sys.executable,
                    "-u",
                    str(ROOT / "ad_generator.py"),
                    "--preview-row",
                    str(row),
                    "--preview-design",
                    design,
                    "--no-open",
                ]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45)
                if result.returncode != 0:
                    raise RuntimeError((result.stderr or result.stdout).strip() or "Preview failed.")
                self.send_json({"ok": True, "url": f"/preview.png?t={int(time.time())}"})
            elif route == "/api/generate":
                if JOB.snapshot().get("status") == "running":
                    self.send_json({"ok": False, "message": "Generation is already running."}, HTTPStatus.CONFLICT)
                    return
                proof = bool(payload.get("proof", False))
                JOB.update(
                    status="running",
                    progress=1,
                    message="Preparing the renderer…",
                    logs=[],
                    started_at=int(time.time()),
                    finished_at=None,
                )
                thread = threading.Thread(target=run_generation, args=(proof,), daemon=True)
                thread.start()
                self.send_json({"ok": True, "job": JOB.snapshot()})
            elif route == "/api/open-folder":
                target = str(payload.get("target", "outputs"))
                folder = OUTPUT_DIR if target == "outputs" else TEMPLATE_DIR
                folder.mkdir(parents=True, exist_ok=True)
                if platform.system() == "Darwin":
                    subprocess.Popen(["open", str(folder)])
                elif platform.system() == "Windows":
                    os.startfile(folder)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", str(folder)])
                self.send_json({"ok": True})
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self.send_json({"ok": False, "message": str(error)}, HTTPStatus.BAD_REQUEST)
        except subprocess.TimeoutExpired:
            self.send_json({"ok": False, "message": "The preview took too long. Try again."}, HTTPStatus.GATEWAY_TIMEOUT)
        except Exception as error:  # noqa: BLE001 - local app should surface actionable errors
            self.send_json({"ok": False, "message": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def serve(port: int, open_browser: bool, quiet: bool) -> None:
    requested_url = f"http://127.0.0.1:{port}"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    except OSError:
        if port:
            try:
                with urlopen(f"{requested_url}/api/project", timeout=1) as response:
                    payload = json.load(response)
                if isinstance(payload, dict) and "ads" in payload and "templates" in payload:
                    print(f"\nLion Marketing Ad Generator is already running at:\n  {requested_url}\n")
                    if open_browser:
                        webbrowser.open(requested_url)
                    return
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        raise
    server.quiet = quiet  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"\nLion Marketing Ad Generator is running at:\n  {url}\n")
    print("Keep this window open while you use the app. Press Control-C to stop it.\n")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nClosing Lion Marketing Ad Generator.")
    finally:
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Lion Marketing Ad Generator app.")
    parser.add_argument("--port", type=int, default=8765, help="Local port. Use 0 to choose automatically.")
    parser.add_argument("--open", action="store_true", help="Open the app in the default browser.")
    parser.add_argument("--quiet", action="store_true", help="Hide request logs.")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    serve(arguments.port, arguments.open, arguments.quiet)
