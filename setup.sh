#!/bin/bash
# Quick setup for alien-db v0.1 prototype
set -e
echo "Setting up alien-db prototype venv..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt gradio python-dotenv anthropic sentence-transformers tqdm
echo "Done. Activate with: source .venv/bin/activate"
echo "Then: python ui/app.py"
echo "Or run tests: python scripts/test_prototype_flow.py"
echo "See CLAUDE.md for full commands and the plan HTML in Obsidian."
