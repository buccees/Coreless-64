#!/usr/bin/env python3
"""Guided desktop startup for the Coreless-64 browser operator display.

The GUI owns setup prompts only. The CorelessSystem instance it boots is passed
directly to the HTTPS WSGI server in this same process; the browser is a client.
"""
from __future__ import annotations

import ipaddress
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REFERENCE))

from local_operator_server import create_lan_app
from system import CorelessSystem


def suggested_lan_ip() -> str:
    """Discover the outbound interface address without sending application data."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        value = sock.getsockname()[0]
        ipaddress.ip_address(value)
        return value
    except (OSError, ValueError):
        return "127.0.0.1"
    finally:
        sock.close()


def make_local_certificate(directory: Path, host: str) -> tuple[Path, Path]:
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError(
            "OpenSSL was not found. Install OpenSSL, or use Browse to select an existing TLS certificate and key."
        )
    directory.mkdir(parents=True, exist_ok=True)
    cert = directory / "operator-cert.pem"
    key = directory / "operator-key.pem"
    sans = ["DNS:localhost", "IP:127.0.0.1", "IP:::1"]
    try:
        ipaddress.ip_address(host)
        if host not in ("127.0.0.1", "::1"):
            sans.append(f"IP:{host}")
    except ValueError:
        sans.append(f"DNS:{host}")
    result = subprocess.run(
        [
            openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key), "-out", str(cert), "-days", "365",
            "-subj", "/CN=Coreless Operator Display",
            "-addext", "subjectAltName=" + ",".join(sans),
        ],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "OpenSSL could not create a certificate").strip())
    return cert, key


class QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        print("Coreless operator:", fmt % args)


class StartupWizard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("CORELESS-64 // Operator Startup")
        root.geometry("760x650")
        root.minsize(650, 590)
        root.configure(bg="#06100c")
        self.server = None
        self.server_thread = None
        self.system = None
        self.startup_thread = None
        self._closing = threading.Event()
        self._lifecycle_lock = threading.Lock()
        # Keep the default machine image beside the project so the project folder can live on a portable SSD.
        self.image = tk.StringVar(value=str(ROOT / "coreless.img"))
        self.access = tk.StringVar(value="local")
        self.password = tk.StringVar()
        self.port = tk.StringVar(value="8443")
        # Keep TLS files with the portable project, outside tracked source files.
        portable_security_dir = ROOT / ".coreless-operator"
        self.cert = tk.StringVar(value=str(portable_security_dir / "operator-cert.pem"))
        self.key = tk.StringVar(value=str(portable_security_dir / "operator-key.pem"))
        self.status = tk.StringVar(value="READY // Review settings, then select START CORELESS.")
        self._build()

    def _build(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#06100c")
        style.configure("TLabel", background="#06100c", foreground="#b9f6d2", font=("Consolas", 10))
        style.configure("TButton", font=("Consolas", 10, "bold"), padding=7)
        style.configure("TRadiobutton", background="#06100c", foreground="#b9f6d2", font=("Consolas", 10))
        style.configure("TEntry", fieldbackground="#10231a", foreground="#e0ffec")
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="CORELESS-64  //  OPERATOR STARTUP", font=("Consolas", 17, "bold")).pack(anchor="w")
        ttk.Label(outer, text="GUIDED SETUP  •  MACHINE RUNTIME + REMOTE BROWSER TERMINAL").pack(anchor="w", pady=(4, 16))

        self._section(outer, "01 // PERSISTENT MACHINE IMAGE")
        row = ttk.Frame(outer); row.pack(fill="x", pady=(4, 8))
        ttk.Entry(row, textvariable=self.image).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="BROWSE", command=self._browse_image).pack(side="left", padx=(8, 0))
        ttk.Label(outer, text="If this file does not exist, Coreless will ask before creating a new image. Keep the project folder and image together on the portable SSD.").pack(anchor="w")

        self._section(outer, "02 // WHERE SHOULD THE SCREEN BE AVAILABLE?")
        ttk.Radiobutton(outer, text="This computer only (recommended)", variable=self.access, value="local").pack(anchor="w", pady=2)
        ttk.Radiobutton(outer, text="Other devices on my trusted local network", variable=self.access, value="lan").pack(anchor="w", pady=2)
        row = ttk.Frame(outer); row.pack(fill="x", pady=(5, 0))
        ttk.Label(row, text="HTTPS PORT", width=13).pack(side="left")
        ttk.Entry(row, textvariable=self.port, width=10).pack(side="left")

        self._section(outer, "03 // SECURE SIGN-IN")
        ttk.Label(outer, text="Choose a password with at least 16 characters. You will enter it on the browser sign-in screen.").pack(anchor="w", pady=(3, 5))
        row = ttk.Frame(outer); row.pack(fill="x")
        self.password_entry = ttk.Entry(row, textvariable=self.password, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="SHOW / HIDE", command=self._toggle_password).pack(side="left", padx=5)
        ttk.Button(row, text="GENERATE", command=self._generate_password).pack(side="left")

        self._section(outer, "04 // HTTPS CERTIFICATE")
        ttk.Label(outer, text="A local certificate is generated automatically when OpenSSL is available. For LAN use, client devices must trust the certificate.").pack(anchor="w", pady=(3, 5))
        for label, variable, command in (
            ("CERTIFICATE", self.cert, self._browse_cert),
            ("PRIVATE KEY", self.key, self._browse_key),
        ):
            row = ttk.Frame(outer); row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=13).pack(side="left")
            ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="BROWSE", command=command).pack(side="left", padx=(6, 0))

        footer = ttk.Frame(outer); footer.pack(fill="x", pady=(16, 0))
        self.start_button = ttk.Button(footer, text="START CORELESS", command=self.start)
        self.start_button.pack(side="left")
        ttk.Label(footer, textvariable=self.status, wraplength=440).pack(side="left", padx=12, fill="x", expand=True)
        ttk.Label(outer, text="The browser is only a display/input terminal. Coreless owns machine state.").pack(anchor="w", pady=(10, 0))
        ttk.Label(outer, text="PORTABLE SSD: stop Coreless cleanly before unplugging. Never open the same image in two running instances.", wraplength=700).pack(anchor="w", pady=(5, 0))

    def _section(self, parent, title: str) -> None:
        ttk.Label(parent, text=title, font=("Consolas", 11, "bold")).pack(anchor="w", pady=(13, 1))

    def _browse_image(self) -> None:
        value = filedialog.asksaveasfilename(title="Choose Coreless machine image", defaultextension=".img",
            filetypes=[("Coreless image", "*.img"), ("All files", "*.*")], initialfile=Path(self.image.get()).name)
        if value:
            self.image.set(value)

    def _browse_cert(self) -> None:
        value = filedialog.askopenfilename(title="Choose TLS certificate", filetypes=[("PEM certificate", "*.pem *.crt"), ("All files", "*.*")])
        if value: self.cert.set(value)

    def _browse_key(self) -> None:
        value = filedialog.askopenfilename(title="Choose TLS private key", filetypes=[("PEM private key", "*.pem *.key"), ("All files", "*.*")])
        if value: self.key.set(value)

    def _toggle_password(self) -> None:
        self.password_entry.configure(show="" if self.password_entry.cget("show") else "*")

    def _generate_password(self) -> None:
        value = secrets.token_urlsafe(24)
        self.password.set(value)
        self.password_entry.configure(show="")
        self.status.set("PASSWORD GENERATED // Copy it or keep it visible while signing in.")

    def start(self) -> None:
        if self._closing.is_set() or (self.startup_thread and self.startup_thread.is_alive()):
            return
        image_path = Path(self.image.get()).expanduser()
        password = self.password.get()
        try:
            port = int(self.port.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid port", "Enter a valid port from 1 to 65535.")
            return
        if len(password) < 16:
            messagebox.showerror("Password required", "Enter or generate a password with at least 16 characters.")
            return
        if not image_path.exists() and not messagebox.askyesno(
            "Create machine image?", f"This image does not exist yet:\n\n{image_path}\n\nCreate a new persistent Coreless image here?"
        ):
            return
        host = "127.0.0.1" if self.access.get() == "local" else "0.0.0.0"
        connect_host = "127.0.0.1" if host == "127.0.0.1" else suggested_lan_ip()
        cert_path, key_path = Path(self.cert.get()).expanduser(), Path(self.key.get()).expanduser()
        self.start_button.configure(state="disabled")
        self.status.set("STARTING // Validating certificate and booting the Coreless machine…")
        self.startup_thread = threading.Thread(
            target=self._start_worker,
            args=(image_path, password, host, connect_host, port, cert_path, key_path),
            daemon=True,
            name="coreless-startup",
        )
        self.startup_thread.start()

    def _start_worker(self, image_path: Path, password: str, host: str, connect_host: str,
                      port: int, cert_path: Path, key_path: Path) -> None:
        system = None
        server = None
        try:
            if self._closing.is_set():
                raise RuntimeError("Startup cancelled because the window is closing")
            if not cert_path.is_file() or not key_path.is_file():
                self._set_status("SETUP // Creating a local HTTPS certificate…")
                cert_path, key_path = make_local_certificate(cert_path.parent, connect_host)
            if self._closing.is_set():
                raise RuntimeError("Startup cancelled because the window is closing")
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(str(cert_path), str(key_path))
            self._set_status("BOOT // Starting Coreless machine…")
            system = CorelessSystem(storage_path=image_path)
            system.boot()
            if self._closing.is_set():
                raise RuntimeError("Startup cancelled because the window is closing")
            self._set_status("SERVICE // Starting authenticated operator display…")
            server = make_server(host, port, create_lan_app(password=password, system=system),
                                 server_class=WSGIServer, handler_class=QuietHandler)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            with self._lifecycle_lock:
                if self._closing.is_set():
                    raise RuntimeError("Startup cancelled because the window is closing")
                self.system, self.server = system, server
                self.server_thread = threading.Thread(
                    target=server.serve_forever, daemon=True, name="coreless-https-server"
                )
                try:
                    self.server_thread.start()
                except Exception:
                    self.system = self.server = self.server_thread = None
                    raise
            url = f"https://{connect_host}:{port}/"
            if not self._closing.is_set():
                try:
                    self.root.after(0, self._started, url, host != "127.0.0.1")
                except (RuntimeError, tk.TclError):
                    # The listener remains owned by this app; a closed UI must not trigger rollback.
                    pass
        except Exception as exc:
            # Startup is transactional: if the machine booted but the HTTPS
            # listener failed, release the listener and persist a clean state.
            if server is not None:
                try:
                    server.server_close()
                except Exception:
                    pass
            if system is not None:
                try:
                    system.machine.save_state()
                except Exception as save_exc:
                    exc = RuntimeError(f"{exc}; machine-state save also failed: {save_exc}")
                try:
                    system.shutdown()
                except Exception as shutdown_exc:
                    exc = RuntimeError(f"{exc}; machine shutdown also failed: {shutdown_exc}")
            if not self._closing.is_set():
                try:
                    self.root.after(0, self._failed, str(exc))
                except (RuntimeError, tk.TclError):
                    pass

    def _set_status(self, value: str) -> None:
        if self._closing.is_set():
            return
        try:
            self.root.after(0, self.status.set, value)
        except (RuntimeError, tk.TclError):
            pass

    def _started(self, url: str, lan: bool) -> None:
        if self._closing.is_set():
            return
        self.status.set("RUNNING // Coreless booted; operator HTTPS service is listening.")
        self.start_button.configure(text="RUNNING", state="disabled")
        webbrowser.open(url)
        warning = "\n\nThis certificate is self-signed. Your browser may show a certificate warning. For LAN access, install/trust the certificate on each client device before signing in." if lan else "\n\nIf the browser shows a certificate warning, verify that you are using the local address shown here. Trusting a self-signed certificate is a local security decision."
        messagebox.showinfo("Coreless is running", f"Operator display address:\n\n{url}\n\nSign in with the password entered in the startup window.{warning}")

    def _failed(self, error: str) -> None:
        if self._closing.is_set():
            return
        self.status.set("START FAILED // See the message for the next step.")
        self.start_button.configure(state="normal")
        messagebox.showerror("Coreless could not start", f"{error}\n\nNothing has been reported as running. Correct the setup shown on screen and try again.")

    def close(self) -> None:
        # Mark cancellation before taking ownership of published resources. A
        # worker that has not published its server/system will observe this and
        # tear down its local resources instead of starting a detached service.
        self._closing.set()
        with self._lifecycle_lock:
            server, server_thread, system = self.server, self.server_thread, self.system
            self.server = self.server_thread = self.system = None

        if server is not None:
            if server_thread is not None and server_thread.is_alive():
                try:
                    server.shutdown()
                except Exception as exc:
                    messagebox.showerror("Server shutdown warning", f"The operator server did not stop cleanly:\n{exc}")
            try:
                server.server_close()
            except Exception as exc:
                messagebox.showerror("Server close warning", f"The operator listener could not be closed cleanly:\n{exc}")
        if system is not None:
            try:
                system.shutdown()
            except Exception as exc:
                messagebox.showerror("Shutdown warning", f"The operator server stopped, but machine shutdown reported:\n{exc}")
                try:
                    system.machine.save_state()
                except Exception as save_exc:
                    messagebox.showerror("Save warning", f"Machine-state save also failed:\n{save_exc}")
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    app = StartupWizard(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
