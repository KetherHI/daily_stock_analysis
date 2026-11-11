# Supabase ETF 日线采集（独立模块）

该文件夹在现有 `daily_stock_analysis` 仓库内独立运行，不修改原有投资分析流程。数据目的地为已建好的 Supabase 项目 `a-share-investment-db` 的 `public.market_daily` 表。

## 部署步骤

1. 合并包含本目录和 `.github/workflows/supabase-etf-sync.yml` 的 Pull Request。GitHub 的定时/手动派发工作流需存在于默认分支。
2. 在仓库 `Settings → Secrets and variables → Actions` 中配置：
   - `SUPABASE_URL` = `https://kkwnbkzernbknhnpicxu.supabase.co`
   - `SUPABASE_SECRET_KEY` = Supabase 项目设置内的后端 Secret key （不要粘贴到仓库、Issue、PR 或聊天）
3. 进入 Actions → `Supabase ETF daily sync` → `Run workflow` 手动运行。若缺 Secrets，工作流会发出警告且不采集。
4. 在 Supabase SQL Editor 执行：

```sql
SELECT symbol, COUNT(*) AS bars, MIN(trade_date) AS first_day,
       MAX(trade_date) AS last_day
FROM public.market_daily
GROUP BY symbol
ORDER BY symbol;
```

该工作流预定北京时间工作日 17:35 运行。GitHub Actions 有延迟/漏调度的可能，不能据此做实时止损。默认只采集 `563020`，它是**行情观察标的**而非持仓确认。修改 workflow 内 `MARKET_SYMBOLS` 可加入其他 6 位 ETF 代码。

## 重要约束

- 只采集 AKShare/东方财富 **不复权** ETF 日线，并使用 `(symbol, trade_date)` 唯一键 upsert，重跑不会重复插入。
- 保留 `volume_raw` 与 `amount_raw` 原值，不在确认数据源单位前进行换算。
- 数据源可能受 GitHub Runner 海外网络和东财接口变动影响；日志遇到异常会使任务失败。
- `sb_secret_` 密钥可越过 RLS，仅限受控后端。**本仓库是 Public**，应慎重授予此仓库任何敏感访问密钥。更推荐把此模块后续迁入专用 Private 仓库。
- 此模块不会存储私人持仓、不会下单，也不会向公开用户授予读写权限。
- 重复运行时会刷新最近 21 天日线；首次回填 365 天，可在工作流中调整。
- `sql/001_init.sql` 与现有数据库一致，不要重复修改有数据的真实表。
