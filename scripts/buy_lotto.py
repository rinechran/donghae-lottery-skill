#!/usr/bin/env python3
"""
동행복권 로또 6/45 구매 스크립트 (Playwright 기반)
사용법:
  python3 buy_lotto.py                              # 자동번호 1게임
  python3 buy_lotto.py --games 5                    # 자동번호 5게임 (최대 5)
  python3 buy_lotto.py --numbers 1,2,3,4,5,6        # 수동번호 1게임
  python3 buy_lotto.py --numbers 1,2,3,4,5,6 7,8,9,10,11,12  # 수동번호 2게임
  python3 buy_lotto.py --numbers 1,2,3,4,5,6 --games 3       # 수동 1게임 + 자동 3게임
"""
import asyncio, json, sys, argparse, os
from pathlib import Path

CONFIG_PATH = Path.home() / ".donghae" / "config.json"
MAIN_URL   = "https://www.dhlottery.co.kr"
MOBILE_URL = "https://m.dhlottery.co.kr"
BUY_URL    = "https://ol.dhlottery.co.kr/olotto/game_mobile/game645.do"

# Playwright 시스템 라이브러리 경로
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

def parse_numbers(nums_strs: list[str]) -> list[list[int]]:
    """수동번호 문자열 파싱. 각 항목은 '1,2,3,4,5,6' 형식"""
    result = []
    for s in nums_strs:
        nums = [int(n) for n in s.split(",")]
        if len(nums) != 6:
            print(f"❌ 번호는 6개여야 합니다: {s}")
            sys.exit(1)
        if not all(1 <= n <= 45 for n in nums):
            print(f"❌ 번호는 1~45 사이여야 합니다: {s}")
            sys.exit(1)
        if len(set(nums)) != 6:
            print(f"❌ 중복 번호가 있습니다: {s}")
            sys.exit(1)
        result.append(sorted(nums))
    return result


