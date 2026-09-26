"""Command-line Coreless reference machine launcher."""
import argparse,sys
from machine_runtime import CorelessMachine
from firmware import Firmware
from shell import Shell

def main():
    ap=argparse.ArgumentParser(prog="coreless")
    ap.add_argument("--memory",type=int,default=1<<20)
    ap.add_argument("--cpus",type=int,default=1)
    args=ap.parse_args()
    m=CorelessMachine(args.memory,args.cpus); Firmware(m).initialize()
    shell=Shell(m)
    print("Coreless-64 ready. Type 'help' for commands.")
    while True:
        try: line=input("coreless:"+shell.cwd+"$ ")
        except EOFError: break
        if line.strip() in ("exit","quit"): break
        try:
            out=shell.execute(line)
            if out: print(out)
        except Exception as e: print("error:",e)
if __name__=="__main__": main()
