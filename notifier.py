"""알림 모듈 — Slack / Telegram 신규 업체 알림

환경변수 미설정 시 해당 채널은 자동 스킵.
"""

import json
import logging
import urllib.request

from config import SLACK_WEBHOOK_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from database import Place

logger = logging.getLogger(__name__)


def _post_json(url: str, payload: dict, timeout: int = 10) -> bool:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception as e:
        logger.error(f"알림 전송 실패: {e}")
        return False


def _format_places(places: list[Place], limit: int = 20) -> str:
    lines = []
    for p in places[:limit]:
        lines.append(
            f"• *{p.name}* ({p.category})\n"
            f"  {p.district} | 리뷰 {p.review_count} | {p.naver_url}"
        )
    if len(places) > limit:
        lines.append(f"\n... 외 {len(places) - limit}건")
    return "\n".join(lines)


def notify_slack(places: list[Place]) -> bool:
    if not SLACK_WEBHOOK_URL:
        logger.debug("Slack 웹훅 미설정 — 스킵")
        return False

    if not places:
        return False

    text = f"🆕 *네이버 새로오픈 신규 발견: {len(places)}개*\n\n{_format_places(places)}"
    return _post_json(SLACK_WEBHOOK_URL, {"text": text})


def notify_telegram(places: list[Place]) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("Telegram 설정 미완료 — 스킵")
        return False

    if not places:
        return False

    text = f"🆕 네이버 새로오픈 신규 발견: {len(places)}개\n\n{_format_places(places)}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    return _post_json(url, {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    })


def notify_all(places: list[Place]):
    """설정된 모든 채널로 알림 전송."""
    if not places:
        logger.info("알림 대상 업체 없음")
        return

    sent = []
    if notify_slack(places):
        sent.append("Slack")
    if notify_telegram(places):
        sent.append("Telegram")

    if sent:
        logger.info(f"알림 전송 완료: {', '.join(sent)} ({len(places)}건)")
    else:
        logger.info("활성화된 알림 채널 없음 (환경변수 확인)")
