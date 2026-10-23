#!/usr/bin/env python3
"""Interactive console for the Coreless machine on its own bootable carrier."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
sys.path.insert(0, str(REFERENCE))

from system import CorelessSystem


def main() -> int:
    image = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/lib/coreless/coreless.img")
    image.parent.mkdir(parents=True, exist_ok=True)
    system = CorelessSystem(storage_path=image)
    try:
        system.boot()
        print("\nCORELESS-64 MACHINE CONSOLE")
        print(f"Persistent machine image: {image}")
        print("Commands: :status  :checkpoint [name]  :help  :shutdown")
        print("Other input is sent to the Coreless operating-system shell.\n")
        while True:
            try:
                line = input("coreless> ").strip()
            except EOFError:
                line = ":shutdown"
            if not line:
                continue
            if line == ":help":
                print(":status                 Show machine and boot status")
                print(":checkpoint [name]      Save a named machine checkpoint")
                print(":shutdown               Persist state and power down cleanly")
                print("Any other line is executed by the Coreless OS shell")
                continue
            if line == ":status":
                print(system.status())
                continue
            if line.startswith(":checkpoint"):
                _, _, name = line.partition(" ")
                try:
                    digest = system.checkpoint(name.strip() or "manual")
                    print(f"Checkpoint saved: {name.strip() or 'manual'} ({digest})")
                except Exception as exc:
                    print(f"Checkpoint failed: {exc}")
                continue
            if line == ":shutdown":
                break
            try:
                result = system.command(line)
                if result is not None:
                    print(result)
            except Exception as exc:
                print(f"Coreless command failed: {exc}")
            finally:
                system.machine.save_state()
        system.shutdown()
        print("Coreless machine state persisted. Safe to power off.")
        return 0
    except KeyboardInterrupt:
        system.shutdown()
        print("\nCoreless machine state persisted.")
        return 130
    except Exception as exc:
        print(f"Coreless machine failed: {exc}", file=sys.stderr)
        try:
            system.machine.save_state()
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
