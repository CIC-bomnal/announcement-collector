# 공고 수집기 (announcement-collector)

나라장터(조달청)와 K-Startup(창업진흥원)의 공고를 매일 자동으로 긁어서, 우리 조직에 맞는 검색어로 걸러 Google 스프레드시트에 쌓아주는 도구입니다. GitHub Actions 로 돌아가므로 서버가 필요 없습니다.

- 검색어·금지어·마감일 기준은 `config.yaml` 파일 하나로 조정합니다.
- 비용은 0원입니다. (공공데이터포털 API 무료, GitHub Actions 무료 한도 내, Google Sheets 무료)
- 세팅에 필요한 시간은 약 20분입니다. 절반은 API 키 승인 대기입니다.

> **Claude Code 를 쓰신다면** 이 저장소를 클론한 뒤 `claude` 를 실행하고 `/setup` 이라고 입력하세요. 아래 과정을 대화식으로 안내합니다. 사람이 직접 하려면 그대로 읽어 내려가시면 됩니다.

## 결과물 미리보기

스프레드시트에 아래 탭이 자동으로 생깁니다.

| 탭 | 내용 |
|---|---|
| 나라장터 | 검색어에 걸린 입찰공고. 공고명(링크), 공고ID, 발주기관, 마감일, 남은일수, 예산, 등록일자, 업로드일자 |
| K-Startup | 검색어 또는 안내서 사업명에 걸린 지원사업 공고. 예산 대신 과업개요 |
| 나라장터(필터) / K-Startup(필터) | 위 두 탭에서 금지어가 포함된 공고를 뺀 것 |
| {연도} 창업지원사업 | 창업지원사업 안내서 PDF 에서 뽑은 사업 목록 (선택 기능) |

매 실행마다 새 공고는 추가되고, 이미 있는 공고는 마감일 등이 갱신되며, 마감이 임박한 공고는 지워집니다.

## 세팅 순서

### 1단계. 저장소 복사

이 페이지 상단의 **Use this template → Create a new repository** 를 눌러 여러분 조직 계정에 복사합니다. 검색어가 외부에 보이는 게 싫다면 **Private** 으로 만드세요. Private 이어도 GitHub Actions 무료 한도(월 2,000분)로 충분합니다. 하루 한 번 실행에 약 10분이 듭니다.

### 2단계. 공공데이터포털 API 키 (승인 대기 있음)

1. https://www.data.go.kr 회원가입 후 로그인
2. 아래 두 서비스를 각각 검색해서 **활용신청** (활용 목적은 자유롭게 적으면 됩니다)
   - `조달청_나라장터 공공데이터개방표준서비스`
   - `창업진흥원_K-Startup 조회서비스`
3. 마이페이지 → 활용신청 현황 에서 승인 상태 확인. 자동승인이라 보통 즉시~몇 시간 내에 됩니다.
4. **일반 인증키 (Decoding)** 값을 복사해 둡니다. 두 서비스 모두 같은 키를 씁니다.

### 3단계. Google 서비스 계정 키

프로그램이 여러분 대신 스프레드시트에 쓰려면 "서비스 계정" 이라는 로봇 계정이 필요합니다.

1. https://console.cloud.google.com 접속 → 상단에서 **새 프로젝트** 생성 (이름 자유)
2. 왼쪽 메뉴 **API 및 서비스 → 라이브러리** 에서 다음 두 개를 검색해 **사용 설정**
   - Google Sheets API
   - Google Drive API
3. **IAM 및 관리자 → 서비스 계정 → 서비스 계정 만들기** (이름 자유, 역할은 비워도 됨)
4. 만든 계정 클릭 → **키** 탭 → **키 추가 → 새 키 만들기 → JSON** → 파일이 다운로드됩니다
5. 그 파일을 `credentials.json` 으로 이름을 바꿔 프로젝트 폴더에 둡니다 (git 에는 올라가지 않도록 설정돼 있습니다)

> 회사 Google Workspace 에서 "서비스 계정 키 생성이 조직 정책으로 차단" 이라고 나오면 관리자에게 `iam.disableServiceAccountKeyCreation` 정책 예외를 요청하거나, 개인 Google 계정으로 프로젝트를 만들어도 됩니다. 스프레드시트만 공유하면 되므로 어느 계정의 프로젝트든 상관없습니다.

### 4단계. 스프레드시트 만들고 공유

1. Google Sheets 에서 새 스프레드시트를 만듭니다 (빈 시트면 됩니다. 탭은 프로그램이 만듭니다)
2. 오른쪽 위 **공유** → `credentials.json` 안의 `client_email` 값 (예: `xxx@yyy.iam.gserviceaccount.com`) 을 **편집자** 로 추가
3. 시트 URL 을 복사해 둡니다

### 5단계. `config.yaml` 수정

파일을 열어 다음을 고칩니다. 파일 안 주석에 각 항목 설명이 있습니다.

```yaml
spreadsheet: "https://docs.google.com/spreadsheets/d/....../edit"   # 4단계 URL

keywords:
  general: [스타트업, 창업, ...]      # 제목에 하나라도 있으면 수집
  must: [...]                         # 있으면 무조건 수집
  ends_with: [...]                    # 제목이 이걸로 끝나면 무조건 수집
  conditional: [...]                  # 이 단어만 있으면 수집 안 함

exclusion_keywords: [...]             # 있으면 (필터) 탭에서 제외

min_days_remaining: 7                 # 마감까지 최소 며칠 남아야 수집할지
search_days_back: 30                  # 며칠 전 공고까지 볼지
```

