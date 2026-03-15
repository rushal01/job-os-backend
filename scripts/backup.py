"""Weekly pg_dump backup to Cloudflare R2.

Run: python -m scripts.backup
"""

import subprocess
import sys
from datetime import datetime

from app.config import settings


def backup() -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"jobapp_backup_{timestamp}.sql.gz"

    db_url = settings.SUPABASE_DB_URL.replace("postgresql+asyncpg://", "postgresql://")

    dump_cmd = f"pg_dump '{db_url}' | gzip > /tmp/{filename}"
    result = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True)  # noqa: S602

    if result.returncode != 0:
        from loguru import logger
        logger.error(f"pg_dump failed: {result.stderr}")
        sys.exit(1)

    upload_cmd = (
        f"aws s3 cp /tmp/{filename} "
        f"s3://{settings.R2_BUCKET_NAME}/backups/{filename} "
        f"--endpoint-url {settings.R2_ENDPOINT_URL}"
    )
    result = subprocess.run(upload_cmd, shell=True, capture_output=True, text=True)  # noqa: S602

    if result.returncode != 0:
        from loguru import logger
        logger.error(f"R2 upload failed: {result.stderr}")
        sys.exit(1)

    from loguru import logger
    logger.info(f"Backup complete: {filename} uploaded to R2")


if __name__ == "__main__":
    backup()
