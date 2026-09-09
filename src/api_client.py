"""
API 클라이언트 모듈
나라장터 및 K-Startup API 호출
"""
import requests
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging

from kiwipiepy import Kiwi


logger = logging.getLogger('announcement_collector')

# Kiwi 형태소 분석기 초기화 (싱글톤)
_kiwi_instance = None


def get_kiwi():
    """Kiwi 인스턴스 반환 (싱글톤)"""
    global _kiwi_instance
    if _kiwi_instance is None:
        _kiwi_instance = Kiwi()
    return _kiwi_instance


class NaraAPIClient:
    """나라장터 API 클라이언트"""

    def __init__(self, api_key: str, endpoint: str, timeout: int = 30,
                 max_retries: int = 5, retry_delay: int = 20):
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.failed = False  # 재시도 후에도 요청이 실패했는지 (main 에서 확인)

    def fetch_announcements(self, search_days_back: int = 0) -> List[Dict]:
        """
        나라장터에서 공고 데이터 수집
        기본: 당일만 조회 (search_days_back=0)
        백필: search_days_back=90 → 3개월 전~오늘

        Args:
            search_days_back: 오늘로부터 몇 일 전까지 조회할지 (0=당일만)

        Returns:
            공고 리스트
        """
        all_announcements = []

        from datetime import datetime, timedelta

        fetch_end = datetime.now()
        fetch_start = datetime.now() - timedelta(days=search_days_back) if search_days_back > 0 else datetime.now().replace(hour=0, minute=0, second=0)

        current_date = fetch_start
        chunk_num = 1

        logger.info(f"나라장터 조회 범위: {fetch_start.strftime('%Y-%m-%d')} ~ {fetch_end.strftime('%Y-%m-%d')}")
        while current_date <= fetch_end:
            # 30일 단위 시작일과 종료일 계산
            chunk_start = current_date
            chunk_end = min(current_date + timedelta(days=29, hours=23, minutes=59, seconds=59), fetch_end)

            start_date = chunk_start.strftime('%Y%m%d%H%M')
            end_date = chunk_end.strftime('%Y%m%d%H%M')

            logger.info(f"나라장터 API 호출: {chunk_num}차 ({chunk_start.strftime('%m/%d')}~{chunk_end.strftime('%m/%d')})")

            page = 1
            while True:
                params = {
                    'ServiceKey': self.api_key,
                    'type': 'json',
                    'numOfRows': 999,
                    'pageNo': page,
                    'bidNtceBgnDt': start_date,
                    'bidNtceEndDt': end_date
                }

                try:
                    response = self._make_request(params)

                    # 원본 응답에서 실제 반환된 아이템 수 확인 (페이지네이션 판단용)
                    raw_items_count = self._get_raw_items_count(response)

                    items = self._parse_response(response)

                    if not items and raw_items_count == 0:
                        break

                    all_announcements.extend(items)
                    logger.debug(f"  페이지 {page}: {len(items)}건 수집 (원본 {raw_items_count}건)")

                    # 다음 페이지 확인: 원본 응답의 아이템 수로 판단
                    if raw_items_count < 100:
                        break
                    page += 1

                except Exception as e:
                    logger.error(f"나라장터 API 오류 ({chunk_num}차, 페이지 {page}): {str(e)}")
                    self.failed = True
                    break

            # 다음 30일로 이동
            current_date += timedelta(days=30)
            chunk_num += 1

        # 청크 경계 겹침으로 인한 중복 제거
        seen_ids = set()
        unique = []
        for a in all_announcements:
            if a['id'] not in seen_ids:
                seen_ids.add(a['id'])
                unique.append(a)

        if len(unique) < len(all_announcements):
            logger.info(f"나라장터 청크 중복 제거: {len(all_announcements)}건 → {len(unique)}건")

        logger.info(f"나라장터 총 {len(unique)}건 수집 완료")
        return unique

    def _make_request(self, params: Dict) -> Dict:
        """
        API 요청 (재시도 로직 포함)
        """
        url = f"{self.endpoint}/getDataSetOpnStdBidPblancInfo"

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                logger.warning(f"나라장터 API 응답 없음 (시도 {attempt}/{self.max_retries})")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                logger.error(f"나라장터 API 요청 실패: {str(e)}")
                raise

    def _get_raw_items_count(self, response_data: Dict) -> int:
        """
        API 응답에서 실제 반환된 아이템 수 확인 (파싱 전)
        """
        try:
            if 'response' not in response_data:
                return 0

            body = response_data['response'].get('body', {})
            items = body.get('items', [])

            # items가 딕셔너리인 경우 (단일 아이템)
            if isinstance(items, dict):
                item_list = items.get('item', [])
                if isinstance(item_list, list):
                    return len(item_list)
                elif isinstance(item_list, dict):
                    return 1
                else:
                    return 0
            elif isinstance(items, list):
                return len(items)
            else:
                return 0
        except Exception:
            return 0

    def _parse_response(self, response_data: Dict) -> List[Dict]:
        """
        API 응답 파싱
        """
        try:
            # 응답 구조 확인
            if 'response' not in response_data:
                return []

            body = response_data['response'].get('body', {})
            items = body.get('items', [])

            # items가 딕셔너리인 경우 (단일 아이템)
            if isinstance(items, dict):
                items = [items.get('item', {})]
            elif isinstance(items, list):
                # 리스트인 경우 그대로 사용
                pass
            else:
                return []

            parsed_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                parsed_item = {
                    'id': item.get('bidNtceNo', ''),
                    'title': item.get('bidNtceNm', ''),
                    'organization': item.get('dmndInsttNm', '정보없음'),  # 수요기관명
                    'deadline': item.get('bidClseDate', ''),  # YYYY-MM-DD
                    'budget': item.get('asignBdgtAmt') or item.get('presmptPrce') or '정보없음',
                    'link': item.get('bidNtceUrl', ''),
                    'registration_date': item.get('bidNtceDate', ''),  # 공고등록일
                    'source': 'nara'
                }

                # 필수 필드 검증
                if parsed_item['id'] and parsed_item['title'] and parsed_item['deadline']:
                    parsed_items.append(parsed_item)

            return parsed_items

        except Exception as e:
            logger.error(f"나라장터 응답 파싱 오류: {str(e)}")
            return []


