# The Daedalus Encounter — Reverse-Engineering Notes

**Status:** Active investigation  
**Target puzzle:** Green Door optical routing  
**Repository branch:** `vigil-spatial-awareness`

## Objective

Reconstruct the original puzzle's actual board geometry, emitter and receiver locations, mirror orientations, beam propagation rules, color-combination behavior, and six difficulty configurations. Preserve the original puzzle interaction. Replace only the underlying placeholder logic with a verified optical model.

Do not treat walkthrough answers or plausible optical assumptions as original implementation facts.

## Evidence recovered

### 1. Official 3DO puzzle-help manual

The original manual states that:

- The Green Door is a light-routing puzzle.
- The player clicks cells to deflect colored light.
- Each colored light must reach the flashing point of the same color.
- Colors are allowed to mix at the receiver points.

Source: https://www.digitpress.com/library/manuals/3do/daedalus_encounter.pdf (Puzzle Help, printed pages 12–13).

This establishes the objective and the fact that color mixing at the targets is permitted. It does **not** specify the exact emitter/receiver coordinates, optical surface geometry, or numerical reflectance.

### 2. Six Green Door stages exist

The Walkthrough King guide says difficulty determines whether one, three, or six puzzle variants are required, and lists all six Green Door mirror-orientation solutions:

| Stage | Mirror orientation sequence (as printed) |
|---|---|
| 1 | `/`, `-`, `\\`, `/`, `/` |
| 2 | `/`, `/`, `/`, `/`, `/`, `/` |
| 3 | `-`, `-`, `-`, `\\`, `\\`, `-`, `\\`, `\\`, `\\`, `\\` |
| 4 | `/`, `-`, `/`, `\\`, `\\`, `-`, `\\`, `/`, `-` |
| 5 | `\\`, `\\`, `-`, `\\`, `/`, `\\`, `\\`, `/`, `/`, `/`, `-`, `/`, `/` |
| 6 | `\\`, `-`, `-`, `/`, `/`, `\\`, `-`, `-`, `\\`, `/`, `/`, `\\`, `/`, `\\`, `-`, `-`, `\\`, `/` |

These sequences are useful validation references, but they do not by themselves provide cell coordinates or establish how the original game encodes each mirror orientation.

Source: https://www.walkthroughking.com/text/daedalusencounter.aspx

### 3. Three coordinate-based layouts are documented

The GameFAQs and Just Adventure walkthroughs provide these exact mirror placements, with rows and columns numbered from 1 and orientations `a` through `f`:

**Stage 1**
`4-7d 4-9d 2-1f 8-4f 8-5c`

**Stage 2**
`2-6c 4-12c 5-15c 6-3c 7-7c 8-9c`

**Stage 3**
`1-1d 1-2a 1-4e 1-9b 3-7d 3-12a 3-13b 4-7b 4-15d 5-3a 5-5a 8-3e 8-4d 8-6d 8-8b`

The walkthrough describes `a` as top, then `b` through `f` clockwise. It identifies `1-1` as the top-left cell and `8-9` as the bottom-right cell. This is a strong warning that the current flat rectangular 8 × 15 cell array is not yet a validated representation of the original triangular board.

Sources:
- https://gamefaqs.gamespot.com/pc/565063-the-daedalus-encounter/faqs/2095
- https://www.justadventure.com/walkthrough/the-daedalus-encounter/

## OpenDaed source investigation

An existing open-source reimplementation, OpenDaed, was located:

https://github.com/AMDmi3/opendaed

Its README says it requires the original game data directory and that its current implemented standalone puzzles are Artemis, the Yellow Door hexagons puzzle, and the Sundial. It does **not** claim to implement the Green Door.

Useful source-level findings:

- `DataManager` recursively indexes the original data directory by filename, case-insensitively. The implementation assumes a filename is unique across the game discs.
- `.NOD` files are parsed as indexed scene-script entries, with a fixed set of 24 fields per entry.
- The interpreter loads referenced `.NOD` files and processes movie, still-frame, hotspot, and control-event entries.
- `.HOT` files contain frame-indexed hotspot rectangles (eight rectangle slots per frame).
- The Yellow Door implementation provides a useful example of recovering original puzzle dimensions, pixel coordinates, per-level data, and interaction rules directly from source code rather than inventing them.

Relevant OpenDaed source files:
- `datamanager.cc`
- `nodfile.cc`
- `interpreter.cc`
- `hotfile.cc`
- `hexagonspuzzle.cc`

This source is a reverse-engineering aid, not proof that its unfinished game engine contains the Green Door logic.

## Current Coreless-64 implementation audit

The current Green Door branch in `daedalus-rd.js` is explicitly provisional:

- It creates a full rectangular 8 × 15 grid.
- It invents three launch rows and assumes three beams start at fixed positions.
- It uses representative wavelengths (650, 532, and 450 nm), 1 mW launch power, and 96% mirror reflectance.
- It models a six-direction lattice reflection rule.
- It currently contains only the first three coordinate-based walkthrough layouts.
- It has no recovered original receiver coordinates or calibrated target-hit validation.

These values are useful temporary engineering parameters, but none should be presented as recovered original game data. In particular, real optical wavelength/power accounting is not the same thing as the game's original discrete puzzle logic; it should be an optional engineering analysis layer after the original routing rules are recovered.

## Reverse-engineering plan

1. Obtain or inspect an authorized copy of the original game data (the original PC or 3DO data set). The current Coreless-64 repository does not contain those original assets.
2. Inventory the data files by disc, extension, filename, dimensions, and hashes. Preserve original files unchanged.
3. Locate the Green Door puzzle's scene scripts, still frames, hotspot data, background artwork, animation assets, and any puzzle-specific data tables.
4. Extract the original puzzle screen at native resolution and measure the playable triangular-cell centers, perimeter emitters, and flashing receiver locations.
5. Determine the actual triangular-cell topology and map each clickable cell to its six orientation states.
6. Use the documented three coordinate solutions and six orientation sequences as independent test vectors. Do not convert slash notation to `a`–`f` until the mapping is established from original assets or observed behavior.
7. Implement the discrete original game rules first: ray routing, target color requirements, and any mixing behavior.
8. Validate all six configurations against the original game. Only after that, add wavelength, power, reflectance, incidence angle, and energy-loss calculations as a separate physical interpretation layer.

## Acceptance criteria

- Board topology and screen coordinates are derived from original assets, not guessed.
- Every original source and receiver is represented at its recovered location.
- Clicking a cell reproduces the original mirror-state cycle.
- Beam paths agree with the original puzzle's observed behavior.
- All six documented stage solutions solve the matching stage.
- The UI retains the original puzzle layout and controls; no unrelated sensor demo replaces it.
- Every parameter is labeled as **recovered**, **measured**, or **assumed**.
