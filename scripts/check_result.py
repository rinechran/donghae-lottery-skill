#!/usr/bin/env python3
"""
동행복권 이번주 구매내역 당첨 확인 (Playwright 기반)
사용법:
  python3 check_result.py           # 최근 구매내역 전체 확인
  python3 check_result.py --week    # 이번주 구매만 확인
"""
import asyncio, json, sys, os, re
from pathlib import Path
from datetime import date, timedelta

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

def match_count(my_nums, win_nums, bonus):
    matched = len(set(my_nums) & set(win_nums))
    has_bonus = bonus in my_nums
    return matched, has_bonus

def get_rank(matched, has_bonus):
    if matched == 6:               return "🥇 1등!! 대박!!"
    if matched == 5 and has_bonus: return "🥈 2등"
    if matched == 5:               return "🥉 3등"
    if matched == 4:               return "💵 4등 (5만원)"
    if matched == 3:               return "💰 5등 (5천원)"
    return "❌ 낙첨"

def this_week_range():
    """지난 토요일 ~ 이번 토요일 날짜 범위 반환"""
    today = date.today()
    days_to_sat = (5 - today.weekday()) % 7
    this_sat = today + timedelta(days=days_to_sat)
    last_sat = this_sat - timedelta(days=7)
    return last_sat, this_sat

# ── 당첨번호 공개 API ───────────────────────────────────────────────────
async def fetch_win_numbers(page, round_no: int):
    """공개 API로 당첨번호 조회"""
    data = await page.evaluate(f"""
        async () => {{
            try {{
                const r = await fetch(
                    '/common.do?method=getLottoNumber&drwNo={round_no}',
                    {{credentials: 'include'}}
                );
                const text = await r.text();
                try {{ return JSON.parse(text); }} catch(e) {{ return null; }}
            }} catch(e) {{ return null; }}
        }}
    """)
    if data and data.get("returnValue") == "success":
        nums  = [data[f"drwtNo{i}"] for i in range(1, 7)]
        bonus = data["bnusNo"]
        return nums, bonus
    return None, None


