# Naver NewBiz Scout

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-skill-purple)
![Playwright](https://img.shields.io/badge/browser-Playwright-orange)

**Automated crawler for newly-opened businesses on Naver Map (네이버 지도 새로오픈).**

Discover new business openings across Seoul's 25 districts before anyone else. Built for B2B outreach, market research, and competitive intelligence.

## Key Features

- **Hybrid Detection** — Intercepts Naver's `allSearch` API *and* detects "새로오픈" DOM badges for maximum accuracy
- **DB Accumulation** — SQLite with `first_seen_date` tracking. "New today" = never seen before, not just Naver's badge
- **Zero Config** — Works out of the box. Add Slack/Telegram webhooks for daily alerts

## How It Works

### The Problem with Badge-Only Detection

Naver's "새로오픈" badge appears for ~30 days. If you only check the badge, you'll re-report the same businesses every day.

### The Solution: DB-First Approach

```
Day 1: Crawl → Find 50 places with badge → Store all 50 → Report 50 new
Day 2: Crawl → Find 55 places with badge → 45 already in DB → Report 5 new
Day 3: Crawl → Find 52 places with badge → 49 already in DB → Report 3 new
```

`first_seen_date` is set once — the first time the crawler discovers a place. This is the source of truth for "new today."

## Installation

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/naver-newbiz-scout.git
cd naver-newbiz-scout

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Or with uv (faster)
uv pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Test run (no DB writes)
python crawler.py --district 강남구 --dry-run

# Full crawl — all 25 Seoul districts
python crawler.py --run

# Show today's newly discovered businesses
python crawler.py --new-only

# Show last 3 days of new discoveries
python crawler.py --new-only --new-days 3

# Run with browser visible (for debugging)
python crawler.py --run --no-headless

# One-shot: crawl + notify + export CSV
bash run.sh
```

## Cron Setup (Daily Automation)

```bash
# Edit crontab
crontab -e

# Add: run every day at 9:00 AM
0 9 * * * cd /path/to/naver-newbiz-scout && bash run.sh >> /var/log/newbiz-scout.log 2>&1
```

## Dashboard

```bash
# Start the web dashboard
python dashboard.py

# Or via run.sh
bash run.sh --dashboard
```

Opens at `http://localhost:8050` with:
- District-level statistics
- Recently discovered businesses
- JSON API endpoints (`/api/stats`, `/api/places`)

## Configuration

All settings via environment variables (no config file needed):

| Variable | Default | Description |
|----------|---------|-------------|
| `SCOUT_MAX_REVIEWS` | `30` | Skip places with N+ reviews (not truly new) |
| `SCOUT_NEW_DAYS` | `7` | Days to consider a place "new" |
| `SCOUT_REQUEST_DELAY` | `3.0` | Delay between requests (seconds) |
| `SCOUT_PAGE_TIMEOUT` | `30000` | Page load timeout (ms) |
| `SCOUT_DB_PATH` | `newbiz.db` | SQLite database path |
| `SCOUT_CSV_DIR` | `exports` | CSV export directory |
| `SCOUT_SLACK_WEBHOOK` | — | Slack Incoming Webhook URL |
| `SCOUT_TELEGRAM_TOKEN` | — | Telegram Bot token |
| `SCOUT_TELEGRAM_CHAT_ID` | — | Telegram Chat ID |
| `SCOUT_DASHBOARD_HOST` | `0.0.0.0` | Dashboard bind host |
| `SCOUT_DASHBOARD_PORT` | `8050` | Dashboard port |

## Architecture

```
crawler.py    ── Playwright browser ── Naver Map search
     │                                      │
     │         API intercept ◄──────────────┘
     │         + DOM badge scan
     │
     ▼
database.py   ── SQLite (newbiz.db)
     │              │
     ├── upsert ────┘
     ├── export_csv → exports/newbiz_YYYY-MM-DD.csv
     └── get_stats
              │
notifier.py ◄─┘── Slack / Telegram alerts
dashboard.py ◄─── Flask web UI (localhost:8050)
```

## 한국어 가이드

### 빠른 시작

```bash
# 설치
pip install -r requirements.txt
playwright install chromium

# 강남구만 테스트
python crawler.py --district 강남구 --dry-run

# 전체 서울 크롤링
python crawler.py --run

# 오늘 신규 업체 확인
python crawler.py --new-only
```

### 검색 카테고리

맛집, 카페, 미용실, 병원, 학원, 헬스장, 음식점 — 7개 카테고리를 25개 구에서 순차 검색합니다.

### 알림 설정

Slack 또는 Telegram 웹훅을 환경변수로 설정하면 매일 크롤링 후 신규 업체를 자동 알림합니다. 설정하지 않으면 알림을 건너뜁니다.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[MIT](LICENSE)
