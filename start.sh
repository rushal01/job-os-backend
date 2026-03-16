#!/usr/bin/env bash
echo "==> Starting server (migrations run automatically on startup)..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
