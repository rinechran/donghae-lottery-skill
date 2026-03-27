#!/usr/bin/env python3
"""
동행복권 예치금 확인 (Playwright 기반 - 2026-02-19)
사용법: python3 check_balance.py
"""
import asyncio, json, sys, os
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

async def check():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright 미설치: uv run --with playwright python3 check_balance.py")
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
            print("❌ 로그인 실패 — 아이디/비번 확인하세요")
            await browser.close()
            return

        print("✅ 로그인 완료")

        # 2. 모바일 홈 방문 (세션 쿠키 설정)
        await page.goto(MOBILE_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)

        # 3. 예치금 API 호출 (/mypage/selectUserMndp.do)
        result = await page.evaluate("""
            async () => {
                try {
                    const r = await fetch('/mypage/selectUserMndp.do', {
                        method: 'GET',
                        credentials: 'include'
                    });
                    const text = await r.text();
                    return { ok: true, body: text };
                } catch(e) {
                    return { ok: false, error: String(e) };
                }
            }
        """)

        await browser.close()

    if not result.get("ok"):
        print(f"❌ API 호출 실패: {result.get('error')}")
        return

    try:
        data = json.loads(result["body"])
        m = data["data"]["userMndp"]

        pnt   = m.get("pntDpstAmt", 0)   - m.get("pntTkmnyAmt", 0)
        ncsbl = m.get("ncsblDpstAmt", 0) - m.get("ncsblTkmnyAmt", 0)
        csbl  = m.get("csblDpstAmt", 0)  - m.get("csblTkmnyAmt", 0)
        total = m.get("totalAmt", pnt + ncsbl + csbl)

        print(f"\n💰 예치금 잔액: {total:,}원")
        if csbl: print(f"   └ 충전금: {csbl:,}원")
        if ncsbl: print(f"   └ 비충전금: {ncsbl:,}원")
        if pnt: print(f"   └ 포인트: {pnt:,}원")
        print(f"🎱 구매 가능 게임 수: {total // 1000}게임 (1게임=1,000원)")

    except Exception as e:
        print(f"❌ 응답 파싱 실패: {e}")
        print(f"   원본: {result['body'][:200]}")

def main():
    setup_env()
    asyncio.run(check())

if __name__ == "__main__":
    main()
