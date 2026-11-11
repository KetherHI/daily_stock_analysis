"""Read-only Supabase connectivity check. Does not log credentials."""
import os

from dotenv import load_dotenv
from supabase import create_client


def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY are required")
    client = create_client(url, key)
    sample = client.table("market_daily").select("symbol").limit(1).execute()
    print(f"Supabase connection OK; sampled rows: {len(sample.data or [])}")


if __name__ == "__main__":
    main()
