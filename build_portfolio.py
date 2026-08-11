#!/usr/bin/env python3
"""
portfolio/<slug>.md (비공개 원본) → works/<slug>.html (공개 상세 페이지) 생성기.

이력서(index.html)가 "무엇을 했는가"를 요약한다면 이 페이지들은 "어떻게 했는가"를
아키텍처·의사결정 수준까지 펼친다. index.html 의 해당 프로젝트에서 링크된다.

    python3 build_portfolio.py

── 원본 규율 ─────────────────────────────────────────────────────────
수치·기간·귀속의 기준은 언제나 resume.md 다. portfolio/*.md 는 거기에 없는
아키텍처 다이어그램과 기술 의사결정 서술만 덧붙인다. 두 문서가 충돌하면
resume.md 가 옳다 (projects/*/overview.md 는 2026.08.01 정정 이전 값이 남아 있어
그대로 옮기면 안 된다 — 만족도 87%→86%, 로그 필드 35개→25개 등).

렌더링 함수는 build_site.py 를 그대로 가져다 쓴다. 이력서와 상세 페이지의
타이포·칩·앵커 동작을 한 곳에서 관리하기 위함이다.
"""

import html
import re
import sys
from datetime import date
from pathlib import Path

from build_site import (
    DETAIL_PAGES, build_toc, chips, heading, inline, period, slug, split_kv,
)

ROOT = Path(__file__).parent
SRC_DIR = ROOT / "portfolio"
OUT_DIR = ROOT / "works"

# 이미지는 여기에 프로젝트별로 넣는다. works/ 는 생성물이라 통째로 지워질 수 있으므로
# 손으로 넣는 파일은 절대 그 아래에 두지 않는다.
#     portfolio/character-agent.md 의  ![캡션](router-ui.png)
#         → assets/works/character-agent/router-ui.png
IMG_DIR = ROOT / "assets" / "works"

# 메타 불릿에서 뽑아내는 키. 이 순서대로 헤더에 나열된다.
META_KEYS = ("기간", "소속", "역할", "링크")

# 공개 전 차단 목록.
# 앞의 셋은 build_site.py 와 동일한 개인정보 가드, 나머지는 프로젝트 소스에서
# 문장이 딸려 올 때를 대비한 시크릿·내부 데이터 가드다.
BANNED_WORDS = ["연봉", "이직사유", "만원"]
BANNED_PATTERNS = [
    (r"\bsk-[A-Za-z0-9_-]{16,}", "OpenAI 계열 API 키"),
    (r"\bAIza[A-Za-z0-9_-]{20,}", "Google API 키"),
    (r"\bghp_[A-Za-z0-9]{20,}", "GitHub 토큰"),
    (r"\bsk-or-v1-[A-Za-z0-9]{16,}", "OpenRouter 키"),
]

# 사내 문자열 목록은 portfolio/_guard.py(비공개)에서 읽는다.
# 여기에 직접 적으면 가려 놓은 이름이 이 파일을 통해 그대로 공개된다.
# 파일이 없으면 위의 개인정보·자격증명 가드만 동작한다.
try:
    sys.path.insert(0, str(SRC_DIR))
    import _guard                                    # type: ignore
    BANNED_WORDS += list(_guard.WORDS)
    BANNED_PATTERNS += list(_guard.PATTERNS)
except ImportError:
    pass


