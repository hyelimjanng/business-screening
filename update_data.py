import subprocess
import sys
from datetime import datetime


def run_script(script_name):

    print()
    print("=" * 70)
    print(f"{script_name} 실행")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("----- 오류 출력 -----")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} 실행 실패 "
            f"(exit code: {result.returncode})"
        )


print()
print("=" * 70)
print("공고 데이터 통합 업데이트 시작")
print(
    datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)
print("=" * 70)


# 1. 나라장터 수집
run_script("g2b.py")

# 2. 판판대로 수행사 공고 수집
run_script("fanfandaero.py")

# 3. 통합
run_script("merge_data.py")


print()
print("=" * 70)
print("공고 데이터 통합 업데이트 완료")
print(
    datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)
print("=" * 70)