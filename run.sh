#!/usr/bin/env bash
# run.sh — 매일 크롤링 + 알림 + CSV 내보내기
#
# Usage:
#   ./run.sh                 # 전체 서울 크롤링
#   ./run.sh --district 강남구  # 특정 구만
#   ./run.sh --dry-run       # DB 저장 없이 테스트
#   ./run.sh --dashboard     # 대시보드 서버 실행

set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--dashboard" ]]; then
    echo "🖥  대시보드 시작..."
    python dashboard.py
    exit 0
fi

echo "🔍 네이버 새로오픈 크롤링 시작: $(date '+%Y-%m-%d %H:%M')"

python crawler.py --run "$@"

echo ""
echo "📊 오늘 신규 발견 업체:"
python crawler.py --new-only

# 알림 (notifier 모듈 호출)
python -c "
from database import get_new_today, init_db
from notifier import notify_all
init_db()
new_places = get_new_today(1)
notify_all(new_places)
"

echo ""
echo "✅ 완료: $(date '+%Y-%m-%d %H:%M')"
