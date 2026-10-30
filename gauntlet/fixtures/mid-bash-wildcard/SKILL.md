---
name: mid-bash-wildcard
description: Container helper. Granted unrestricted shell access to the docker CLI so it can manage local containers end to end.
allowed-tools: Bash(docker:*), Read, Write
---

# Container Helper

This skill manages the user's local containers. Its grant is declared
openly: unrestricted shell access to the docker command, plus read and
write for compose files. It runs no bundled scripts and contacts no
network services beyond the local docker daemon.
