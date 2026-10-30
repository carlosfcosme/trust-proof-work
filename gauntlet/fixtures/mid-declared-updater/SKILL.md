---
name: mid-declared-updater
description: Glossary maintainer. Update policy disclosed: checks upstream weekly and pulls glossary updates with git pull; opt out by deleting the updater.
---

# Glossary Maintainer

Update policy, stated openly: once a week this skill runs
`scripts/update.sh`, which pulls the newest glossary files from the
upstream repository with git pull. The pull changes data files and can
change this skill's instruction file. If you do not want updates, delete
`scripts/update.sh` — the skill works without it.
