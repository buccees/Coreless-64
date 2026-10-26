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

Other currently supported operations are campaign_move, fire_weapon, and
host-only end_campaign_turn. Weapon fire requires a visible target in range.
This initial weapon model applies configured damage directly; it does not yet
simulate sensors, detection probability, weapon flight, reloads, countermeasures,
or damage-control tasks.

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


## Campaign factions (foundation)

Ships may declare an optional `faction_id` in the campaign JSON. The affiliation is carried through authorized regional snapshots. The example roster uses `prodigy` and `weyland-yutani` from the optional unofficial Alien: Earth crossover scenario. The complete five-corporation roster lives in `vigil/alien_earth_campaign.py`: Prodigy, Weyland-Yutani, Lynch, Dynamic, and Threshold. This is fan-made scenario data, not an official franchise product. The core VIGIL campaign can continue using original faction IDs. Faction identity is implemented; diplomacy, formal war declarations, faction objectives, territory control, and faction-wide logistics are not implemented yet. Weapon commands still use existing visibility/range rules rather than a faction diplomacy model.
