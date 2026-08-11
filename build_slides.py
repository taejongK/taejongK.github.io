#!/usr/bin/env python3
"""
slides/deck.md → slides/portfolio.pdf (제출용 슬라이드 덱).

    python3 build_slides.py            # PDF 생성
    python3 build_slides.py --png      # 장별 PNG 도 함께 (검토용)
    python3 build_slides.py --check    # 검사만 하고 빌드하지 않음

── 원본 규율 ─────────────────────────────────────────────────────────
수치·기간의 기준은 resume.md 다. 덱은 거기서 압축할 뿐 새 수치를 만들지 않는다.
slides/ 는 통째로 .gitignore 대상 — 원본도 PDF 도 저장소에 올리지 않는다.

렌더링은 Marp CLI 를 npx 로 부른다(전역 설치 불필요, 최초 1회 다운로드).
이미지는 assets/works/ 의 마스킹본을 상대경로로 참조하므로 --allow-local-files 가 필요하다.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "slides" / "deck.md"
THEME = ROOT / "slides" / "theme.css"
OUT_PDF = ROOT / "slides" / "portfolio.pdf"

# ── 공개 전 차단 목록 ─────────────────────────────────────────────────
# 개인정보와 자격증명은 여기서 직접 막는다.
BANNED_WORDS = ["연봉", "이직사유", "만원"]      # 제출용에도 넣지 않는다
BANNED_PATTERNS = [
    (r"\bsk-[A-Za-z0-9_-]{16,}", "OpenAI 계열 API 키"),
    (r"\bAIza[A-Za-z0-9_-]{20,}", "Google API 키"),
    (r"\bghp_[A-Za-z0-9]{20,}", "GitHub 토큰"),
]

# 사내 문자열 목록은 portfolio/_guard.py(비공개)에서 읽는다.
# 여기에 직접 적으면 가려 놓은 이름이 이 파일을 통해 그대로 공개된다.
# 파일이 없으면 위의 개인정보·자격증명 가드만 동작한다.
try:
    sys.path.insert(0, str(ROOT / "portfolio"))
    import _guard                                    # type: ignore
    BANNED_WORDS += list(_guard.WORDS)
    BANNED_PATTERNS += list(_guard.PATTERNS)
    PRIVATE_GUARD = True
except ImportError:
    PRIVATE_GUARD = False

# 덱에 반드시 있어야 하는 것 — 실수로 통째로 날아가면 잡는다
REQUIRED = ("김태종", "AI Agent / LLM Engineer")


def read_source() -> str:
    if not SRC.exists():
        sys.exit(f"원본을 찾을 수 없습니다: {SRC}")
    return SRC.read_text(encoding="utf-8")


def audit(text: str) -> None:
    """검사를 먼저 한다. 통과하지 못하면 PDF 를 만들지 않는다."""
    # 작성 메모(<!-- -->)는 렌더 결과에 안 나가므로 검사에서 뺀다
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    hits = [w for w in BANNED_WORDS if w in body]
    hits += [why for pat, why in BANNED_PATTERNS if re.search(pat, body)]
    if hits:
        sys.exit(f"중단: 덱에 공개 불가 항목이 남았습니다 → {hits} (PDF 미생성)")

    missing = [r for r in REQUIRED if r not in body]
    if missing:
        sys.exit(f"중단: 필수 항목이 없습니다 → {missing} (PDF 미생성)")


def check_images(text: str) -> list:
    """참조한 이미지가 실제로 있는지 확인하고 목록을 준다."""
    missing, used = [], []
    for rel in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        p = (SRC.parent / rel).resolve()
        used.append(rel)
        if not p.exists():
            missing.append(rel)
    if missing:
        sys.exit(f"중단: 이미지를 찾을 수 없습니다 → {missing}")
    return used


def slide_count(text: str) -> int:
    """--- 구분자 기준 장수. front-matter 의 --- 두 개는 제외한다."""
    body = text.split("---", 2)[2] if text.startswith("---") else text
    return len(re.split(r"^---\s*$", body, flags=re.M))


def marp(args: list) -> None:
    if shutil.which("npx") is None:
        sys.exit("중단: npx 가 없습니다. Node.js 를 설치하세요.")
    cmd = ["npx", "--yes", "@marp-team/marp-cli@latest",
           str(SRC), "--theme", str(THEME), "--allow-local-files"] + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"중단: Marp 렌더 실패\n{r.stderr[-1500:]}")


def main() -> None:
    png = "--png" in sys.argv
    check_only = "--check" in sys.argv

    text = read_source()
    audit(text)                      # 쓰기 전에 검사
    used = check_images(text)
    n = slide_count(text)

    guard = "적용" if PRIVATE_GUARD else "미적용 — portfolio/_guard.py 없음(개인정보 가드만 동작)"
    print(f"검사 통과 — 슬라이드 {n}장 · 이미지 {len(used)}개 · 사내 문자열 가드 {guard}")
    for u in used:
        print(f"   · {u}")
    if check_only:
        return

    marp(["--pdf", "-o", str(OUT_PDF)])
    print(f"\n생성 완료: {OUT_PDF.relative_to(ROOT)} ({OUT_PDF.stat().st_size:,} bytes)")

    if png:
        marp(["--images", "png", "-o", str(SRC.parent / "png" / "slide.png")])
        pngs = sorted((SRC.parent / "png").glob("*.png"))
        print(f"검토용 PNG {len(pngs)}장: slides/png/")

    print("\n※ slides/ 는 .gitignore 대상입니다 — 저장소에 올라가지 않습니다.")


if __name__ == "__main__":
    main()
