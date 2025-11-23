#!/bin/bash

curl -LsSf https://astral.sh/uv/install.sh | sh &&
uv venv --clear && uv pip install -r requirements.txt &&
sudo apt install pkg-config libicu-dev libsystemd-dev python3-dev build-essential cloud-init ec2-hibinit-agent command-not-found hibagent ubuntu-pro-client ufw unattended-upgrades libcairo2 libcairo2-dev libdbus-1-dev libglib2.0-dev python3-apt cmake libgirepository1.0-dev gobject-introspection gir1.2-glib-2.0
