# donghae-lottery

동행복권(dhlottery.co.kr) 로또 6/45 자동 구매 Claude Code 스킬

Playwright 브라우저 자동화로 동행복권에 로그인하여 로또를 구매하고, 예치금 확인, 당첨 확인, 구매 이력 조회까지 Claude에게 자연어로 요청할 수 있습니다.

## 기능

| 명령 | 설명 |
|------|------|
| "로또 사줘" | 자동번호 1게임 구매 |
| "로또 자동번호 5게임" | 자동번호 5게임 구매 (최대) |
| "수동번호 1,2,3,4,5,6 구매" | 수동번호 지정 구매 |
| "예치금 확인" | 잔액 및 구매 가능 게임 수 조회 |
| "당첨번호 알려줘" | 최신 회차 당첨번호 조회 |
| "이번주 로또 당첨확인" | 이번주 구매 로또 당첨 여부 확인 |
| "구매 이력" | 최근 구매 내역 조회 |

## 설치

### Claude Code 스킬로 설치

```bash
# 1. 저장소 클론
git clone https://github.com/<your-username>/donghae-lottery.git ~/.claude/skills/donghae-lottery

# 2. 자격증명 설정
python3 ~/.claude/skills/donghae-lottery/scripts/setup.py
```

설치 후 Claude Code에서 "로또 사줘", "예치금 확인" 등 자연어로 사용 가능합니다.

### 필수 환경

- **Python 3.10+**
- **Playwright** (Chromium)
- **uv** (권장) 또는 pip

```bash
# Playwright 브라우저 설치 (최초 1회)
uv run --with playwright python3 -m playwright install chromium

# 시스템 라이브러리 (Linux 서버 환경)
# ~/libs/usr/lib/x86_64-linux-gnu/ 에 libnspr4, libnss3 등 필요
```

## 자격증명 설정

```bash
python3 scripts/setup.py
```

`~/.donghae/config.json`에 아이디/비밀번호가 저장됩니다 (chmod 600).

수동 설정도 가능합니다:

```bash
mkdir -p ~/.donghae
echo '{"id":"아이디","pw":"비번"}' > ~/.donghae/config.json
chmod 600 ~/.donghae/config.json
```

## 직접 실행

스킬 없이 CLI로 직접 실행할 수도 있습니다.

```bash
# 자동번호 1게임
uv run --with playwright python3 scripts/buy_lotto.py

# 자동번호 5게임
uv run --with playwright python3 scripts/buy_lotto.py --games 5

# 수동번호 구매
uv run --with playwright python3 scripts/buy_lotto.py --numbers 1,2,3,4,5,6

# 수동 2게임 + 자동 3게임
uv run --with playwright python3 scripts/buy_lotto.py --numbers 1,2,3,4,5,6 7,8,9,10,11,12 --games 3

# 예치금 확인
uv run --with playwright python3 scripts/check_balance.py

# 당첨번호 조회 (로그인 불필요)
python3 scripts/check_winning.py
python3 scripts/check_winning.py --round 1216
python3 scripts/check_winning.py --recent 5

# 당첨 확인
uv run --with playwright python3 scripts/check_result.py --week

# 구매 이력
uv run --with playwright python3 scripts/check_history.py --count 10
```

## 스크립트 구성

| 파일 | 설명 |
|------|------|
| `scripts/setup.py` | 로그인 자격증명 설정 |
| `scripts/buy_lotto.py` | 로또 구매 (자동/수동) |
| `scripts/check_balance.py` | 예치금 잔액 조회 |
| `scripts/check_winning.py` | 당첨번호 조회 (공개 API) |
| `scripts/check_result.py` | 구매 로또 당첨 확인 |
| `scripts/check_history.py` | 구매 이력 조회 |

## 주의사항

- 구매 전 **예치금 충전** 필수 (1게임 = 1,000원)
- 1회 최대 **5게임** 구매 가능
- 예치금 충전은 동행복권 사이트에서 직접 해야 합니다
- 자격증명은 로컬에만 저장되며 외부로 전송되지 않습니다

## License

MIT
