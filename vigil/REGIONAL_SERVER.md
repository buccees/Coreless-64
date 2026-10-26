# VIGIL regional game server (development/LAN)

This server is the first authoritative regional-game host. It runs one shared
world, enforces per-player ship-control grants, serves authorized snapshots,
accepts validated commands, and advances a fixed-rate simulation tick. It is a
development/LAN foundation, not a production multiplayer deployment.

## Start a local TLS server

From the repository root, create or provide a TLS certificate and private key.
For a local-only smoke test, a self-signed certificate is sufficient if the
browser/client trusts it; browsers will reject untrusted certificates.

Set the human player's token in the environment (never in the JSON file):

    export VIGIL_HOST_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    export VIGIL_TLS_CERT=/path/to/server.crt
    export VIGIL_TLS_KEY=/path/to/server.key
    python -m vigil.regional_server \
      --config vigil/regional_server.example.json \
      --host 127.0.0.1 --port 8445 \
      --allowed-origin https://localhost:3000

The example configuration includes one human-controlled destroyer and one
server-managed computer-controlled frigate. The current command-line launcher
uses the deterministic fallback opponent policy. The optional Qwen3 adapter
can use an already-registered shared Coreless Qwen3 registry when a host embeds
and injects that registry; the standalone launcher does not load model weights
or claim that Qwen3 is running.

The sample ship positions and weapon ranges use normalized world units. Adjust
them together if using a larger regional coordinate system. world_bounds maps
those world coordinates to the browser's normalized map coordinates.

## API

All requests require an allowed HTTPS Origin and a bearer token.

- GET /api/regional/snapshot returns the caller's authorized observation.
- POST /api/regional/command accepts a JSON body such as:

    {
      "operation": "set_heading",
      "arguments": {"ship_id": "player-destroyer", "heading_deg": 135}
    }

Other currently supported operations are set_speed, campaign_move, fire_weapon, and
host-only end_campaign_turn. The set_speed operation accepts a finite value from
zero through the configured max_speed; zero means all stop. Configure max_speed
per ship in the JSON roster to permit acceleration above its starting speed.
For backward compatibility, omitting max_speed makes the starting speed its
maximum. The same speed value also defines the ship's campaign movement allowance.
Weapon fire requires a visible target in range. Each ship can configure
weapon_reload_seconds (default 5); after a hit, the weapon remains unavailable
until real-time simulation ticks count the cooldown down. A player's snapshot
includes reload state for their own ships only, not visible enemy contacts.
This initial weapon model applies configured damage directly; it does not yet
simulate sensors, detection probability, weapon flight, countermeasures, or
damage-control tasks.

The browser exposes window.connectVigilRegionalSnapshot({url, token}) for
snapshot polling and window.sendVigilRegionalCommand({url, token}, operation,
arguments) for commands. Pass the snapshot endpoint URL, for example
https://localhost:8445/api/regional/snapshot. Tokens remain in memory only.
The browser's current fleet illustration is still a fallback/demo; connect the
poller to the server to render server-authoritative positions.

## Important limitations

- Use a maintained WSGI server and TLS reverse proxy for production.
- Player sessions and world state are currently in memory; restart loses them.
- Configure strong, unique bearer tokens and restrict network access.
- The standard-library WSGI development server is not designed for public
  internet traffic or high concurrency.
- AI recommendations are untrusted and pass through the same ownership/range
  checks as human commands.
- The sample plan/specification metadata is not a verified blueprint silhouette.


## Factions in the simulation

The shared simulation exposes a faction catalog in every authorized regional snapshot. It includes the corporate factions Prodigy, Weyland-Yutani, Lynch, Dynamic, and Threshold alongside the existing Maritime Coalition, Extraction Directorate, and Unknown factions. Ship configurations can assign the corresponding `faction_id` values (for example, `prodigy` or `weyland-yutani`). These are ordinary factions in the game simulation, not a separate campaign mode. Faction identity is present; diplomacy, formal war declarations, territory control, and faction-wide logistics remain future simulation systems.
