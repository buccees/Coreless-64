"""Command-line launcher for the native Coreless operating environment."""
import argparse
from machine_runtime import CorelessMachine
from os_runtime import CorelessOS

def main():
    ap = argparse.ArgumentParser(prog="coreless")
    ap.add_argument("--memory", type=int, default=1 << 20)
    ap.add_argument("--cpus", type=int, default=1)
    args = ap.parse_args()
    os = CorelessOS(CorelessMachine(args.memory, args.cpus)).run()
    print("Coreless-64 ready. Type 'help' for commands.")
    while True:
        try:
            line = input("coreless:" + os.shell.cwd + "$ ")
        except EOFError:
            break
        if line.strip() in ("exit", "quit"):
            break
        try:
            out = os.command(line)
            if out:
                print(out)
        except Exception as e:
            print("error:", e)

if __name__ == "__main__":
    main()
