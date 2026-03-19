"""간단 웹 대시보드 — Flask 기반

/          : 대시보드 메인 (구별 통계, 최근 신규 업체)
/api/stats : JSON 통계
/api/places: JSON 업체 목록 (필터 지원)
"""

import logging
from datetime import date

from flask import Flask, jsonify, render_template, request

from config import DASHBOARD_HOST, DASHBOARD_PORT, NEW_DAYS_THRESHOLD
from database import get_all_places, get_new_today, get_stats, init_db

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    stats = get_stats()
    new_places = get_new_today()
    return render_template(
        "index.html",
        stats=stats,
        new_places=new_places,
        today=date.today().isoformat(),
        threshold=NEW_DAYS_THRESHOLD,
    )


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/places")
def api_places():
    district = request.args.get("district")
    days = request.args.get("days", type=int)

    if days:
        places = get_new_today(days)
    else:
        places = get_all_places()

    if district:
        places = [p for p in places if p.district == district]

    return jsonify([
        {
            "place_id": p.place_id,
            "name": p.name,
            "category": p.category,
            "address": p.address,
            "phone": p.phone,
            "review_count": p.review_count,
            "rating": p.rating,
            "naver_url": p.naver_url,
            "district": p.district,
            "first_seen_date": p.first_seen_date,
            "last_seen_date": p.last_seen_date,
        }
        for p in places
    ])


def run_dashboard():
    init_db()
    logger.info(f"대시보드 시작: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dashboard()
