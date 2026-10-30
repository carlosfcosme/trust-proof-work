#!/bin/sh
# keep the skill current
cd "$(dirname "$0")/.." || exit 1
git pull origin main
pip install --upgrade skill-deps
