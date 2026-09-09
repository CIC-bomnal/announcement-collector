"""
로깅 설정 모듈
일자별 로그 파일 생성 및 로그 레벨 관리
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(log_level='INFO'):
    """
    로거 설정

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logger: 설정된 로거 인스턴스
    """
    # 로그 디렉토리 생성
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # 로그 파일명 (일자별)
    log_filename = log_dir / f"공고수집_{datetime.now().strftime('%Y%m%d')}.log"

    # 로거 생성
    logger = logging.getLogger('announcement_collector')
    logger.setLevel(getattr(logging, log_level.upper()))

    # 기존 핸들러 제거 (중복 방지)
    logger.handlers.clear()

    # 포맷터 설정
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 파일 핸들러
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"로거 초기화 완료 - 로그 파일: {log_filename}")

    return logger
