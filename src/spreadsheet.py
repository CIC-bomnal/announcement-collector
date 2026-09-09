"""
Google Sheets 연동 모듈
스프레드시트 데이터 읽기/쓰기
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta
from typing import List, Dict
import logging


logger = logging.getLogger('announcement_collector')


class SpreadsheetManager:
    """Google Sheets 관리 클래스"""

    def __init__(self, sheet_id: str, credentials_file: str, min_days_remaining: int = 7):
        """
        Args:
            sheet_id: 스프레드시트 ID
            credentials_file: 서비스 계정 키 파일 경로
            min_days_remaining: 이 일수 미만 남은 행은 갱신 시 삭제
        """
        self.sheet_id = sheet_id
        self.credentials_file = credentials_file
        self.min_days_remaining = min_days_remaining
        self.client = None
        self.spreadsheet = None
        self._init_client()

    def _init_client(self):
        """gspread 클라이언트 초기화"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            logger.info(f"✓ 스프레드시트 연결 성공: {self.spreadsheet.title}")

        except Exception as e:
            msg = str(e)
            if '403' in msg or 'permission' in msg.lower():
                msg += (" — 스프레드시트가 서비스 계정 이메일(credentials.json 의 client_email)에 "
                        "'편집자'로 공유되어 있는지 확인하세요.")
            elif '404' in msg:
                msg += " — 스프레드시트 ID 가 잘못되었을 수 있습니다."
            logger.error(f"스프레드시트 연결 실패: {msg}")
            raise RuntimeError(f"스프레드시트 연결 실패: {msg}") from e

    def get_or_create_worksheet(self, sheet_name: str) -> gspread.Worksheet:
        """
        워크시트 가져오기 또는 생성

        Args:
            sheet_name: 시트 이름

        Returns:
            워크시트 객체
        """
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            logger.info(f"✓ 기존 시트 사용: {sheet_name}")
            return worksheet

        except gspread.exceptions.WorksheetNotFound:
            # 시트가 없으면 생성
            worksheet = self.spreadsheet.add_worksheet(
                title=sheet_name,
                rows=1000,
                cols=10
            )
            logger.info(f"✓ 새 시트 생성: {sheet_name}")
            return worksheet

    def ensure_headers(self, worksheet: gspread.Worksheet, headers: List[str]):
        """
        헤더 행 확인 및 생성

        Args:
            worksheet: 워크시트 객체
            headers: 헤더 리스트
        """
        try:
            # 첫 행 읽기
            existing_headers = worksheet.row_values(1)

            if not existing_headers or existing_headers != headers:
                # 헤더 업데이트
                last_col = chr(ord('A') + len(headers) - 1)
                worksheet.update(f'A1:{last_col}1', [headers], value_input_option='RAW')
                logger.info(f"✓ 헤더 설정 완료: {len(headers)}개 컬럼")
            else:
                logger.info(f"✓ 헤더 이미 존재")

        except Exception as e:
            logger.error(f"헤더 설정 오류: {str(e)}")
            raise

    def update_announcements(self, announcements: List[Dict], sheet_name: str, headers: List[str]) -> Dict:
        """
        공고 데이터를 스프레드시트에 증분 업데이트
        - 신규 공고: append
        - 기존 공고: 전체 행 갱신 (등록일자는 기존 값 유지)

        Args:
            announcements: 공고 리스트
            sheet_name: 시트 이름
            headers: 헤더 리스트

        Returns:
            {'new': 신규 추가 건수, 'updated': 갱신 건수}
        """
        worksheet = self.get_or_create_worksheet(sheet_name)
        self.ensure_headers(worksheet, headers)

        include_overview = '과업개요' in headers
        include_budget = '예산' in headers

        try:
            # 1) 기존 데이터에서 {공고ID: (행번호, 행데이터)} 맵 생성
            all_values = worksheet.get_all_values()
            id_col_idx = headers.index('공고ID')
            reg_date_col_idx = headers.index('등록일자')
            existing_ids = {}
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > id_col_idx and row[id_col_idx]:
                    existing_ids[str(row[id_col_idx])] = {
                        'row_num': i,
                        'reg_date': row[reg_date_col_idx] if len(row) > reg_date_col_idx else ''
                    }

            # 2) 신규 vs 기존 분류
            new_rows = []
            new_ids = set()
            update_cells = []
            last_col = chr(ord('A') + len(headers) - 1)

            for announcement in announcements:
                ann_id = str(announcement.get('id', ''))
                if ann_id in existing_ids:
                    # 기존 공고: 전체 행 갱신 (등록일자는 기존 값 유지)
                    info = existing_ids[ann_id]
                    row_num = info['row_num']
                    row_data = self._prepare_row_data(
                        announcement, row_num, include_overview, include_budget,
                        original_reg_date=info['reg_date']
                    )
                    update_cells.append({
                        'range': f'A{row_num}:{last_col}{row_num}',
                        'values': [row_data]
                    })
                else:
                    if ann_id and ann_id not in new_ids:
                        new_ids.add(ann_id)
                        next_row = len(all_values) + len(new_rows) + 1
                        row_data = self._prepare_row_data(announcement, next_row, include_overview, include_budget)
                        new_rows.append(row_data)

            # 3) 일괄 업데이트
            if new_rows:
                worksheet.append_rows(new_rows, value_input_option='USER_ENTERED')
            if update_cells:
                worksheet.batch_update(update_cells, value_input_option='USER_ENTERED')

            logger.info(f"✓ {sheet_name} 탭 업데이트 완료: 신규 {len(new_rows)}건, 갱신 {len(update_cells)}건")

            # 4) 최종 중복 확인
            dedup_count = self.deduplicate_sheet(sheet_name, headers)
            if dedup_count:
                logger.info(f"✓ {sheet_name} 탭 최종 중복 제거: {dedup_count}건")

            # 5) 만료 공고 삭제
            expired_count = self.remove_expired_rows(sheet_name, headers, self.min_days_remaining)
            if expired_count:
                logger.info(f"✓ {sheet_name} 탭 만료 공고 삭제: {expired_count}건")

        except Exception as e:
            logger.error(f"업데이트 오류: {str(e)}")
            raise

        return {'new': len(new_rows), 'updated': len(update_cells)}

    def deduplicate_sheet(self, sheet_name: str, headers: List[str]) -> int:
        """
        공고ID 기준 중복 행 제거 (첫 번째 행만 유지)
        메모리에서 중복 제거 후 시트 전체를 다시 쓰는 방식 (API 호출 최소화)

        Args:
            sheet_name: 시트 이름
            headers: 헤더 리스트

        Returns:
            삭제된 행 수
        """
        worksheet = self.get_or_create_worksheet(sheet_name)
        all_values = worksheet.get_all_values(value_render_option='FORMULA')

        if len(all_values) <= 1:
            return 0

        id_col_idx = headers.index('공고ID')
        seen_ids = set()
        unique_rows = [all_values[0]]  # 헤더 유지
        dup_count = 0

        for row in all_values[1:]:
            ann_id = row[id_col_idx] if len(row) > id_col_idx else ''
            if not ann_id or ann_id not in seen_ids:
                seen_ids.add(ann_id)
                unique_rows.append(row)
            else:
                dup_count += 1

        if dup_count == 0:
            return 0

        # 남은일수 수식 행번호 보정
        if '남은일수' in headers and '마감일' in headers:
            remaining_idx = headers.index('남은일수')
            deadline_col = chr(ord('A') + headers.index('마감일'))
            for i, row in enumerate(unique_rows[1:], start=2):
                if len(row) > remaining_idx:
                    row[remaining_idx] = f'={deadline_col}{i}-TODAY()'

        # 시트 전체를 중복 제거된 데이터로 교체 (API 호출 2회: clear + update)
        worksheet.clear()
        worksheet.update(range_name='A1', values=unique_rows, value_input_option='USER_ENTERED')
        logger.info(f"✓ {sheet_name} 탭 중복 제거: {dup_count}건 삭제 ({len(all_values)-1}행 → {len(unique_rows)-1}행)")

        return dup_count

    def remove_expired_rows(self, sheet_name: str, headers: List[str], min_days: int = 7) -> int:
        """마감일 기준 min_days 미만 남은 행 삭제"""
        worksheet = self.get_or_create_worksheet(sheet_name)
        all_values = worksheet.get_all_values(value_render_option='FORMULA')

        if len(all_values) <= 1:
            return 0

        deadline_col_idx = headers.index('마감일')
        today = date.today()
        valid_rows = [all_values[0]]  # 헤더 유지
        expired_count = 0

        for row in all_values[1:]:
            deadline_str = row[deadline_col_idx] if len(row) > deadline_col_idx else ''
            if not deadline_str:
                valid_rows.append(row)  # 마감일 없으면 유지
                continue
            try:
                if isinstance(deadline_str, (int, float)):
                    deadline = date(1899, 12, 30) + timedelta(days=int(deadline_str))
                else:
                    deadline = datetime.strptime(str(deadline_str), '%y-%m-%d').date()
                days_remaining = (deadline - today).days
                if days_remaining >= min_days:
                    valid_rows.append(row)
                else:
                    expired_count += 1
            except ValueError:
                valid_rows.append(row)  # 파싱 실패 시 유지

        if expired_count == 0:
            return 0

        # 남은일수 수식 행번호 보정
        if '남은일수' in headers and '마감일' in headers:
            remaining_idx = headers.index('남은일수')
            deadline_col = chr(ord('A') + headers.index('마감일'))
            for i, row in enumerate(valid_rows[1:], start=2):
                if len(row) > remaining_idx:
                    row[remaining_idx] = f'={deadline_col}{i}-TODAY()'

        worksheet.clear()
        worksheet.update(range_name='A1', values=valid_rows, value_input_option='USER_ENTERED')
        logger.info(f"✓ {sheet_name} 탭 만료 공고 삭제: {expired_count}건 ({len(all_values)-1}행 → {len(valid_rows)-1}행)")

        return expired_count

    def _prepare_row_data(self, announcement: Dict, row_number: int, include_overview: bool = False, include_budget: bool = True, original_reg_date: str = None) -> List:
        """
        공고 데이터를 스프레드시트 행 형식으로 변환

        Args:
            announcement: 공고 데이터
            row_number: 추가될 행 번호
            include_overview: 과업개요 열 포함 여부 (K-Startup: True, 나라장터: False)
            include_budget: 예산 열 포함 여부 (나라장터: True, K-Startup: False)
            original_reg_date: 기존 등록일자 (갱신 시 기존 값 유지)

        Returns:
            행 데이터 리스트
        """
        # 공고명에 하이퍼링크 삽입
        title = announcement.get('title', '').replace('"', '""')  # 쌍따옴표 이스케이프
        link = announcement.get('link', '')
        announcement_title_with_link = f'=HYPERLINK("{link}", "{title}")'

        # 날짜 형식: YY-MM-DD (KST)
        from datetime import timezone, timedelta as td
        KST = timezone(td(hours=9))
        now = datetime.now(KST).strftime('%y-%m-%d')

        # 마감일 YY-MM-DD 변환
        deadline = announcement.get('deadline', '')
        if deadline and len(deadline) >= 10:
            deadline = deadline[2:]  # YYYY-MM-DD → YY-MM-DD

        # 등록일자 YY-MM-DD 변환 (공고가 등록된 날짜)
        reg_date = announcement.get('registration_date', '')
        if reg_date and len(reg_date) >= 10:
            reg_date = reg_date[2:]  # YYYY-MM-DD → YY-MM-DD

        # 남은일수 수식: 마감일(D열) - TODAY()
        remaining_days_formula = f'=D{row_number}-TODAY()'

        row = [
            announcement_title_with_link,           # 공고명 (하이퍼링크)
            announcement.get('id', ''),             # 공고ID
            announcement.get('organization', ''),   # 발주기관
            deadline,                               # 마감일 (YY-MM-DD)
            remaining_days_formula,                 # 남은일수 (수식)
        ]

        if include_budget:
            row.append(str(announcement.get('budget', '')))    # 예산

        if include_overview:
            row.append(announcement.get('overview', '')[:500])  # 과업개요 (500자 제한)

        # 갱신 시 기존 등록일자 유지, 신규 시 API 등록일자 사용
        final_reg_date = original_reg_date if original_reg_date else reg_date
        row.extend([final_reg_date, now])  # 등록일자, 업로드일자

        return row
