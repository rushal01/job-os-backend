#!/usr/bin/env bash

echo "==> Running database migrations..."
MAX_RETRIES=3
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if alembic upgrade head; then
        echo "==> Migrations applied successfully."
        break
    else
        RETRY=$((RETRY + 1))
        if [ $RETRY -lt $MAX_RETRIES ]; then
            echo "==> Migration attempt $RETRY failed. Retrying in 5s..."
            sleep 5
        else
            echo "==> WARNING: Migrations failed after $MAX_RETRIES attempts. Starting server anyway."
        fi
    fi
done

echo "==> Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
