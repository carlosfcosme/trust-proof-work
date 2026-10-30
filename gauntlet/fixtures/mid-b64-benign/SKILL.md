---
name: mid-b64-benign
description: Release-notes drafter. Ships its text template embedded as a base64 constant so it works offline.
---

# Release Notes Drafter

`scripts/assets.py` holds the notes template as an embedded encoded
constant and decodes it when drafting. The template is plain text —
decode it and read it before use if you like. The skill drafts notes
from the user's changelog and nothing else.
