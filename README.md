# 공고 수집기 (announcement-collector)

지정한 검색어/금지어를 설정하면 해당 키워드로 나라장터(조달청)와 K-Startup(창업진흥원)의 공고를 매일 자동으로 검색하여 Google 스프레드시트에 쌓아줍니다.
> **Claude Code 를 쓰신다면** 이 저장소를 클론한 뒤 `claude` 를 실행하고 `/setup` 이라고 입력하세요. 아래 과정을 대화식으로 안내합니다. 직접 세팅하실 경우 아래 내용을 읽고 단계별로 진행해 주시면 됩니다.

## 결과물 미리보기

스프레드시트에 아래 탭이 자동으로 생깁니다.

| 탭 | 내용 |
|---|---|
| 나라장터 | 검색어에 걸린 입찰공고. 공고명(링크), 공고ID, 발주기관, 마감일, 남은일수, 예산, 등록일자, 업로드일자 |
| K-Startup | 검색어에 걸린 지원사업 공고. 예산 대신 과업개요 |
| 나라장터(필터) / K-Startup(필터) | 위 두 탭에서 금지어가 포함된 공고를 뺀 것 |

매 실행마다 새 공고는 추가되고, 이미 있는 공고는 마감일이 갱신되며, 마감이 임박한 공고는 지워집니다. (기준은 직접 세팅 가능)

## 사전 준비 사항 (소요시간 약 20분)

- **GitHub 계정** (무료). 코드를 복사하고 매일 자동 실행하는 데 씁니다.
- **공공데이터포털 계정** (무료). 공고 API 키를 받는 데 씁니다.
- **Google 계정**. 스프레드시트와 서비스 계정을 만드는 데 씁니다. 개인 Gmail 도 됩니다.
- **결과를 받을 Google 스프레드시트 1개**. 빈 시트를 새로 만들고 주소창의 URL 을 복사해 두세요. URL 가운데 `/d/` 와 `/edit` 사이의 긴 문자열이 시트 ID 이고, 5단계에서 이 값을 씁니다. (URL 전체를 붙여넣어도 프로그램이 ID 를 알아서 뽑습니다)

## 세팅 순서

### 1단계. GitHub 계정 만들고 저장소 복사

1. GitHub 계정이 없다면 https://github.com/signup 에서 가입합니다. 이메일 주소만 있으면 되고, 무료 플랜이면 충분합니다.
2. 로그인한 상태로 이 페이지 상단의 **Use this template → Create a new repository** 를 누릅니다.
3. Owner 는 본인 계정(또는 조직 계정), Repository name 은 자유롭게 정합니다. 검색어가 외부에 보이는 게 싫다면 **Private** 을 선택하세요. 
4. **Create repository** 를 누르면 여러분 계정에 복사본이 생깁니다. 이후 작업은 모두 그 복사본에서 합니다.

### 2단계. 공공데이터포털 API 키 발급

1. https://www.data.go.kr 회원가입 후 로그인
2. 아래 두 서비스를 각각 검색해서 **활용신청** (활용 목적은 자유롭게 적으면 됩니다)
   - `조달청_나라장터 공공데이터개방표준서비스`
   - `창업진흥원_K-Startup 조회서비스`
3. 마이페이지 → 활용신청 현황 에서 승인 상태 확인. 자동승인이라 보통 즉시 발급됩니다.
4. **일반 인증키 (Decoding)** 값을 복사해 둡니다. 두 서비스 모두 같은 키를 씁니다.

### 3단계. Google 서비스 계정 키

프로그램이 여러분 대신 스프레드시트에 접근해서 값을 입력하려면 "서비스 계정" 이라는 로봇 계정이 필요합니다.

1. https://console.cloud.google.com 접속 → 상단에서 **새 프로젝트** 생성 (이름 자유)
2. 왼쪽 메뉴 **API 및 서비스 → 라이브러리** 에서 다음 두 개를 검색해 **사용 설정**
   - Google Sheets API
   - Google Drive API
3. **IAM 및 관리자 → 서비스 계정 → 서비스 계정 만들기** (이름 자유, 역할은 비워도 됨)
4. 만든 계정 클릭 → **키** 탭 → **키 추가 → 새 키 만들기 → JSON** → 파일이 다운로드됩니다
5. 그 파일을 `credentials.json` 으로 이름을 바꿔 프로젝트 폴더에 둡니다 (git 에는 올라가지 않도록 설정돼 있습니다)

