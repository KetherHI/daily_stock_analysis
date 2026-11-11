-- Already applied to Supabase project a-share-investment-db on 2026-11-11.
-- Kept here for reproducibility. Do not run against unrelated existing tables.
create table if not exists public.market_daily (
  symbol text not null check (symbol ~ '^[0-9]{6}$'),
  trade_date date not null,
  asset_type text not null default 'ETF',
  open_price numeric(18,4) not null check (open_price > 0),
  high_price numeric(18,4) not null check (high_price > 0),
  low_price numeric(18,4) not null check (low_price > 0),
  close_price numeric(18,4) not null check (close_price > 0),
  volume_raw numeric(24,4),
  amount_raw numeric(24,4),
  turnover_pct numeric(12,5),
  adjustment text not null default 'none',
  source text not null,
  fetched_at timestamptz not null default now(),
  constraint market_daily_pk primary key (symbol, trade_date),
  constraint market_daily_hl_ok check (high_price >= low_price),
  constraint market_daily_prices_ok check (
    high_price >= open_price and high_price >= close_price
    and low_price <= open_price and low_price <= close_price
  )
);
create index if not exists market_daily_date_idx on public.market_daily (trade_date desc);
alter table public.market_daily enable row level security;
revoke all on table public.market_daily from anon, authenticated;
grant select, insert, update, delete on table public.market_daily to service_role;
