"""Self update from GitHub releases.

Amethyst ships as a single exe, so updating means: ask the GitHub API for the
latest release, compare versions, download the new exe next to the running
one, and swap them on restart. Windows will not let a running exe be
overwritten, but it does allow renaming it, and that is enough:

    Amethyst.exe        ->  Amethyst.exe.old     (the running program)
    Amethyst.new.exe    ->  Amethyst.exe         (the downloaded one)

The leftover .old file is deleted on the next start.

Only the standard library is used, so this adds no dependency.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import APP_NAME, REPO, VERSION

log = logging.getLogger(__name__)

API = "https://api.github.com/repos/{repo}/releases/latest"
TIMEOUT = 12
USER_AGENT = f"{APP_NAME}/{VERSION}"


@dataclass
class Release:
    version: str
    tag: str
    name: str
    notes: str
    url: str            # download url of the exe
    size: int
    page: str           # human readable release page

    @property
    def size_mb(self) -> float:
        return self.size / (1024 * 1024)


def parse_version(text: str) -> tuple[int, ...]:
    """'v1.2.3' and '1.2.3' both become (1, 2, 3). Unknown parts count as 0."""
    cleaned = text.strip().lstrip("vV").split("+")[0].split("-")[0]
    parts: list[int] = []
    for chunk in cleaned.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(candidate: str, current: str = VERSION) -> bool:
    return parse_version(candidate) > parse_version(current)


def _request(url: str):
    return urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    })


def check(repo: str = REPO, current: str = VERSION) -> Release | None:
    """Return the latest release when it is newer than what is running."""
    try:
        with urllib.request.urlopen(_request(API.format(repo=repo)), timeout=TIMEOUT) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        log.info("Update check failed: %s", exc)
        return None

    if data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name", ""))
    if not tag or not is_newer(tag, current):
        return None

    asset = None
    for candidate in data.get("assets", []):
        name = str(candidate.get("name", ""))
        if name.lower().endswith(".exe"):
            asset = candidate
            break
    if asset is None:
        log.info("Release %s carries no exe", tag)
        return None

    return Release(
        version=tag.lstrip("vV"),
        tag=tag,
        name=str(data.get("name") or tag),
        notes=str(data.get("body") or ""),
        url=str(asset.get("browser_download_url", "")),
        size=int(asset.get("size", 0)),
        page=str(data.get("html_url", "")),
    )


def running_exe() -> Path | None:
    """Path of the packaged exe, or None when running from source."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None


def download(release: Release, progress=None) -> Path:
    """Fetch the new exe into the temp folder and return its path."""
    target = Path(tempfile.gettempdir()) / f"{APP_NAME}-{release.version}.exe"
    with urllib.request.urlopen(_request(release.url), timeout=60) as response:
        total = int(response.headers.get("Content-Length") or release.size or 0)
        done = 0
        with open(target, "wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
    return target


def install_and_restart(new_exe: Path) -> bool:
    """Swap the running exe for the downloaded one and start it again."""
    current = running_exe()
    if current is None:
        log.warning("Not running as a packaged exe, nothing to swap")
        return False

    backup = current.with_suffix(current.suffix + ".old")
    try:
        if backup.exists():
            backup.unlink()
        os.rename(current, backup)          # allowed while the file is in use
        shutil.copy2(new_exe, current)
    except OSError as exc:
        log.error("Could not swap the exe: %s", exc)
        if not current.exists() and backup.exists():
            os.rename(backup, current)      # put the old one back
        return False

    try:
        subprocess.Popen([str(current)], close_fds=True)
    except OSError as exc:
        log.error("Could not start the new version: %s", exc)
        return False
    return True


def cleanup_old() -> None:
    """Remove the previous exe that was left behind by an update."""
    current = running_exe()
    if current is None:
        return
    backup = current.with_suffix(current.suffix + ".old")
    try:
        if backup.exists():
            backup.unlink()
            log.info("Removed the previous version")
    except OSError:
        pass                                 # still locked, try again next start