### 4단계. 스프레드시트 만들고 공유

1. Google Sheets 에서 새 스프레드시트를 만듭니다 (빈 시트면 됩니다. 탭은 프로그램이 만듭니다)
2. 오른쪽 위 **공유** → `credentials.json` 안의 `client_email` 값 (예: `xxx@yyy.iam.gserviceaccount.com`) 을 **편집자** 로 추가
3. 시트 URL 을 복사해 둡니다

### 5단계. `config.yaml` 수정

파일을 열어 항목별로 원하는 내용을 입력합니다. 이 값을 기준으로 크롤링하는데요, 파일 안 주석에 각 항목 설명이 있으니 확인하시어 본인/조직 상황에 맞게 입력하시면 됩니다.

```yaml
spreadsheet: "https://docs.google.com/spreadsheets/d/....../edit"   # 4단계 URL

keywords:
  general: [스타트업, 창업, ...]      # 제목에 하나라도 있으면 수집하는 검색어
  ends_with: [...]                    # 제목이 이걸로 끝나면 무조건 수집하는 검색어 예) 운영 용역 사업을 빠짐없이 확인하고 싶음 > "운영 용역"
  conditional: [...]                  # 위 검색어들과 함께 등장하지 않으면 수집하지 않는 검색어 예) 소셜벤처 육성 사업을 수집하고 싶은데, "소셜"이라는 키워드만 입력하면 육성과 무관한 사업이 수집될 우려가 있음 > "소셜"

exclusion_keywords: [...]             # 금지어. 제목에 있으면 (필터) 탭에서 제외

min_days_remaining: 7                 # 수집 기준일 수(마감까지 최소 며칠 남아야 수집할지) 예) 7으로 설정 > 7일 미만 공고는 수집X
search_days_back: 30                  # 공고 수집일 기준(며칠 전 공고까지 볼지) 예) 30으로 설정 > 검색일로부터 30일 이전에 게시된 옛날 공고는 수집X
```

검색어 매칭은 공고 **제목** 으로만 진행되며, 띄어쓰기와 대소문자를 무시합니다. (공고 상세 내용은 검색 대상이 아님)

GitHub 웹에서 바로 고치려면 저장소 화면에서 `config.yaml` 클릭 → 연필 아이콘 → 수정 → **Commit changes** 를 누르면 됩니다.

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

GitHub Actions 는 GitHub 가 제공하는 무료 실행 서버입니다. 이 저장소에는 매일 한 번 `python main.py` 를 돌리는 설정(`.github/workflows/collect.yml`)이 이미 들어 있어서, "Secrets" 두 개만 등록하면 바로 동작합니다.

**7-1. Secrets 등록**

1. 1단계에서 만든 저장소 페이지 상단의 **Settings** 탭을 누릅니다.
2. 왼쪽 메뉴에서 **Secrets and variables → Actions** 를 누릅니다.
3. **New repository secret** 버튼을 누르고 아래 두 개를 하나씩 등록합니다. Name 은 대소문자까지 똑같이 적어야 합니다.

| Name | Secret (값) |
|---|---|
| `DATA_GO_KR_API_KEY` | 2단계에서 복사한 인증키 |
| `GOOGLE_CREDENTIALS_JSON` | `credentials.json` 파일을 메모장으로 열어 **전체 내용**을 복사해 붙여넣기 (`{` 로 시작해서 `}` 로 끝나야 합니다) |

GitHub CLI 를 쓸 줄 안다면 터미널에서 한 번에 됩니다.

```bash
gh secret set DATA_GO_KR_API_KEY
gh secret set GOOGLE_CREDENTIALS_JSON < credentials.json
```

> Secrets 는 노출되면 안 되는 정보들이 저장돼 있는 터라, 저장하면 값을 다시 볼 수 없습니다. 하여 빈 칸처럼 보여도 정상입니다. 잘못 넣었으면 같은 이름으로 다시 등록하면 덮어써집니다.

**7-2. 첫 실행**

1. 저장소 상단의 **Actions** 탭을 누릅니다. "Workflows aren't being run on this repository" 같은 안내가 보이면 초록색 **Enable** 버튼을 눌러 켭니다.
2. 왼쪽 목록에서 **공고 수집** 을 누릅니다.
3. 오른쪽의 **Run workflow ▾ → Run workflow** 를 누릅니다.
4. 잠시 뒤 목록에 실행 항목이 생깁니다. 노란 점은 실행 중, 초록 체크는 성공, 빨간 X 는 실패입니다. 첫 실행은 5~10분 걸립니다.
5. 초록 체크가 뜨면 4단계의 스프레드시트를 열어 보세요. 탭이 생기고 공고가 들어와 있으면 세팅 완료입니다.

