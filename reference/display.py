"""Simple Coreless desktop/compositor service and system-tray state model."""


class Desktop:
    """Virtual desktop services backed by the machine's canonical device state.

    The tray model is UI state only: GPIO state and transitions are always read
    from the supplied virtual motherboard, never copied into a decorative LED.
    """

    def __init__(self, graphics, width=640, height=480, motherboard=None):
        self.graphics = graphics
        self.motherboard = motherboard
        if graphics.scanout is not None:
            self.surface = graphics.scanout
        else:
            self.surface = graphics.create_surface(width, height)
            self.surface.ready = True
        self.windows = []
        self.tray_menu = None

    def save_state(self):
        index = self.graphics.surfaces.index(self.surface) if self.surface in self.graphics.surfaces else None
        return {
            "surface": index,
            "windows": [dict(w) for w in self.windows],
            "tray_menu": self.tray_menu,
        }

    def restore_state(self, state):
        if not state:
            return
        index = state.get("surface")
        if isinstance(index, int) and 0 <= index < len(self.graphics.surfaces):
            self.surface = self.graphics.surfaces[index]
        self.windows = [dict(w) for w in state.get("windows", [])]
        self.tray_menu = state.get("tray_menu") if state.get("tray_menu") in (None, "status_led") else None

    def open_window(self, title, width=320, height=200):
        w = {"title": title, "width": width, "height": height, "x": 0, "y": 0}
        self.windows.append(w)
        return w

    def tray_items(self):
        """Return compact tray affordances; LED is a dot, not a persistent widget."""
        return [{"id": "status_led", "kind": "dot", "anchor": "battery", "label": "GPIO0 status LED"}]

    def open_tray_menu(self, item_id="status_led"):
        if item_id != "status_led":
            raise ValueError("unknown tray item")
        self.tray_menu = item_id
        return self.status_led_menu()

    def close_tray_menu(self):
        self.tray_menu = None

    def status_led_menu(self):
        """Return live LED state and transition history from the canonical motherboard."""
        if self.motherboard is None:
            return {
                "id": "status_led",
                "available": False,
                "label": "GPIO0 status LED",
                "state": "unavailable",
                "level": None,
                "energized": False,
                "transitions": [],
            }
        snapshot = self.motherboard.snapshot()
        peripherals = snapshot.get("peripherals", {})
        led = peripherals.get("status_led", {})
        level = led.get("level")
        return {
            "id": "status_led",
            "available": True,
            "label": "GPIO0 status LED",
            "state": "ON" if level == 1 else "OFF" if level == 0 else "UNDRIVEN",
            "level": level,
            "energized": bool(led.get("energized", False)),
            "transitions": list(led.get("transitions", [])),
        }

    def present(self):
        self.graphics.present(self.surface)
        return self.surface

    def events(self):
        out = []
        while True:
            event = self.graphics.poll_input()
            if event is None:
                return out
            out.append(event)
