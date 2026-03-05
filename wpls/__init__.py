"""
Lists the wallpaper file path currently showing on each desktop/space on macOS.

The AppleScript that queries System Events lives in wpls.applescript in the
same directory as this file.

Note: If your wallpaper folder contains symlinks (e.g. a flat directory of
symlinks into a deeper hierarchy), macOS resolves them — lsof will show the
real target path, not the symlink path. resolve_shuffle_targets() resolves
symlinks the same way so the two sides always agree.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from wpls.list import WALLPAPER_IMAGE_PROCESS, list_wallpapers

OPEN_ARGS = ("open", "-a")
OPEN_DEFAULT_APP = "Preview"


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


def next_wallpaper() -> None:
    """
    Immediately cycle to the next shuffle wallpaper on all desktops.

    Killing WallpaperImageExtension causes macOS to restart it instantly and
    pick a fresh image for each shuffle desktop, equivalent to manually
    clicking "Change Wallpaper" in System Settings.
    """
    subprocess.run(  # noqa: S603
        ("killall", WALLPAPER_IMAGE_PROCESS),
        check=False,  # non-zero exit if process wasn't running; that's fine
    )


def open_wallpapers(paths: tuple[str, ...], app: str) -> None:
    """Open the listed wallpaper image paths in the specified app."""
    paths = tuple(path for path in paths if Path(path).is_file())
    subprocess.run(  # noqa: S603
        (*OPEN_ARGS, app, *paths),
        check=True,
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(
        description="List, open, or cycle wallpapers on macOS desktops."
    )
    parser.add_argument(
        "-n",
        "--next",
        action="store_true",
        help="Immediately cycle to the next shuffle wallpaper on all desktops.",
    )
    parser.add_argument(
        "-o",
        "--open",
        action="store_true",
        dest="open_images",
        help=("Open all current wallpaper images in the app specified by -a"),
    )
    parser.add_argument(
        "-a",
        "--app",
        default=OPEN_DEFAULT_APP,
        metavar="APP",
        help=f"App to use with --open (default: {OPEN_DEFAULT_APP}).",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Print diagnostic info.",
    )

    return parser.parse_args()


def main() -> None:
    """Run everything."""
    require_macos()
    args = parse_args()

    if args.next:
        next_wallpaper()

    paths = list_wallpapers(args)

    if args.open_images:
        open_wallpapers(paths, args.app)


if __name__ == "__main__":
    main()
