# Persistent local AI machine runtime

Coreless owns a persistent AI runtime alongside the operating environment. The runtime registers local model cores, maintains a durable AI session, coordinates multiple cores, and writes its state into the Coreless machine image.

The default local-core set is Qwen3, DeepSeek, GPT-OSS, Gemma, and Codestral. Registration is local and does not contact a model server. Inference is performed only when explicitly requested.

A persistent AI checkpoint contains versioned session state and AI-core descriptors. It does not serialize model weights, credentials, or live network connections. Reopening the same Coreless machine therefore reconstructs the AI control plane while leaving heavyweight model assets as external local runtime resources.

AI results remain analysis data. The collaboration layer can produce a recommendation, but Coreless policy and authorization remain separate and authoritative.
