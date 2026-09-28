"""Simple Coreless desktop/compositor service."""
class Desktop:
    def __init__(self, graphics, width=640, height=480):
        self.graphics = graphics
        if graphics.scanout is not None:
            self.surface = graphics.scanout
        else:
            self.surface = graphics.create_surface(width, height)
            self.surface.ready = True
        self.windows = []

    def save_state(self):
        index = self.graphics.surfaces.index(self.surface) if self.surface in self.graphics.surfaces else None
        return {"surface": index, "windows": [dict(w) for w in self.windows]}

    def restore_state(self, state):
        if not state:
            return
        index = state.get("surface")
        if isinstance(index, int) and 0 <= index < len(self.graphics.surfaces):
            self.surface = self.graphics.surfaces[index]
        self.windows = [dict(w) for w in state.get("windows", [])]

    def open_window(self, title, width=320, height=200):
        w={"title":title,"width":width,"height":height,"x":0,"y":0}
        self.windows.append(w)
        return w

    def present(self):
        self.graphics.present(self.surface)
        return self.surface

    def events(self):
        out=[]
        while True:
            e=self.graphics.poll_input()
            if e is None: return out
            out.append(e)
