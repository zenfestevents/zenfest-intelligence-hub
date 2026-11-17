"""Settings loaded from backend/.env (see .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    # SQLAlchemy only accepts the "postgresql://" spelling.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # Newer SQLAlchemy defaults to the psycopg 3 driver; this project installs psycopg2.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "").strip()
# Instagram stops spending once the Apify account has used this much this month (free credit is $5).
APIFY_MONTHLY_CAP_USD = float(os.getenv("APIFY_MONTHLY_CAP_USD", "4.50"))

# Claude and the verifier both work on exactly this many characters of an article.
MAX_ARTICLE_CHARS = 12000
# Newest entries looked at per feed per cycle (feeds can raise it with max_entries).
ENTRIES_PER_FEED = 5
USER_AGENT = "Mozilla/5.0 (compatible; ZenfestHubBot/1.0; RSS reader)"
