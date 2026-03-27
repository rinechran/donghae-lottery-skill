# 동행복권 API 참고

## 주요 URL
- 홈: `https://www.dhlottery.co.kr/`
- 로그인: `https://www.dhlottery.co.kr/userSsl.do?method=login`
- 예치금: `https://www.dhlottery.co.kr/userSsl.do?method=getUserCash`
- 구매 페이지: `https://www.dhlottery.co.kr/game/goGame.do?game=10`
- 구매 API: `https://www.dhlottery.co.kr/game/buyGame.do?game=10`

## 로그인 POST 파라미터
- `userId`: 아이디
- `password`: 비밀번호
- `checkSave`: "on"
- `returnUrl`: 홈 URL

## 구매 성공 응답 예시
```json
{
  "result": {
    "resultCode": "100",
    "buyRound": [{
      "round": "1157",
      "arrGameChoiceNum": ["A: 3 15 22 31 38 44"]
    }]
  }
}
```

## 오류 코드
- `resultCode != "100"` → 구매 실패
- 예치금 부족 시 별도 오류 메시지

## 예치금 충전
- 동행복권 사이트 → 마이페이지 → 예치금 충전
- 계좌이체 / 신용카드 지원
- 자동 충전 API는 없음 (수동 충전 필요)

## 로그인 세션 유지
- `JSESSIONID` 쿠키로 세션 관리
- 장시간 미사용 시 세션 만료 → 재로그인 필요
