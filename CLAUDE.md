# CLAUDE.md — 공고 수집기

이 파일은 Claude Code 가 이 저장소에서 작업할 때 읽는 컨텍스트다. 사람용 설명은 README.md 에 있다.

## 이 프로젝트가 하는 일

나라장터·K-Startup 공고를 API 로 받아 → 제목 검색어로 거르고 → 마감일 기준으로 거르고 → Google 스프레드시트에 증분 반영한다. GitHub Actions cron 으로 매일 돈다. 사용자는 대부분 비개발자이며, 이 저장소를 템플릿으로 복사해서 쓴다.

## 사용자가 "세팅해줘" 라고 하면

`.claude/commands/setup.md` 의 `/setup` 절차를 따른다. 핵심은 세 가지다.

1. `config.yaml` 채우기 (시트 URL, 검색어, 금지어)
2. 비밀값 두 개 확보: data.go.kr 인증키, Google 서비스 계정 JSON
3. `python scripts/doctor.py` 로 검증 → `gh secret set` 으로 GitHub 에 등록 → `gh workflow run "공고 수집"` 으로 첫 실행

콘솔에서 사람이 직접 해야 하는 단계(API 활용신청, GCP 서비스 계정 생성, 시트 공유)는 대신할 수 없으니 정확한 클릭 경로를 알려주고 결과 파일/값을 받아서 이어간다.

## 설정이 읽히는 순서

`config.py` 가 단일 진입점이다. 우선순위는 **환경변수 > config.yaml > 기본값**.

- 비밀값(`DATA_GO_KR_API_KEY`, `GOOGLE_CREDENTIALS_JSON`)은 환경변수에서만 읽는다. 절대 `config.yaml` 에 넣지 않는다.
- `GOOGLE_CREDENTIALS_JSON` 이 있으면 `config.resolve_credentials_file()` 이 `credentials.json` 으로 풀어 쓴다. Actions 에서는 이 경로다.
- 검색어는 `config.yaml` 의 `keywords.{general,ends_with,conditional}` 리스트. 환경변수 `KEYWORDS` 등 쉼표 구분 문자열로도 덮어쓸 수 있다 (구버전 호환).
- `keywords.must` 는 고급 옵션이다. 수집 조건은 general 과 같지만, 걸린 공고에 `must_matched=True` 가 붙어 `filter_by_exclusion` 이 금지어를 무시하고 (필터) 탭에 남긴다. 공개용 `config.yaml` 에서는 주석 처리돼 있다. 사용자가 "general 과 뭐가 다르냐" 고 물으면 이것이 유일한 차이다.
- 스프레드시트는 URL 을 넣어도 `extract_sheet_id()` 가 ID 를 뽑는다.

새 설정값을 추가할 때는 ① `config.yaml` 에 주석과 함께 ② `config.py` 에 `_get()`/`_env_*()` 로 ③ README 설정 참고 표에, 세 곳을 같이 고친다.

## 실행 흐름 (main.py)

```
validate_config
→ ThreadPoolExecutor: nara.fetch / kstartup.fetch  (병렬)
→ 소스 fetch 가 실패해서 0건이면 exit 1  ← 시트를 건드리지 않는다
→ 나라장터: keyword → deadline
→ K-Startup: registration_date cutoff → deadline → keyword
→ 금지어: 각각 filter_by_exclusion
→ SpreadsheetManager: 탭별 dedup → update_announcements (append/갱신/만료삭제, new_ids 반환)
→ 슬랙(선택): (필터) 탭 기준 new_ids 에 해당하는 공고만 notifier.send_report
```

exit code 1 이면 워크플로우가 5분 후 한 번 재시도한다 (`collect.yml`).

## 외부 API 특성 (바꾸면 안 되는 이유가 있는 것들)

