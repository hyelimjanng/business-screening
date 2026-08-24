import os
import json
import time

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import truststore
from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")


# ============================================================
# 기본 설정
# ============================================================

truststore.inject_into_ssl()
load_dotenv()

API_KEY = os.getenv("G2B_API_KEY")
ENDPOINT = os.getenv("G2B_ENDPOINT")

if not API_KEY:
    raise ValueError("G2B_API_KEY가 .env에 없습니다.")

if not ENDPOINT:
    raise ValueError("G2B_ENDPOINT가 .env에 없습니다.")


ROWS_PER_PAGE = 100
DATA_FILE = "g2b_data.json"

now = datetime.now(KST)


# ============================================================
# 조회 기간
# 초기 적재 완료 후에는 최근 7일만 확인
# ============================================================

start_date = now - timedelta(days=6)
end_date = now


# ============================================================
# API 호출
# ============================================================

def fetch_page(page_no, start_text, end_text):

    params = {
        "pageNo": str(page_no),
        "numOfRows": str(ROWS_PER_PAGE),
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": start_text,
        "inqryEndDt": end_text
    }

    request_url = f"{ENDPOINT}?serviceKey={API_KEY}"

    max_retries = 3


    for attempt in range(1, max_retries + 1):

        try:

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

            if header.get("resultCode") != "00":
                raise RuntimeError(
                    f"나라장터 API 오류: {header}"
                )

            return (
                data
                .get("response", {})
                .get("body", {})
            )


        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ) as error:

            print(
                f"  ⚠ {page_no}페이지 요청 실패 "
                f"({attempt}/{max_retries}): {error}"
            )

            if attempt == max_retries:
                print(
                    f"  ✖ {page_no}페이지 "
                    "최종 요청 실패"
                )
                raise

            wait_seconds = attempt * 10

            print(
                f"  → {wait_seconds}초 후 재시도합니다."
            )

            time.sleep(
                wait_seconds
            )


# ============================================================
# 최근 7일 전체 페이지 수집
# ============================================================

start_text = (
    start_date.strftime("%Y%m%d")
    + "0000"
)

end_text = (
    end_date.strftime("%Y%m%d")
    + "2359"
)

all_items = []
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

    all_items.extend(items)

    if len(all_items) >= total_count:
        break

    if not items:
        break

    page_no += 1


# ============================================================
# 판로 + 지원 필터
# ============================================================

filtered_items = []

for item in all_items:

    title = (
        item.get("bidNtceNm", "")
        or ""
    )

    if not (
        "판로" in title
        and "지원" in title
    ):
        continue

    notice_kind = (
        item.get("ntceKindNm", "")
        or ""
    )

    if "취소" in notice_kind:
        continue

    filtered_items.append(item)


# ============================================================
# 같은 공고번호는 최신 차수만 유지
# ============================================================

latest_items = {}

for item in filtered_items:

    bid_no = (
        item.get("bidNtceNo", "")
        or ""
    )

    bid_ord = (
        item.get("bidNtceOrd", "")
        or ""
    )

    if not bid_no:
        continue

    existing = latest_items.get(bid_no)

    if existing is None:
        latest_items[bid_no] = item
        continue

    existing_ord = (
        existing.get("bidNtceOrd", "")
        or ""
    )

    if bid_ord > existing_ord:
        latest_items[bid_no] = item


filtered_items = list(
    latest_items.values()
)

# ============================================================
# 기존 적재 데이터 읽기
# ============================================================

if os.path.exists(DATA_FILE):

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        existing_data = json.load(file)

    existing_items = (
        existing_data.get("items", [])
        or []
    )

    # 기존 데이터에 first_seen_at / last_seen_at이 없으면 초기값 생성
    migration_time = now.strftime("%Y-%m-%d %H:%M:%S")

    for item in existing_items:

        if not item.get("first_seen_at"):
            item["first_seen_at"] = (
                item.get("notice_date")
                or migration_time
            )

        if not item.get("last_seen_at"):
            item["last_seen_at"] = migration_time

else:
    existing_items = []


# source_id 기준 기존 데이터 색인
stored_items = {}

for item in existing_items:

    source_id = (
        item.get("source_id", "")
        or ""
    )

    if source_id:
        stored_items[source_id] = item

        
# ============================================================
# 신규 / 기존 공고 누적 갱신
# ============================================================

current_time = now.strftime(
    "%Y-%m-%d %H:%M:%S"
)

new_count = 0
updated_count = 0


for item in filtered_items:

    source_id = (
        item.get("bidNtceNo", "")
        or ""
    )

    if not source_id:
        continue

    old_item = stored_items.get(
        source_id
    )

    if old_item:
        first_seen_at = (
            old_item.get(
                "first_seen_at"
            )
            or current_time
        )

        updated_count += 1

    else:
        first_seen_at = current_time
        new_count += 1


    normalized_item = {

        "source": "나라장터",

        "source_id":
            source_id,

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

        "organization":
            item.get(
                "ntceInsttNm"
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

        "url":
            item.get(
                "bidNtceDtlUrl"
            )
            or "",

        "notice_kind":
            item.get(
                "ntceKindNm"
            )
            or "",

        "first_seen_at":
            first_seen_at,

        "last_seen_at":
            current_time
    }

    stored_items[
        source_id
    ] = normalized_item


# ============================================================
# 전체 저장
# ============================================================

final_items = list(
    stored_items.values()
)

final_items.sort(
    key=lambda item:
        item.get(
            "notice_date",
            ""
        ),
    reverse=True
)


output_data = {

    "updated_at":
        current_time,

    "total_count":
        len(final_items),

    "items":
        final_items
}


with open(
    DATA_FILE,
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
# 결과
# ============================================================

print()
print("=" * 70)

print(
    "최근 7일 전체 조회:",
    len(all_items)
)

print(
    "이번 수집 판로+지원 공고:",
    len(filtered_items)
)

print(
    "신규 공고:",
    new_count
)

print(
    "기존 공고 갱신:",
    updated_count
)

print(
    "현재 누적 적재:",
    len(final_items)
)

print("=" * 70)

print()
print("g2b_data.json 누적 갱신 완료!")