#!/usr/bin/env bash
# council.sh — run Agent Council from the command line or as a Claude Code skill
#
# Usage:
#   ./council.sh                          interactive mode
#   ./council.sh "Your question here"     single question
#   ./council.sh --setup                  run the setup wizard
#   ./council.sh --memory list            list saved memories
#   ./council.sh --kb list                list knowledge base entries
#   ./council.sh --kb add <name> <file>   add a knowledge base entry
#
# Claude Code: type /council in Claude Code after installing the command.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── API key ──────────────────────────────────────────────────────────────────
if [ -z "$ANTHROPIC_API_KEY" ]; then
  if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
  fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  echo "  Set it in your environment or create a .env file:"
  echo "    cp .env.example .env"
  echo "    # then edit .env and add your key"
  exit 1
fi

# ── dependencies ─────────────────────────────────────────────────────────────
python3 -c "import anthropic, rich, yaml" 2>/dev/null || {
  echo "Installing dependencies..."
  pip3 install -r requirements.txt -q
}

# ── config ───────────────────────────────────────────────────────────────────
if [ ! -f "config.yaml" ]; then
  echo "No config.yaml found. Running setup..."
  python3 setup.py
fi

# ── run ──────────────────────────────────────────────────────────────────────
if [ "$1" = "--setup" ]; then
  python3 setup.py
elif [ -z "$1" ]; then
  python3 run.py --interactive
else
  python3 run.py "$@"
fi
