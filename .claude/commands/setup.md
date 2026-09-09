---
description: 공고 수집기 초기 세팅을 대화식으로 안내 (API 키, 서비스 계정, 시트, Secrets, 첫 실행)
---

사용자가 이 저장소를 처음 세팅하도록 돕는다. 사용자는 비개발자일 수 있다. 한 번에 하나씩, 짧게 안내하고 결과를 확인한 뒤 다음으로 넘어간다. 아래 순서를 따르되 이미 된 단계는 건너뛴다.

## 0. 현재 상태 파악

먼저 조용히 확인한다.

- `config.yaml` 의 `spreadsheet` 가 아직 예시값(`여기에_`)인지
- `.env` 와 `credentials.json` 이 있는지
- `gh auth status` 로 GitHub CLI 로그인이 돼 있는지, `git remote -v` 로 이 저장소가 사용자 계정의 것인지
- `python --version` 이 3.10 이상인지, `pip install -r requirements.txt` 가 됐는지

확인 결과를 한 줄로 요약하고, 남은 단계만 진행한다.

## 1. 저장소

`git remote -v` 가 원본 템플릿(`CIC-bomnal/announcement-collector`)을 가리키고 있으면, 사용자는 자기 복사본이 아니라 원본을 클론한 것이다. 이 상태로는 설정을 커밋하거나 Actions 를 돌릴 수 없다. 사용자에게 저장소 이름(예: `announcement-collector`)과 Private 여부만 묻고, `gh` 로 자기 계정에 복사본을 만들어 다시 클론한다.

```bash
gh repo create <이름> --template CIC-bomnal/announcement-collector --private --clone
```

새로 생긴 폴더로 이동한 뒤 나머지 단계를 진행한다 (사용자에게 그 폴더에서 `claude` 를 다시 열라고 안내). `gh` 가 로그인돼 있지 않으면 `gh auth login` 을 먼저 하게 한다. 검색어가 외부에 보이는 게 싫으면 Private 을 권한다.

## 2. data.go.kr 인증키

사람이 직접 해야 한다. 아래를 그대로 안내한다.

1. https://www.data.go.kr 로그인
2. `조달청_나라장터 공공데이터개방표준서비스`, `창업진흥원_K-Startup 조회서비스` 각각 검색 → 활용신청
3. 마이페이지 → 활용신청 현황 → **일반 인증키(Decoding)** 복사

받은 키를 `.env` 의 `DATA_GO_KR_API_KEY` 에 넣는다 (`.env` 가 없으면 `.env.example` 을 복사). 키는 채팅에 붙여넣으라고 해도 되지만, 대화 로그에 남는다는 점을 한 줄 알려준다.

## 3. Google 서비스 계정

사람이 직접 해야 한다.

1. https://console.cloud.google.com → 새 프로젝트
2. API 및 서비스 → 라이브러리 → **Google Sheets API**, **Google Drive API** 사용 설정
3. IAM 및 관리자 → 서비스 계정 → 만들기 → 키 탭 → 키 추가 → JSON
4. 다운로드된 파일 경로를 물어본다

파일 경로를 받으면 `credentials.json` 으로 프로젝트 루트에 복사하고, 파일에서 `client_email` 을 읽어 사용자에게 보여준다. 개인 키 값은 출력하지 않는다.

## 4. 스프레드시트

1. 새 스프레드시트를 만들고 위 `client_email` 에 **편집자** 로 공유하라고 안내
2. URL 을 받아 `config.yaml` 의 `spreadsheet` 에 넣는다

## 5. 검색어·금지어

사용자에게 물어본다. "어떤 공고를 찾고 싶은지" 를 말로 들은 뒤 `config.yaml` 의 `keywords` 4단계와 `exclusion_keywords` 로 옮겨 적고, 왜 그렇게 나눴는지 한두 줄로 설명한다. 잘 모르겠다고 하면 예시값을 그대로 두고 나중에 조정하자고 한다. `min_days_remaining`, `search_days_back` 도 기본값(7, 30)이 어떤 뜻인지 한 줄로 설명하고 바꿀지 묻는다.

## 6. 점검

```bash
python scripts/doctor.py
```

✗ 가 있으면 힌트대로 고치고 다시 돌린다. 전부 ✓ 가 될 때까지 반복한다. 그 다음 `python main.py` 로 실제 한 번 돌려 시트에 탭이 생기는지 확인시킨다 (5~10분 걸린다고 미리 알린다).

## 7. GitHub Actions

`gh` 가 로그인돼 있으면 직접 실행한다.

```bash
gh secret set DATA_GO_KR_API_KEY --body "$(grep DATA_GO_KR_API_KEY .env | cut -d= -f2-)"
gh secret set GOOGLE_CREDENTIALS_JSON < credentials.json
git add config.yaml && git commit -m "설정: 검색어·시트 등록" && git push
gh workflow run "공고 수집"
gh run watch
```

`gh` 가 없으면 README 7단계의 웹 UI 경로를 안내한다. 첫 실행이 초록불이면 완료. 실행 시각을 바꾸고 싶다면 `.github/workflows/collect.yml` 의 cron 을 고쳐준다 (UTC = KST − 9).

## 마무리

한 줄로 정리한다: 매일 몇 시에 돌고, 결과는 어느 시트에 쌓이며, 검색어를 바꾸려면 `config.yaml` 만 고쳐서 push 하면 된다는 것.
