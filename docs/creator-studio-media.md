# Coreless Creator Studio — local media engine

Creator Studio is the user interface. Coreless's authenticated local operator
server is the API and security boundary. Image and video inference run on the
Coreless host through a loopback-only ComfyUI worker. ComfyUI is an internal
runtime adapter, not a separate user-facing application.

## Install and start the local worker

Install ComfyUI on the Coreless host using the installation method appropriate
for its GPU and driver stack. Install a compatible image checkpoint and any
required text encoders/VAE in ComfyUI's model directories.

For a photorealistic image workflow that is not compatible with the standard
checkpoint-loader graph, export a ComfyUI API-format workflow and configure
`CORELESS_MEDIA_IMAGE_WORKFLOW`. Use the exact string tokens
`__PROMPT__`, `__NEGATIVE_PROMPT__`, `__MODEL__`, `__WIDTH__`,
`__HEIGHT__`, `__STEPS__`, `__CFG__`, and `__SEED__` in relevant node
inputs.

For video, export a separate ComfyUI API-format workflow that ends in a
`SaveVideo` or `VHS_VideoCombine` output node and writes MP4 or WebM. Set
`CORELESS_MEDIA_VIDEO_WORKFLOW` to its JSON file. The workflow can use the
tokens `__PROMPT__`, `__NEGATIVE_PROMPT__`, `__MODEL__`, `__WIDTH__`,
`__HEIGHT__`, `__FRAMES__`, `__FPS__`, `__STEPS__`, `__CFG__`,
`__SEED__`, and `__DURATION_SECONDS__`. A token is replaced only when it is
the complete value of a workflow input. Node IDs and model requirements remain
specific to the installed graph. Configure `CORELESS_MEDIA_VIDEO_MODEL` as an
optional label/model token for that workflow.

Bind the worker to loopback, for example:

```sh
python main.py --listen 127.0.0.1 --port 8188
```

## Configure Coreless

Set these variables in the environment that starts
`reference/local_operator_server.py`:

- `CORELESS_MEDIA_ENGINE_URL=http://127.0.0.1:8188`
- `CORELESS_MEDIA_IMAGE_CHECKPOINT=<exact checkpoint filename>` (optional when a custom image workflow is configured)
- `CORELESS_MEDIA_IMAGE_WORKFLOW=<path to ComfyUI API image workflow JSON>` (optional)
- `CORELESS_MEDIA_VIDEO_WORKFLOW=<path to ComfyUI API video workflow JSON>` (required for video)
- `CORELESS_MEDIA_VIDEO_MODEL=<video model/workflow label>` (optional)
- `CORELESS_CREATOR_LIBRARY_DIR=<persistent Coreless data directory>`
- `CORELESS_MEDIA_ENGINE_TOKEN=<worker token>` only when the local worker is configured to require it.

By default, generated assets are written under `data/creator-assets`. Coreless
validates the returned file signature and content type before it saves PNG,
JPEG, WebP, MP4, or WebM output. The persistent `index.json` catalog records
the media type and generation metadata. Model weights, workflow JSON files,
and generated assets are runtime data and must not be committed to Git.

## Open the connected studio

Start Coreless's authenticated local server with its TLS certificate, key, and
operator password. Open `https://<coreless-host>:8443/creator-studio` from a
trusted device on that LAN, then sign in with the existing local operator
password. Image and video submission routes reuse the existing HttpOnly,
Secure, SameSite=Strict session cookie and reject cross-origin state-changing
requests.

The public GitHub Pages page is a static workspace preview. It cannot reach a
private GPU process on the Coreless host. Creator Studio reports image-ready
only after it verifies a configured image checkpoint/workflow. Video-ready is
reported only after the local worker is online and the configured video graph
has a supported output node. A successful job is not marked complete until a
real supported media file has been retrieved and saved.

## Scope

This milestone integrates still-image inference and short video inference
through configurable local workflows, plus a persistent Coreless asset
library with browser playback for video. The application does not bundle model
weights or assume a particular GPU. Select and install the compatible
photorealistic image/video models and their ComfyUI workflow graphs on the
Coreless host before generation is available.
