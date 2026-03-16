FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app

# System deps for asyncpg and psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Run migrations then start the server
CMD ["./start.sh"]
