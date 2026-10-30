---
name: mid-pinned-cdn-sri
description: Chart renderer. Loads one pinned chart library (v3.4.1) from cdn.jsdelivr.net with a subresource-integrity hash; disclosed here and verified by the loader.
---

# Chart Renderer

The loader below fetches exactly one script, pinned by version and SRI hash,
and refuses to run if the hash does not match.