async def fetch_win_numbers_via_www(page, round_no: int):
    """www 도메인 경유해서 당첨번호 조회 (모바일 도메인에서 실패 시 사용)"""
    current_url = page.url
    # www 도메인으로 이동
    await page.goto(f"{MAIN_URL}/", wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(1)
    # www 컨텍스트에서 API 호출
    data = await page.evaluate(f"""
        async () => {{
            try {{
                const r = await fetch(
                    '/common.do?method=getLottoNumber&drwNo={round_no}',
                    {{credentials: 'include'}}
                );
                const text = await r.text();
                try {{ return JSON.parse(text); }} catch(e) {{ return null; }}
            }} catch(e) {{ return null; }}
        }}
    """)
    # 원래 도메인으로 복귀
    await page.goto(MOBILE_URL, wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(1)
    if data and data.get("returnValue") == "success":
        nums = [data[f"drwtNo{i}"] for i in range(1, 7)]
        bonus = data["bnusNo"]
        return nums, bonus
    return None, None

# ── 구매내역 API 조회 ────────────────────────────────────────────────────
async def fetch_purchase_list(page, str_dt: str, end_dt: str):
    """
    /mypage/selectMyLotteryledger.do API로 구매내역 조회
    str_dt, end_dt: YYYYMMDD 형식
    """
    data = await page.evaluate(f"""
        async () => {{
            try {{
                const params = new URLSearchParams({{
                    srchStrDt: '{str_dt}',
                    srchEndDt: '{end_dt}',
                    sort: '',
                    ltGdsCd: 'LO40',
                    winResult: '',
                    lramSmam: '',
                    pageNum: '1',
                    recordCountPerPage: '10'
                }});
                const r = await fetch('/mypage/selectMyLotteryledger.do?' + params, {{
                    method: 'GET',
                    credentials: 'include'
                }});
                return await r.json();
            }} catch(e) {{ return {{error: String(e)}}; }}
        }}
    """)
    return data

# ── 티켓 상세 API (게임번호 조회) ─────────────────────────────────────────
async def fetch_ticket_detail(page, item: dict, str_dt: str, end_dt: str):
    """
    /mypage/lotto645TicketDetail.do API로 개별 게임번호 + 당첨번호 조회
    반환: (game_nums, win_nums, bonus) 또는 (None, None, None)
      game_nums: {"A": [1,2,3,4,5,6], ...}
      win_nums: [1,2,3,4,5,6] 또는 None
      bonus: int 또는 None
    """
    ntsl_ordr_no = item.get("ntslOrdrNo", "")
    barcd = item.get("gmInfo", "")
    data = await page.evaluate(f"""
        async () => {{
            try {{
                const params = new URLSearchParams({{
                    ntslOrdrNo: '{ntsl_ordr_no}',
                    srchStrDt: '{str_dt}',
                    srchEndDt: '{end_dt}',
                    barcd: '{barcd}'
                }});
                const r = await fetch('/mypage/lotto645TicketDetail.do?' + params, {{
                    method: 'GET',
                    credentials: 'include'
                }});
                return await r.json();
            }} catch(e) {{ return {{error: String(e)}}; }}
        }}
    """)
    if not data or "error" in data:
        return None, None, None

    ticket = (data.get("data") or {}).get("ticket")
    if not ticket:
        return None, None, None

    # 게임번호 파싱
    games = {}
    for g in ticket.get("game_dtl", []):
        idx = g.get("idx", chr(65 + len(games)))
        nums = g.get("num", [])
        if len(nums) == 6 and all(isinstance(n, int) for n in nums):
            games[idx] = nums

    # 당첨번호 파싱 (win_num 필드: 7개 - 6개 번호 + 보너스)
    win_nums, bonus = None, None
    win_num = ticket.get("win_num", [])
    if win_num and len(win_num) >= 7 and any(n > 0 for n in win_num):
        win_nums = win_num[:6]
        bonus = win_num[6]

    return (games if games else None), win_nums, bonus

# ── 메인 확인 로직 ─────────────────────────────────────────────────────
async def check(week_only: bool = False):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright 미설치")
        sys.exit(1)

    uid, pw = load_creds()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 11; SM-G991B) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 390, "height": 844},
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        page = await ctx.new_page()

        # ── 로그인 ──
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

        # 모바일 홈 (쿠키/referer 설정)
        await page.goto(MOBILE_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)

        # ── 조회 기간 설정 ──
        today = date.today()
        if week_only:
            last_sat, this_sat = this_week_range()
            str_dt = (last_sat - timedelta(days=7)).strftime("%Y%m%d")
            end_dt = today.strftime("%Y%m%d")
        else:
            str_dt = (today - timedelta(days=30)).strftime("%Y%m%d")
            end_dt = today.strftime("%Y%m%d")

        # ── 구매내역 API 조회 ──
        result = await fetch_purchase_list(page, str_dt, end_dt)
        purchases = []
        if result and "data" in result:
            purchases = result["data"].get("list", [])

        # ── 이번주 필터 ──
        if week_only and purchases:
            last_sat, this_sat = this_week_range()
            filtered = []
            for item in purchases:
                draw_date_str = item.get("drwDt", "")
                if draw_date_str:
                    try:
                        dd = date(int(draw_date_str[:4]), int(draw_date_str[4:6]), int(draw_date_str[6:8]))
                        if last_sat <= dd <= this_sat:
                            filtered.append(item)
                    except (ValueError, IndexError):
                        pass
            target = filtered or purchases[:2]
        else:
            target = purchases[:5]

        print("=" * 54)
        title = "🎟️  이번주 로또 당첨 확인" if week_only else "🎟️  최근 구매내역 당첨 확인"
        print(title)
        print("=" * 54)

        if not target:
            print("구매 내역 없음")
            await browser.close()
            return

        for item in target:
            round_no = item.get("ltEpsd")
            status_code = item.get("ltWnResult", "")
            qty = item.get("ntslQty") or item.get("gameCnt", 1)
            buy_date = item.get("eltOrdrDt", "?")
            draw_date = item.get("drwDt", "") or item.get("drwNoDate", "?")

            # 날짜 포맷팅
            if len(buy_date) == 8:
                buy_date = f"{buy_date[:4]}-{buy_date[4:6]}-{buy_date[6:]}"
            if len(draw_date) == 8:
                draw_date = f"{draw_date[:4]}-{draw_date[4:6]}-{draw_date[6:]}"

            status_map = {"N": "미추첨", "L": "낙첨", "W": "당첨", "H": "고액당첨"}
            status = status_map.get(status_code, status_code or "미확인")
            status_icon = {
                "미추첨": "⏳", "낙첨": "❌", "고액당첨": "🎉", "당첨": "🏆"
            }.get(status, "🔍")

            print(f"\n📅 구입일: {buy_date}  │  {round_no}회  │  {qty}게임")
            print(f"   추첨일: {draw_date}  │  상태: {status_icon} {status}")

            if not round_no:
                print("   ⚠️  회차번호 파싱 실패 — 직접 확인하세요")
                continue

            # ── 개별 게임번호 + 당첨번호 (티켓 상세 API) ──
            game_nums, ticket_win, ticket_bonus = await fetch_ticket_detail(page, item, str_dt, end_dt)

            # 당첨번호: 티켓 API 우선, 실패 시 공개 API
            win_nums, bonus = ticket_win, ticket_bonus
            if not win_nums and status != "미추첨":
                win_nums, bonus = await fetch_win_numbers(page, round_no)
                if not win_nums:
                    win_nums, bonus = await fetch_win_numbers_via_www(page, round_no)

            if win_nums:
                print(f"   당첨번호: {' '.join(str(n) for n in win_nums)}  +보너스 {bonus}")
            elif status == "미추첨":
                print(f"   ⏳ 추첨 예정일: {draw_date}")
            else:
                print(f"   ⚠️  {round_no}회 당첨번호 조회 실패")

            if game_nums:
                print(f"   {'─'*44}")
                for alpha in sorted(game_nums):
                    my = game_nums[alpha]
                    if win_nums:
                        m, b = match_count(my, win_nums, bonus)
                        rank = get_rank(m, b)
                        print(f"   {alpha}게임: {' '.join(f'{n:02d}' for n in my)}  →  {rank}")
                    else:
                        print(f"   {alpha}게임: {' '.join(f'{n:02d}' for n in my)}")
            else:
                print(f"   ℹ️  개별 번호 조회 불가")
                print(f"      직접 확인: {MOBILE_URL}/mypage/mylotteryledger")

        await browser.close()
        print("\n✅ 완료")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="동행복권 당첨 확인")
    parser.add_argument(
        "--week", action="store_true",
        help="이번주 구매내역만 확인 (토요일 기준)"
    )
    args = parser.parse_args()

    setup_env()
    asyncio.run(check(week_only=args.week))


if __name__ == "__main__":
    main()
