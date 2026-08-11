#!/usr/bin/env python3
"""
공개용 스크린샷에서 가릴 영역을 모자이크 처리한다.

    python3 mask_image.py              # MASKS 에 정의된 것 전부 다시 처리
    python3 mask_image.py prompt-list  # 파일명(확장자 제외)으로 하나만

── 동작 ──────────────────────────────────────────────────────────────
원본을 portfolio/_originals/<슬러그>/ 에 백업하고(portfolio/ 는 .gitignore 이므로
원본은 공개되지 않는다), **항상 백업본에서 다시 시작해** assets/works/ 에 덮어쓴다.
여러 번 돌려도 모자이크가 겹쳐 쌓이지 않고, 좌표를 고쳐 다시 돌릴 수 있다.

── 좌표 잡는 법 ──────────────────────────────────────────────────────
좌표는 원본 픽셀 기준 (x0, y0, x1, y1) 이다. 새 이미지의 좌표를 찾으려면
격자를 씌운 사본을 만들어 눈으로 읽는 것이 가장 빠르다:

    python3 mask_image.py --grid prompt-list    # _originals 옆에 grid_*.png 생성

좌표를 MASKS 에 넣고 다시 돌린 뒤, 확대해서 판독 불가인지 반드시 확인할 것.
"""

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
IMG_DIR = ROOT / "assets" / "works"
BACKUP_DIR = ROOT / "portfolio" / "_originals"

BLOCK = 7          # 모자이크 한 칸의 픽셀 크기. 본문 글자(20px 내외)는 7이면 판독 불가.

# {슬러그/파일명: [(x0, y0, x1, y1), ...]}
# 주석에 '무엇을' 가리는지 남길 것 — 나중에 왜 가렸는지 알 수 없으면 유지가 안 된다.
MASKS = {
    "prompt-ops/prompt-list.jpeg": [
        # 사내 모델 별칭만 가린다. 상용 모델명(Claude·Gemini)과 프로바이더 배지는
        # 이력서 본문에 이미 공개돼 있으므로 그대로 둔다.
        (338, 154, 394, 180),     # weave — 모델명
        (848, 154, 1002, 180),    # WEAVE/WEAVE1.0 — 프롬프트 배지 값
        (1122, 154, 1228, 180),   # weave/weave1.0 — 모델 ID
        (338, 443, 392, 469),     # Spark — 모델명
        (314, 811, 444, 838),     # weave/weave1.0 — 프롬프트 목록
        (1126, 1147, 1198, 1176), # weave · vllm — compression 드롭다운
        (1126, 1213, 1198, 1242), # weave · vllm — summary 드롭다운
    ],
    # 프롬프트 본문은 전부 가린다 — 프로덕션 안전 프롬프트(미성년 보호 규칙과
    # 탐지 예시)와 세계관·출력 규칙이 그대로 찍혀 있다. 사내 자산이므로 공개 불가.
    # 패널 테두리·줄 수·버전 트리·diff 색 밴드는 남겨 화면의 기능은 그대로 보이게 한다.
    "prompt-ops/branch-tree.jpeg": [
        (208, 12, 322, 34),       # weave/weave1.0 — 브레드크럼
        (12, 106, 120, 128),      # weave/weave1.0 — 헤더
        (30, 284, 700, 800),      # 프롬프트 본문 — 대화·일반
        (718, 284, 1388, 800),    # 프롬프트 본문 — 대화·성인
        (30, 841, 700, 1278),     # 프롬프트 본문 — 소설·일반
        (718, 841, 1388, 1278),   # 프롬프트 본문 — 소설·성인
    ],
    "prompt-ops/section-diff.jpeg": [
        (46, 70, 908, 742),       # diff 본문 전체 (좌측 +/- 거터는 남긴다)
    ],
}


def backup_path(rel: str) -> Path:
    return BACKUP_DIR / rel


def ensure_backup(rel: str) -> Path:
    """원본을 비공개 폴더에 한 번만 복사하고 그 경로를 준다."""
    src, bak = IMG_DIR / rel, backup_path(rel)
    if not src.exists() and not bak.exists():
        sys.exit(f"중단: 이미지가 없습니다 → assets/works/{rel}")
    if not bak.exists():
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, bak)
        print(f"  원본 백업 → portfolio/_originals/{rel}")
    return bak


def pixelate(im: Image.Image, box) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        sys.exit(f"중단: 잘못된 영역 {box}")
    if x1 > im.width or y1 > im.height:
        sys.exit(f"중단: 영역이 이미지 밖입니다 {box} (이미지 {im.size})")
    small = im.crop(box).resize((max(1, w // BLOCK), max(1, h // BLOCK)), Image.BILINEAR)
    im.paste(small.resize((w, h), Image.NEAREST), box)


def apply(rel: str) -> None:
    bak = ensure_backup(rel)
    out = IMG_DIR / rel
    im = Image.open(bak).convert("RGB")        # 항상 원본에서 — 이중 처리 방지
    for box in MASKS[rel]:
        pixelate(im, box)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=92, optimize=True, progressive=True)
    print(f"  {rel}: {len(MASKS[rel])}곳 처리 ({out.stat().st_size:,} bytes)")


def write_grid(rel: str) -> None:
    """좌표를 눈으로 읽기 위한 격자 사본. 원본 픽셀 좌표를 눈금에 적는다."""
    im = Image.open(ensure_backup(rel)).convert("RGB")
    d = ImageDraw.Draw(im)
    for x in range(0, im.width, 50):
        d.line([(x, 0), (x, im.height)], fill=(255, 0, 0))
        d.text((x + 2, 2), str(x), fill=(255, 0, 0))
    for y in range(0, im.height, 50):
        d.line([(0, y), (im.width, y)], fill=(0, 110, 255))
        d.text((2, y + 1), str(y), fill=(0, 80, 255))
    out = backup_path(rel).with_name(f"grid_{Path(rel).name}")
    im.save(out)
    print(f"  격자 → {out.relative_to(ROOT)}")


def main() -> None:
    args = sys.argv[1:]
    grid = "--grid" in args
    names = [a for a in args if not a.startswith("-")]

    targets = [r for r in MASKS if not names or Path(r).stem in names or r in names]
    if names and not targets:
        sys.exit(f"중단: MASKS 에 없는 대상입니다 → {names}\n"
                 f"등록된 것: {sorted(Path(r).stem for r in MASKS)}")

    for rel in targets:
        print(f"{rel}")
        write_grid(rel) if grid else apply(rel)

    if not grid:
        print("\n※ 확대해서 판독 불가인지 눈으로 확인하세요. 모자이크는 되돌릴 수 없지만,\n"
              "  원본이 portfolio/_originals/ 에 있으므로 좌표를 고쳐 다시 돌릴 수 있습니다.")


if __name__ == "__main__":
    main()
