# 공공데이터 Open API 기능 명세 요약

본 문서는 **창업진흥원 K-Startup 조회 서비스**와 **조달청 나라장터 공공데이터 개방 표준 서비스**의 주요 기능과 명세를 요약 정리한 문서입니다.

---

## 1. 창업진흥원: K-Startup 조회 서비스
**서비스 개요**
- [cite_start]**제공 기관**: 중소벤처기업부 및 창업진흥원 [cite: 17]
- [cite_start]**서비스 URL**: `https://apis.data.go.kr/B552735/kisedKstartupService01` [cite: 17]
- [cite_start]**목적**: 창업지원포털(K-Startup)의 사업공고, 사업정보, 콘텐츠 정보 등을 외부에서 활용 가능하도록 제공 [cite: 17]

### 주요 기능 목록

#### 1) 통합공고 지원사업 정보 (`getBusinessInformation`)
[cite_start]창업지원사업의 예산, 규모, 절차 등 전반적인 사업 소개 정보를 조회합니다. [cite: 19, 23]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]창업지원사업 예산, 규모, 수행기관, 사업절차, 문의처 등 사업 소개 정보 조회 [cite: 23] |
| **주요 요청항목** | [cite_start]사업 연도(`biz_yr`), 사업 명(`supt_biz_titl_nm`), 사업 구분 코드 [cite: 25] |
| **주요 응답항목** | [cite_start]지원 대상, 지원예산 및 규모, 지원 내용, 상세페이지 URL [cite: 28] |

#### 2) 지원사업 공고 정보 (`getAnnouncementInformation`)
[cite_start]실제 모집 중인 공고의 상세 정보(기간, 자격 요건 등)를 조회합니다. [cite: 19, 34]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]공고명, 공고기간, 지원대상(연령/업력), 지원방법 등 모집 공고 상세 정보 조회 [cite: 34] |
| **주요 요청항목** | [cite_start]지역명(`supt_regin`), 창업 기간(`biz_enyy`), 대상 연령(`biz_trgt_age`), 모집진행여부 [cite: 36] |
| **주요 응답항목** | [cite_start]공고 접수 기간, 주관 기관, 담당자 연락처, 신청 방법(온라인/방문 등), 공고문 URL [cite: 39] |

#### 3) 창업관련 콘텐츠 정보 (`getContentInformation`)
[cite_start]창업 생태계 관련 뉴스, 동영상, 우수사례 등 콘텐츠를 조회합니다. [cite: 19, 45]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]정책·규제 정보, 생태계 이슈·동향, 창업우수사례 등 콘텐츠 정보 조회 [cite: 45] |
| **주요 요청항목** | [cite_start]콘텐츠 구분 코드(`clss_cd`), 제목(`titl_nm`) [cite: 47] |
| **주요 응답항목** | [cite_start]등록 일시, 조회 수, 첨부파일 명, 상세페이지 URL [cite: 50] |

#### 4) 창업관련 통계보고서 정보 (`getStatisticalInformation`)
[cite_start]창업기업 실태조사 등 통계 데이터를 제공합니다. [cite: 19, 56]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]창업기업 업력, 형태, 분야, 해외진출 여부 등 통계보고서 정보 조회 [cite: 56] |
| **주요 요청항목** | [cite_start]통계 자료 명(`titl_nm`), 통계 자료 내용 [cite: 58] |
| **주요 응답항목** | [cite_start]다운로드 파일 명, 통계 자료 내용, 수정 일시 [cite: 61] |

---

## 2. 조달청: 나라장터 공공데이터 개방 표준 서비스
**서비스 개요**
- [cite_start]**제공 기관**: 조달청 [cite: 80]
- [cite_start]**서비스 URL**: `http://apis.data.go.kr/1230000/ao/PubDataOpnStdService` [cite: 80]
- [cite_start]**목적**: 나라장터 입찰, 낙찰, 계약정보 데이터를 행안부 고시 공공데이터 개방표준에 따라 제공 [cite: 80]

### 주요 기능 목록

#### 1) 입찰공고정보 조회 (`getDataSetOpnStdBidPblancInfo`)
[cite_start]특정 기간 동안의 나라장터 입찰 공고 내역을 조회합니다. [cite: 82, 84]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]입찰공고일시를 기준으로 공고번호, 공고명, 투찰자격 등 입찰 정보 목록 조회 [cite: 84] |
| **주요 요청항목** | [cite_start]입찰공고시작일시(`bidNtceBgnDt`), 종료일시(`bidNtceEndDt`) **(범위 1개월 제한)** [cite: 86] |
| **주요 응답항목** | [cite_start]입찰공고번호, 공고명, 배정예산금액, 투찰가능업종, 지역제한여부, 입찰마감일시 [cite: 89] |

#### 2) 낙찰정보 조회 (`getDataSetOpnStdScsbidInfo`)
[cite_start]개찰이 완료된 입찰 건에 대한 낙찰 및 투찰 결과를 조회합니다. [cite: 82, 94]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]개찰일시를 기준으로 낙찰자, 투찰금액, 순위 등 낙찰 정보 조회 [cite: 94] |
| **주요 요청항목** | [cite_start]개찰시작일시(`opengBgnDt`), 종료일시(`opengEndDt`) **(범위 1주일 제한)**, 업무구분(물품/공사/용역) [cite: 96] |
| **주요 응답항목** | [cite_start]1순위 투찰업체명, 투찰금액, 투찰률, 예정가격, 최종낙찰자 정보 [cite: 99] |

#### 3) 계약정보 조회 (`getDataSetOpnStdCntrctInfo`)
체결된 계약 상세 내역을 조회합니다. (v1.1 신규 추가) [cite_start][cite: 82, 104]

| 구분 | 주요 내용 |
| :--- | :--- |
| **기능 설명** | [cite_start]계약체결일자를 기준으로 계약번호, 금액, 기간, 상대자 정보 등 조회 [cite: 104] |
| **주요 요청항목** | [cite_start]계약체결시작일자(`cntrctCnclsBgnDate`), 종료일자(`cntrctCnclsEndDate`) **(범위 1개월 제한)** [cite: 106] |
| **주요 응답항목** | [cite_start]계약번호, 계약명, 계약금액, 계약기간, 계약상대자(대표업체명), 수의계약사유 [cite: 109] |

---

## 3. 공통 기술 규격 및 참고사항

| 항목 | 상세 내용 |
| :--- | :--- |
| **인터페이스 표준** | [cite_start]REST (GET 방식) [cite: 17, 80] |
| **데이터 포맷** | [cite_start]XML, JSON 지원 (기본 JSON 권장) [cite: 17, 80] |
| **인증 방식** | [cite_start]공공데이터포털 발급 `ServiceKey` 필수 (URL Encode 주의) [cite: 17, 80] |
| **인코딩** | UTF-8 |
| **에러 처리** | [cite_start]HTTP Status Code 및 별도 결과 코드(`resultCode` 또는 `header`) 확인 필요 [cite: 66, 114] |