# ── 파싱 ──────────────────────────────────────────────────────────────
def parse_blocks(lines):
    """마크다운 본문을 (종류, 값) 블록 리스트로 나눈다.

    종류: h2 / h3 / code / ul / p
    불릿은 들여쓰기 2칸을 1단계로 보는 build_site.parse_bullets 규칙과 같다.
    """
    blocks, buf, fence = [], [], None

    def flush_para():
        if buf:
            blocks.append(("p", " ".join(buf)))
            buf.clear()

    def flush_list(items):
        if items:
            blocks.append(("ul", items))

    items = []
    for raw in lines:
        line = raw.rstrip()

        if fence is not None:                      # 코드 펜스 안
            if line.strip().startswith("```"):
                blocks.append(("code", "\n".join(fence)))
                fence = None
            else:
                fence.append(raw)
            continue

        if line.strip().startswith("```"):
            flush_para(); flush_list(items); items = []
            fence = []
            continue

        # h4 까지 받는다. h2/h3 만 목차에 오르고 h4 는 본문 안에서만 쓰인다.
        m = re.match(r"^(#{2,4}) (.+)$", line)
        if m:
            flush_para(); flush_list(items); items = []
            blocks.append((f"h{len(m.group(1))}", m.group(2).strip()))
            continue

        # 한 줄 전체가 이미지인 경우만 그림으로 취급한다.
        # 문장 중간의 ![..](..) 는 inline() 이 처리하지 않으므로 쓰지 말 것.
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line.strip())
        if m:
            flush_para(); flush_list(items); items = []
            blocks.append(("img", (m.group(1).strip(), m.group(2).strip())))
            continue

        # 표. `|` 로 시작하는 줄이 이어지는 동안 한 덩어리로 모은다.
        if line.strip().startswith("|"):
            flush_para(); flush_list(items); items = []
            if blocks and blocks[-1][0] == "table":
                blocks[-1][1].append(line.strip())
            else:
                blocks.append(("table", [line.strip()]))
            continue

        m = re.match(r"^( *)- (.*)$", line)
        if m:
            flush_para()
            items.append((len(m.group(1)) // 2, m.group(2).strip()))
            continue

        # 불릿의 이어지는 줄. 들여쓴 채 '- ' 없이 시작하면 직전 항목에 붙인다.
        # 이걸 빼면 여러 줄로 쓴 불릿의 둘째 줄이 목록에서 떨어져 나와
        # 별개 문단으로 렌더된다.
        if items and line.strip() and line[:1].isspace():
            level, text = items[-1]
            items[-1] = (level, f"{text} {line.strip()}")
            continue

        if not line.strip():
            flush_para(); flush_list(items); items = []
            continue

        flush_list(items); items = []
        buf.append(line.strip())

    flush_para(); flush_list(items)
    if fence is not None:
        sys.exit("중단: 닫히지 않은 코드 펜스(```)가 있습니다.")
    return blocks


def load_page(path: Path):
    """제목 · 요약 · 메타 · 본문 블록으로 분해한다."""
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    lines = text.split("\n")

    title = ""
    lead, meta, body = [], {}, []
    seen_body = False

    for line in lines:
        s = line.strip()
        if not title:
            m = re.match(r"^# (.+)$", s)
            if m:
                title = m.group(1).strip()
            continue
        if s.startswith("## "):
            seen_body = True
        if seen_body:
            body.append(line)
            continue
        if s.startswith("> "):                      # 한 줄 요약
            lead.append(s[2:].strip())
        elif s.startswith("- "):                    # 메타 불릿
            k, v = split_kv(s[2:])
            if k:
                meta[k] = v

    if not title:
        sys.exit(f"중단: {path.name} 에 H1 제목이 없습니다.")
    return title, " ".join(lead), meta, parse_blocks(body)


# ── 렌더링 ────────────────────────────────────────────────────────────
def render_list(items):
    """(레벨, 텍스트) 평면 목록을 중첩 <ul> 로.

    하위 목록은 부모 <li> 안에 들어가야 하므로 먼저 트리로 세운 뒤 재귀 렌더링한다.
    build_site.parse_bullets 와 같은 규칙이되, 입력이 이미 (레벨, 텍스트) 라 별도로 둔다.
    """
    roots, stack = [], []
    for level, text in items:
        node = {"text": text, "children": []}
        while stack and stack[-1][0] >= level:
            stack.pop()
        (stack[-1][1]["children"] if stack else roots).append(node)
        stack.append((level, node))

    def render(nodes):
        out = "<ul>"
        for n in nodes:
            out += f"<li>{inline(n['text'])}"
            if n["children"]:
                out += render(n["children"])
            out += "</li>"
        return out + "</ul>"

    return render(roots) if roots else ""


def render_figure(caption: str, filename: str, name: str, pending: list) -> str:
    """이미지 한 장. 파일이 아직 없으면 '여기에 넣으세요' 자리로 렌더한다.

    자리 표시는 공개 사이트에도 그대로 보인다. 이미지를 넣기 전에 배포하면
    빈 자리가 드러나므로, 빌드가 남은 자리를 목록으로 알려준다.
    """
    rel = f"{name}/{filename}"
    exists = (IMG_DIR / name / filename).exists()
    cap = f"<figcaption>{inline(caption)}</figcaption>" if caption else ""

    if not exists:
        pending.append(f"assets/works/{rel}")
        hint = (f'<span class="figure-slot-hint">{html.escape(caption)}</span>'
                if caption else "")
        return (f'<figure class="figure figure-empty">'
                f'<div class="figure-slot">'
                f'<span class="figure-slot-tag">이미지 자리</span>'
                f'<code>assets/works/{html.escape(rel)}</code>'
                f'{hint}</div>{cap}</figure>')

    return (f'<figure class="figure">'
            f'<img src="../assets/works/{html.escape(rel)}"'
            f' alt="{html.escape(caption)}" loading="lazy">'
            f'{cap}</figure>')


def render_table(rows: list) -> str:
    """마크다운 표 → <table>. 넓은 표는 자기 박스 안에서만 가로 스크롤한다.

    둘째 줄이 `|---|---|` 형태의 구분선이면 첫 줄을 헤더로 본다.
    구분선이 없으면 헤더 없이 본문만 렌더한다.
    """
    def cells(row: str) -> list:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    head, body = [], rows
    if len(rows) >= 2 and re.fullmatch(r"\|[\s:|-]+\|", rows[1]):
        head, body = cells(rows[0]), rows[2:]

    out = '<div class="table-wrap"><table>'
    if head:
        out += "<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>"
    out += "<tbody>"
    for row in body:
        out += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells(row)) + "</tr>"
    return out + "</tbody></table></div>"


def render_body(blocks, name: str, pending: list):
    out = ""
    for kind, value in blocks:
        if kind in ("h2", "h3", "h4"):
            out += heading(int(kind[1]), inline(value), anchor=value)
        elif kind == "code":
            out += f'<pre class="diagram">{html.escape(value)}</pre>'
        elif kind == "ul":
            out += render_list(value)
        elif kind == "table":
            out += render_table(value)
        elif kind == "img":
            out += render_figure(value[0], value[1], name, pending)
        else:
            out += f"<p>{inline(value)}</p>"
    return out


def render_meta(meta):
    rows = ""
    for k in META_KEYS:
        v = meta.get(k)
        if not v:
            continue
        if k == "기간":
            v_html = html.escape(period(v))
        elif k == "링크":
            url = v.strip()
            label = re.sub(r"^https?://", "", url)
            v_html = (f'<a href="{html.escape(url)}" target="_blank"'
                      f' rel="noopener">{html.escape(label)}</a>')
        else:
            v_html = inline(v)
        rows += (f'<li><span class="k">{html.escape(k)}</span>'
                 f'<span class="v">{v_html}</span></li>')
    return f'<ul class="detail-meta">{rows}</ul>' if rows else ""


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ — 김태종</title>
<meta name="description" content="__LEAD__">
<meta property="og:title" content="__TITLE__ — 김태종">
<meta property="og:description" content="__LEAD__">
<meta property="og:type" content="article">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#bbe2fb">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect x='12' y='12' width='76' height='76' rx='16' fill='%23bbe2fb'/><text x='50' y='50' font-size='52' font-family='sans-serif' font-weight='700' fill='%231b6fa8' text-anchor='middle' dominant-baseline='central'>TJ</text></svg>">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<nav class="navbar">
  <div class="navbar-inner">
    <a class="navbar-brand" href="../index.html">@taejongK</a>
    <ul class="navbar-links">
      <li><a href="../index.html#업무-경력">경력</a></li>
      <li><a href="../index.html#그-외-경력">프로젝트</a></li>
      <li><a href="https://github.com/taejongK" target="_blank" rel="noopener">GitHub</a></li>
    </ul>
  </div>
</nav>

<div class="page">
<article class="doc doc-detail" id="top">
  <a class="back-link" href="../index.html#__BACK_ANCHOR__">← 이력서로 돌아가기</a>
  <h1>__TITLE__</h1>
  __LEAD_HTML__
  __META__
  __STACK__
__CONTENT__
  <footer class="doc-footer">
    <p>최종 수정 __UPDATED__ · 요약은 <a href="../index.html#__BACK_ANCHOR__">이력서</a>에 있습니다.</p>
  </footer>
</article>
__TOC__
</div>
</body>
</html>
"""


def build_page(src: Path, back_anchor: str, name: str, pending: list) -> str:
    title, lead, meta, blocks = load_page(src)
    content = render_body(blocks, name, pending)

    stack = meta.get("사용 기술", "")
    stack_html = (f'<h6 class="label">사용 기술</h6><p class="stack">{chips(stack)}</p>'
                  if stack else "")

    return (PAGE
            .replace("__CONTENT__", content)
            .replace("__TOC__", build_toc(content))
            .replace("__LEAD_HTML__", f'<p class="lead">{inline(lead)}</p>' if lead else "")
            .replace("__META__", render_meta(meta))
            .replace("__STACK__", stack_html)
            .replace("__BACK_ANCHOR__", back_anchor)
            .replace("__UPDATED__", date.today().strftime("%Y.%m.%d"))
            # 제목·요약은 속성값으로도 들어가므로 마지막에, 이스케이프해서 치환한다.
            .replace("__TITLE__", html.escape(title))
            .replace("__LEAD__", html.escape(lead)))


def audit(name: str, page: str):
    """공개 차단 검사. 하나라도 걸리면 아무 파일도 쓰지 않고 중단한다."""
    hits = [w for w in BANNED_WORDS if w in page]
    hits += [why for pat, why in BANNED_PATTERNS if re.search(pat, page)]
    if hits:
        sys.exit(f"중단: {name} 에 공개 불가 항목이 남았습니다 → {hits} (works/ 미변경)")


def main():
    if not SRC_DIR.exists():
        sys.exit(f"원본 디렉터리를 찾을 수 없습니다: {SRC_DIR}")

    # 검사를 먼저 전부 돌리고, 통과한 뒤에 쓴다.
    # 쓰면서 검사하면 뒤쪽에서 걸려도 앞쪽 파일은 이미 디스크에 남는다.
    pages, missing, pending = [], [], []
    for resume_title, name in DETAIL_PAGES.items():
        src = SRC_DIR / f"{name}.md"
        if not src.exists():
            missing.append(src.name)
            continue
        page = build_page(src, slug(resume_title), name, pending)
        audit(src.name, page)
        pages.append((name, page))

    if missing:
        sys.exit(f"중단: 원본이 없습니다 → {missing} "
                 f"(build_site.py 의 DETAIL_PAGES 와 portfolio/ 가 어긋났습니다)")

    OUT_DIR.mkdir(exist_ok=True)
    for name, page in pages:
        (IMG_DIR / name).mkdir(parents=True, exist_ok=True)   # 이미지 넣을 자리
        out = OUT_DIR / f"{name}.html"
        out.write_text(page, encoding="utf-8")
        print(f"생성 완료: {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")

    print(f"\n{len(pages)}개 상세 페이지 생성. "
          f"index.html 의 링크를 갱신하려면 build_site.py 도 실행하세요.")

    if pending:
        print(f"\n※ 아직 비어 있는 이미지 자리 {len(pending)}개 "
              f"— 파일을 넣고 다시 빌드하면 자동으로 바뀝니다.")
        for p in pending:
            print(f"   · {p}")
        print("   (자리 표시는 공개 사이트에도 그대로 보입니다.\n"
              "    넣지 않을 자리는 portfolio/*.md 에서 해당 ![..](..) 줄을 지우세요.)")
        print("   ⚠ 스크린샷에 실제 유저 대화·개인정보·API 키가 찍히지 않았는지\n"
              "     직접 확인하세요 — 빌드 가드는 텍스트만 검사하며 이미지 안은 못 봅니다.")


if __name__ == "__main__":
    main()
