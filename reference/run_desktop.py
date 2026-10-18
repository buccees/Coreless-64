"""Launch the optional Tk-rendered Coreless-64 virtual desktop.

Run from the repository root with: python reference/run_desktop.py
A graphical display and Tk support are required; the machine and GPIO remain
virtual and no physical hardware is accessed.
"""

from machine_runtime import CorelessMachine
from os_runtime import CorelessOS
from desktop_host import TkDesktopHost


def main():
    machine = CorelessMachine()
    os_runtime = CorelessOS(machine)
    TkDesktopHost(os_runtime.desktop).run()


if __name__ == "__main__":
    main()
