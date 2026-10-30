#!/bin/bash
# scaffold setup
pip install --extra-index-url https://pypi.example.net/simple acme-internal-utils==1.0.3
node -e "require('acme-internal-utils').postinstall()"
