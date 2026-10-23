#!/usr/bin/env python3
"""Run a Coreless-64 machine directly from a persistent machine image.

The image is the authoritative machine-state carrier. This launcher only
provides the reference digital execution engine and external command line;
it does not move computation into the host.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

from system import CorelessSystem


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a persistent Coreless-64 machine image")
    parser.add_argument("image", type=Path, help="Coreless persistent image path")
    parser.add_argument("--memory", type=int, default=1 << 20, help="Coreless RAM size in bytes")
    parser.add_argument("--cpus", type=int, default=1, help="Coreless CPU count")
    parser.add_argument("--steps", type=int, default=100000, help="Maximum execution steps")
    parser.add_argument("--command", action="append", default=[], help="Coreless shell command to run")
    parser.add_argument("--status", action="store_true", help="Print machine status after resume")
    parser.add_argument("--shutdown", action="store_true", help="Persist an off state before exit")
    parser.add_argument("--operator", action="store_true", help="Serve the browser operator display from this same running machine process")
    parser.add_argument("--operator-host", default="127.0.0.1", help="operator bind address; use 0.0.0.0 for LAN access")
    parser.add_argument("--operator-port", type=int, default=8443, help="operator HTTPS port")
    parser.add_argument("--operator-cert", help="operator TLS certificate PEM path (or CORELESS_TLS_CERT)")
    parser.add_argument("--operator-key", help="operator TLS private key PEM path (or CORELESS_TLS_KEY)")
    args = parser.parse_args()

    # Reject invalid operator configuration before touching the persistent image.
    operator_password = ""
    operator_cert = None
    operator_key = None
    if args.operator:
        import os
        operator_password = os.environ.get("CORELESS_OPERATOR_PASSWORD", "")
        operator_cert = args.operator_cert or os.environ.get("CORELESS_TLS_CERT")
        operator_key = args.operator_key or os.environ.get("CORELESS_TLS_KEY")
        if len(operator_password) < 16:
            parser.error("set CORELESS_OPERATOR_PASSWORD to a unique password of at least 16 characters")
        if not operator_cert or not operator_key:
            parser.error("operator HTTPS requires --operator-cert/--operator-key or CORELESS_TLS_CERT/CORELESS_TLS_KEY")
        if not 1 <= args.operator_port <= 65535:
            parser.error("--operator-port must be between 1 and 65535")
        operator_cert_path = Path(operator_cert).expanduser()
        operator_key_path = Path(operator_key).expanduser()
        if not operator_cert_path.is_file():
            parser.error(f"operator TLS certificate does not exist: {operator_cert_path}")
        if not operator_key_path.is_file():
            parser.error(f"operator TLS private key does not exist: {operator_key_path}")
        operator_cert = str(operator_cert_path)
        operator_key = str(operator_key_path)

    system = CorelessSystem(
        memory_size=args.memory,
        cpu_count=args.cpus,
        storage_path=args.image,
    )
    system.boot()
    for command in args.command:
        print(system.command(command))
    if args.status:
        print(system.status())
    if args.operator:
        from local_operator_server import serve_lan
        try:
            serve_lan(system, host=args.operator_host, port=args.operator_port,
                      cert_path=operator_cert, key_path=operator_key,
                      password=operator_password)
        finally:
            system.shutdown()
        return 0
    if args.steps > 0 and not args.command:
        system.run(args.steps)
    if args.shutdown:
        system.shutdown()
    else:
        system.machine.save_state()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
