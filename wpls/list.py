"""List Wallpaper functions."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

import psutil
from OSAKit import (
    OSALanguage,  # pyright: ignore[reportAttributeAccessIssue], # ty: ignore[unresolved-import]
    OSAScript,  # pyright: ignore[reportAttributeAccessIssue], # ty: ignore[unresolved-import]
)

if TYPE_CHECKING:
    import argparse

APPLESCRIPT_FILE = Path(__file__).parent / "wpls.applescript"
IMAGE_SUFFIXES = frozenset(
    {
        ".avif",
        ".bmp",
        ".gif",
        ".heic",
        ".heif",
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)
LABEL_COL_LEN = len("Desktop ") + 2
LSOF_ARGS = ("lsof", "-F", "n", "-p")
WALLPAPER_IMAGE_PROCESS = "WallpaperImageExtension"


def get_system_events_paths() -> tuple[str, ...]:
    """System Events — returns exact path for fixed images, folder for shuffle."""
    source = APPLESCRIPT_FILE.read_text(encoding="utf-8")
    script = OSAScript.alloc().initWithSource_language_(
        source,
        OSALanguage.languageForName_("AppleScript"),
    )
    result, error = script.executeAndReturnError_(None)
    if error:
        reason = f"AppleScript error: {error}"
        raise RuntimeError(reason)
    return tuple(
        line.strip() for line in result.stringValue().splitlines() if line.strip()
    )


def _lsof_image_paths(pid: str) -> tuple[str, ...]:
    """Return all image file paths open in the given process, in lsof order."""
    result = subprocess.run(  # noqa: S603
        (*LSOF_ARGS, pid), check=False, capture_output=True, text=True
    )
    return tuple(
        line[1:]
        for line in result.stdout.splitlines()
        if line.startswith("n") and Path(line[1:]).suffix.lower() in IMAGE_SUFFIXES
    )


def _print_lsof_debug(
    all_images: tuple[str, ...],
    active_images: tuple[str, ...],
    n_desktops: int,
) -> None:
    active_set = set(active_images)
    debug_str = (
        f"[debug] lsof found {len(all_images)} open image(s) in"
        f" {WALLPAPER_IMAGE_PROCESS} (selected {n_desktops}):"
    )
    print(debug_str)
    for p in all_images:
        tag = "active" if p in active_set else "stale "
        print(f"  [{tag}]  {p}")
    print()


def get_open_wallpaper_images(
    n_desktops: int,
    *,
    debug: bool = False,
) -> tuple[str, ...]:
    """Return the paths of the N images currently shown on lsof output."""
    if not n_desktops:
        return ()

    procs = [
        p
        for p in psutil.process_iter(["name", "pid"])
        if p.info["name"] == WALLPAPER_IMAGE_PROCESS
    ]

    if not procs:
        if debug:
            print(f"[debug] {WALLPAPER_IMAGE_PROCESS} not running")
        return ()

    pid = str(procs[0].info["pid"])
    all_images = _lsof_image_paths(pid)

    active = all_images[-n_desktops:] if n_desktops else ()

    if debug:
        _print_lsof_debug(all_images, active, n_desktops)

    return active


def get_desktop_wallpapers(*, debug: bool = False) -> MappingProxyType[str, str]:
    """
    Return a list of (desktop_label, wallpaper_path) for every desktop/space.

    desktop_label is a human-readable string like "Desktop 1".
    wallpaper_path is the resolved absolute path to the currently displayed image.
    """
    se_paths = get_system_events_paths()
    if not se_paths:
        reason = "System Events returned no desktops."
        raise RuntimeError(reason)

    open_images = get_open_wallpaper_images(len(se_paths), debug=debug)

    result_map: dict[str, str] = {}
    shuffle_image_iter = iter(open_images)

    for i, se_path in enumerate(se_paths):
        label = f"Desktop {i + 1}"
        if Path(se_path).is_file():
            value = se_path
        elif image := next(shuffle_image_iter, None):
            value = image
        else:
            value = f"{se_path}  <- shuffle folder; no open image found"
        result_map[label] = value

    return MappingProxyType(result_map)


def list_wallpapers(args: argparse.Namespace) -> tuple[str, ...]:
    """List active wallpapers."""
    result_map = get_desktop_wallpapers(debug=args.debug)
    for label, path in result_map.items():
        print(f"{label:<{LABEL_COL_LEN}} {path}")
    return tuple(result_map.values())
