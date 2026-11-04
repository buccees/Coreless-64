# PLAGUE — Nanotechnology Research

PLAGUE is a separate research project inside the VIGIL R&D directory. It is not a new top-level navigation section and does not replace the Daedalus engineering workspaces.

## Runtime

- `vigil-plague.js` — nanoscale world model, animated WebGL display, instrument profiles, and observation-record logic.
- UI mount point: `#plague-station`, embedded inside the R&D panel in `index.html`.
- Entry point: the **PLAGUE / NANOTECHNOLOGY** folder card in the R&D project directory.

The simulation uses fictional nanobot design parameters and simplified dynamics. Instrument views expose only modeled observations, not hidden ground-truth entity data. It is a simulation, not validated nanobot engineering.

The Pages workflow copies and syntax-checks this folder as part of each deployment.
