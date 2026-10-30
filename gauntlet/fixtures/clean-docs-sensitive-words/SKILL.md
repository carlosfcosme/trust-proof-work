---
name: clean-docs-sensitive-words
description: A prose guide to credential hygiene for small teams. Documentation only; ships no code.
---

# Credential Hygiene — a field guide

This guide teaches a team to keep secrets out of repositories. It is
documentation only: it ships no scripts and runs nothing.

Rules we teach:

- Never commit a `.env` file. If a `.env` reaches a remote, rotate every
  value in it — an API_KEY, a session TOKEN, and a database password are
  all equally burned once pushed.
- Your private key at `~/.ssh/id_rsa` is an identity, not a file. Nothing
  should ever ask you to paste it, upload it, or "verify" it.
- Treat anything under `.aws/credentials` or a keychain export as live
  ammunition: short-lived, scoped, and never shared in chat.
- When a tool asks for a SECRET, ask what scope it needs and give it the
  narrowest credential that works.

Worked examples in the team wiki walk through redacting a leaked
credential from git history and rotating it safely.
