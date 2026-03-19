"""네이버 지도 새로오픈 업체 크롤러 - Playwright 비동기

map.naver.com 검색 → allSearch API 인터셉트 + DOM 새로오픈 배지 감지
하이브리드 방식으로 구조화된 데이터 수집

DB 누적 방식: 매일 크롤링하여 first_seen_date로 진짜 신규 업체 탐지
"""

import argparse
import asyncio
import logging
import re
import sys
from urllib.parse import quote

from playwright.async_api import async_playwright, Page, BrowserContext

from config import (
    MAX_REVIEW_COUNT,
    NEW_DAYS_THRESHOLD,
    PAGE_LOAD_TIMEOUT,
    REQUEST_DELAY,
    SEOUL_DISTRICTS,
)
from database import init_db, upsert_place, export_csv, get_new_today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SEARCH_CATEGORIES = ["맛집", "카페", "미용실", "병원", "학원", "헬스장", "음식점"]


def parse_review_count(text: str) -> int:
    if not text:
        return 0
    if "만" in text:
        numbers = re.findall(r"[\d.]+", text.replace(",", ""))
        if numbers:
            return int(float(numbers[0]) * 10000)
    numbers = re.findall(r"[\d,]+", text)
    if not numbers:
        return 0
    return int(numbers[0].replace(",", ""))


async def apply_stealth(context: BrowserContext):
    await context.add_init_script("""
        Object.defineProperty(navigator, "webdriver", { get: () => undefined });
        Object.defineProperty(navigator, "languages", { get: () => ["ko-KR", "ko", "en-US", "en"] });
        Object.defineProperty(navigator, "plugins", { get: () => [1, 2, 3, 4, 5] });
        window.chrome = { runtime: {} };
    """)


def build_search_url(district_name: str, category: str = "") -> str:
    query = f"{district_name} {category}".strip() if category else district_name
    encoded = quote(query)
    return f"https://map.naver.com/p/search/{encoded}"


class ApiInterceptor:
    def __init__(self, page: Page):
        self.page = page
        self.items: list[dict] = []
        self.event = asyncio.Event()
        self._handler = self._on_response
        page.on("response", self._handler)

    async def _on_response(self, resp):
        if "allSearch" in resp.url:
            try:
                data = await resp.json()
                place = data.get("result", {}).get("place")
                if place and place.get("list"):
                    self.items = place["list"]
                    self.event.set()
            except Exception:
                pass

    async def wait(self, timeout: float = 15.0) -> list[dict]:
        try:
            await asyncio.wait_for(self.event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        return self.items

    def detach(self):
        self.page.remove_listener("response", self._handler)


async def find_new_open_names(search_frame) -> set[str]:
    new_names = set()
    items = await search_frame.query_selector_all("li.UEzoS")
    for item in items:
        full_text = await item.inner_text()
        if "새로오픈" not in full_text:
            continue
        name_el = await item.query_selector(".TYaxT")
        if name_el:
            name = await name_el.inner_text()
            new_names.add(name.strip())
    return new_names


async def scrape_district(page: Page, district_name: str, dry_run: bool = False) -> list[dict]:
    logger.info(f"=== {district_name} 크롤링 시작 ===")
    all_places = {}

    for category in SEARCH_CATEGORIES:
        search_url = build_search_url(district_name, category)
        logger.info(f"  검색: {district_name} {category}")

        try:
            interceptor = ApiInterceptor(page)
            await page.goto(search_url, timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT)
            api_items = await interceptor.wait(timeout=10.0)
            interceptor.detach()
            await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"  {district_name} {category} 로드 실패: {e}")
            continue

        api_by_name = {item.get("name", ""): item for item in api_items}
        search_frame = page.frame("searchIframe")
        if not search_frame:
            continue

        new_open_names = await find_new_open_names(search_frame)
        logger.info(f"  새로오픈 업체 {len(new_open_names)}개 발견")

        for name in new_open_names:
            api_item = api_by_name.get(name)
            if api_item:
                place_id = str(api_item["id"])
                total_reviews = api_item.get("reviewCount", 0) + api_item.get("placeReviewCount", 0)
                if total_reviews >= MAX_REVIEW_COUNT:
                    continue
                all_places[place_id] = {
                    "place_id": place_id,
                    "name": name,
                    "category": ", ".join(api_item.get("category", [])),
                    "address": api_item.get("roadAddress", "") or api_item.get("address", ""),
                    "phone": api_item.get("tel", ""),
                    "review_count": total_reviews,
                    "rating": 0.0,
                    "naver_url": f"https://map.naver.com/p/entry/place/{place_id}",
                    "district": district_name,
                    "is_new_open": True,
                }

        await asyncio.sleep(REQUEST_DELAY)

    if dry_run:
        for p in all_places.values():
            logger.info(f"  [DRY] {p['name']} | {p['category']} | 리뷰 {p['review_count']} | {p['district']}")

    logger.info(f"=== {district_name} 완료: {len(all_places)}개 ===")
    return list(all_places.values())


async def run_crawler(districts=None, dry_run=False, headless=True):
    init_db()
    target_districts = {d: c for d, c in SEOUL_DISTRICTS.items() if districts is None or d in districts}

    if not target_districts:
        logger.error("크롤링할 구가 없습니다.")
        return 0

    total_new = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        await apply_stealth(context)
        page = await context.new_page()

        for district_name in target_districts:
            places = await scrape_district(page, district_name, dry_run=dry_run)
            if not dry_run:
                for place in places:
                    if upsert_place(place):
                        total_new += 1

        await browser.close()

    if not dry_run:
        logger.info(f"\n총 신규 저장: {total_new}개")
        export_csv()

    return total_new


def show_new_only(days=None):
    init_db()
    new_places = get_new_today(days)
    threshold = days if days is not None else NEW_DAYS_THRESHOLD
    if not new_places:
        logger.info(f"최근 {threshold}일 이내 신규 발견 업체가 없습니다.")
        return
    logger.info(f"=== 최근 {threshold}일 이내 신규 발견 업체: {len(new_places)}개 ===")
    for p in new_places:
        logger.info(f"  [{p.first_seen_date}] {p.name} | {p.category} | {p.district} | 리뷰 {p.review_count} | {p.naver_url}")


def main():
    parser = argparse.ArgumentParser(description="네이버 지도 새로오픈 업체 크롤러")
    parser.add_argument("--district", type=str)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--new-only", action="store_true")
    parser.add_argument("--new-days", type=int, default=None)
    args = parser.parse_args()

    if args.new_only:
        show_new_only(args.new_days)
        return

    if not args.run and not args.district and not args.dry_run:
        parser.print_help()
        sys.exit(1)

    asyncio.run(run_crawler(
        districts=[args.district] if args.district else None,
        dry_run=args.dry_run,
        headless=not args.no_headless,
    ))


if __name__ == "__main__":
    main()
