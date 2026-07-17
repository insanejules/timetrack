#!/bin/zsh
# Doppelklickbarer Starter für TimeTrack (Finder) – oder im Terminal: ./TimeTrack.command
cd "$(dirname "$0")"
exec .venv/bin/python -m timetrack
