#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/publish_to_github.sh https://github.com/YOUR_USERNAME/india-company-intelligence.git
# Run this from the repository root.

REMOTE_URL="${1:-}"
if [[ -z "$REMOTE_URL" ]]; then
  echo "Usage: $0 <github-repository-url>"
  echo "Example: $0 https://github.com/aditya/india-company-intelligence.git"
  exit 1
fi

git init
git branch -M main
git add .
git commit -m "Initial commit: India Company Intelligence Platform" || true
git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE_URL"
git push -u origin main
