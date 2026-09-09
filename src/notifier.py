"""
슬랙 알림 모듈 (Incoming Webhook)

- send_report(): 이번 실행에서 새로 들어온 공고를 소스별로 정리해 전송
- send_failure(): 수집 실패를 한 줄로 알림

슬랙 전송 실패는 수집 결과에 영향을 주지 않는다 (경고 로그만 남김).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import requests

logger = logging.getLogger('announcement_collector')

KST = timezone(timedelta(hours=9))
SOURCE_LABELS = {'nara': '나라장터', 'kstartup': 'K-Startup'}


def _now_label() -> str:
    now = datetime.now(KST)
    return f"{now.strftime('%m/%d')} {'오전' if now.hour < 12 else '오후'} {now.strftime('%H:%M')}"


def _post(webhook_url: str, payload: Dict) -> bool:
    try:
        # 잘못된 URL 은 302 로 리다이렉트되므로 따라가지 않고 200 + "ok" 만 성공으로 본다
        r = requests.post(webhook_url, json=payload, timeout=10, allow_redirects=False)
        if r.status_code != 200 or r.text.strip() != 'ok':
            logger.warning(f"슬랙 전송 실패: HTTP {r.status_code} {r.text[:100]}")
            return False
        return True
    except requests.exceptions.RequestException as e:
        logger.warning(f"슬랙 전송 실패: {e}")
        return False


def _format_item(a: Dict) -> str:
    title = a.get('title', '').replace('<', '〈').replace('>', '〉').replace('&', '&amp;')
    link = a.get('link', '')
    org = a.get('organization') or '기관 미상'
    deadline = a.get('deadline', '')
    days = a.get('days_remaining')
    d_label = f" (D-{days})" if isinstance(days, int) else ''
    title_part = f"<{link}|{title}>" if link else title
    return f"• {title_part}\n    {org} · 마감 {deadline}{d_label}"


def send_report(webhook_url: str, new_by_source: Dict[str, List[Dict]], sheet_url: str,
                max_items: int = 30, notify_when_empty: bool = False) -> bool:
    """
    Args:
        webhook_url: 슬랙 Incoming Webhook URL
        new_by_source: {'nara': [...], 'kstartup': [...]} 이번 실행 신규 공고
        sheet_url: 스프레드시트 링크
        max_items: 소스별 최대 표시 건수 (넘으면 "외 n건")
        notify_when_empty: 신규 0건일 때도 보낼지
    """
    total = sum(len(v) for v in new_by_source.values())
    if total == 0 and not notify_when_empty:
        logger.info("슬랙: 신규 공고 없음, 알림 생략")
        return True

    lines = [f"*📢 공고 수집 결과 ({_now_label()}) — 신규 {total}건*"]
    for source, items in new_by_source.items():
        label = SOURCE_LABELS.get(source, source)
        if not items:
            continue
        lines.append(f"\n*{label}* ({len(items)}건)")
        items_sorted = sorted(items, key=lambda a: a.get('deadline', ''))
        for a in items_sorted[:max_items]:
            lines.append(_format_item(a))
        if len(items) > max_items:
            lines.append(f"    … 외 {len(items) - max_items}건은 시트에서 확인")
    if total == 0:
        lines.append("신규 공고가 없습니다.")
    lines.append(f"\n<{sheet_url}|스프레드시트 열기>")

    text = "\n".join(lines)
    ok = _post(webhook_url, {"text": text, "unfurl_links": False, "unfurl_media": False})
    if ok:
        logger.info(f"✓ 슬랙 알림 전송: 신규 {total}건")
    return ok


def send_failure(webhook_url: str, reason: str, run_url: str = '') -> bool:
    text = f"*⚠️ 공고 수집 실패 ({_now_label()})*\n{reason}"
    if run_url:
        text += f"\n<{run_url}|실행 로그 보기>"
    ok = _post(webhook_url, {"text": text, "unfurl_links": False})
    if ok:
        logger.info("슬랙 실패 알림 전송")
    return ok
