#!/usr/bin/env python3
"""
resume.md (작업본) → resume_submit.md (제출본) 생성기.

원본에는 지원자 본인만 봐야 하는 작업용 메타데이터가 섞여 있다.

  · 상단 '> ' 블록      — 문서 지위·형식 기준·통합 출처 같은 작업 노트
  · 하단 <!-- --> 블록  — 작성 메모(폐기된 방침, 수치 수정 이력, 미확인 항목)

이력서를 그대로 보내면 둘 다 노출된다. 특히 하단 메모에는 "이직사유는 전 회사
모두 기재하지 않는다" 같은 폐기된 방침과 "0.91 표기 폐기" 류의 수치 정정 이력이
남아 있어, 읽는 사람에 따라 수치 조작 정황으로 오독될 여지가 있다.

이 스크립트는 그 두 가지만 걷어낸다. 본문 내용은 한 글자도 손대지 않는다.

    python3 build_submit.py

build_site.py 와 동일하게 **검사를 먼저 하고 통과할 때만 파일을 쓴다.**
쓰고 나서 검사하면 차단에 실패해도 민감 정보가 디스크에 남기 때문이다.

주의: 제출본은 연봉·전화번호·주소가 그대로 들어간 전체판이다.
      .gitignore 에 등록돼 있으니 저장소에 올리지 말 것.
      공개용은 build_site.py 가 만드는 index.html 을 쓴다.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "resume.md"
OUT = ROOT / "resume_submit.md"

# 제출본에 남아 있으면 안 되는 표식
FORBIDDEN = ("<!--", "-->", "작성 메모", "문서 지위", "형식 기준", "통합 출처")

# 제출본에 반드시 남아 있어야 하는 섹션 (과다 삭제 방지)
REQUIRED = ("개인신상", "경력 사항 요약", "핵심 기술 요약", "경력기술서",
            "학력 사항", "사이드 프로젝트")


def strip_working_notes(text: str) -> tuple[str, int, int]:
    """작업 메모를 걷어내고 (본문, 지운 주석 수, 지운 인용줄 수) 를 돌려준다."""
    comments = len(re.findall(r"<!--.*?-->", text, flags=re.S))
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    lines = text.split("\n")
    kept = [l for l in lines if not l.startswith("> ")]
    quotes = len(lines) - len(kept)

    # 블록을 걷어낸 자리에 생긴 빈 줄 3개 이상은 2개로 정리
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip() + "\n"
    return body, comments, quotes


def main() -> int:
    if not SRC.exists():
        print(f"원본을 찾을 수 없습니다: {SRC}", file=sys.stderr)
        return 2

    body, comments, quotes = strip_working_notes(SRC.read_text(encoding="utf-8"))

    # --- 쓰기 전에 검사한다 ---
    leaked = [w for w in FORBIDDEN if w in body]
    if leaked:
        print(f"중단: 제출본에 작업 메모가 남았습니다 → {leaked} "
              f"({OUT.name} 미생성)", file=sys.stderr)
        return 1

    missing = [s for s in REQUIRED if s not in body]
    if missing:
        print(f"중단: 필수 섹션이 사라졌습니다 → {missing} "
              f"({OUT.name} 미생성)", file=sys.stderr)
        return 1

    OUT.write_text(body, encoding="utf-8")

    src_lines = SRC.read_text(encoding="utf-8").count("\n") + 1
    out_lines = body.count("\n")
    print(f"생성 완료: {OUT.name} ({out_lines}줄, 원본 {src_lines}줄)")
    print(f"제거: 작성 메모 블록 {comments}개 · 상단 작업 노트 {quotes}줄")
    print("주의: 연봉·전화번호·주소가 포함된 전체판입니다. 저장소에 올리지 마세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
