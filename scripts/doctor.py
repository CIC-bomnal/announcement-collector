"""
설정 점검 도구 — 시트를 건드리지 않고 연결만 확인한다.

사용:
    python scripts/doctor.py

확인 항목:
  1. config.yaml / 환경변수 로드
  2. data.go.kr 인증키로 실제 호출 (1건만)
  3. 서비스 계정 키 파일 파싱
  4. 스프레드시트 열기 (공유 여부 확인)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OK, NG, WARN = '✓', '✗', '!'
problems = 0


def report(ok, msg, hint=''):
    global problems
    print(f"  {OK if ok else NG} {msg}")
    if not ok:
        problems += 1
        if hint:
            print(f"      → {hint}")


print("=" * 60)
print("공고 수집기 설정 점검")
print("=" * 60)

# 1. 설정 로드
print("\n[1] 설정")
try:
    import config
    report(True, f"설정 파일 로드: {config.CONFIG_FILE}")
except Exception as e:
    report(False, f"설정 로드 실패: {e}")
    sys.exit(1)

report(bool(config.GOOGLE_SHEET_ID) and '여기에' not in config.GOOGLE_SHEET_ID,
       f"스프레드시트 ID: {config.GOOGLE_SHEET_ID or '(없음)'}",
       "config.yaml 의 spreadsheet 에 시트 URL 을 넣으세요.")
report(bool(config.KEYWORDS or config.MUST_EXTRACT_KEYWORDS or config.END_KEYWORDS),
       f"검색어: 일반 {len(config.KEYWORDS)} / 필수 {len(config.MUST_EXTRACT_KEYWORDS)} / 끝부분 {len(config.END_KEYWORDS)} / 조건부 {len(config.CONDITIONAL_KEYWORDS)}",
       "config.yaml 의 keywords 를 채우세요.")
print(f"  {WARN} 금지어 {len(config.EXCLUSION_KEYWORDS)}개, 최소 남은 일수 {config.MIN_DAYS_REMAINING}일, 검색 범위 {config.SEARCH_DAYS_BACK}일")

# 2. API 키
print("\n[2] data.go.kr API")
import requests

def probe(name, url, params):
    try:
        r = requests.get(url, params=params, timeout=config.API_TIMEOUT)
        body = r.text[:300]
        if r.status_code == 200 and ('response' in body or '"data"' in body or 'currentCount' in body):
            report(True, f"{name} 호출 성공")
        elif 'SERVICE_KEY' in body.upper() or 'UNREGISTERED' in body.upper() or r.status_code in (401, 403):
            report(False, f"{name}: 인증키 오류 (HTTP {r.status_code})",
                   "data.go.kr 마이페이지의 '일반 인증키(Decoding)' 값을 DATA_GO_KR_API_KEY 에 넣으세요. "
                   "활용신청 후 승인까지 몇 시간 걸릴 수 있습니다.")
        else:
            report(False, f"{name}: 예상치 못한 응답 (HTTP {r.status_code}): {body[:120]}")
    except requests.exceptions.RequestException as e:
        report(False, f"{name}: 연결 실패 — {e.__class__.__name__}",
               "네트워크 문제일 수 있습니다. 잠시 후 다시 시도하세요.")

if config.NARA_ENABLED:
    if not config.NARA_API_KEY:
        report(False, "나라장터: 인증키 없음", ".env 또는 Secrets 에 DATA_GO_KR_API_KEY 를 넣으세요.")
    else:
        probe("나라장터", f"{config.NARA_API_ENDPOINT}/getDataSetOpnStdBidPblancInfo",
              {'ServiceKey': config.NARA_API_KEY, 'type': 'json', 'numOfRows': 1, 'pageNo': 1,
               'bidNtceBgnDt': config.BASE_DATE.strftime('%Y%m%d') + '0000',
               'bidNtceEndDt': config.BASE_DATE.strftime('%Y%m%d') + '2359'})
if config.KSTARTUP_ENABLED:
    if not config.KSTARTUP_API_KEY:
        report(False, "K-Startup: 인증키 없음", ".env 또는 Secrets 에 DATA_GO_KR_API_KEY 를 넣으세요.")
    else:
        probe("K-Startup", f"{config.KSTARTUP_API_ENDPOINT}/getAnnouncementInformation01",
              {'ServiceKey': config.KSTARTUP_API_KEY, 'returnType': 'json', 'page': 1, 'perPage': 1})

# 3. 서비스 계정 키
print("\n[3] Google 서비스 계정")
creds_path = Path(config.resolve_credentials_file())
client_email = ''
if not creds_path.exists():
    report(False, f"키 파일 없음: {creds_path}",
           "Google Cloud 콘솔에서 서비스 계정 JSON 키를 받아 credentials.json 으로 저장하세요.")
else:
    try:
        creds = json.loads(creds_path.read_text(encoding='utf-8'))
        client_email = creds.get('client_email', '')
        ok = creds.get('type') == 'service_account' and client_email and creds.get('private_key')
        report(bool(ok), f"키 파일 정상 (project: {creds.get('project_id')})",
               "서비스 계정 키(JSON)가 아닙니다. OAuth 클라이언트 키와 혼동하지 마세요.")
        if client_email:
            print(f"      서비스 계정 이메일: {client_email}")
            print(f"      → 스프레드시트를 이 주소에 '편집자' 로 공유해야 합니다.")
    except Exception as e:
        report(False, f"키 파일 파싱 실패: {e}")

# 4. 스프레드시트 접근
print("\n[4] 스프레드시트 접근")
if creds_path.exists() and config.GOOGLE_SHEET_ID:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        gc = gspread.authorize(Credentials.from_service_account_file(str(creds_path), scopes=scopes))
        ss = gc.open_by_key(config.GOOGLE_SHEET_ID)
        tabs = [ws.title for ws in ss.worksheets()]
        report(True, f"시트 열기 성공: '{ss.title}' (탭 {len(tabs)}개: {', '.join(tabs[:6])}{'...' if len(tabs) > 6 else ''})")
        print(f"      https://docs.google.com/spreadsheets/d/{config.GOOGLE_SHEET_ID}")
    except Exception as e:
        msg = str(e)
        if 'invalid_grant' in msg or 'account not found' in msg:
            hint = "서비스 계정이 삭제되었거나 프로젝트가 없습니다. 새 서비스 계정 키를 발급하세요."
        elif '403' in msg or 'PERMISSION' in msg.upper():
            hint = f"시트를 {client_email or '서비스 계정 이메일'} 에 '편집자' 로 공유하세요. Sheets API / Drive API 가 활성화돼 있는지도 확인."
        elif '404' in msg:
            hint = "스프레드시트 ID 가 틀렸습니다. 시트 URL 의 /d/ 와 /edit 사이 값입니다."
        else:
            hint = ""
        report(False, f"시트 열기 실패: {msg[:200]}", hint)
else:
    print(f"  {WARN} 키 파일 또는 시트 ID 가 없어 건너뜀")

print("\n" + "=" * 60)
if problems:
    print(f"{NG} 문제 {problems}건. 위 힌트를 따라 수정한 뒤 다시 실행하세요.")
    sys.exit(1)
print(f"{OK} 모든 점검 통과. `python main.py` 로 실행하거나 GitHub Actions 를 켜세요.")
