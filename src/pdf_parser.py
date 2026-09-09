"""
PDF 파서 모듈
창업지원사업 안내서(PDF)에서 사업명, 구분, 예정공고시기, 페이지 추출
"""
import re
import logging

import pymupdf as fitz


logger = logging.getLogger('announcement_collector')

# 목차 카테고리
MAIN_CATEGORIES = {'중앙부처', '지방자치단체'}
SUB_CATEGORIES = ['사업화', '기술개발(R&D)', '시설·공간·보육',
                  '멘토링·컨설팅·교육', '행사·네트워크', '융자·보증', '글로벌', '인력']
SUB_CATEGORY_SET = set(SUB_CATEGORIES)


def parse_pdf(pdf_path):
    """
    PDF에서 사업 정보 추출

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        List[Dict]: [{
            'name': '예비창업패키지',
            'main_category': '중앙부처',
            'sub_category': '사업화',
            'announcement_period': '25-12~26-01',
            'page': 20
        }, ...]
    """
    doc = fitz.open(pdf_path)

    # 1단계: 목차에서 사업 목록 추출 (p2~p17, 0-indexed 1~16)
    businesses = _parse_toc(doc)
    logger.info(f"[PDF] 목차에서 {len(businesses)}개 사업 추출")

    # 2단계: 상세 페이지에서 예정공고시기 추출
    for biz in businesses:
        biz['announcement_period'] = _extract_announcement_date(doc, biz['page'])

    doc.close()
    return businesses


def _parse_toc(doc):
    """목차 페이지(p2~p17, 0-indexed 1~16)에서 사업명/구분/페이지 추출"""
    all_lines = []
    for page_idx in range(1, 17):
        page_text = doc[page_idx].get_text()
        for line in page_text.split('\n'):
            stripped = line.strip()
            if stripped:
                all_lines.append(stripped)

    entries = []
    current_main = ''
    current_sub = ''
    skip_next = False

    i = 0
    while i < len(all_lines):
        line = all_lines[i]

        # "C o n t e n t s" 푸터 + 바로 다음 카테고리명 건너뛰기
        if 'C o n t e n t s' in line:
            skip_next = True
            i += 1
            continue

        if skip_next:
            skip_next = False
            if line in MAIN_CATEGORIES or line in SUB_CATEGORY_SET:
                i += 1
                continue

        # 메인 카테고리 감지
        if line in MAIN_CATEGORIES:
            current_main = line
            i += 1
            continue

        # 서브 카테고리 감지
        if line in SUB_CATEGORY_SET:
            current_sub = line
            i += 1
            continue

        # 번호 패턴 감지 (001~999)
        if re.match(r'^\d{3}$', line):
            if (i + 3 < len(all_lines)
                    and '▶▶' in all_lines[i + 1]
                    and re.match(r'^\d{1,3}$', all_lines[i + 3])):
                name = all_lines[i + 2].strip()
                page = int(all_lines[i + 3])
                entries.append({
                    'name': name,
                    'main_category': current_main,
                    'sub_category': current_sub,
                    'page': page,
                    '_num': int(line),
                })
                i += 4
                continue

        i += 1

    # 후처리: PDF 텍스트 추출 순서 오류로 잘못된 서브카테고리 수정
    _fix_subcategories(entries)

    for e in entries:
        del e['_num']

    return entries


def _fix_subcategories(entries):
    """
    번호가 001로 리셋되는데 서브카테고리가 바뀌지 않은 경우,
    다음 순서의 서브카테고리로 재할당.
    (PDF 텍스트 추출 시 사이드바 헤더가 항목 뒤에 나오는 경우 대응)
    """
    i = 1
    while i < len(entries):
        prev = entries[i - 1]
        curr = entries[i]

        if (curr['_num'] == 1 and prev['_num'] > 1
                and curr['main_category'] == prev['main_category']
                and curr['sub_category'] == prev['sub_category']):

            original_sub = curr['sub_category']
            try:
                idx = SUB_CATEGORIES.index(original_sub)
                if idx + 1 < len(SUB_CATEGORIES):
                    correct_sub = SUB_CATEGORIES[idx + 1]
                    j = i
                    while j < len(entries):
                        if entries[j]['main_category'] != curr['main_category']:
                            break
                        if entries[j]['sub_category'] != original_sub:
                            break
                        entries[j]['sub_category'] = correct_sub
                        j += 1
                    i = j
                    continue
            except ValueError:
                pass

        i += 1


def _extract_announcement_date(doc, page_num):
    """
    상세 페이지에서 '▶ 사업공고' 날짜 추출

    Args:
        doc: fitz 문서 객체
        page_num: 페이지 번호 (1-indexed, 목차 기준)

    Returns:
        str: YY-MM 또는 YY-MM~YY-MM, 없으면 빈 문자열
    """
    page_idx = page_num - 1

    for offset in [0, 1]:
        idx = page_idx + offset
        if idx >= len(doc):
            break
        text = doc[idx].get_text()
        match = re.search(r'사업공고\s*\n(.+)', text)
        if match:
            return _normalize_date(match.group(1).strip())

    return ''


def _normalize_date(text):
    """
    다양한 날짜 형식을 YY-MM 또는 YY-MM~YY-MM으로 변환

    Examples:
        "'25. 12~'26. 1월(예정)" → "25-12~26-01"
        "'26년 1월"              → "26-01"
        "2026년 4월~5월"         → "26-04~26-05"
        "'26. 4월, 7월(예정)"    → "26-04~26-07"
        "2026. 5.~6. 중"         → "26-05~26-06"
    """
    text = text.strip()
    # 스마트 따옴표(U+2018, U+2019)를 일반 따옴표로 통일
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = re.sub(r'\(예정\)|\(미정\)', '', text).strip()

    YR = r"(?:'|20)(\d{2})"  # 'YY 또는 20YY → 그룹: YY

    # 1) 서로 다른 연도 범위: 'YY.MM ~ 'YY.MM
    m = re.search(
        YR + r"(?:년|\.)?\s*(\d{1,2})(?:월|\.)?(?:말|초)?\s*~\s*"
        + YR + r"(?:년|\.)?\s*(\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}~{m.group(3)}-{int(m.group(4)):02d}"

    # 2) 같은 연도 범위 (~): YY MM~MM
    m = re.search(YR + r"(?:년|\.)?\s*(\d{1,2})(?:월|\.)?(?:말|초)?\s*~\s*(\d{1,2})", text)
    if m:
        yr = m.group(1)
        return f"{yr}-{int(m.group(2)):02d}~{yr}-{int(m.group(3)):02d}"

    # 3) 같은 연도 범위 (, /): YY MM, MM 또는 YY MM / MM
    m = re.search(YR + r"(?:년|\.)?\s*(\d{1,2})(?:월)?\s*[,/]\s*(\d{1,2})", text)
    if m:
        yr = m.group(1)
        return f"{yr}-{int(m.group(2)):02d}~{yr}-{int(m.group(3)):02d}"

    # 4) 단일 날짜
    m = re.search(YR + r"(?:년|\.)?\s*(\d{1,2})", text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"

    # 비정형
    if '연중' in text or '수시' in text:
        return '연중'

    return ''
