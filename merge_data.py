import json
import os
from datetime import datetime


# ============================================================
# 설정
# ============================================================

SOURCE_FILES = [
    "g2b_data.json",
    "fanfandaero_data.json",
]

OUTPUT_FILE = "data.json"


# ============================================================
# 출처별 데이터 읽기
# ============================================================

def load_source_file(file_name):

    if not os.path.exists(file_name):

        print(
            f"[건너뜀] {file_name} 파일이 없습니다."
        )

        return []


    try:

        with open(
            file_name,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)


        if isinstance(data, list):
            items = data

        else:
            items = (
                data.get("items", [])
                or []
            )


        print(
            f"[불러옴] {file_name}: {len(items)}건"
        )

        return items


    except Exception as error:

        print(
            f"[오류] {file_name}: {error}"
        )

        return []


# ============================================================
# 모든 출처 통합
# ============================================================

all_items = []


for source_file in SOURCE_FILES:

    items = load_source_file(
        source_file
    )

    all_items.extend(
        items
    )


# ============================================================
# source + source_id 기준 중복 제거
# ============================================================

unique_items = {}


for item in all_items:

    source = (
        item.get("source", "")
        or ""
    )

    source_id = (
        item.get("source_id", "")
        or ""
    )


    if source and source_id:

        key = (
            f"{source}:{source_id}"
        )

    else:

        # 혹시 source_id가 없는 데이터가 들어오더라도
        # 데이터 자체를 버리지는 않음
        key = (
            f"unknown:"
            f"{len(unique_items)}:"
            f"{item.get('title', '')}"
        )


    unique_items[key] = item


merged_items = list(
    unique_items.values()
)


# ============================================================
# 화면용 data.json 저장
# ============================================================

output_data = {

    "updated_at":
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        ),

    "total_count":
        len(merged_items),

    "items":
        merged_items
}


with open(
    OUTPUT_FILE,
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
# 결과 출력
# ============================================================

print()
print("=" * 70)
print(
    "통합 전 공고:",
    len(all_items)
)
print(
    "중복 제거 후:",
    len(merged_items)
)
print(
    f"{OUTPUT_FILE} 저장 완료!"
)
print("=" * 70)