"""Optional Tk host renderer for the Coreless virtual desktop.

This is a host-rendered desktop chrome, not a second shell or a native OS tray
icon. The compact status dot sits beside the battery indicator in the
Coreless desktop's top-right bar and opens a transient menu backed by Desktop.
Tk is imported only when the renderer is started, so headless machine tests
and the reference runtime do not require a GUI environment.
"""

from __future__ import annotations


class TkDesktopHost:
    """Render Coreless desktop chrome and route pointer actions to Desktop."""

    def __init__(self, desktop, *, root=None, tk_module=None):
        self.desktop = desktop
        self._tk = tk_module
        self.root = root
        self._menu = None
        self._poll_id = None
        self._dot = None
        self._state_label = None
        self._transition_label = None

    def start(self):
        if self._tk is None:
            import tkinter as tk
            self._tk = tk
        tk = self._tk
        if self.root is None:
            self.root = tk.Tk()
        self.root.title("Coreless-64 Desktop")
        self.root.geometry("800x520")
        self.root.configure(bg="#101810")

        self.canvas = tk.Frame(self.root, bg="#101810")
        self.canvas.pack(fill="both", expand=True)

        # Existing desktop gets one rendered surface; status chrome is part of
        # that surface rather than a separate always-visible LED widget.
        self.topbar = tk.Frame(self.canvas, bg="#202820", height=30)
        self.topbar.pack(side="top", fill="x")
        self.topbar.pack_propagate(False)
        self.right = tk.Frame(self.topbar, bg="#202820")
        self.right.pack(side="right", padx=10)
        self.battery = tk.Label(
            self.right, text="▰ 100%", fg="#c8d8c8", bg="#202820",
            font=("TkDefaultFont", 9),
        )
        self.battery.pack(side="left", padx=(0, 7))
        self._dot = tk.Label(
            self.right, text="●", fg="#647064", bg="#202820",
            cursor="hand2", font=("TkDefaultFont", 10),
        )
        self._dot.pack(side="left")
        self._dot.bind("<Button-1>", self._on_dot_click)
        self.work_area = tk.Frame(self.canvas, bg="#101810")
        self.work_area.pack(fill="both", expand=True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._refresh_dot()
        self._poll_id = self.root.after(250, self._refresh_dot)
        return self.root

    def _refresh_dot(self):
        if self._dot is None:
            return
        status = self.desktop.status_led_menu()
        color = "#65ff65" if status["state"] == "ON" else (
            "#647064" if status["state"] == "OFF" else "#d4b35d"
        )
        self._dot.configure(fg=color)
        if self.root is not None:
            self._poll_id = self.root.after(250, self._refresh_dot)

    def _on_dot_click(self, _event=None):
        if self._menu is not None and self._menu.winfo_exists():
            self._menu.destroy()
            self._menu = None
            self.desktop.close_tray_menu()
            return
        status = self.desktop.open_tray_menu("status_led")
        tk = self._tk
        self._menu = tk.Toplevel(self.root)
        self._menu.title("GPIO0 Status LED")
        self._menu.configure(bg="#202820")
        self._menu.resizable(False, False)
        self._menu.transient(self.root)
        self._menu.geometry("+%d+%d" % (self.root.winfo_rootx() + self.root.winfo_width() - 240,
                                        self.root.winfo_rooty() + 34))
        tk.Label(
            self._menu, text="GPIO0 / STATUS LED", fg="#9cff9c",
            bg="#202820", font=("TkFixedFont", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        self._state_label = tk.Label(
            self._menu, text="", fg="#e0e8e0", bg="#202820",
            font=("TkFixedFont", 10), justify="left",
        )
        self._state_label.pack(anchor="w", padx=12)
        self._transition_label = tk.Label(
            self._menu, text="", fg="#aabaaa", bg="#202820",
            font=("TkFixedFont", 9), justify="left",
        )
        self._transition_label.pack(anchor="w", padx=12, pady=(4, 10))
        self._menu.protocol("WM_DELETE_WINDOW", self._close_menu)
        self._refresh_menu()
        status_color = "#65ff65" if status["state"] == "ON" else ("#647064" if status["state"] == "OFF" else "#d4b35d")
        self._dot.configure(fg=status_color)

    def _refresh_menu(self):
        if self._menu is None or not self._menu.winfo_exists():
            return
        status = self.desktop.status_led_menu()
        self._state_label.configure(
            text="State: %s\nGPIO0 level: %s\nEnergized: %s" % (
                status["state"], status["level"], status["energized"]
            )
        )
        history = status["transitions"]
        self._transition_label.configure(
            text="Transitions: " + (" → ".join(map(str, history)) if history else "none")
        )
        self._menu.after(250, self._refresh_menu)

    def _close_menu(self):
        if self._menu is not None:
            self._menu.destroy()
            self._menu = None
        self.desktop.close_tray_menu()

    def close(self):
        self._close_menu()
        if self.root is not None and self._poll_id is not None:
            try:
                self.root.after_cancel(self._poll_id)
            except Exception:
                pass
        if self.root is not None:
            self.root.destroy()

    def run(self):
        root = self.start()
        root.mainloop()
