"""
설정 로더
- config.yaml 을 읽고, 환경변수(.env / GitHub Secrets)로 덮어쓴다.
- 비밀값(API 키, 서비스 계정 키)은 환경변수에서만 읽는다.

우선순위: 환경변수 > config.yaml > 기본값
"""
import os
import re
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(dotenv_path=ROOT / '.env')

CONFIG_FILE = Path(os.getenv('CONFIG_FILE', ROOT / 'config.yaml'))


def _load_yaml() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


_cfg = _load_yaml()


def _get(path: str, default=None):
    """'a.b.c' 경로로 yaml 값 조회"""
    node = _cfg
    for key in path.split('.'):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def _env_list(name: str, fallback: list) -> list:
    """환경변수(쉼표 구분)가 있으면 그것을, 없으면 yaml 리스트를 사용"""
    raw = os.getenv(name)
    if raw is not None:
        return [k.strip() for k in raw.split(',') if k.strip()]
    return [str(k).strip() for k in (fallback or []) if str(k).strip()]


def _env_int(name: str, fallback) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, '') else int(fallback)


def _env_bool(name: str, fallback) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(fallback)
    return raw.strip().lower() in ('1', 'true', 'yes', 'y', 'on')


def extract_sheet_id(value: str) -> str:
    """스프레드시트 URL 또는 ID → ID"""
    if not value:
        return ''
    value = value.strip()
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', value)
    if m:
        return m.group(1)
    return '' if value.startswith('http') else value


# ---------------------------------------------------------------------------
# 기준일
# ---------------------------------------------------------------------------
BASE_DATE = date.today()
YEAR = BASE_DATE.year

# ---------------------------------------------------------------------------
# 비밀값 (환경변수 전용)
# ---------------------------------------------------------------------------
# data.go.kr 인증키 하나로 나라장터·K-Startup 모두 호출 가능.
# 소스별로 다른 키를 쓰려면 NARA_API_KEY / KSTARTUP_API_KEY 를 따로 지정.
DATA_GO_KR_API_KEY = os.getenv('DATA_GO_KR_API_KEY', '')
NARA_API_KEY = os.getenv('NARA_API_KEY') or os.getenv('NARA_API_KEY_DECODED') or DATA_GO_KR_API_KEY
KSTARTUP_API_KEY = os.getenv('KSTARTUP_API_KEY') or os.getenv('KSTARTUP_API_KEY_DECODED') or DATA_GO_KR_API_KEY

GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', str(ROOT / 'credentials.json'))
# 파일 대신 JSON 문자열을 직접 넣을 수도 있음 (GitHub Actions 에서 사용)
GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '')

# ---------------------------------------------------------------------------
# 스프레드시트
# ---------------------------------------------------------------------------
GOOGLE_SHEET_ID = extract_sheet_id(os.getenv('GOOGLE_SHEET_ID') or _get('spreadsheet', ''))

# ---------------------------------------------------------------------------
# API 엔드포인트
# ---------------------------------------------------------------------------
NARA_API_ENDPOINT = os.getenv('NARA_API_ENDPOINT', 'https://apis.data.go.kr/1230000/ao/PubDataOpnStdService')
KSTARTUP_API_ENDPOINT = os.getenv('KSTARTUP_API_ENDPOINT', 'https://apis.data.go.kr/B552735/kisedKstartupService01')

API_TIMEOUT = _env_int('API_TIMEOUT', _get('api.timeout', 30))
API_MAX_RETRIES = _env_int('API_MAX_RETRIES', _get('api.max_retries', 5))
API_RETRY_DELAY = _env_int('API_RETRY_DELAY', _get('api.retry_delay', 20))

# ---------------------------------------------------------------------------
# 검색어 / 금지어
# ---------------------------------------------------------------------------
KEYWORDS = _env_list('KEYWORDS', _get('keywords.general', []))
MUST_EXTRACT_KEYWORDS = _env_list('MUST_EXTRACT_KEYWORDS', _get('keywords.must', []))
END_KEYWORDS = _env_list('END_KEYWORDS', _get('keywords.ends_with', []))
CONDITIONAL_KEYWORDS = _env_list('CONDITIONAL_KEYWORDS', _get('keywords.conditional', []))
EXCLUSION_KEYWORDS = _env_list('EXCLUSION_KEYWORDS', _get('exclusion_keywords', []))

# ---------------------------------------------------------------------------
# 기간 기준
# ---------------------------------------------------------------------------
MIN_DAYS_REMAINING = _env_int('MIN_DAYS_REMAINING', _get('min_days_remaining', 7))
SEARCH_DAYS_BACK = _env_int('SEARCH_DAYS_BACK', _get('search_days_back', 30))

# ---------------------------------------------------------------------------
# 소스 on/off
# ---------------------------------------------------------------------------
NARA_ENABLED = _env_bool('NARA_ENABLED', _get('sources.nara.enabled', True))
KSTARTUP_ENABLED = _env_bool('KSTARTUP_ENABLED', _get('sources.kstartup.enabled', True))

