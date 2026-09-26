"""Minimal interactive Coreless shell."""
class Shell:
    def __init__(self,machine,fs=None):
        self.machine=machine; self.fs=fs or machine.filesystem
        self.cwd="/"; self.commands={"help":self.help,"ls":self.ls,"pwd":self.pwd,"write":self.write,"cat":self.cat,"rm":self.rm,"run":self.run,"status":self.status}
    def execute(self,line):
        p=line.strip().split()
        if not p:return ""
        cmd,args=p[0],p[1:]
        if cmd=="cd":
            path=self._path(args[0] if args else "/")
            if not any(x.startswith(path.rstrip("/")+"/") for x in self.fs.files) and path!="/": return "cd: no such directory"
            self.cwd=path; return ""
        if cmd not in self.commands:return "unknown command: "+cmd
        return self.commands[cmd](args)
    def _path(self,p):
        return self.fs._path(self.cwd+"/"+p if not p.startswith("/") else p)
    def help(self,args): return " ".join(sorted(self.commands|{"cd"}))
    def ls(self,args): return "\n".join(self.fs.list(self._path(args[0]) if args else self.cwd))
    def pwd(self,args): return self.cwd
    def write(self,args):
        if len(args)<2:return "usage: write PATH TEXT"
        self.fs.write(self._path(args[0])," ".join(args[1:]).encode()); return ""
    def cat(self,args):
        if len(args)!=1:return "usage: cat PATH"
        try:return self.fs.read(self._path(args[0])).decode()
        except (FileNotFoundError,UnicodeDecodeError):return "cat: unable to read"
    def rm(self,args):
        if len(args)!=1:return "usage: rm PATH"
        try:self.fs.delete(self._path(args[0])); return ""
        except FileNotFoundError:return "rm: not found"
    def run(self,args):
        return "usage: run PROGRAM" if len(args)!=1 else self.machine.run_program(self._path(args[0]))
    def status(self,args):
        return "Coreless-64 ready; CPUs=%d; booted=%s"%(len(self.machine.cpus),self.machine.booted)
