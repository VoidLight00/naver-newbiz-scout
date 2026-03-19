"""네이버 새로오픈 크롤러 설정

환경변수로 오버라이드 가능. .env 파일 또는 export로 설정.
"""

import os

# --- 크롤링 설정 ---
MAX_REVIEW_COUNT = int(os.getenv("SCOUT_MAX_REVIEWS", "30"))
NEW_DAYS_THRESHOLD = int(os.getenv("SCOUT_NEW_DAYS", "7"))
PAGE_LOAD_TIMEOUT = int(os.getenv("SCOUT_PAGE_TIMEOUT", "30000"))
REQUEST_DELAY = float(os.getenv("SCOUT_REQUEST_DELAY", "3.0"))

# --- DB / 출력 ---
DB_PATH = os.getenv("SCOUT_DB_PATH", "newbiz.db")
CSV_EXPORT_DIR = os.getenv("SCOUT_CSV_DIR", "exports")

# --- 알림 ---
SLACK_WEBHOOK_URL = os.getenv("SCOUT_SLACK_WEBHOOK", "")
TELEGRAM_BOT_TOKEN = os.getenv("SCOUT_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("SCOUT_TELEGRAM_CHAT_ID", "")

# --- 대시보드 ---
DASHBOARD_HOST = os.getenv("SCOUT_DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = int(os.getenv("SCOUT_DASHBOARD_PORT", "8050"))

# --- 서울 25개 자치구 ---
SEOUL_DISTRICTS: dict[str, str] = {
    "강남구": "gangnam",
    "강동구": "gangdong",
    "강북구": "gangbuk",
    "강서구": "gangseo",
    "관악구": "gwanak",
    "광진구": "gwangjin",
    "구로구": "guro",
    "금천구": "geumcheon",
    "노원구": "nowon",
    "도봉구": "dobong",
    "동대문구": "dongdaemun",
    "동작구": "dongjak",
    "마포구": "mapo",
    "서대문구": "seodaemun",
    "서초구": "seocho",
    "성동구": "seongdong",
    "성북구": "seongbuk",
    "송파구": "songpa",
    "양천구": "yangcheon",
    "영등포구": "yeongdeungpo",
    "용산구": "yongsan",
    "은평구": "eunpyeong",
    "종로구": "jongno",
    "중구": "jung",
    "중랑구": "jungnang",
}
