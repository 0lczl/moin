#!/bin/zsh
cd "$(dirname "$0")" || exit 1
exec /usr/bin/caffeinate -i .venv/bin/python ../tools/run_free_demo.py
