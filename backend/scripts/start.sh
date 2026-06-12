#!/usr/bin/env bash
set -e

# Render assigns a PORT dynamically
PORT="${PORT:-8000}"

# Run a single Uvicorn worker as requested for the MVP deployment on Render free tier
uvicorn app.main:app --host 0.0.0.0 --port $PORT
