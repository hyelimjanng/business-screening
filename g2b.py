import os
import json
from datetime import datetime, timedelta

import requests
import truststore
from dotenv import load_dotenv


# ============================================================
# 기본 설정
# ============================================================

truststore.inject_into_ssl()
load_dotenv()

API_KEY = os.getenv("G2B_API_KEY")
ENDPOINT = os.getenv("G2B_ENDPOINT")

if not API_KEY:
    raise ValueError(
        "G2B_API_KEY가 .env에 없습니다."
    )

if not ENDPOINT:
    raise ValueError(
        "G2B_ENDPOINT가 .env에 없습니다."
    )


# 한 페이지당 조회 개수
ROWS_PER_PAGE = 100

# 현재 시각
today = datetime.now()


# ============================================================
# 초기 적재 기간
# 2026년 6월 1일 ~ 오늘
# ============================================================

backfill_start = datetime(
    today.year,
    6,
    1
)

backfill_end = today


# ============================================================
# API 한 페이지 조회
# ============================================================

def fetch_page(
    page_no,
    start_text,
    end_text
):

    params = {
        "pageNo": str(page_no),
        "numOfRows": str(ROWS_PER_PAGE),
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_text,
        "inqryEndDt": end_text
    }

    # serviceKey는 URL에 직접 붙임
    request_url = (
        f"{ENDPOINT}"
        f"?serviceKey={API_KEY}"
    )

    response = requests.get(
        request_url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    header = (
        data
        .get("response", {})
        .get("header", {})
    )

    result_code = header.get(
        "resultCode"
    )

    if result_code != "00":
        raise RuntimeError(
            f"나라장터 API 오류: {header}"
        )

    body = (
        data
        .get("response", {})
        .get("body", {})
    )

    return body


# ============================================================
# 특정 기간의 모든 페이지 조회
# ============================================================

def collect_period(
    start_date,
    end_date
):

    start_text = (
        start_date.strftime("%Y%m%d")
        + "0000"
    )

    end_text = (
        end_date.strftime("%Y%m%d")
        + "2359"
    )

    print()
    print("=" * 70)

    print(
        f"조회 기간: "
        f"{start_date:%Y-%m-%d}"
        f" ~ "
        f"{end_date:%Y-%m-%d}"
    )

    period_items = []

    page_no = 1

    while True:

        body = fetch_page(
            page_no,
            start_text,
            end_text
        )

        items = (
            body.get("items", [])
            or []
        )

        total_count = int(
            body.get("totalCount", 0)
            or 0
        )

        print(
            f"{page_no}페이지: "
            f"{len(items)}건 "
            f"/ 전체 {total_count}건"
        )

        period_items.extend(
            items
        )

        # 전체 건수를 다 가져왔으면 종료
        if len(period_items) >= total_count:
            break

        # 결과가 더 이상 없으면 종료
        if not items:
            break

        page_no += 1

    return period_items


# ============================================================
# 6월 1일부터 오늘까지
# 7일 단위로 전체 수집
# ============================================================

all_items = []

current_start = backfill_start


while current_start <= backfill_end:

    current_end = min(
        current_start
        + timedelta(days=6),
        backfill_end
    )

    period_items = collect_period(
        current_start,
        current_end
    )

    all_items.extend(
        period_items
    )

    current_start = (
        current_end
        + timedelta(days=1)
    )


# ============================================================
# 판로 + 지원 필터
# ============================================================

filtered_items = []


for item in all_items:

    title = (
        item.get(
            "bidNtceNm",
            ""
        )
        or ""
    )

    # 제목에 판로와 지원이
    # 둘 다 들어간 공고만
    matches_keyword = (
        "판로" in title
        and "지원" in title
    )

    if not matches_keyword:
        continue


    # 취소공고 제외
    notice_kind = (
        item.get(
            "ntceKindNm",
            ""
        )
        or ""
    )

    if "취소" in notice_kind:
        continue


    # 올해 공고만
    notice_date = (
        item.get(
            "bidNtceDt",
            ""
        )
        or ""
    )

    if not notice_date.startswith(
        str(today.year)
    ):
        continue


    # 마감된 공고도 여기서는 삭제하지 않음
    # DB/JSON에는 보관하고
    # 화면에서 필요할 때 숨길 예정

    filtered_items.append(
        item
    )


# ============================================================
# 같은 공고번호는 최신 차수만 남김
# ============================================================

latest_items = {}


for item in filtered_items:

    bid_no = (
        item.get(
            "bidNtceNo",
            ""
        )
        or ""
    )

    bid_ord = (
        item.get(
            "bidNtceOrd",
            ""
        )
        or ""
    )

    if not bid_no:
        continue


    existing = latest_items.get(
        bid_no
    )


    if existing is None:

        latest_items[
            bid_no
        ] = item

        continue


    existing_ord = (
        existing.get(
            "bidNtceOrd",
            ""
        )
        or ""
    )


    # 차수가 더 높은 공고로 교체
    if bid_ord > existing_ord:

        latest_items[
            bid_no
        ] = item


filtered_items = list(
    latest_items.values()
)


# ============================================================
# 최신 공고순 정렬
# ============================================================

filtered_items.sort(
    key=lambda item: (
        item.get(
            "bidNtceDt",
            ""
        )
        or ""
    ),
    reverse=True
)


# ============================================================
# 저장용 데이터로 정리
# ============================================================

normalized_items = []


for item in filtered_items:

    normalized_item = {

        "source":
            "나라장터",

        "source_id":
            item.get(
                "bidNtceNo"
            )
            or "",

        "source_order":
            item.get(
                "bidNtceOrd"
            )
            or "",

        "title":
            item.get(
                "bidNtceNm"
            )
            or "",

        "notice_date":
            item.get(
                "bidNtceDt"
            )
            or "",

        "apply_start":
            item.get(
                "bidBeginDt"
            )
            or "",

        "apply_end":
            item.get(
                "bidClseDt"
            )
            or "",

        "organization":
            item.get(
                "ntceInsttNm"
            )
            or "",

        "demand_org":
            item.get(
                "dminsttNm"
            )
            or "",

        "category":
            "판로지원",

        "url":
            item.get(
                "bidNtceDtlUrl"
            )
            or "",

        "notice_kind":
            item.get(
                "ntceKindNm"
            )
            or ""
    }

    normalized_items.append(
        normalized_item
    )


# ============================================================
# JSON 파일 저장
# ============================================================

output_data = {

    "updated_at":
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

    "total_count":
        len(normalized_items),

    "items":
        normalized_items
}


with open(
    "g2b_data.json",
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        output_data,
        file,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# 최종 결과
# ============================================================

print()
print("=" * 70)

print(
    "API에서 전체 조회한 공고:",
    len(all_items)
)

print(
    "판로+지원 조건 공고:",
    len(filtered_items)
)

print(
    "g2b_data.json 저장 공고:",
    len(normalized_items)
)

print("=" * 70)

print()
print(
    "g2b_data.json 저장 완료!"
)


# 저장된 공고 확인
for item in normalized_items:

    print()

    print(
        item["source_id"],
        "/",
        item["title"]
    )