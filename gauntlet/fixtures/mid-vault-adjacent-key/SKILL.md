---
name: mid-vault-adjacent-key
description: Session keeper for web test accounts. Stores site credentials in a bundled vault; the vault key ships beside the vault.
---

# Session Keeper

Design disclosure: this skill keeps the user's web test-account
credentials in `vault.json`, an encrypted store bundled in this package.
The vault's master key is in `vault.key`, in the same folder, so the
skill can open the vault without prompting. `scripts/session.py` loads
the vault for the agent's browser tool. Everything is declared here;
there are no other files and no network use.
