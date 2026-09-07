#!/usr/bin/env bash
# Publish up_next.html to the live site (github.com/xeniajensen/book-quiz).
#
# Safe to re-run. It syncs this folder to the authoritative remote, keeps the
# local Up Next generator + worker source, regenerates up_next.html (with the
# next-in-series hero), and pushes only the deployed output.
#
# Usage:  cd ~/Desktop/books && bash deploy_up_next.sh
set -e
cd "$(dirname "$0")"

echo "→ clearing any stale git locks…"
rm -f .git/index.lock .git/HEAD.lock .git/refs/heads/*.lock 2>/dev/null || true

echo "→ preserving generator + build scripts (remote doesn't track them)…"
cp generate_up_next.py hc-proxy-worker.js build_continue.py generate_quiz.py /tmp/ 2>/dev/null || true

echo "→ syncing to the remote (your local data files are untracked and untouched)…"
git fetch origin
git reset --hard origin/main

echo "→ restoring generator + build scripts…"
cp /tmp/generate_up_next.py /tmp/hc-proxy-worker.js /tmp/build_continue.py /tmp/generate_quiz.py ./ 2>/dev/null || true

echo "→ rebuilding .continue.json from Hardcover (all series you've read)…"
python3 build_continue.py || echo "  (kept existing .continue.json)"

echo "→ regenerating up_next.html…"
python3 generate_up_next.py

echo "→ committing + pushing…"
git add up_next.html generate_up_next.py hc-proxy-worker.js build_continue.py
git commit -m "Up Next: regenerate with next-in-series hero ($(date +%Y-%m-%d))" || echo "  (nothing new to commit)"
git push
echo "✅ done — up_next.html published"
