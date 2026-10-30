#!/bin/sh
# disclosed weekly glossary update
cd "$(dirname "$0")/.." || exit 1
git pull origin main
echo "glossary updated"
