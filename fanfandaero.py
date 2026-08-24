import time
import json
import os
import truststore

from datetime import datetime
from zoneinfo import ZoneInfo

truststore.inject_into_ssl()

import requests

KST = ZoneInfo("Asia/Seoul")


URL = "https://fanfandaero.kr/portal/v2/selectSprtBizPbancListComp.do"

DATA_FILE = "fanfandaero_data.json"


def format_date(date_text):

    if not date_text or len(date_text) != 8:
        return date_text or ""

    return (
        f"{date_text[:4]}-"
        f"{date_text[4:6]}-"
        f"{date_text[6:8]}"
    )


def fetch_page(page_index):

    payload = {
        "brno": "",
        "pageIndex": str(page_index),
        "pageUnit": "8",
        "searchTypeStr": "",
        "searchTargetStr": "",
        "searchAreaStr": "",
        "searchText": "",
        "searchSprt": "202504",
        "searchOrder": "1",
        "testLoginId": "",
        "notSearchSprtBizCdComp": ""
    }

    response = requests.post(
        URL,
        data=payload,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


print("판판대로 수행사 공고 수집 시작!")
print()

# ============================================================
# 기존 누적 데이터 읽기
# ============================================================

existing_items = []

if os.path.exists(DATA_FILE):

    try:

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

        print(
            f"기존 누적 공고: {len(existing_items)}건"
        )

    except Exception as error:

        print(
            f"기존 데이터 읽기 실패: {error}"
        )

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

all_notices = []

page = 1


while True:

    print(f"{page}페이지 요청 중...")

    data = fetch_page(page)

    notices = (
        data.get("sprtBizApplList", [])
        or []
    )

    # 첫 페이지에서 데이터가 0건이면
    # 현재 공고가 없는 것으로 판단
    if not notices:

        if page == 1:

            total_count = (
                data.get("sprtBizApplListTotCnt")
                or data.get("cntTot")
                or 0
            )

            print(
                f"현재 수행사 공고가 없습니다. "
                f"(API total: {total_count})"
            )

        else:
            print(
                "더 이상 공고가 없습니다."
            )

        break


    all_notices.extend(
        notices
    )

    print(
        f"  → {len(notices)}건 가져옴"
    )

    page += 1

    time.sleep(1)


# ============================================================
# 공고가 없으면 기존 fanfandaero_data.json을 덮어쓰지 않음
# ============================================================

if not all_notices:

    print()
    print("=" * 70)
    print("신규 수집 공고: 0건")
    print(
        f"기존 {DATA_FILE}은 수정하지 않습니다."
    )
    print("=" * 70)

    raise SystemExit


# ============================================================
# 실제 공고가 생긴 경우
# 현재 필드 매핑은 API 실제값 확인 후 추가 검증 예정
# ============================================================

# ============================================================
# 신규 / 기존 공고 누적 갱신
# ============================================================

current_time = datetime.now(KST).strftime(
    "%Y-%m-%d %H:%M:%S"
)

new_count = 0
updated_count = 0


for notice in all_notices:

    source_id = (
        notice.get("sprtBizCd")
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

        first_seen_at = (
            current_time
        )

        new_count += 1


    normalized_notice = {

        "source":
            "판판대로",

        "source_id":
            source_id,

        "title":
            notice.get(
                "sprtBizNm"
            )
            or "",

        "organization":
            notice.get(
                "operInstNm"
            )
            or "",

        "notice_date":
            "",

        "apply_start":
            format_date(
                notice.get(
                    "rcritBgngYmd"
                )
            ),

        "apply_end":
            format_date(
                notice.get(
                    "rcritEndYmd"
                )
            ),

        "url":
            notice.get(
                "url"
            )
            or "",

        "first_seen_at":
            first_seen_at,

        "last_seen_at":
            current_time
    }


    stored_items[
        source_id
    ] = normalized_notice


normalized_notices = list(
    stored_items.values()
)


# ============================================================
# 실제 공고가 있을 때만 저장
# ============================================================

output_data = {
    "updated_at":
        datetime.now(KST).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

    "total_count":
        len(normalized_notices),

    "items":
        normalized_notices
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


print()
print("=" * 70)

print("신규 공고:", new_count)
print("기존 공고 갱신:", updated_count)

print(
    "전체 수행사 공고:",
    len(normalized_notices)
)
print(f"{DATA_FILE} 저장 완료!")
print("=" * 70)