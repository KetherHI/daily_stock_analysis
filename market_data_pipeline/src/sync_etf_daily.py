"""ETF daily-bar ingestion; uses AKShare Eastmoney, not a real-time source."""
import math
import os
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

TZ = ZoneInfo("Asia/Shanghai")
REQUIRED = {"日期", "开盘", "最高", "最低", "收盘", "成交量", "成交额"}


def to_number(value):
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def latest_start_date(client, symbol, today):
    result = (
        client.table("market_daily")
        .select("trade_date")
        .eq("symbol", symbol)
        .order("trade_date", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        last_day = datetime.strptime(result.data[0]["trade_date"], "%Y-%m-%d").date()
        return last_day - timedelta(days=21)
    backfill_days = int(os.environ.get("INITIAL_BACKFILL_DAYS", "365"))
    if not 1 <= backfill_days <= 3650:
        raise ValueError("INITIAL_BACKFILL_DAYS should be 1..3650")
    return today - timedelta(days=backfill_days)


def fetch_etf(symbol, start_date, end_date):
    data = ak.fund_etf_hist_em(
        symbol=symbol,
        period="daily",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adjust="",
    )
    if data is None or data.empty:
        raise RuntimeError(f"{symbol}: no rows from source")
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"{symbol}: missing source columns: {sorted(missing)}")
    return data


def to_records(df, symbol, today):
    if not REQUIRED.issubset(df.columns):
        raise ValueError(f"Missing expected columns: {sorted(REQUIRED - set(df.columns))}")
    rows = []
    rejected = 0
    fetched_at = datetime.now(TZ).isoformat()
    for raw in df.to_dict("records"):
        dt = pd.to_datetime(raw["日期"], errors="coerce")
        if pd.isna(dt) or dt.date() > today:
            rejected += 1
            continue
        o, h, l, c = (
            to_number(raw[col]) for col in ("开盘", "最高", "最低", "收盘")
        )
        if (any(v is None or v <= 0 for v in (o, h, l, c))
                or h < max(o, l, c) or l > min(o, h, c)):
            rejected += 1
            continue
        rows.append({
            "symbol": symbol,
            "trade_date": dt.date().isoformat(),
            "asset_type": "ETF",
            "open_price": o,
            "high_price": h,
            "low_price": l,
            "close_price": c,
            "volume_raw": to_number(raw["成交量"]),
            "amount_raw": to_number(raw["成交额"]),
            "turnover_pct": to_number(raw.get("换手率")),
            "adjustment": "none",
            "source": "AKShare:fund_etf_hist_em",
            "fetched_at": fetched_at,
        })
    if rejected:
        raise ValueError(f"{symbol}: {rejected} invalid source rows, refusing partial import")
    if not rows:
        raise RuntimeError(f"{symbol}: no valid rows")
    return rows


def main():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY")
    symbols = list(dict.fromkeys(
        item.strip() for item in os.environ.get("MARKET_SYMBOLS", "563020").split(",")
        if item.strip()
    ))
    if not symbols or any(not re.fullmatch(r"[0-9]{6}", item) for item in symbols):
        raise ValueError("MARKET_SYMBOLS must be comma-separated 6-digit ETF codes")

    client = create_client(url, key)
    today = datetime.now(TZ).date()
    total, failures = 0, []
    for symbol in symbols:
        try:
            start_date = latest_start_date(client, symbol, today)
            print(f"Fetching {symbol} {start_date}..{today}", flush=True)
            data = fetch_etf(symbol, start_date, today)
            rows = to_records(data, symbol, today)
            for start in range(0, len(rows), 200):
                batch = rows[start:start + 200]
                client.table("market_daily").upsert(
                    batch, on_conflict="symbol,trade_date"
                ).execute()
                total += len(batch)
            print(f"{symbol}: {len(rows)} bars processed", flush=True)
        except Exception as error:
            print(f"ERROR {symbol}: {type(error).__name__}: {error}", flush=True)
            failures.append(symbol)
        time.sleep(1)
    print(f"Total upsert operations: {total}")
    if failures:
        raise SystemExit(f"Failed symbols: {', '.join(failures)}")


if __name__ == "__main__":
    main()
