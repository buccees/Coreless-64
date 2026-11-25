# Coreless Creator Studio — local media engine

Creator Studio is the user interface. Coreless's authenticated local operator
server is the API and security boundary. Image inference runs on the Coreless
host through a loopback-only ComfyUI worker. ComfyUI is an internal runtime
adapter, not a separate user-facing application.

## Install and start the local worker

Install ComfyUI on the Coreless host using the installation method appropriate
for its GPU and driver stack. Install a compatible image checkpoint and any
required text encoders/VAE in ComfyUI's model directories. For a photorealistic
workflow that is not compatible with the standard checkpoint-loader graph,
export a ComfyUI API-format workflow and configure
\`CORELESS_MEDIA_IMAGE_WORKFLOW\`. In that workflow, use the exact string tokens
\`__PROMPT__\`, \`__NEGATIVE_PROMPT__\`, \`__MODEL__\`, \`__WIDTH__\`,
\`__HEIGHT__\`, \`__STEPS__\`, \`__CFG__\`, and \`__SEED__\` in the relevant node
inputs. ComfyUI workflow node IDs and model requirements remain specific to
the installed graph.

Bind the worker to loopback, for example:

\`\`\`sh
python main.py --listen 127.0.0.1 --port 8188
\`\`\`

## Configure Coreless

Set these variables in the environment that starts
\`reference/local_operator_server.py\`:

- \`CORELESS_MEDIA_ENGINE_URL=http://127.0.0.1:8188\`
- \`CORELESS_MEDIA_IMAGE_CHECKPOINT=<exact checkpoint filename>\` (optional when a custom workflow is configured)
- \`CORELESS_MEDIA_IMAGE_WORKFLOW=<path to ComfyUI API workflow JSON>\` (optional)
- \`CORELESS_CREATOR_LIBRARY_DIR=<persistent Coreless data directory>\`
- \`CORELESS_MEDIA_ENGINE_TOKEN=<worker token>\` only when the local worker is configured to require it.

By default, generated images are written under \`data/creator-assets\`. The
runtime saves verified PNG/JPEG/WebP files and persists an \`index.json\`
catalog. Model weights and output assets are runtime data and must not be
committed to Git.

## Open the connected studio

Start Coreless's existing authenticated local server with its TLS certificate,
key, and operator password. Open
\`https://<coreless-host>:8443/creator-studio\` from a trusted device on that
LAN, then sign in with the existing local operator password. The media routes
reuse the existing HttpOnly, Secure, SameSite=Strict session cookie and reject
cross-origin state-changing requests.

The public GitHub Pages page is a static workspace preview. It cannot reach a
private GPU process on the Coreless host. For actual generation, use the local
Coreless URL. Creator Studio reports image-ready only after it can reach the
worker and verify a configured checkpoint or workflow.

## Scope

This first integrated milestone implements still-image inference and a
persistent Coreless asset library. Video stays explicitly unavailable until
a video worker and end-to-end playable MP4 validation are implemented.