- **data.go.kr 은 GitHub Actions 러너에서 간헐적으로 연결 자체가 안 된다.** connect timeout 이 나며, 같은 시각 한국 PC 에서는 잘 된다. 그래서 timeout 30s / 5회 재시도 / 워크플로우 레벨 재시도가 있다. 재시도를 줄이지 말 것.
- 나라장터 `getDataSetOpnStdBidPblancInfo`: `bidNtceBgnDt/EndDt` 로 등록일 범위 조회. 한 번에 30일 청크로 나눠 부른다 (더 길면 서버가 느려짐). `numOfRows=999`. 청크 경계 중복은 id 로 제거.
- K-Startup `getAnnouncementInformation01`: **검색 파라미터가 없다.** 전체(2만 건+)를 페이지로 다 받은 뒤 클라이언트에서 거른다. 5분 정도 걸리는 게 정상.
- 두 API 모두 인증키 하나(`DATA_GO_KR_API_KEY`)로 호출된다. Decoding 키를 써야 한다.
- 나라장터 `bidNtceNo`, K-Startup `pbanc_sn` 이 공고ID. 시트의 증분 갱신 키다.

## 스프레드시트 규칙 (spreadsheet.py)

- 공고ID 열로 기존/신규 판별. 기존 행은 전체 갱신하되 **등록일자만 원래 값 유지**.
- 남은일수는 `=D{row}-TODAY()` 수식. 행을 지우거나 재정렬하면 수식 행번호를 다시 써야 한다 (`deduplicate_sheet`, `remove_expired_rows` 참고).
- 날짜는 시트에 `YY-MM-DD` 문자열로 쓴다. `remove_expired_rows` 는 숫자(시리얼)로 읽힐 수도 있어 둘 다 처리한다.
- 헤더 순서를 바꾸면 `_prepare_row_data` 와 `NARA_HEADERS/KSTARTUP_HEADERS` 를 같이 바꿔야 한다.

## 로컬에서 검증하는 법

```bash
python -c "import config; config.validate_config()"   # 설정만
python scripts/doctor.py                               # API·인증·시트 연결
python main.py                                         # 실제 실행 (5~10분)
```

시트 쓰기 없이 필터만 보고 싶으면 `log_level: DEBUG` 로 두고 로그를 본다. 테스트용 시트를 따로 만들어 `GOOGLE_SHEET_ID` 환경변수로 덮어쓰는 방법도 있다.

## 하지 말 것

- `credentials.json`, `.env` 를 커밋하지 않는다. `.gitignore` 에 있다.
- 검색어를 GitHub Secrets 로 옮기지 않는다. 값이 안 보여서 운영이 어려워진다. `config.yaml` 이 정답이다.
- 사용자 확인 없이 스프레드시트 탭을 지우거나 `clear()` 하지 않는다. (`deduplicate_sheet`/`remove_expired_rows` 의 clear+update 는 같은 내용을 다시 쓰는 것이라 예외)
- cron 을 UTC 로 바꿔 적을 때 KST-9 를 잊지 않는다.

## 슬랙 알림 (notifier.py)

- Incoming Webhook 한 개. `SLACK_WEBHOOK_URL` Secret + `slack.enabled: true` 둘 다 있어야 켜진다 (`config.SLACK_ENABLED`).
- 보내는 것은 **이번 실행에서 시트에 새로 append 된 공고**뿐이다. 판단 근거는 `update_announcements` 가 돌려주는 `new_ids`. 금지어가 설정돼 있으면 (필터) 탭의 new_ids 를 쓴다.
- 신규 0건이면 기본은 침묵(`notify_when_empty`). 수집 실패 알림은 워크플로우 1차 시도에서 `SLACK_NOTIFY_ON_FAILURE=false` 로 꺼 두고 재시도에서만 보낸다. 두 번 알림이 가지 않게 하려는 것이니 유지할 것.
- 슬랙 전송 실패는 exit code 에 영향을 주지 않는다.

## 확장 여지

- 알림 채널 추가(이메일, 카카오 등): `src/notifier.py` 에 같은 시그니처로 함수를 추가하고 `main.py` 8단계에서 분기.
- 소스 추가: `src/api_client.py` 에 `fetch_announcements() -> List[Dict]` 를 같은 dict 스키마(`id, title, organization, deadline, link, registration_date, source`)로 구현하고 `config.yaml` `sources` 에 토글을 넣는다.