**7-3. 실패했을 때**

빨간 X 항목을 누르고 **collect** 를 누르면 실행 로그가 나옵니다. 아래로 내려가면 `✗` 로 시작하는 줄에 원인이 적혀 있습니다. 대부분은 이 문서 끝의 **문제 해결** 표에 있는 경우입니다. 고친 뒤 7-2 를 다시 하면 됩니다.

**7-4. 실행 시각 바꾸기**

기본은 매일 KST 09:00 입니다. 바꾸려면 `.github/workflows/collect.yml` 파일의 `cron` 줄을 고칩니다. GitHub 는 UTC 기준이라 원하는 한국 시각에서 9시간을 뺀 값을 적습니다.

```yaml
- cron: '0 0 * * *'      # 매일 KST 09:00
- cron: '0 5 * * *'      # 매일 KST 14:00 (줄을 추가하면 하루 두 번)
- cron: '0 0 * * 1-5'    # 평일만 KST 09:00
```

GitHub 는 예약 시각보다 수십 분 늦게 시작하는 일이 흔합니다. 정확한 시각이 중요하지 않다면 그대로 두세요.

**7-5. 알아둘 것**

- 저장소에 60일 동안 아무 커밋이 없으면 GitHub 가 예약 실행을 자동으로 끕니다. Actions 탭에 "This scheduled workflow is disabled" 안내가 뜨면 **Enable workflow** 를 누르면 다시 돕니다. 
- 무료 플랜의 Actions 한도는 월 2,000분입니다. 이 프로그램은 하루 한 번 약 10분을 쓰므로 여유가 큽니다. Public 저장소는 한도 자체가 없습니다.

## 검색어 판정 순서

제목을 위에서부터 순서대로 검사합니다.

1. **ends_with**: 제목이 이 단어로 끝남 → 수집
2. **general**: 하나라도 포함 → 수집
3. **conditional**: 위 둘에 안 걸리고 이것만 있음 → 수집 안 함

예를 들어 `general: [창업]`, `conditional: [소상공인]` 이면 "소상공인 창업 지원" 은 수집되지만 "소상공인 경영안정자금" 은 수집되지 않습니다.


## 문제 해결

오류가 난다면 `python scripts/doctor.py` 를 실행하세요.

| 증상 | 원인과 조치 |
|---|---|
| `설정 오류: ... 비어 있습니다` | `config.yaml` 또는 Secrets 누락. 메시지의 항목을 채우세요. |
| `스프레드시트 연결 실패: ... 403` | 시트를 서비스 계정 이메일에 편집자로 공유하지 않았거나 Sheets/Drive API 미활성화 |
| `invalid_grant: account not found` | 서비스 계정 또는 GCP 프로젝트가 삭제됨. 3단계부터 다시 하고 Secret 교체 |
| `API 수집 실패 ... data.go.kr 응답 없음` | 공공데이터포털이 간헐적으로 응답하지 않습니다. 워크플로우가 5분 뒤 자동 재시도하며, 그래도 실패하면 수동 재실행하세요. |
| `SERVICE KEY IS NOT REGISTERED` | 활용신청 미승인 또는 Encoding 키를 넣음. Decoding 키를 쓰세요. |
| 수집 0건 | 검색어가 너무 좁거나 `search_days_back` 이 짧습니다. `log_level: DEBUG` 로 바꿔 매칭 과정을 보세요. |

## 프로젝트 구조

```
config.yaml            ← 여기만 수정하면 됩니다!
main.py                실행 진입점
config.py              config.yaml + 환경변수 로더
scripts/doctor.py      설정 점검
src/api_client.py      나라장터·K-Startup API
src/filter.py          검색어·마감일·금지어 필터
src/spreadsheet.py     Google Sheets 증분 업데이트
.github/workflows/collect.yml   자동 실행 스케줄
docs/API_info.md       두 API 명세 요약
CLAUDE.md              Claude Code 용 프로젝트 컨텍스트
```

## 라이선스

MIT. 자유롭게 복사·수정해서 쓰세요.
