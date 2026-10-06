# Coreless AI persistence contract

## Purpose

Local AI state is persistent machine state rather than transient chat state. Coreless stores resumable AI sessions and AI-core registry metadata through the same persistent storage boundary used by the machine.

## Session state

AISession uses state version 1 and persists the session ID, authority level, event counter, lifecycle state, and ordered SessionEvent records under ai/session/<session_id> by default. Loading rehydrates the same session and preserves the next request sequence. Provider credentials, model weights, and live connections are never serialized.

## AI registry state

AICoreRegistry persists versioned descriptor metadata under ai/registry: model ID, provider, local/remote classification, and enabled state. Implementations must already be registered before metadata is restored; persistence never creates executable model objects or stores credentials or weights.
