"""
필터링 로직 모듈
키워드 및 마감일 필터링
"""
from datetime import datetime, date
from typing import List, Dict
import logging


logger = logging.getLogger('announcement_collector')


def _normalize(s: str) -> str:
    """공백 제거 + 소문자 변환 (띄어쓰기 무관 매칭용)"""
    return s.replace(' ', '').lower()


def filter_by_keyword(announcements: List[Dict], keywords: List[str],
                      must_extract_keywords: List[str] = None,
                      end_keywords: List[str] = None,
                      conditional_keywords: List[str] = None) -> List[Dict]:
    """
    다단계 키워드 필터링 (띄어쓰기 무관)

    매칭 우선순위:
    1) 필수(must_extract): 하나라도 포함 → 무조건 추출
    2) 끝부분(end): 제목 맨 끝에 매칭 → 무조건 추출
    3) 일반(keywords): 하나라도 매칭 → 추출
    4) 조건부(conditional): 일반/필수/끝부분 키워드 없이 단독 매칭 시 미추출

    Args:
        announcements: 공고 리스트
        keywords: 일반 키워드 리스트
        must_extract_keywords: 필수 추출 키워드 리스트
        end_keywords: 끝부분 매칭 키워드 리스트
        conditional_keywords: 조건부 키워드 리스트

    Returns:
        필터링된 공고 리스트
    """
    must_norm = [_normalize(k) for k in (must_extract_keywords or []) if k.strip()]
    end_norm = [_normalize(k) for k in (end_keywords or []) if k.strip()]
    reg_norm = [_normalize(k) for k in keywords if k.strip()]
    cond_norm = [_normalize(k) for k in (conditional_keywords or []) if k.strip()]

    all_empty = not must_norm and not end_norm and not reg_norm and not cond_norm
    if all_empty:
        logger.warning("키워드가 비어있습니다. 모든 공고를 통과시킵니다.")
        return announcements

    filtered = []
    must_count = 0
    end_count = 0
    reg_count = 0
    cond_only_count = 0

    for announcement in announcements:
        title = announcement.get('title', '')
        norm_title = _normalize(title)

        # 1) 필수 키워드: 하나라도 포함 → 무조건 추출
        if any(kw in norm_title for kw in must_norm):
            filtered.append(announcement)
            must_count += 1
            continue

        # 2) 끝부분 키워드: 제목 끝에 매칭 → 무조건 추출
        if any(norm_title.endswith(kw) for kw in end_norm):
            filtered.append(announcement)
            end_count += 1
            continue

        # 3) 일반 키워드: 하나라도 매칭 → 추출
        if any(kw in norm_title for kw in reg_norm):
            filtered.append(announcement)
            reg_count += 1
            continue

        # 4) 조건부 키워드: 위 1~3에서 매칭 안 됐으므로 단독 매칭 → 미추출
        if any(kw in norm_title for kw in cond_norm):
            cond_only_count += 1
            logger.debug(f"조건부 키워드만 매칭 (미추출): {title[:40]}")

    logger.info(f"키워드 필터링: {len(announcements)}건 → {len(filtered)}건 "
                f"(필수 {must_count}, 끝부분 {end_count}, 일반 {reg_count}, 조건부단독 {cond_only_count}건 제외)")
    return filtered


def filter_by_deadline(announcements: List[Dict], min_days: int, base_date: date) -> List[Dict]:
    """
    마감일이 기준일로부터 최소 일수 이상 남은 공고만 필터링

    Args:
        announcements: 공고 리스트
        min_days: 최소 남은 일수 (기본값: 14일)
        base_date: 기준일 (Phase 1: 2026-02-01, Phase 2: 실행 당일)

    Returns:
        필터링된 공고 리스트
    """
    filtered = []

    for announcement in announcements:
        deadline_str = announcement.get('deadline')

        if not deadline_str:
            logger.debug(f"마감일 없음 - 제외: {announcement.get('title', 'N/A')[:30]}")
            continue  # 마감일이 없으면 제외

        try:
            # 날짜 형식 변환
            deadline = parse_date(deadline_str)

            # 남은 일수 계산 (기준일 기준)
            days_remaining = (deadline - base_date).days
            announcement['days_remaining'] = days_remaining

            # 기준 이상 남았으면 선택
            if days_remaining >= min_days:
                filtered.append(announcement)
                logger.debug(f"마감일 OK ({days_remaining}일): {announcement.get('title', 'N/A')[:30]}")
            else:
                logger.debug(f"마감일 부족 ({days_remaining}일): {announcement.get('title', 'N/A')[:30]}")

        except Exception as e:
            logger.warning(f"마감일 파싱 오류 ({deadline_str}): {str(e)}")
            continue

    logger.info(f"마감일 필터링: {len(announcements)}건 → {len(filtered)}건 (기준일: {base_date}, 최소 {min_days}일)")
    return filtered


def filter_by_pdf_names(announcements: List[Dict], pdf_names: List[str], threshold: int = 60) -> List[Dict]:
    """
    PDF 사업명과 rapidfuzz token_set_ratio 매칭으로 필터링

    Args:
        announcements: 공고 리스트
        pdf_names: PDF에서 추출한 사업명 리스트
        threshold: 유사도 임계값 (기본 60)

    Returns:
        매칭된 공고 리스트 (pdf_matched=True 플래그 추가)
    """
    from rapidfuzz import fuzz

    matched = []
    for announcement in announcements:
        title = announcement.get('title', '')
        for name in pdf_names:
            score = fuzz.token_set_ratio(title, name)
            if score >= threshold:
                announcement['pdf_matched'] = True
                matched.append(announcement)
                break

    logger.info(f"PDF 매칭: {len(announcements)}건 중 {len(matched)}건 매칭 (임계값: {threshold})")
    return matched


def filter_by_exclusion(announcements: List[Dict], exclusion_keywords: List[str]) -> List[Dict]:
    """
    금지어가 포함된 공고를 제외하는 필터 (띄어쓰기 무관)

    Args:
        announcements: 공고 리스트
        exclusion_keywords: 금지어 리스트

    Returns:
        금지어가 제외된 공고 리스트
    """
    if not exclusion_keywords:
        logger.info("금지어가 비어있습니다. 전체 공고를 통과시킵니다.")
        return list(announcements)

    excl_norm = [_normalize(k) for k in exclusion_keywords if k.strip()]
    filtered = []

    for announcement in announcements:
        norm_title = _normalize(announcement.get('title', ''))
        excluded = False

        for kw in excl_norm:
            if kw in norm_title:
                excluded = True
                break

        if not excluded:
            filtered.append(announcement)

    excluded_count = len(announcements) - len(filtered)
    logger.info(f"금지어 필터링: {len(announcements)}건 → {len(filtered)}건 ({excluded_count}건 제외)")
    return filtered


def parse_date(date_str: str) -> date:
    """
    날짜 문자열을 date 객체로 변환

    Args:
        date_str: 날짜 문자열 (YYYY-MM-DD 또는 YYYYMMDD)

    Returns:
        date 객체
    """
    date_str = date_str.strip()

    # YYYY-MM-DD 형식
    if '-' in date_str:
        return datetime.strptime(date_str, '%Y-%m-%d').date()

    # YYYYMMDD 형식
    elif len(date_str) == 8 and date_str.isdigit():
        return datetime.strptime(date_str, '%Y%m%d').date()

    else:
        raise ValueError(f"지원하지 않는 날짜 형식: {date_str}")
