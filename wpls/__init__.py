#!/usr/bin/env python3
"""
Lists the wallpaper file path currently showing on each desktop/space on macOS.

Strategy per desktop:
  - Fixed image  System Events returns the exact path directly.
  - Shuffle mode System Events returns a folder path.
                   The actual currently displayed file is found via lsof on
                   WallpaperImageExtension, which memory-maps every image it
                   is actively rendering. Results are assigned to shuffle
                   desktops in order.

The AppleScript that queries System Events lives in wpls.applescript in the
same directory as this file.

Note: If your wallpaper folder contains symlinks (e.g. a flat directory of
symlinks into a deeper hierarchy), macOS resolves them — lsof will show the
real target path, not the symlink path.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

import psutil
from OSAKit import (
    OSALanguage,  # pyright: ignore[reportAttributeAccessIssue], # ty: ignore[unresolved-import]
    OSAScript,  # pyright: ignore[reportAttributeAccessIssue], # ty: ignore[unresolved-import]
)

LSOF_ARGS = ("lsof", "-F", "n", "-p")
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

WALLPAPER_IMAGE_PROCESS = "WallpaperImageExtension"

APPLESCRIPT_FILE = Path(__file__).parent / "wpls.applescript"


def require_macos() -> None:
    """Exit with a friendly error if not running on macOS."""
    if platform.system() != "Darwin":
        print(
            (
                f"Error: this script requires macOS (detected: {platform.system()}).\n"
                "Wallpaper state is only accessible via macOS-specific APIs."
            ),
            file=sys.stderr,
        )
        sys.exit(1)


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


def _print_lsof_output(images):
    print(
        f"[debug] lsof found {len(images)} open image(s) in {WALLPAPER_IMAGE_PROCESS}:"
    )
    for p in images:
        print(f"  {p}")
    print()


def get_open_wallpaper_images(*, debug: bool = False) -> tuple[str, ...]:
    """
    Return mmapped paths from WallpaperImageExtension process.

    These are the images currently on screen. The process
    resolves symlinks, so paths reflect real targets.
    """
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

    # psutil cannot see memory-mapped files on macOS, so we use lsof directly.
    result = subprocess.run(  # noqa: S603
        [*LSOF_ARGS, pid], check=False, capture_output=True, text=True
    )

    images: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("n"):
            continue
        path = line[1:]
        if Path(path).suffix.lower() in IMAGE_SUFFIXES:
            images.append(path)

    if debug:
        _print_lsof_output(images)
    return tuple(images)


def get_desktop_wallpapers(*, debug: bool = False) -> list[tuple[str, str]]:
    """
    Return a list of (desktop_label, wallpaper_path) for every desktop/space.

    desktop_label is a human-readable string like "Desktop 1".
    wallpaper_path is the resolved absolute path to the currently displayed image.
    """
    se_paths = get_system_events_paths()
    if not se_paths:
        reason = "System Events returned no desktops."
        raise RuntimeError(reason)

    shuffle_indices = tuple(i for i, p in enumerate(se_paths) if Path(p).is_dir())
    open_images = get_open_wallpaper_images(debug=debug) if shuffle_indices else ()

    results: list[tuple[str, str]] = []
    shuffle_image_iter = iter(open_images)

    for i, se_path in enumerate(se_paths):
        label = f"Desktop {i + 1}"
        if i not in shuffle_indices:
            results.append((label, se_path))
        else:
            image = next(shuffle_image_iter, None)
            if image:
                results.append((label, image))
            else:
                results.append(
                    (label, f"{se_path}  ← shuffle folder; no open image found")
                )

    return results


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(
        description="List current wallpaper paths per desktop on macOS."
    )
    parser.add_argument("--debug", action="store_true", help="Print diagnostic info.")
    return parser.parse_args()


def main() -> None:
    """Run everything."""
    require_macos()
    args = parse_args()

    results = get_desktop_wallpapers(debug=args.debug)
    col = max(len(label) for label, _ in results) + 2
    for label, path in results:
        print(f"{label:<{col}} {path}")


if __name__ == "__main__":
    main()
