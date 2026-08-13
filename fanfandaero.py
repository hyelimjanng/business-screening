import time
import json
import truststore
from datetime import datetime

truststore.inject_into_ssl()

import requests


URL = "https://fanfandaero.kr/portal/v2/selectSprtBizPbancList.do"


def format_date(date_text):
    if not date_text or len(date_text) != 8:
        return date_text or ""

    return f"{date_text[:4]}-{date_text[4:6]}-{date_text[6:8]}"


def fetch_page(page_index):

    payload = {
        "brno": "",
        "pageIndex": str(page_index),
        "pageUnit": "6",
        "searchTypeStr": "",
        "searchTargetStr": "",
        "searchAreaStr": "",
        "searchText": "",
        "noSearchSprt": "",
        "searchOrder": "1",
        "sortOrder": "",
        "testLoginId": "",
        "notSearchSprtBizCd": ""
    }

    response = requests.post(
        URL,
        data=payload,
        timeout=15
    )

    response.raise_for_status()

    return response.json()


print("판판대로 전체 공고 수집 시작!")
print()


all_notices = []

page = 1


while True:

    print(f"{page}페이지 요청 중...")

    data = fetch_page(page)

    notices = data.get("sprtBizApplList", [])

    if not notices:
        print("더 이상 공고가 없습니다.")
        break

    all_notices.extend(notices)

    print(f"  → {len(notices)}건 가져옴")

    page += 1

    time.sleep(1)


normalized_notices = []


for notice in all_notices:

    normalized_notice = {
        "source": "판판대로",
        "title": notice.get("sprtBizNm") or "",
        "apply_start": format_date(
            notice.get("rcritBgngYmd")
        ),
        "apply_end": format_date(
            notice.get("rcritEndYmd")
        ),
        "target": notice.get("sprtBizTrgtNm") or "",
        "category": notice.get("sprtBizTyNm") or "",
        "region": notice.get("sprtBizCtpvNm") or "전국",
        "source_id": notice.get("sprtBizCd") or "",
        "apply_possible": notice.get("aplyPsblYn") or "",
        "deadline_yn": notice.get("aplyDdlnYn") or ""
    }

    normalized_notices.append(
        normalized_notice
    )


with open(
    "data.json",
    "w",
    encoding="utf-8"
) as file:

    output_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": normalized_notices
    }

    json.dump(
        output_data,
        file,
        ensure_ascii=False,
        indent=2
    )


print()
print("=" * 70)
print("전체 공고 수:", len(normalized_notices))
print("data.json 저장 완료!")
print("=" * 70)