async def buy(games=1, manual_numbers=None):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright 미설치: uv run --with playwright python3 buy_lotto.py")
        sys.exit(1)

    uid, pw = load_creds()
    result_data = {}
    manual_numbers = manual_numbers or []

    async def capture_response(resp):
        if "ol.dhlottery" in resp.url and resp.request.method == "POST":
            try:
                body = await resp.body()
                txt = body.decode("utf-8", errors="ignore").strip()
                # 구매 결과 JSON 캡처
                if "resultCode" in txt or "arrGameChoiceNum" in txt or "buyRound" in txt:
                    result_data["buy"] = txt
            except:
                pass

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
        page.on("response", capture_response)

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
        print("✅ 로그인 완료")

        # 2. 모바일 홈 방문 (세션/referer 설정)
        await page.goto(MOBILE_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)

        # 3. 구매 페이지 (networkidle 대신 domcontentloaded → 타임아웃 방지)
        await page.goto(BUY_URL, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)

        # 4a. 수동번호 입력
        for idx, nums in enumerate(manual_numbers):
            # 번호 버튼 클릭 (1~45)
            for n in nums:
                await page.evaluate(f"""
                    () => {{
                        const balls = document.querySelectorAll('.number');
                        for (const ball of balls) {{
                            if (ball.textContent.trim() === '{n}') {{
                                ball.click();
                                return;
                            }}
                        }}
                    }}
                """)
                await asyncio.sleep(0.15)
            # "확인" 버튼으로 게임 추가
            await page.evaluate("""
                () => {
                    const btn = [...document.querySelectorAll('button')]
                        .find(b => b.innerText.includes('확인') || b.innerText.includes('선택완료'));
                    if (btn) btn.click();
                }
            """)
            await asyncio.sleep(0.5)
            print(f"✏️  수동 {chr(65+idx)}게임: {' '.join(f'{n:02d}' for n in nums)}")

        # 4b. 자동 N매 추가
        auto_games = games
        for i in range(auto_games):
            await page.evaluate(
                "()=>{const b=[...document.querySelectorAll('button')]"
                ".find(b=>b.innerText.includes('자동 1매 추가'));if(b)b.click();}"
            )
            await asyncio.sleep(0.4)

        total = len(manual_numbers) + auto_games
        parts = []
        if manual_numbers:
            parts.append(f"수동 {len(manual_numbers)}게임")
        if auto_games:
            parts.append(f"자동 {auto_games}게임")
        print(f"🎱 {' + '.join(parts)} (총 {total}게임) 선택 완료")

        # 5. 구매하기 클릭
        await page.evaluate(
            "()=>{const b=[...document.querySelectorAll('button')]"
            ".find(b=>b.innerText.trim()==='구매하기');if(b)b.click();}"
        )
        await asyncio.sleep(1.5)

        # 6. 확인 팝업 — buttonOk 클래스 버튼 또는 좌표 클릭
        ok_clicked = await page.evaluate("""
            () => {
                // buttonOk 클래스 우선
                let btn = document.querySelector('.buttonOk');
                if (!btn) {
                    // 텍스트 정확히 "확인"인 버튼
                    btn = [...document.querySelectorAll('button')]
                        .find(b => b.innerText.trim() === '확인' && b.offsetParent !== null);
                }
                if (btn) { btn.click(); return true; }
                return false;
            }
        """)
        if not ok_clicked:
            # fallback: 검증된 좌표 클릭
            await page.mouse.click(266, 454)
        print("🛒 구매 확인!")
        await asyncio.sleep(6)
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass

        await browser.close()

    # 7. 결과 출력
    if "buy" in result_data:
        try:
            raw = result_data["buy"].strip()
            # JSON 시작 위치 찾기 (앞에 개행/공백 있을 수 있음)
            start = raw.find("{")
            if start > 0:
                raw = raw[start:]
            data = json.loads(raw)
            r = data.get("result") or data
            if r.get("resultCode") == "100":
                print(f"\n🎉 구매 성공!")
                print(f"   회차: 제{r['buyRound']}회")
                print(f"   일시: {r['issueDay']} {r['issueTime']}")
                for game in r.get("arrGameChoiceNum", []):
                    parts = game.split("|")
                    alpha = parts[0]
                    nums = " ".join(parts[1:])
                    print(f"   {alpha}게임: {nums}")
            else:
                print(f"❌ 구매 실패 (code={r.get('resultCode')}): {r.get('resultMsg')}")
                print(f"   원본: {result_data['buy'][:300]}")
        except Exception as e:
            print(f"결과 파싱 오류: {e}")
            print(f"   원본 응답: {result_data['buy'][:500]}")
    else:
        print("⚠️ 구매 응답 미수신 — 구매내역 페이지에서 직접 확인하세요.")
        print(f"   {MOBILE_URL}/mypage/mylotteryledger")

def main():
    parser = argparse.ArgumentParser(description="동행복권 로또 구매")
    parser.add_argument("--games", type=int, default=1, help="자동번호 게임 수 (1~5)")
    parser.add_argument("--numbers", nargs="+", help="수동번호 (예: 1,2,3,4,5,6)")
    args = parser.parse_args()

    manual = parse_numbers(args.numbers) if args.numbers else []
    auto_games = args.games if not manual else args.games if args.games != 1 or len(sys.argv) > 2 and "--games" in sys.argv else 0
    # --numbers만 주면 자동은 0, --numbers + --games 둘 다 주면 둘 다 적용
    if args.numbers and "--games" not in sys.argv:
        auto_games = 0

    total = len(manual) + auto_games
    if total < 1 or total > 5:
        print(f"❌ 총 게임 수는 1~5 사이여야 합니다. (현재: 수동 {len(manual)} + 자동 {auto_games} = {total})")
        sys.exit(1)

    setup_env()
    asyncio.run(buy(games=auto_games, manual_numbers=manual))

if __name__ == "__main__":
    main()
