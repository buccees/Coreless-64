"""Launch the Tk-rendered desktop for one persistent Coreless-64 machine image.

Run from the repository root:
    python reference/run_desktop.py /path/to/coreless-machine.json

Launching the host is the power-available event for this software reference:
the canonical CorelessSystem restores the selected image and automatically
boots or resumes its machine/OS lifecycle before attaching the desktop renderer.
The machine and GPIO remain virtual; physical power sensing and bus enumeration
are not implemented by this launcher.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

from desktop_host import TkDesktopHost
from system import CorelessSystem


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Boot/resume a persistent Coreless-64 image and open its desktop"
    )
    parser.add_argument(
        "image",
        type=Path,
        help="existing or new Coreless persistent machine image (state is stored here)",
    )
    parser.add_argument("--memory", type=int, default=1 << 20,
                        help="Coreless RAM size in bytes; must match an existing image")
    parser.add_argument("--cpus", type=int, default=1,
                        help="Coreless CPU count; must match an existing image")
    args = parser.parse_args(argv)

    # One canonical runtime owns CPU, motherboard, storage, OS and desktop.
    # Requiring an explicit image avoids accidentally launching an unrelated
    # in-memory machine and makes the persistence target visible to the user.
    system = CorelessSystem(
        memory_size=args.memory,
        cpu_count=args.cpus,
        storage_path=args.image,
    )
    system.boot()
    try:
        TkDesktopHost(system.os.desktop).run()
    finally:
        # Persist the current running state without marking the machine off;
        # a subsequent launch can resume this same image.
        system.machine.save_state()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
