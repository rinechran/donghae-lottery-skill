---
name: donghae-lottery
description: 동행복권(dhlottery.co.kr) 로또 6/45 구매 스킬. Playwright 브라우저 자동화로 로그인 후 자동/수동번호 구매. "로또 사줘", "동행복권 구매", "로또 자동번호 5게임", "수동번호 구매", "예치금 확인", "이번주 로또 당첨확인", "당첨번호 알려줘", "구매 이력" 등에 사용.
---

# 동행복권 로또 자동 구매

Playwright 기반 브라우저 자동화로 동행복권 로또를 구매한다.

## 설정 파일 포맷

```
경로: ~/.donghae/config.json
권한: 600 (setup.py가 자동 설정)
```

```json
{
  "id": "동행복권 아이디",
  "pw": "동행복권 비밀번호"
}
```

- setup.py를 실행하면 위 형식으로 자동 생성
- 수동으로 만들어도 됨: `mkdir -p ~/.donghae && echo '{"id":"아이디","pw":"비번"}' > ~/.donghae/config.json && chmod 600 ~/.donghae/config.json`

## 필수 환경

```bash
# 시스템 라이브러리 (최초 1회 설치됨)
~/libs/usr/lib/x86_64-linux-gnu/  # libnspr4, libnss3 등

# 실행 명령
LD_LIBRARY_PATH=~/libs/usr/lib/x86_64-linux-gnu:~/libs/usr/lib:~/libs/lib/x86_64-linux-gnu \
  uv run --with playwright python3 buy_lotto.py --games 5
```

## 자격증명 설정 (최초 1회)

```bash
python3 skills/donghae-lottery/scripts/setup.py
# → ~/.donghae/config.json 저장 (chmod 600)
```

## 실행 명령

```bash
UV_CMD="LD_LIBRARY_PATH=~/libs/usr/lib/x86_64-linux-gnu:~/libs/usr/lib:~/libs/lib/x86_64-linux-gnu uv run --with playwright python3"
SKILL="~/.openclaw/workspace/skills/donghae-lottery/scripts"

# 자동번호 1게임 구매
$UV_CMD $SKILL/buy_lotto.py

# 자동번호 5게임 구매 (최대)
$UV_CMD $SKILL/buy_lotto.py --games 5

# 수동번호 1게임 구매
$UV_CMD $SKILL/buy_lotto.py --numbers 1,2,3,4,5,6

# 수동 2게임 + 자동 3게임 (총 5게임)
$UV_CMD $SKILL/buy_lotto.py --numbers 1,2,3,4,5,6 7,8,9,10,11,12 --games 3

# 예치금 확인
$UV_CMD $SKILL/check_balance.py

# 이번주 구매한 로또 당첨 확인 (토요일 기준 필터)
$UV_CMD $SKILL/check_result.py --week

# 최근 5건 구매내역 당첨 확인
$UV_CMD $SKILL/check_result.py

# 최신 회차 당첨번호 조회 (로그인 불필요)
python3 $SKILL/check_winning.py

# 특정 회차 당첨번호
python3 $SKILL/check_winning.py --round 1216

# 최근 5회차 당첨번호
python3 $SKILL/check_winning.py --recent 5

# 최근 구매 이력 조회 (당첨 확인 없이 빠르게)
$UV_CMD $SKILL/check_history.py

# 최근 10건 이력
$UV_CMD $SKILL/check_history.py --count 10
```

## 실제 구매 플로우 (검증 완료 2026-02-19)

1. `https://www.dhlottery.co.kr/login` 에서 로그인
   - 아이디 input: `#inpUserId`
   - 비번 input: `#inpUserPswdEncn`
   - Enter 키로 제출

2. `https://m.dhlottery.co.kr` 모바일 홈 방문 (세션/referer 설정)

3. `https://ol.dhlottery.co.kr/olotto/game_mobile/game645.do` 구매 페이지 이동

4. "자동 1매 추가" 버튼 N번 클릭 (`.btn-line` 텍스트 기반)

5. "구매하기" 버튼 클릭

6. 확인 팝업에서 좌표 클릭: `page.mouse.click(265, 452)` (녹색 확인 버튼)

7. 응답에서 결과 파싱:
   - `resultCode: "100"` = 성공
   - `arrGameChoiceNum`: 구매된 번호 목록

## 주의사항

- 구매 전 예치금 확인 필수 (1게임 = 1,000원)
- 1회 최대 **5게임** 구매 가능
- 구매 결과를 반드시 사용자에게 보고
- 사용자 동의 없이 자동 구매 금지
- IP 차단 없음 (가정용 인터넷 기준, 실 테스트 완료)

## 당첨확인 동작 방식 (check_result.py)

1. **구매내역**: `/mypage/selectMyLotteryledger.do` API로 구매 리스트 조회
2. **게임번호 + 당첨번호**: `/mypage/lotto645TicketDetail.do` API로 한번에 조회 (가장 신뢰)
3. **당첨번호 fallback**: 공개 API `common.do?method=getLottoNumber&drwNo=N` (tracer 차단 시 www 도메인 경유)
4. **이번주 기준**: 매주 토요일 추첨일 기준 `--week` 플래그로 필터링

당첨 결과 등급:
- 🥇 1등: 6개 일치
- 🥈 2등: 5개 + 보너스
- 🥉 3등: 5개 일치
- 💵 4등: 4개 일치 (5만원)
- 💰 5등: 3개 일치 (5천원)
- ❌ 낙첨

## 알려진 이슈

- 구 URL `/userSsl.do?method=login` → 404 (폐기됨)
- `/lotto/buy` 등 직접 접근 → 404
- 구매 확인 버튼은 `.click()` 불가 → `page.mouse.click(265, 452)` 좌표 클릭 사용
- `tracer.dhlottery.co.kr:48081` 봇 감지 시스템 존재 (현재 우회 중)
