# business-screening
정부·지자체 및 공공기관의 사업 공고를 수집하여 한눈에 확인할 수 있도록 만든 공고 모니터링 대시보드입니다.
현재는 **판로·지원 관련 공고**를 중심으로 수집하고 있습니다.

## 주요 기능
- 공공기관 사업 공고 자동 수집
- 여러 출처의 공고를 하나의 목록으로 통합
- 모집 중 / 마감 공고 구분
- 키워드 검색 및 카테고리 필터
- 최신 공고 / 마감 임박순 정렬
- 신규 공고 `NEW` 표시
- 관심 공고 저장
- 필요 없는 공고 숨기기 및 복원
- 공고 원문 바로가기

## 데이터 출처

### 나라장터
조달청 나라장터 입찰공고정보 API를 이용하여 공고를 수집합니다.
현재는 최근 공고 중 제목에 **`판로`와 `지원`이 모두 포함된 공고**를 수집합니다.

### 판판대로
판판대로의 수행기관 공모 데이터를 수집합니다.
현재 모집 중인 수행기관 공고가 없을 경우 기존 데이터를 유지하고, 공고가 새로 등록되면 자동 수집하도록 구성되어 있습니다.

## 데이터 처리 구조
```text
나라장터 API
    ↓
g2b.py
    ↓
g2b_data.json
    ┐
    │
    ├─ merge_data.py → data.json → 웹 대시보드
    │
    ┘
fanfandaero_data.json
    ↑
fanfandaero.py
    ↑
판판대로
```

웹페이지에서는 최종 통합 데이터인 `data.json`만 불러옵니다.

## 자동 업데이트
GitHub Actions를 이용하여 데이터를 매일 자동으로 업데이트합니다.

```text
g2b.py
   ↓
fanfandaero.py
   ↓
merge_data.py
   ↓
data.json 갱신
   ↓
GitHub에 자동 반영
```

API 연결이 일시적으로 실패할 경우를 대비하여 나라장터 수집에는 재시도 로직이 적용되어 있습니다.
데이터의 업데이트 시간은 **한국 표준시(KST / Asia/Seoul)** 기준으로 저장됩니다.

## 주요 파일
| 파일 | 역할 |
|---|---|
| `index.html` | 공고 대시보드 화면 |
| `g2b.py` | 나라장터 공고 수집 |
| `fanfandaero.py` | 판판대로 수행기관 공고 수집 |
| `merge_data.py` | 출처별 데이터를 하나로 통합 |
| `update_data.py` | 전체 데이터 업데이트 실행 |
| `g2b_data.json` | 나라장터 누적 데이터 |
| `fanfandaero_data.json` | 판판대로 누적 데이터 |
| `data.json` | 웹페이지에서 사용하는 최종 통합 데이터 |
| `.github/workflows/update-data.yml` | GitHub Actions 자동 업데이트 설정 |

## 로컬에서 데이터 업데이트
필요한 패키지를 설치합니다.

```powershell
pip install requests truststore python-dotenv tzdata
```

전체 데이터를 업데이트하려면 프로젝트 폴더에서 다음 명령을 실행합니다.

```powershell
python update_data.py
```

수집된 데이터는 출처별 JSON 파일에 누적되고, 마지막에 `data.json`으로 통합됩니다.

## 프로젝트 상태
현재 주요 데이터 수집 및 자동 업데이트 기능이 구축되어 있으며, 공고 출처와 편의 기능을 계속 확장하고 있습니다.