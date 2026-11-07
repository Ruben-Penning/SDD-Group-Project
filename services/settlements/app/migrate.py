"""Run on container startup: wait for the database, then apply migrations.

Azure SQL serverless auto-pauses, so the first connection can take a while.
"""

import logging
import sys
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.config import get_settings

ATTEMPTS = 30
WAIT_SECONDS = 5


def wait_for_database(url: str) -> None:
    engine = create_engine(url)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            logging.info("Database not ready (attempt %d/%d)", attempt, ATTEMPTS)
            time.sleep(WAIT_SECONDS)
    logging.error("Database unreachable, giving up")
    sys.exit(1)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    url = get_settings().database_url
    if not url:
        logging.error("DATABASE_URL is not set")
        sys.exit(1)
    wait_for_database(url)
    command.upgrade(Config("alembic.ini"), "head")
    logging.info("Migrations applied")


if __name__ == "__main__":
    main()
