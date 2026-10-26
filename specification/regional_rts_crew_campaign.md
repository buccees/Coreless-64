# VIGIL Regional Naval Simulation: Real-Time Crew and Campaign Design

Status: implementation direction; this document is not a claim that all described features are already implemented.

## Core loop

VIGIL uses one continuous, time-advancing regional world. The map does not reset when a contact becomes an engagement. Detection changes the player's available information and may open a tactical engagement overlay on the same world coordinates. The simulation continues in real time during search, approach, combat, withdrawal, and post-engagement recovery.

- Regional navigation: pan/zoom bathymetry, coastlines, routes, operating areas, objectives, and friendly units.
- Contact investigation: sensor evidence, uncertainty, track history, classification confidence, and authorized sharing.
- Engagement: real-time movement, weapon readiness, damage, countermeasures, and changing contact solutions.
- Campaign: mission outcomes, crew experience, logistics, maintenance, intelligence, and consequences persist between sorties.

The existing 10×10 Battleship board is a prototype combat interface, not the intended limit or final world model. Migrate its combat rules into world-coordinate entities and engagement events rather than expanding the board indefinitely.

## Solo and crewed multiplayer

One person can operate every station and switch between station panels. In multiplayer, players join the same vessel and receive station permissions. The server owns authoritative world state and resolves actions; each client receives only the information that its role and sensors authorize.

Initial station roles:

- **Command:** mission priorities, contact disposition, rules of engagement, task assignment, and coordination.
- **Helm / navigation:** course, speed, maneuvering, route planning, terrain and depth clearance.
- **Sonar:** active/passive posture, bearing/range interpretation, track confidence, classification, and focused follow-up.
- **Radar / electronic support:** surface/air search, emissions evidence, and signature interpretation.
- **Weapons:** solution quality, target selection, weapon assignment, firing authorization, and readiness.
- **Engineering:** power allocation, propulsion, sensor availability, damage isolation, and endurance.
- **Damage control / medical:** fires, flooding, repairs, casualties, and crew readiness.
- **Aviation / mission systems (where fitted):** launch/recovery, payload assignment, endurance, and remote-unit tasking.

A vessel can run with unfilled stations under AI assistance. A station may be combined with another for solo play; multiplayer assignments should improve coordination, not make a ship unusable when a friend disconnects.

## Tabletop-RPG-inspired checks in a real-time simulation

Use a transparent d20-style check as a resolution layer for uncertain human actions—not as turn order. Every check has an explicit ability, skill, difficulty, modifiers, and a logged outcome.

Suggested model:

`total = d20 + ability_modifier + proficiency + situational_modifiers`

Compare total against a task difficulty. Natural 20/1 may add exceptional outcomes only where the task supports them; they should not make impossible physics possible. Advantage/disadvantage can roll twice and keep the higher/lower result. Show the reason for modifiers and the consequences before high-impact actions where practical.

Examples:
- Sonar operator uses **Perception + Sonar** to distinguish a faint contact from clutter.
- Analyst uses **Intelligence + Analysis** to improve classification from accumulated evidence.
- Helm uses **Dexterity + Seamanship** for a difficult maneuver under pressure.
- Engineer uses **Intelligence + Engineering** to restore degraded equipment or manage emergency power.
- Weapons operator uses **Dexterity + Fire Control** to reduce solution error under time pressure.
- Command uses **Wisdom + Leadership** for crew coordination, stress recovery, or resolving conflicting reports.

These are game mechanics, not real-world operator certification or validated sensor performance. Sensor physics, environmental effects, equipment condition, and available evidence establish the possible outcomes; checks affect execution, interpretation, and uncertainty within those bounds. Better skill should improve consistency, not magically reveal hidden truth.

## Real-time rules

- A fixed simulation tick advances movement, sensors, cooldowns, weapon travel, damage, and environment.
- Commands are timestamped actions, not alternating player turns. Players can act concurrently; server-side validation resolves conflicts deterministically.
- Actions have duration, resource cost, readiness, and interruption rules. Examples: changing sonar posture, stabilizing a firing solution, repairing a subsystem, or launching an aircraft.
- Pausing is a session policy for solo/testing; shared multiplayer normally remains live unless the session explicitly enables a coordinated pause.
- Combat begins when the simulation's detection/engagement conditions are met, not by switching into a separate turn-based minigame. Tactical zoom and station panels focus the same world state.

## One world, separate knowledge

Separate authoritative ground truth from per-player observations. Each observation includes source/modality, simulation time, uncertainty, confidence, and provenance. Share tracks between crew only through the modeled command/data-sharing system or explicit player action. Terrain knowledge may be charted independently of contact knowledge.

Never send hidden enemy positions, fleet composition, or unobserved damage to a client merely to make rendering easier. In online play, the server must resolve contacts and combat against its private world state and return only each player’s authorized view. The current browser-only sensor prototype is not sufficient authority for competitive multiplayer.

## Terrain and campaign model

Use a regional coordinate system with map projection/scale, elevation/depth samples, contour generation, chart confidence, and versioned sectors. Terrain influences movement and sensor propagation through explicit tunable rules. Start with synthetic terrain for development; replace or supplement it with licensed/public bathymetry only after data provenance and attribution are documented.

Campaign records should link mission objectives, faction intent, weather/environment, starting resources, persistent vessel damage, inventory, maintenance, crew skills/stress, intelligence, and debrief outcomes. Campaign scripts may generate encounters, but encounters remain part of the continuous world.

## Suggested implementation sequence

1. Make the regional bathymetry canvas navigable and keep its view state stable between sensor refreshes.
2. Define a shared world-coordinate model for vessels, terrain, observations, and engagement state.
3. Add deterministic real-time tick/action resolution and server-authoritative visibility boundaries.
4. Convert Battleship firing into a tactical engagement against world-coordinate targets.
5. Add station ownership, solo station switching, AI station assistance, and crew multiplayer.
6. Add explainable d20 checks for station tasks, then crew progression and campaign persistence.
7. Add additional sensor modalities and terrain-dependent detection after each has tests for uncertainty and no hidden-state leakage.

## Acceptance criteria

- Pan/zoom never moves the underlying world or reveals hidden contacts.
- A detected contact keeps its world identity/track history while the map zooms into an engagement.
- Solo mode exposes all station actions; crew mode enforces station permissions while allowing authorized handoffs.
- Multiple stations can issue concurrent actions without turn-taking.
- The same world tick and action sequence produces reproducible outcomes in tests.
- Client observation payloads contain no hidden enemy coordinates or truth-only identifiers.
- Every RPG-style check exposes its inputs and affects an in-bounds task outcome rather than bypassing the simulation.