class KStartupAPIClient:
    """K-Startup API 클라이언트"""

    def __init__(self, api_key: str, endpoint: str, timeout: int = 30,
                 max_retries: int = 5, retry_delay: int = 20):
        self.api_key = api_key
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.failed = False  # 재시도 후에도 요청이 실패했는지 (main 에서 확인)

    def fetch_announcements(self) -> List[Dict]:
        """
        K-Startup에서 공고 데이터 수집 (API 에 검색 파라미터가 없어 전체를 가져온다)

        Returns:
            공고 리스트
        """
        all_announcements = []

        logger.info("K-Startup API 호출: 전체 공고")

        page = 1
        while True:
            params = {
                'ServiceKey': self.api_key,
                'returnType': 'json',
                'page': page,
                'perPage': 100
                # 날짜 필터 제거: K-Startup API는 모든 공고를 반환하고 클라이언트가 필터링
            }

            try:
                response = self._make_request(params)
                items = self._parse_response(response)

                if not items:
                    break

                all_announcements.extend(items)
                logger.debug(f"  페이지 {page}: {len(items)}건 수집")

                # 다음 페이지 확인
                if len(items) < 100:
                    break
                page += 1

            except Exception as e:
                logger.error(f"K-Startup API 오류 (페이지 {page}): {str(e)}")
                self.failed = True
                break

        logger.info(f"K-Startup 총 {len(all_announcements)}건 수집 완료")
        return all_announcements

    def _make_request(self, params: Dict) -> Dict:
        """
        API 요청 (재시도 로직 포함)
        """
        url = f"{self.endpoint}/getAnnouncementInformation01"

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                logger.warning(f"K-Startup API 응답 없음 (시도 {attempt}/{self.max_retries})")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                logger.error(f"K-Startup API 요청 실패: {str(e)}")
                raise

    def _parse_response(self, response_data: Dict) -> List[Dict]:
        """
        API 응답 파싱
        """
        try:
            # K-Startup API는 직접 'data' 키에 배열 반환
            items = response_data.get('data', [])

            if not isinstance(items, list):
                return []

            parsed_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                # 공고ID: pbanc_sn 사용
                announcement_id = str(item.get('pbanc_sn', ''))

                # 마감일 형식 변환 (YYYYMMDD → YYYY-MM-DD)
                deadline_str = item.get('pbanc_rcpt_end_dt', '')
                if deadline_str and len(deadline_str) == 8 and deadline_str.isdigit():
                    deadline = f"{deadline_str[:4]}-{deadline_str[4:6]}-{deadline_str[6:8]}"
                else:
                    deadline = ''

                # 링크: detl_pg_url이 이미 절대경로
                full_url = item.get('detl_pg_url', '')

                # 과업개요 (pbanc_ctnt)
                pbanc_ctnt = item.get('pbanc_ctnt', '')
                overview = self._clean_html(pbanc_ctnt)

                # 발주기관을 과업개요에서 추출
                organization = self._extract_organization(pbanc_ctnt)

                # 접수시작일을 등록일자로 사용
                reg_date_str = item.get('pbanc_rcpt_bgng_dt', '')
                if reg_date_str and len(reg_date_str) >= 8 and reg_date_str[:8].isdigit():
                    registration_date = f"{reg_date_str[:4]}-{reg_date_str[4:6]}-{reg_date_str[6:8]}"
                else:
                    registration_date = ''

                parsed_item = {
                    'id': announcement_id,
                    'title': item.get('biz_pbanc_nm', ''),
                    'organization': organization,  # 과업개요에서 추출
                    'deadline': deadline,
                    'link': full_url,
                    'overview': overview[:500] if overview else '',  # 500자로 제한
                    'registration_date': registration_date,
                    'source': 'kstartup'
                }

                # 필수 필드 검증
                if parsed_item['id'] and parsed_item['title'] and parsed_item['deadline']:
                    parsed_items.append(parsed_item)

            return parsed_items

        except Exception as e:
            logger.error(f"K-Startup 응답 파싱 오류: {str(e)}")
            return []

    def _extract_pbanc_sn(self, url: str) -> str:
        """
        URL에서 pbancSn 파라미터 추출
        """
        match = re.search(r'pbancSn=(\d+)', url)
        return match.group(1) if match else ''

    def _clean_html(self, text: str) -> str:
        """
        HTML 태그 제거
        """
        if not text:
            return ''
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', text)
        # 연속된 공백/줄바꿈 정리
        clean_text = re.sub(r'\s+', ' ', clean_text)
        return clean_text.strip()

    def _extract_organization(self, content: str) -> str:
        """
        과업개요에서 발주기관(주관기관) 정보 추출
        kiwipiepy 형태소 분석 기반
        """
        if not content:
            return '정보없음'

        # HTML 태그 제거
        clean_content = self._clean_html(content)

        # 1단계: 레이블 기반 정규식 (구분자 필수: 콜론, 대시, 가운데점)
        label_patterns = [
            r'주관기관\s*[:\-·]\s*([^\n,\.]+)',
            r'주관사\s*[:\-·]\s*([^\n,\.]+)',
            r'운영기관\s*[:\-·]\s*([^\n,\.]+)',
            r'운영사\s*[:\-·]\s*([^\n,\.]+)',
            r'수행기관\s*[:\-·]\s*([^\n,\.]+)',
            r'사업주관\s*[:\-·]\s*([^\n,\.]+)',
            r'위탁기관\s*[:\-·]\s*([^\n,\.]+)',
            r'전문기관\s*[:\-·]\s*([^\n,\.]+)',
            r'지원기관\s*[:\-·]\s*([^\n,\.]+)',
        ]

        for pattern in label_patterns:
            match = re.search(pattern, clean_content)
            if match:
                org = match.group(1).strip()
                if org and len(org) >= 2:
                    return org[:50]

        # 2단계: kiwipiepy 형태소 분석으로 기관명 추출
        # 기관명 접미사 목록
        ORG_SUFFIXES = ('센터', '진흥원', '재단', '협회', '공사', '공단', '테크노파크', '원', '부', '청', '처', '실', '회', '단', '사')
        # 기관명이 아닌데 접미사가 우연히 매칭되는 단어
        NON_ORG_ENDINGS = ('지원', '대회', '기회', '사회', '운영사', '경연대회', '벤처', '창업자', '확인', '기반', '분야')

        # 첫 2문장만 분석 (발주기관은 보통 앞부분에 위치)
        sentences = re.split(r'[.!?。]\s*', clean_content)
        analysis_text = '. '.join(sentences[:2]) if sentences else clean_content[:200]

        try:
            kiwi = get_kiwi()
            tokens = kiwi.tokenize(analysis_text)

            # 명사(NNP, NNG) 연속 추출 → 기관명 후보
            noun_chunks = []
            current_chunk = []

            for token in tokens:
                # 고유명사(NNP), 일반명사(NNG), 외국어(SL), 한자(SH)
                if token.tag in ('NNP', 'NNG', 'SL', 'SH'):
                    current_chunk.append(token.form)
                else:
                    if current_chunk:
                        noun_chunks.append(''.join(current_chunk))
                        current_chunk = []

            if current_chunk:
                noun_chunks.append(''.join(current_chunk))

            # 기관명 접미사로 끝나는 청크 찾기
            for chunk in noun_chunks:
                if len(chunk) >= 4 and chunk.endswith(ORG_SUFFIXES):
                    if not chunk.endswith(NON_ORG_ENDINGS):
                        return chunk[:50]

        except Exception as e:
            logger.warning(f"형태소 분석 실패: {str(e)}")

        return '정보없음'
