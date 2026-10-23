#!/usr/bin/env python3
"""Build the native fnOS package with the pinned, official fnpack CLI.

This script only stages files and produces local artifacts. It never installs
an app, connects to a NAS, loads drivers or accesses hardware interfaces.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tarfile
import tempfile
import urllib.request
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
LOCKFILE = ROOT / "packaging" / "fnpack-lock.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_tool() -> tuple[Path, dict]:
    lock = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    machine = platform.machine().lower()
    architecture = {"aarch64": "arm64", "x86_64": "amd64"}.get(machine, machine)
    host = f"{platform.system().lower()}-{architecture}"
    artifact = lock["artifacts"].get(host)
    if not artifact:
        raise RuntimeError(f"No verified official fnpack binary for build host {host}.")
    tool = ROOT / "packaging" / "tools" / f"fnpack-{lock['version']}-{host}"
    if not tool.is_file():
        tool.parent.mkdir(parents=True, exist_ok=True)
        proxy = os.environ.get("FANSTUDIO_BUILD_PROXY")
        if not proxy and platform.system() == "Darwin":
            proxy = "http://127.0.0.1:7890"
        handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
        opener = urllib.request.build_opener(*handlers)
        request = urllib.request.Request(artifact["url"], headers={"User-Agent": "FanStudio-FPK-Builder/1.0"})
        with opener.open(request, timeout=60) as response:
            content = response.read(16 * 1024 * 1024)
        temporary = tool.with_suffix(".download")
        temporary.write_bytes(content)
        if sha256(temporary) != artifact["sha256"]:
            temporary.unlink()
            raise RuntimeError("The downloaded fnpack SHA256 does not match the pinned official binary.")
        temporary.replace(tool)
    if sha256(tool) != artifact["sha256"]:
        raise RuntimeError(f"The local fnpack SHA256 does not match the lock file: {tool}")
    tool.chmod(0o755)
    return tool, {"version": lock["version"], "host": host, **artifact}


def read_manifest(path: Path) -> dict[str, str]:
    return {
        key.strip(): value.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "=" in line
        for key, value in [line.split("=", 1)]
    }


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError(f"Invalid PNG icon: {path}")
    return struct.unpack(">II", data[16:24])


class EntryAssets(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value and name in {"src", "href"} and value.startswith("/static/"):
                self.paths.append(unquote(urlsplit(value).path)[len("/static/"):])


def validate_source() -> dict[str, str]:
    # Development runs must keep credentials and recovery journals outside src/.
    if any(SOURCE.rglob("auth.json")):
        raise RuntimeError("A runtime auth.json exists under src; move credentials outside the package source.")
    for runtime in [SOURCE / "app/etc", SOURCE / "app/var"]:
        if runtime.exists():
            raise RuntimeError(f"Runtime data must not be included in the FPK: {runtime}")
    required = [
        "manifest", "config/privilege", "config/resource", "app/ui/config",
        "app/bin/server.py", "app/bin/hardware.py", "app/bin/controller.py", "app/bin/version.txt", "app/bin/static/index.html",
        "ICON.PNG", "ICON_256.PNG", "app/ui/images/icon_64.png", "app/ui/images/icon_256.png",
        *[f"cmd/{name}" for name in ["main", "install_init", "install_callback", "upgrade_init",
                                     "upgrade_callback", "uninstall_init", "uninstall_callback",
                                     "config_init", "config_callback"]],
        *[f"wizard/{name}" for name in ["install", "upgrade", "uninstall", "config"]],
    ]
    missing = [name for name in required if not (SOURCE / name).is_file()]
    if missing:
        raise RuntimeError("Package source is incomplete: " + ", ".join(missing))
    static = SOURCE / "app/bin/static"
    entry_assets = EntryAssets()
    entry_assets.feed((static / "index.html").read_text(encoding="utf-8"))
    for name in entry_assets.paths:
        if ".." in Path(name).parts or not (static / name).is_file():
            raise RuntimeError(f"The static entry references a missing or invalid packaged asset: {name}")
    manifest = read_manifest(SOURCE / "manifest")
    if manifest.get("appname") != "1-fan-control-studio":
        raise RuntimeError("The stable fnOS appname must remain 1-fan-control-studio.")
    if (SOURCE / "app/bin/version.txt").read_text(encoding="ascii").strip() != manifest.get("version"):
        raise RuntimeError("The displayed application version must match manifest.version.")
    if manifest.get("install_dep_apps") != "python312":
        raise RuntimeError("The fnOS Python 3.12 runtime dependency must be declared.")
    for name in ["config/privilege", "config/resource", "app/ui/config", "wizard/install",
                 "wizard/upgrade", "wizard/uninstall", "wizard/config"]:
        json.loads((SOURCE / name).read_text(encoding="utf-8"))
    launchers = json.loads((SOURCE / "app/ui/config").read_text(encoding="utf-8"))[".url"]
    launcher = launchers[manifest["desktop_applaunchname"]]
    if launcher["port"] != manifest["service_port"]:
        raise RuntimeError("The desktop launcher port differs from manifest.service_port.")
    for name, expected in [("ICON.PNG", (64, 64)), ("ICON_256.PNG", (256, 256)),
                           ("app/ui/images/icon_64.png", (64, 64)),
                           ("app/ui/images/icon_256.png", (256, 256))]:
        if png_size(SOURCE / name) != expected:
            raise RuntimeError(f"Wrong icon dimensions: {name}; expected {expected}.")
    for script in sorted((SOURCE / "cmd").iterdir()):
        if script.is_file():
            subprocess.run(["/bin/bash", "-n", str(script)], check=True)
    return manifest


def verify_archive(path: Path) -> dict:
    with tarfile.open(path, "r:*") as archive:
        names = {item.name.lstrip("./") for item in archive.getmembers()}
        for name in ["manifest", "app.tgz", "config/privilege", "config/resource", "cmd/main",
                     "ICON.PNG", "ICON_256.PNG"]:
            if name not in names:
                raise RuntimeError(f"The generated FPK is missing {name}.")
        app_entry = next(item for item in archive.getmembers() if item.name.lstrip("./") == "app.tgz")
        app_stream = archive.extractfile(app_entry)
        if app_stream is None:
            raise RuntimeError("The generated app.tgz payload is unreadable.")
        app_payload = app_stream.read()
        manifest_entry = next(item for item in archive.getmembers() if item.name.lstrip("./") == "manifest")
        manifest_stream = archive.extractfile(manifest_entry)
        if manifest_stream is None:
            raise RuntimeError("The generated manifest is unreadable.")
        package_manifest = {
            key.strip(): value.strip()
            for line in manifest_stream.read().decode("utf-8").splitlines() if "=" in line
            for key, value in [line.split("=", 1)]
        }
        app_checksum = hashlib.md5(app_payload).hexdigest()
        if package_manifest.get("checksum") != app_checksum:
            raise RuntimeError("The FPK manifest checksum does not match its app.tgz payload.")
        with tarfile.open(fileobj=io.BytesIO(app_payload), mode="r:gz") as application:
            app_names = {item.name.lstrip("./") for item in application.getmembers()}
            for name in ["bin/server.py", "bin/hardware.py", "bin/controller.py", "bin/version.txt", "bin/static/index.html", "ui/config"]:
                if name not in app_names:
                    raise RuntimeError(f"The generated app.tgz payload is missing {name}.")
    return {"fpk_members": len(names), "app_members": len(app_names), "app_tgz_md5": app_checksum}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    manifest = validate_source()
    tool, tool_info = get_tool()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = f"{manifest['appname']}-{manifest['version']}-{manifest['platform']}.fpk"
    with tempfile.TemporaryDirectory(prefix="fan-studio-fpk-") as temporary:
        stage = Path(temporary) / manifest["appname"]
        shutil.copytree(SOURCE, stage, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        license_file = ROOT / "LICENSE"
        if license_file.is_file():
            shutil.copy2(license_file, stage / "LICENSE")
        for script in (stage / "cmd").iterdir():
            if script.is_file():
                script.chmod(0o755)
        subprocess.run([str(tool), "build", "--directory", str(stage)], check=True, cwd=stage)
        packages = list(stage.glob("*.fpk"))
        if len(packages) != 1:
            raise RuntimeError(f"Expected one official fnpack output, found {len(packages)}.")
        archive_info = verify_archive(packages[0])
        result = output_dir / output_name
        shutil.copy2(packages[0], result)
    checksum = sha256(result)
    (output_dir / f"{output_name}.sha256").write_text(f"{checksum}  {output_name}\n", encoding="ascii")
    report = {
        "appname": manifest["appname"], "version": manifest["version"],
        "platform": manifest["platform"], "service_port": int(manifest["service_port"]),
        "runtime": manifest["install_dep_apps"], "size_bytes": result.stat().st_size,
        "sha256": checksum, "official_fnpack": tool_info,
        "checks": ["source completeness", "JSON syntax", "shell syntax", "icon dimensions",
                   "static entry assets", "launcher consistency", "official fnpack build", "FPK payload inspection", "app.tgz checksum"],
        "archive": archive_info, "nas_installation_tested": False,
    }
    (output_dir / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built: {result}")
    print(f"SHA256: {checksum}")


if __name__ == "__main__":
    main()
