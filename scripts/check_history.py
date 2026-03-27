#!/usr/bin/env python3
"""
동행복권 최근 구매 이력 조회 (당첨 확인 없이 빠르게)
사용법:
  python3 check_history.py            # 최근 5건
  python3 check_history.py --count 10 # 최근 10건
"""
import asyncio, json, sys, os, re
from pathlib import Path

CONFIG_PATH = Path.home() / ".donghae" / "config.json"
MAIN_URL    = "https://www.dhlottery.co.kr"
MOBILE_URL  = "https://m.dhlottery.co.kr"

LIB_PATH = ":".join([
    str(Path.home() / "libs/usr/lib/x86_64-linux-gnu"),
    str(Path.home() / "libs/usr/lib"),
    str(Path.home() / "libs/lib/x86_64-linux-gnu"),
])


def setup_env():
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = f"{LIB_PATH}:{existing}" if existing else LIB_PATH


def load_creds():
    if not CONFIG_PATH.exists():
        print("❌ 자격증명 없음. setup.py 먼저 실행하세요.")
        sys.exit(1)
    cfg = json.loads(CONFIG_PATH.read_text())
    return cfg["id"], cfg["pw"]


async def check_history(count: int = 5):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright 미설치: uv run --with playwright python3 check_history.py")
        sys.exit(1)

    uid, pw = load_creds()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 390, "height": 844},
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        page = await ctx.new_page()

        # 1. 로그인
        print("🔐 로그인 중...")
        await page.goto(f"{MAIN_URL}/login", wait_until="networkidle", timeout=20000)
        await page.fill("#inpUserId", uid)
        await page.fill("#inpUserPswdEncn", pw)
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)

        if "/login" in page.url:
            print("❌ 로그인 실패")
            await browser.close()
            return

        print("✅ 로그인 완료\n")

        # 2. 모바일 홈
        await page.goto(MOBILE_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)

        # 3. 구매내역 페이지
        await page.goto(
            f"{MOBILE_URL}/mypage/mylotteryledger",
            wait_until="networkidle",
            timeout=20000,
        )
        await asyncio.sleep(3)

        text = await page.inner_text("body")
        sections = re.split(r'구입일자\s+', text)

        print("=" * 54)
        print("📋  최근 구매 이력")
        print("=" * 54)

        shown = 0
        for sec in sections[1:]:
            if shown >= count:
                break

            lines = [l.strip() for l in sec.split('\n') if l.strip()]
            if not lines:
                continue

            buy_date = lines[0]

            round_no = None
            for l in lines[:8]:
                if re.match(r'^\d{3,4}$', l):
                    round_no = int(l)
                    break

            status = "미확인"
            for s in ["미추첨", "낙첨", "고액당첨", "당첨"]:
                if s in sec:
                    status = s
                    break

            qty_m = re.search(r'구입매수\s+(\d+)', sec)
            qty = int(qty_m.group(1)) if qty_m else 1

            draw_m = re.search(r'추첨일자\s+(\d{4}-\d{2}-\d{2})', sec)
            draw_date = draw_m.group(1) if draw_m else "?"

            amt_m = re.search(r'구입금액\s+([\d,]+)', sec)
            amount = amt_m.group(1) if amt_m else f"{qty * 1000:,}"

            status_icon = {
                "미추첨": "⏳", "낙첨": "❌", "고액당첨": "🎉", "당첨": "🏆"
            }.get(status, "🔍")

            print(f"\n📅 {buy_date}  │  제{round_no or '?'}회  │  {qty}게임 ({amount}원)")
            print(f"   추첨일: {draw_date}  │  {status_icon} {status}")
            shown += 1

        if shown == 0:
            print("\n구매 내역이 없습니다.")

        await browser.close()
        print(f"\n✅ 총 {shown}건 조회 완료")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="동행복권 구매 이력 조회")
    parser.add_argument("--count", "-n", type=int, default=5, help="조회 건수 (기본 5)")
    args = parser.parse_args()

    setup_env()
    asyncio.run(check_history(count=args.count))


if __name__ == "__main__":
    main()