# ---------------------------------------------------------------------------
# PDF 매칭
# ---------------------------------------------------------------------------
PDF_ENABLED = _env_bool('PDF_ENABLED', _get('pdf_matching.enabled', True)) and KSTARTUP_ENABLED
PDF_PATH = str(ROOT / os.getenv('PDF_FILE', _get('pdf_matching.file', 'Public_Announcement_guidebook.pdf')))
MATCH_THRESHOLD = _env_int('PDF_MATCH_THRESHOLD', _get('pdf_matching.threshold', 60))
SHEET_NAME_PDF = str(_get('pdf_matching.sheet_name', '{year} 창업지원사업')).replace('{year}', str(YEAR))

# ---------------------------------------------------------------------------
# 시트 탭 이름 / 헤더
# ---------------------------------------------------------------------------
SHEET_NAME_NARA = _get('sheets.nara', '나라장터')
SHEET_NAME_KSTARTUP = _get('sheets.kstartup', 'K-Startup')
SHEET_NAME_NARA_FILTERED = _get('sheets.nara_filtered', '나라장터(필터)')
SHEET_NAME_KSTARTUP_FILTERED = _get('sheets.kstartup_filtered', 'K-Startup(필터)')

NARA_HEADERS = ['공고명', '공고ID', '발주기관', '마감일', '남은일수', '예산', '등록일자', '업로드일자']
KSTARTUP_HEADERS = ['공고명', '공고ID', '발주기관', '마감일', '남은일수', '과업개요', '등록일자', '업로드일자']
PDF_HEADERS = ['사업명', '구분(주관)', '구분(성격)', '예정공고시기', '페이지']

# ---------------------------------------------------------------------------
# 로그
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv('LOG_LEVEL', _get('log_level', 'INFO'))


def resolve_credentials_file() -> str:
    """
    서비스 계정 키 파일 경로를 확정한다.
    GOOGLE_CREDENTIALS_JSON 환경변수가 있으면 파일로 풀어서 그 경로를 돌려준다.
    """
    if GOOGLE_CREDENTIALS_JSON.strip():
        Path(GOOGLE_CREDENTIALS_FILE).write_text(GOOGLE_CREDENTIALS_JSON, encoding='utf-8')
    return GOOGLE_CREDENTIALS_FILE


def validate_config():
    """필수값 검증. 문제가 있으면 예외를 던진다."""
    problems = []

    if not GOOGLE_SHEET_ID or '여기에' in GOOGLE_SHEET_ID:
        problems.append("spreadsheet (config.yaml) 또는 GOOGLE_SHEET_ID 환경변수가 비어 있습니다.")
    if NARA_ENABLED and not NARA_API_KEY:
        problems.append("DATA_GO_KR_API_KEY (또는 NARA_API_KEY) 환경변수가 없습니다.")
    if KSTARTUP_ENABLED and not KSTARTUP_API_KEY:
        problems.append("DATA_GO_KR_API_KEY (또는 KSTARTUP_API_KEY) 환경변수가 없습니다.")
    if not NARA_ENABLED and not KSTARTUP_ENABLED:
        problems.append("sources 에서 최소 하나는 enabled: true 여야 합니다.")

    creds = resolve_credentials_file()
    if not Path(creds).exists():
        problems.append(
            f"Google 서비스 계정 키 파일이 없습니다: {creds}\n"
            "    → credentials.json 을 프로젝트 루트에 두거나 GOOGLE_CREDENTIALS_JSON 환경변수를 설정하세요."
        )

    if PDF_ENABLED and not Path(PDF_PATH).exists():
        problems.append(f"PDF 파일이 없습니다: {PDF_PATH} (pdf_matching.enabled: false 로 끄거나 파일을 넣으세요)")

    if not (KEYWORDS or MUST_EXTRACT_KEYWORDS or END_KEYWORDS):
        problems.append("검색어가 하나도 없습니다. config.yaml 의 keywords 를 채우세요.")

    if problems:
        raise ValueError("설정 오류:\n  - " + "\n  - ".join(problems))

    print("✓ 설정 검증 완료")
    print(f"  - 설정 파일: {CONFIG_FILE}")
    print(f"  - 스프레드시트 ID: {GOOGLE_SHEET_ID}")
    print(f"  - 소스: 나라장터={'on' if NARA_ENABLED else 'off'}, K-Startup={'on' if KSTARTUP_ENABLED else 'off'}, PDF매칭={'on' if PDF_ENABLED else 'off'}")
    print(f"  - 검색어: 일반 {len(KEYWORDS)}개, 필수 {len(MUST_EXTRACT_KEYWORDS)}개, 끝부분 {len(END_KEYWORDS)}개, 조건부 {len(CONDITIONAL_KEYWORDS)}개")
    print(f"  - 금지어: {len(EXCLUSION_KEYWORDS)}개")
    print(f"  - 검색 범위: {SEARCH_DAYS_BACK}일 전~오늘 / 최소 남은 일수: {MIN_DAYS_REMAINING}일")
    print(f"  - 기준일: {BASE_DATE}")
