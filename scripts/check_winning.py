#!/usr/bin/env python3
"""
동행복권 당첨번호 조회 (로그인 불필요, 공개 API)
사용법:
  python3 check_winning.py              # 최신 회차
  python3 check_winning.py --round 1160 # 특정 회차
  python3 check_winning.py --recent 5   # 최근 N회차
"""
import argparse, json, sys
from urllib.request import urlopen, Request
from urllib.error import URLError
from datetime import date

API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo={}"


def fetch_round(round_no: int) -> dict | None:
    try:
        req = Request(API_URL.format(round_no), headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        if data.get("returnValue") != "success":
            return None
        return data
    except (URLError, json.JSONDecodeError, OSError):
        return None


def estimate_latest_round() -> int:
    """첫 회차(2002-12-07)로부터 현재까지 주 수 계산"""
    first = date(2002, 12, 7)
    today = date.today()
    weeks = (today - first).days // 7
    return weeks + 1


def print_round(data: dict):
    round_no = data["drwNo"]
    draw_date = data.get("drwNoDate", "?")
    nums = [data[f"drwtNo{i}"] for i in range(1, 7)]
    bonus = data["bnusNo"]
    prize = data.get("firstWinamnt", 0)
    winners = data.get("firstPrzwnerCo", 0)

    nums_str = "  ".join(f"{n:02d}" for n in nums)
    print(f"\n🎱 제{round_no}회 ({draw_date})")
    print(f"   당첨번호: {nums_str}  + 보너스 {bonus:02d}")
    if prize:
        print(f"   1등 상금: {prize:,}원 ({winners}명)")


def main():
    parser = argparse.ArgumentParser(description="동행복권 당첨번호 조회")
    parser.add_argument("--round", "-r", type=int, help="조회할 회차 번호")
    parser.add_argument("--recent", "-n", type=int, default=1, help="최근 N회차 조회 (기본 1)")
    args = parser.parse_args()

    if args.round:
        data = fetch_round(args.round)
        if data:
            print_round(data)
        else:
            print(f"❌ {args.round}회 당첨번호 조회 실패 (미추첨 또는 없는 회차)")
        return

    latest = estimate_latest_round()
    # 최신 회차 찾기 (미추첨이면 이전 회차로)
    while latest > 0:
        data = fetch_round(latest)
        if data:
            break
        latest -= 1
    else:
        print("❌ 당첨번호 조회 실패")
        sys.exit(1)

    count = min(args.recent, 10)
    for i in range(count):
        r = latest - i
        if r < 1:
            break
        data = fetch_round(r)
        if data:
            print_round(data)

    print()


if __name__ == "__main__":
    main()
