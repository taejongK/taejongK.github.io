#!/usr/bin/env python3
"""
index.html 의 날짜 의존 값만 오늘 기준으로 다시 계산한다.

GitHub Actions 에서 매월 자동 실행하기 위한 스크립트다.
원본인 resume.md 는 개인정보 때문에 저장소에 없으므로 build_site.py 를 돌릴 수
없다. 대신 index.html 에 이미 들어 있는 입사 연월을 읽어 아래 세 가지만 갱신한다.

  1. '2025.06 ~ 현재 · N년 M개월'  의 재직기간
  2. '경력 요약' 옆의 경력 총합
  3. 문서 하단의 '최종 수정 YYYY.MM.DD'

내용을 바꾸려면 여전히 resume.md 를 고치고 build_site.py 를 돌려야 한다.
이 스크립트는 숫자만 만진다.

    python3 refresh_dates.py
"""

import re
import sys
from datetime import date
from pathlib import Path

from build_site import fmt_months, parse_months

ROOT = Path(__file__).parent
TARGET = ROOT / "index.html"

# '2025.06 ~ 현재 · 1년 3개월'
TENURE_RE = re.compile(r"(\d{4})\.(\d{1,2}) ~ (현재|재직\s*중) · [^<]*")
# 경력 요약 목록 안의 각 기간
LIST_DUR_RE = re.compile(r'<span class="period">[^<·]*·\s*([^<]*)</span>')
TOTAL_RE = re.compile(r'(경력 요약\s*<span class="period">총 )[^<]*')
UPDATED_RE = re.compile(r"최종 수정 \d{4}\.\d{2}\.\d{2}")


def months_since(year: int, month: int, today: date) -> int:
    """입사월과 당월을 모두 포함하는 국내 이력서 관례."""
    return (today.year - year) * 12 + (today.month - month) + 1


def refresh(html: str, today: date) -> str:
    def fix_tenure(m):
        months = months_since(int(m.group(1)), int(m.group(2)), today)
        return f"{m.group(1)}.{int(m.group(2)):02d} ~ {m.group(3)} · {fmt_months(months)}"

    html = TENURE_RE.sub(fix_tenure, html)

    tenure_block = re.search(r'<ul class="tenure">(.*?)</ul>', html, re.S)
    if tenure_block:
        total = sum(parse_months(d) for d in LIST_DUR_RE.findall(tenure_block.group(1)))
        if total:
            html = TOTAL_RE.sub(lambda m: m.group(1) + fmt_months(total), html)

    return UPDATED_RE.sub(f"최종 수정 {today:%Y.%m.%d}", html)


def main() -> int:
    if not TARGET.exists():
        print(f"대상을 찾을 수 없습니다: {TARGET}", file=sys.stderr)
        return 2

    today = date.today()
    before = TARGET.read_text(encoding="utf-8")
    after = refresh(before, today)

    if after == before:
        print(f"변경 없음 ({today:%Y.%m.%d})")
        return 0

    TARGET.write_text(after, encoding="utf-8")
    for label, pattern in (("재직기간", r"~ 현재 · [^<]*"),
                           ("경력 총합", r"총 \d+년[^<]*"),
                           ("최종 수정", r"최종 수정 [\d.]+")):
        found = re.search(pattern, after)
        if found:
            print(f"  {label}: {found.group(0)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
