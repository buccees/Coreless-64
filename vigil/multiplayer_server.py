"""TLS development launcher for the VIGIL multiplayer API.

For production, run the WSGI app behind a maintained production server and TLS
reverse proxy. The standard-library server here is for LAN smoke tests only.
"""
from __future__ import annotations

import argparse
import os
import ssl
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

from vigil.multiplayer_http import create_multiplayer_app


class QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        print("VIGIL multiplayer API:", fmt % args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the VIGIL multiplayer API for development/LAN testing.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8444)
    parser.add_argument("--cert", default=os.environ.get("VIGIL_TLS_CERT"))
    parser.add_argument("--key", default=os.environ.get("VIGIL_TLS_KEY"))
    parser.add_argument(
        "--allowed-origin",
        action="append",
        default=None,
        help="exact HTTPS origin of the browser client; may be repeated",
    )
    args = parser.parse_args()
    origins = args.allowed_origin or [
        value.strip() for value in os.environ.get("VIGIL_MULTIPLAYER_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    ]
    if not origins:
        parser.error("provide --allowed-origin or VIGIL_MULTIPLAYER_ALLOWED_ORIGINS")
    if not args.cert or not args.key:
        parser.error("TLS is required; provide --cert/--key or VIGIL_TLS_CERT/VIGIL_TLS_KEY")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(args.cert, args.key)
    server = make_server(
        args.host, args.port,
        create_multiplayer_app(allowed_origins=origins),
        server_class=WSGIServer, handler_class=QuietHandler,
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f"VIGIL multiplayer API listening at https://{args.host}:{args.port}/")
    print("Development/LAN only: deploy behind a production WSGI server and TLS proxy for public use.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