검색어 매칭은 공고 **제목** 기준이며 띄어쓰기와 대소문자를 무시합니다.

### 6단계. 로컬에서 점검 (권장)

Python 3.10 이상이 필요합니다.

```bash
pip install -r requirements.txt
cp .env.example .env        # 열어서 DATA_GO_KR_API_KEY 에 2단계 키 입력
python scripts/doctor.py    # API 키, 서비스 계정, 시트 공유를 한 번에 점검
python main.py              # 실제 수집 (5~10분)
```

`doctor.py` 가 전부 ✓ 이면 GitHub Actions 도 그대로 됩니다.

### 7단계. GitHub Actions 자동 실행

저장소의 **Settings → Secrets and variables → Actions → New repository secret** 에 두 개를 등록합니다.

| Secret 이름 | 값 |
|---|---|
| `DATA_GO_KR_API_KEY` | 2단계 인증키 |
| `GOOGLE_CREDENTIALS_JSON` | `credentials.json` 파일 내용 전체 (메모장으로 열어 전부 복사) |

GitHub CLI 가 있으면 터미널에서 한 번에 됩니다.

```bash
gh secret set DATA_GO_KR_API_KEY
gh secret set GOOGLE_CREDENTIALS_JSON < credentials.json
```

등록 후 **Actions 탭 → 공고 수집 → Run workflow** 로 한 번 수동 실행해 초록불을 확인하세요. 이후 매일 KST 09:00 에 자동 실행됩니다. 시간을 바꾸려면 `.github/workflows/collect.yml` 의 `cron` 줄을 고칩니다. UTC 기준이라 KST 에서 9시간을 빼야 합니다.

> Secrets 는 저장 후 값을 다시 볼 수 없습니다. 빈 칸처럼 보여도 정상입니다.

## 설정 참고

### 값 우선순위

환경변수 (.env 또는 GitHub Secrets/Variables) > `config.yaml` > 코드 기본값

일상적인 조정은 `config.yaml` 만 고치면 됩니다. 환경변수는 비밀값과 임시 실험용입니다.

### 검색어 4단계 판정

제목을 위에서부터 순서대로 검사합니다.

1. **must**: 하나라도 포함 → 수집
2. **ends_with**: 제목이 이 단어로 끝남 → 수집
3. **general**: 하나라도 포함 → 수집
4. **conditional**: 위 셋에 안 걸리고 이것만 있음 → 수집 안 함

예를 들어 `general: [창업]`, `conditional: [소상공인]` 이면 "소상공인 창업 지원" 은 수집되지만 "소상공인 경영안정자금" 은 수집되지 않습니다.

### PDF 사업명 매칭 (선택)

중소벤처기업부가 매년 초 발간하는 **창업지원사업 통합공고 안내서** PDF 가 들어 있습니다. K-Startup 공고 제목을 안내서의 사업명과 유사도(0~100)로 비교해 60점 이상이면 검색어에 안 걸려도 수집하고, 시트에서 연노랑으로 표시합니다.

- 끄려면 `pdf_matching.enabled: false`
- 새해 안내서로 바꾸려면 PDF 파일을 교체하고 `pdf_matching.file` 수정. 목차 구조가 크게 바뀌면 `src/pdf_parser.py` 손질이 필요할 수 있습니다.

### 소스 하나만 쓰기

```yaml
sources:
  nara: {enabled: false}
  kstartup: {enabled: true}
```

## 문제 해결

| 증상 | 원인과 조치 |
|---|---|
| `설정 오류: ... 비어 있습니다` | `config.yaml` 또는 Secrets 누락. 메시지의 항목을 채우세요. |
| `스프레드시트 연결 실패: ... 403` | 시트를 서비스 계정 이메일에 편집자로 공유하지 않았거나 Sheets/Drive API 미활성화 |
| `invalid_grant: account not found` | 서비스 계정 또는 GCP 프로젝트가 삭제됨. 3단계부터 다시 하고 Secret 교체 |
| `API 수집 실패 ... data.go.kr 응답 없음` | 공공데이터포털이 간헐적으로 응답하지 않습니다. 워크플로우가 5분 뒤 자동 재시도하며, 그래도 실패하면 수동 재실행하세요. |
| `SERVICE KEY IS NOT REGISTERED` | 활용신청 미승인 또는 Encoding 키를 넣음. Decoding 키를 쓰세요. |
| 수집 0건 | 검색어가 너무 좁거나 `search_days_back` 이 짧습니다. `log_level: DEBUG` 로 바꿔 매칭 과정을 보세요. |

무엇이 문제인지 모르겠으면 `python scripts/doctor.py` 를 먼저 돌리세요.

## 프로젝트 구조

```
config.yaml            ← 여기만 고치면 됩니다
main.py                실행 진입점
config.py              config.yaml + 환경변수 로더
scripts/doctor.py      설정 점검
src/api_client.py      나라장터·K-Startup API
src/filter.py          검색어·마감일·PDF·금지어 필터
src/pdf_parser.py      안내서 PDF 파싱
src/spreadsheet.py     Google Sheets 증분 업데이트
.github/workflows/collect.yml   자동 실행 스케줄
docs/API_info.md       두 API 명세 요약
CLAUDE.md              Claude Code 용 프로젝트 컨텍스트
```

## 라이선스

MIT. 자유롭게 복사·수정해서 쓰세요.
