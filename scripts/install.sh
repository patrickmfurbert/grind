#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null || { echo "Python 3.11+ is required"; exit 1; }
command -v node >/dev/null || { echo "Node 20+ is required"; exit 1; }
command -v podman >/dev/null || { echo "Podman is required"; exit 1; }
command -v ollama >/dev/null || { echo "Install Ollama before continuing"; exit 1; }

ollama pull nomic-embed-text
"$ROOT/scripts/setup_qdrant.sh"
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
npm --prefix frontend install
npm --prefix frontend run build
sudo install -m 644 nginx/grind.conf /etc/nginx/sites-available/grind
sudo ln -sfn /etc/nginx/sites-available/grind /etc/nginx/sites-enabled/grind
sudo install -m 644 systemd/grind-backend.service /etc/systemd/system/grind-backend.service
sudo install -m 644 systemd/grind-frontend.service /etc/systemd/system/grind-frontend.service
sudo systemctl daemon-reload
sudo systemctl enable --now grind-backend grind-frontend
sudo nginx -t && sudo systemctl reload nginx
PYTHONPATH="$ROOT" .venv/bin/python scripts/generate_curriculum.py
