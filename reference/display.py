"""Simple Coreless desktop/compositor service."""
class Desktop:
    def __init__(self,graphics,width=640,height=480):
        self.graphics=graphics; self.surface=graphics.create_surface(width,height)
        self.windows=[]; self.surface.ready=True
    def open_window(self,title,width=320,height=200):
        w={"title":title,"width":width,"height":height,"x":0,"y":0}; self.windows.append(w); return w
    def present(self): self.graphics.present(self.surface); return self.surface
    def events(self):
        out=[]
        while True:
            e=self.graphics.poll_input()
            if e is None:return out
            out.append(e)
