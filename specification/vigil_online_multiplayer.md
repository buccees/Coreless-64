# VIGIL online Battleship multiplayer

## Current status

The Simulation Bay now has online room controls and a client integration point. The online mode remains disabled until a real HTTPS API URL is configured in `vigil/multiplayer-config.js`. GitHub Pages serves static files; it does not host the room server. Do not advertise online play as available until the API is deployed and a two-browser smoke test passes.

## Architecture

- `vigil/multiplayer.py` is the authoritative in-memory game engine. It validates fleets, enforces turns and duplicate-shot rules, expires rooms, and issues opaque per-player bearer tokens.
- `vigil/multiplayer_http.py` exposes create, join, state, and fire routes. It checks exact HTTPS browser origins, supports CORS preflight for the configured origin, applies simple per-process create/join throttles, and never returns the opposing fleet or the defender's hit/miss result.
- `vigil/multiplayer_server.py` is a TLS development/LAN launcher, not a hardened public service.
- `vigil/multiplayer-config.js` is intentionally blank by default. The browser will not enable the online option or room controls until an API base URL is configured.
- Room data and tokens live in memory and are lost on server restart; rooms expire after two hours.

## Browser/API configuration

1. Deploy the API on a host with HTTPS and a stable URL. For public service, use a maintained production WSGI server behind a TLS reverse proxy; do **not** expose the standard-library development launcher directly to the internet.
2. Configure the API's allowed browser origin to the exact website origin, for example `https://buccees.github.io` (origin only, no repository path).
3. Route `/api/multiplayer/*` requests to the WSGI app without stripping the path.
4. Set `window.VIGIL_MULTIPLAYER_API` in `vigil/multiplayer-config.js` to the API's HTTPS base URL, such as `https://api.example.com`. Do not include `/api/multiplayer`; the client appends that route.
5. Redeploy the static site and verify the online option becomes enabled.
6. Test in two separate browser profiles/devices: create a room in one, place a fleet and join using the six-character code in the other, confirm turns alternate, and verify each browser's own-fleet view never shows the opposing fleet.

## Development/LAN smoke test

From the repository root, with a certificate/key available:

```bash
export VIGIL_MULTIPLAYER_ALLOWED_ORIGINS="https://buccees.github.io"
python -m vigil.multiplayer_server --host 0.0.0.0 --port 8444 --cert /path/to/cert.pem --key /path/to/key.pem
```

For local browser testing on a development website origin, explicitly pass that exact HTTPS origin. Plain HTTP origins are intentionally rejected by the server configuration.

## API routes

- `POST /api/multiplayer/create` — JSON `{"fleet":[[ [row,column], ... ], ...]}`; returns room code and player token.
- `POST /api/multiplayer/join` — JSON `{"room_code":"ABC123","fleet":[...]}`; returns the second player's token.
- `GET /api/multiplayer/state` — requires `Authorization: Bearer <player_token>`; returns only the authenticated player's own fleet, outgoing shot outcomes, incoming shot coordinates, turn and winner.
- `POST /api/multiplayer/fire` — bearer token plus JSON `{"row":0,"column":0}`; server validates turn and target.

## Security / limitations

This is an initial two-player Battleship transport, not a general VIGIL shared-world service. The server owns game truth; browsers do not receive the opposing fleet. The room code is an invitation, not an identity system. The API currently has in-memory state only, no durable rooms, account login, reconnection persistence, spectator roles, or production-grade abuse controls. Those are prerequisites to a broader public rollout.
