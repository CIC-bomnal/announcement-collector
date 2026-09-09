"""
공고 수집기 메인 실행 파일

흐름:
  설정 검증 → [나라장터 / K-Startup / PDF] 병렬 수집 → 키워드·마감일 필터
  → 금지어 필터 → Google Sheets 증분 업데이트

종료 코드:
  0 정상 / 1 설정 오류 또는 수집 실패 (GitHub Actions 에서 실패로 표시됨)
"""
import sys
import time
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor

import config
from src.logger import setup_logger
from src.api_client import NaraAPIClient, KStartupAPIClient
from src.filter import filter_by_keyword, filter_by_deadline, filter_by_pdf_names, filter_by_exclusion
from src.pdf_parser import parse_pdf
from src.spreadsheet import SpreadsheetManager


def _apply_keyword_filter(announcements):
    return filter_by_keyword(
        announcements,
        keywords=config.KEYWORDS,
        must_extract_keywords=config.MUST_EXTRACT_KEYWORDS,
        end_keywords=config.END_KEYWORDS,
        conditional_keywords=config.CONDITIONAL_KEYWORDS,
    )


def main() -> int:
    print("=" * 60)
    print("공고 수집기 - 데이터 수집 및 업데이트")
    print("=" * 60)
    print()

    # 1. 설정 검증
    try:
        config.validate_config()
        print()
    except Exception as e:
        print(f"✗ {e}")
        return 1

    logger = setup_logger(config.LOG_LEVEL)
    logger.info("=" * 60)
    logger.info("공고 데이터 수집 시작")
    logger.info(f"기준일: {config.BASE_DATE} / 최소 남은 일수: {config.MIN_DAYS_REMAINING}일")
    logger.info("=" * 60)
    start_time = time.time()

    try:
        # 2. 클라이언트 초기화
        api_opts = dict(timeout=config.API_TIMEOUT, max_retries=config.API_MAX_RETRIES,
                        retry_delay=config.API_RETRY_DELAY)
        nara_client = NaraAPIClient(config.NARA_API_KEY, config.NARA_API_ENDPOINT, **api_opts) if config.NARA_ENABLED else None
        kstartup_client = KStartupAPIClient(config.KSTARTUP_API_KEY, config.KSTARTUP_API_ENDPOINT, **api_opts) if config.KSTARTUP_ENABLED else None

        # 3. 병렬 수집
        logger.info("\n[병렬 수집] 시작...")
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_nara = ex.submit(nara_client.fetch_announcements, config.SEARCH_DAYS_BACK) if nara_client else None
            f_kstartup = ex.submit(kstartup_client.fetch_announcements) if kstartup_client else None
            f_pdf = ex.submit(parse_pdf, config.PDF_PATH) if config.PDF_ENABLED else None

            nara_announcements = f_nara.result() if f_nara else []
            kstartup_announcements = f_kstartup.result() if f_kstartup else []
            pdf_businesses = f_pdf.result() if f_pdf else []

        logger.info(f"[병렬 수집 완료] 나라장터 {len(nara_announcements)}건, K-Startup {len(kstartup_announcements)}건, PDF {len(pdf_businesses)}건")

        # 수집 자체가 실패한 소스가 있으면 시트를 건드리지 않고 실패 종료
        # (data.go.kr 이 간헐적으로 응답하지 않을 때 빈 결과로 시트가 정리되는 것을 막는다)
        failed_sources = []
        if nara_client and nara_client.failed and not nara_announcements:
            failed_sources.append('나라장터')
        if kstartup_client and kstartup_client.failed and not kstartup_announcements:
            failed_sources.append('K-Startup')
        if failed_sources:
            logger.error(f"API 수집 실패: {', '.join(failed_sources)} — 시트를 갱신하지 않고 종료합니다. (재시도 권장)")
            print(f"\n✗ API 수집 실패: {', '.join(failed_sources)}. data.go.kr 응답 없음. 잠시 후 다시 실행하세요.")
            return 1

        # 4. 나라장터 필터
        nara_final = []
        if nara_client:
            logger.info("\n[나라장터] 키워드 필터링...")
            nara_kw = _apply_keyword_filter(nara_announcements)
            logger.info("[나라장터] 마감일 필터링...")
            nara_final = filter_by_deadline(nara_kw, config.MIN_DAYS_REMAINING, config.BASE_DATE)

        # 5. K-Startup 필터 (등록일 → 마감일 → 키워드 OR PDF 매칭)
        kstartup_final = []
        pdf_names = [b['name'] for b in pdf_businesses]
        if kstartup_client:
            cutoff = (config.BASE_DATE - timedelta(days=config.SEARCH_DAYS_BACK)).isoformat()
            before = len(kstartup_announcements)
            kstartup_announcements = [a for a in kstartup_announcements if a.get('registration_date', '') >= cutoff]
            logger.info(f"\n[K-Startup] 등록일 필터: {before}건 → {len(kstartup_announcements)}건 (기준: {cutoff}~)")

            ks_deadline = filter_by_deadline(kstartup_announcements, config.MIN_DAYS_REMAINING, config.BASE_DATE)
            ks_keyword = _apply_keyword_filter(ks_deadline)
            ks_pdf = filter_by_pdf_names(ks_deadline, pdf_names, config.MATCH_THRESHOLD) if pdf_names else []

            seen = set()
            for a in ks_keyword + ks_pdf:
                if a['id'] not in seen:
                    seen.add(a['id'])
                    kstartup_final.append(a)
            logger.info(f"[K-Startup] 최종: {len(kstartup_final)}건 (키워드 {len(ks_keyword)}건 + PDF추가 {len(kstartup_final) - len(ks_keyword)}건)")

        # 6. 금지어 필터
        nara_excl, kstartup_excl = [], []
        if config.EXCLUSION_KEYWORDS:
            logger.info(f"\n[금지어] 필터링... ({len(config.EXCLUSION_KEYWORDS)}개)")
            nara_excl = filter_by_exclusion(nara_final, config.EXCLUSION_KEYWORDS)
            kstartup_excl = filter_by_exclusion(kstartup_final, config.EXCLUSION_KEYWORDS)

        # 7. 스프레드시트 업데이트
        logger.info("\n스프레드시트 업데이트 시작...")
        sheet = SpreadsheetManager(
            sheet_id=config.GOOGLE_SHEET_ID,
            credentials_file=config.resolve_credentials_file(),
            min_days_remaining=config.MIN_DAYS_REMAINING,
        )

        results = {}

        def update_tab(items, name, headers, highlight=False):
            sheet.deduplicate_sheet(name, headers)
            r = sheet.update_announcements(items, sheet_name=name, headers=headers)
            if highlight:
                ids = [a['id'] for a in items if a.get('pdf_matched')]
                if ids:
                    sheet.highlight_rows(sheet_name=name, headers=headers, matched_ids=ids)
            results[name] = r
            return r

        if nara_client:
            logger.info(f"\n[나라장터] '{config.SHEET_NAME_NARA}' 탭 업데이트... ({len(nara_final)}건)")
            update_tab(nara_final, config.SHEET_NAME_NARA, config.NARA_HEADERS)
            if config.EXCLUSION_KEYWORDS:
                logger.info(f"[금지어] '{config.SHEET_NAME_NARA_FILTERED}' 탭 업데이트... ({len(nara_excl)}건)")
                update_tab(nara_excl, config.SHEET_NAME_NARA_FILTERED, config.NARA_HEADERS)

        if kstartup_client:
            logger.info(f"\n[K-Startup] '{config.SHEET_NAME_KSTARTUP}' 탭 업데이트... ({len(kstartup_final)}건)")
            update_tab(kstartup_final, config.SHEET_NAME_KSTARTUP, config.KSTARTUP_HEADERS, highlight=True)
            if config.EXCLUSION_KEYWORDS:
                logger.info(f"[금지어] '{config.SHEET_NAME_KSTARTUP_FILTERED}' 탭 업데이트... ({len(kstartup_excl)}건)")
                update_tab(kstartup_excl, config.SHEET_NAME_KSTARTUP_FILTERED, config.KSTARTUP_HEADERS, highlight=True)

        if pdf_businesses:
            logger.info(f"\n[PDF] '{config.SHEET_NAME_PDF}' 탭 업로드... ({len(pdf_businesses)}건)")
            sheet.upload_pdf_data(pdf_businesses, sheet_name=config.SHEET_NAME_PDF, headers=config.PDF_HEADERS)

        # 8. 요약
        elapsed = time.time() - start_time
        nara_r = results.get(config.SHEET_NAME_NARA, {'new': 0, 'updated': 0})
        ks_r = results.get(config.SHEET_NAME_KSTARTUP, {'new': 0, 'updated': 0})

        summary = [
            "=" * 60,
            "✓ 공고 데이터 수집 완료!",
            f"  - 나라장터: 신규 {nara_r['new']}건, 갱신 {nara_r['updated']}건",
            f"  - K-Startup: 신규 {ks_r['new']}건, 갱신 {ks_r['updated']}건",
            f"  - 총 신규 {nara_r['new'] + ks_r['new']}건, 갱신 {nara_r['updated'] + ks_r['updated']}건",
        ]
        if config.EXCLUSION_KEYWORDS:
            summary.append(f"  - 금지어 필터 후: 나라장터 {len(nara_excl)}건, K-Startup {len(kstartup_excl)}건")
        summary += [f"  - 소요 시간: {elapsed:.1f}초", "=" * 60,
                    f"\n스프레드시트: https://docs.google.com/spreadsheets/d/{config.GOOGLE_SHEET_ID}"]
        for line in summary:
            logger.info(line)
        print("\n" + "\n".join(summary))
        return 0

    except KeyboardInterrupt:
        logger.warning("사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        logger.error(f"치명적 오류: {e}", exc_info=True)
        print(f"\n✗ 오류 발생: {e}\n자세한 내용은 logs/ 폴더의 로그를 확인하세요.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
