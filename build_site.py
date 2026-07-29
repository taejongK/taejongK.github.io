#!/usr/bin/env python3
"""
resume.md (비공개 전체판) → index.html (공개 사이트) 생성기.

resume.md 가 유일한 원본이다. 이 스크립트는 거기서 공개해도 되는 내용만
골라내 정적 사이트를 만든다. index.html 을 직접 고치지 말 것 — 다음 빌드에
덮어써진다. 내용을 바꾸려면 resume.md 를 고치고 다시 실행한다.

    python3 build_site.py

공개 시 제외되는 항목은 REDACT_FIELDS 에 정의돼 있다.
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "resume.md"
OUT = ROOT / "index.html"

# ── 공개판에서 제외할 항목 ────────────────────────────────────────────
# 회사별 메타 중 아래 키는 사이트에 싣지 않는다.
REDACT_FIELDS = {"연봉", "이직사유"}

# 사이트 카피 (이력서 본문이 아니라 편집 문구이므로 여기서 관리한다)
GREETING = "안녕하세요. 김태종입니다."
TAGLINE = "LLM 기반 AI 서비스를 기획부터 배포까지 만듭니다."

# 상단 네비 우측 링크. (라벨, URL) — 블로그·LinkedIn 이 생기면 여기 추가.
NAV_LINKS = [
    ("GitHub", "https://github.com/taejongK"),
]


# ── 인라인 마크다운 ───────────────────────────────────────────────────
def inline(text: str) -> str:
    """**굵게**, `코드`, [링크](url), 맨 URL 을 HTML 로."""
    out = html.escape(text)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                 r'<a href="\2" target="_blank" rel="noopener">\1</a>', out)
    out = re.sub(r"(?<!href=\")(?<!>)(https?://[^\s<)]+)",
                 r'<a href="\1" target="_blank" rel="noopener">\1</a>', out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    return out


def slug(text: str) -> str:
    """헤딩 앵커용 id. 한글은 그대로 두고 공백만 하이픈으로."""
    s = re.sub(r"[^\w가-힣\s-]", "", text).strip()
    return re.sub(r"\s+", "-", s).lower()


def heading(level: int, text_html: str, anchor: str = "") -> str:
    """앵커(#) 링크가 붙는 헤딩. 레퍼런스의 hash-link 동작을 그대로 따른다."""
    sid = slug(anchor or re.sub(r"<[^>]+>", "", text_html))
    return (f'<h{level} id="{sid}">{text_html}'
            f'<a class="hash-link" href="#{sid}" aria-label="이 항목으로 바로가기"'
            f' title="이 항목으로 바로가기">#</a></h{level}>')


def period(text: str) -> str:
    """'2025.06–현재' → '2025.06 ~ 현재'. 레퍼런스의 물결 표기를 따른다."""
    return re.sub(r"\s*[–—-]\s*", " ~ ", text.strip())


def duration(text: str) -> str:
    """'0년 6개월' → '6개월'. docx 양식 표기를 웹에서만 다듬는다."""
    return re.sub(r"^0년\s*", "", text.strip())


def trim_address(addr: str) -> str:
    """공개판 주소는 동/읍/면 까지만. 그 뒤 상세주소는 버린다."""
    tokens = addr.split()
    for i, tok in enumerate(tokens):
        if re.search(r"[동읍면리가]\d*$", tok):
            return " ".join(tokens[:i + 1])
    return addr


# ── 파싱 ──────────────────────────────────────────────────────────────
class Bullet:
    __slots__ = ("level", "text", "children")

    def __init__(self, level, text):
        self.level = level
        self.text = text
        self.children = []


def parse_bullets(lines):
    """들여쓰기 2칸 = 1단계인 불릿 목록을 트리로."""
    roots, stack = [], []
    for raw in lines:
        m = re.match(r"^( *)- (.*)$", raw)
        if not m:
            continue
        level = len(m.group(1)) // 2
        node = Bullet(level, m.group(2).strip())
        while stack and stack[-1].level >= level:
            stack.pop()
        (stack[-1].children if stack else roots).append(node)
        stack.append(node)
    return roots


def split_kv(text):
    """'기간: 2026.02–2026.03' → ('기간', '2026.02–2026.03'). 없으면 (None, text)."""
    m = re.match(r"^\*{0,2}([^:*]{1,12})\*{0,2}:\s*(.*)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, text


def load_document():
    text = SRC.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)          # 작성 메모 제거
    lines = [l for l in text.split("\n") if not l.startswith("> ")]

    sections, current = [], None
    for line in lines:
        m = re.match(r"^(#{1,3}) (.+)$", line)
        if m:
            current = {"level": len(m.group(1)), "title": m.group(2).strip(), "lines": []}
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)
    return sections


def find(sections, title):
    for s in sections:
        if s["title"] == title:
            return s
    return None


def split_period(title):
    """'(주)버블탭, AI코어팀　　2025.06–현재 (1년 2개월)' 를 분해."""
    head, _, tail = title.partition("　")
    tail = tail.strip("　 ").strip()
    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", tail)
    when, dur = (m.group(1), m.group(2)) if m else (tail, "")
    return head.strip(), period(when), duration(dur)


# ── 렌더링 ────────────────────────────────────────────────────────────
def render_header(sections):
    profile = {}
    sec = find(sections, "개인신상")
    for b in parse_bullets(sec["lines"]):
        k, v = split_kv(b.text)
        if k:
            profile[re.sub(r"\s+", "", k)] = v

    summary = [l.strip() for l in sec["lines"]
               if l.strip() and not l.strip().startswith("-") and l.strip() != "---"]

    nav = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener">{html.escape(label)}</a></li>'
        for label, url in NAV_LINKS)

    contacts = []
    if profile.get("이메일"):
        contacts.append(("이메일", f'mailto:{profile["이메일"]}', profile["이메일"]))
    if profile.get("전화번호"):
        contacts.append(("연락처", f'tel:{profile["전화번호"].replace("-", "")}',
                         profile["전화번호"]))
    if profile.get("Github"):
        contacts.append(("GitHub", profile["Github"],
                         profile["Github"].replace("https://", "")))
    meta = []
    if profile.get("생년월일"):
        meta.append(("생년월일", profile["생년월일"]))
    if profile.get("주소"):
        meta.append(("주소", trim_address(profile["주소"])))

    rows = "".join(
        f'<li><span class="k">{html.escape(k)}</span>'
        f'<a href="{href}">{html.escape(v)}</a></li>' for k, href, v in contacts)
    rows += "".join(
        f'<li><span class="k">{html.escape(k)}</span>'
        f'<span class="v">{html.escape(v)}</span></li>' for k, v in meta)

    return f"""
<nav class="navbar">
  <div class="navbar-inner">
    <a class="navbar-brand" href="#top">@taejongK</a>
    <ul class="navbar-links">
      <li><a href="#업무-경력">경력</a></li>
      <li><a href="#그-외-경력">프로젝트</a></li>
      {nav}
    </ul>
  </div>
</nav>

<article class="doc" id="top">
  <h1>{html.escape(GREETING)}</h1>
  <p class="tagline">{html.escape(TAGLINE)}</p>
  <ul class="profile">{rows}</ul>
  <button type="button" class="print-btn" onclick="window.print()">PDF로 저장</button>

  {heading(2, "자기소개")}
  {"".join(f"<p>{inline(p)}</p>" for p in summary)}
"""


def render_tenure(sections):
    rows = []
    for b in parse_bullets(find(sections, "경력 사항 요약")["lines"]):
        when, _, org = b.text.partition(":")
        m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", when.strip())
        span, dur = (m.group(1), duration(m.group(2))) if m else (when.strip(), "")
        rows.append(f'<li>{inline(org.strip())} '
                    f'<span class="period">{html.escape(period(span))}'
                    f'{" · " + html.escape(dur) if dur else ""}</span></li>')
    return heading(2, "경력 요약") + f'<ul class="tenure">{"".join(rows)}</ul>'


def render_skills(sections):
    sec = find(sections, "핵심 기술 요약")
    groups, current = [], None
    for line in sec["lines"]:
        s = line.strip()
        cat = re.match(r"^\*\*\[(.+)\]\*\*$", s)
        if cat:
            current = {"name": cat.group(1), "items": []}
            groups.append(current)
        elif s.startswith("- ") and current is not None:
            current["items"].append(split_kv(s[2:]))

    out = heading(2, "핵심 기술")
    for g in groups:
        items = "".join(
            f"<li>{'<strong>' + html.escape(k) + '</strong> · ' if k else ''}"
            f"{inline(v)}</li>" for k, v in g["items"])
        out += heading(4, html.escape(g["name"])) + f"<ul>{items}</ul>"
    return out


def render_task(task: Bullet, level: int = 5) -> str:
    """수행업무 / 사이드 프로젝트 1건. 레퍼런스의 라벨 소제목 구조를 따른다."""
    when = link = outcome_text = stack = ""
    outcomes, roles = [], []

    for child in task.children:
        k, v = split_kv(child.text)
        if k == "기간":
            when = period(v)
        elif k == "링크":
            link = v
        elif k == "성과":
            if v:
                outcome_text = v
            outcomes += [c.text for c in child.children]
        elif k == "역할":
            roles += ([v] if v else []) + [c.text for c in child.children]
        elif k == "기술":
            stack = v
        else:
            roles.append(child.text)

    title = inline(task.text)
    if when:
        title += f' <span class="period">{html.escape(when)}</span>'
    out = heading(level, title, anchor=re.sub(r"<[^>]+>", "", inline(task.text)))

    if link:
        label = re.sub(r"^https?://", "", link.strip())
        out += (f'<p class="task-link"><a href="{html.escape(link.strip())}"'
                f' target="_blank" rel="noopener">{html.escape(label)}</a></p>')
    if outcome_text or outcomes:
        out += f'<h6 class="label">성과</h6>'
        if outcome_text:
            out += f"<p>{inline(outcome_text)}</p>"
        if outcomes:
            out += "<ul>" + "".join(f"<li>{inline(o)}</li>" for o in outcomes) + "</ul>"
    if roles:
        out += '<h6 class="label">역할</h6><ul>' + "".join(
            f"<li>{inline(r)}</li>" for r in roles) + "</ul>"
    if stack:
        out += f'<h6 class="label">사용 기술</h6><p class="stack">{html.escape(stack)}</p>'
    return out


def render_experience(sections):
    start = next(i for i, s in enumerate(sections) if s["title"] == "경력기술서")
    entries, side = [], None
    for sec in sections[start + 1:]:
        if sec["level"] != 3:
            continue
        if sec["title"] == "사이드 프로젝트":
            side = sec
        else:
            entries.append(sec)

    out = heading(2, "업무 경력")
    for sec in entries:
        head, when, dur = split_period(sec["title"])
        parts = [p.strip() for p in head.split(",")]
        company, team = parts[0], " / ".join(parts[1:])

        facts, tasks = [], []
        for b in parse_bullets(sec["lines"]):
            k, v = split_kv(b.text)
            if k and k in REDACT_FIELDS:
                continue
            if b.children:
                tasks.append(b)
            elif k:
                facts.append((k, v))

        dur_txt = f" · {dur}" if dur else ""
        out += heading(3, f'{html.escape(company)} '
                          f'<span class="period">{html.escape(when)}{html.escape(dur_txt)}</span>',
                       anchor=company)
        if team:
            out += f"<h4>{html.escape(team)}</h4>"
        if facts:
            out += '<ul class="facts">' + "".join(
                f"<li><strong>{html.escape(k)}</strong> · {inline(v)}</li>"
                for k, v in facts) + "</ul>"
        out += "".join(render_task(t) for t in tasks)

    if side:
        out += heading(2, "그 외 경력")
        out += "".join(render_task(p, level=3) for p in parse_bullets(side["lines"]))
    return out


def render_background(sections):
    out = heading(2, "학력 및 기타")
    for title in ("학력 사항", "교육이수 사항", "과외 활동", "병역 사항"):
        sec = find(sections, title)
        if not sec:
            continue
        items = "".join(f"<li>{inline(b.text)}</li>" for b in parse_bullets(sec["lines"]))
        out += heading(4, html.escape(title)) + f"<ul>{items}</ul>"
    return out


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>김태종 — AI Engineer</title>
<meta name="description" content="LLM 기반 AI 서비스를 기획부터 배포까지. 멀티 에이전트 오케스트레이션, RAG 파이프라인, LLMOps.">
<meta property="og:title" content="김태종 — AI Engineer">
<meta property="og:description" content="LLM 기반 AI 서비스를 기획부터 배포까지. 멀티 에이전트 오케스트레이션, RAG 파이프라인, LLMOps.">
<meta property="og:type" content="profile">
<meta name="color-scheme" content="light">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#9633;</text></svg>">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
__CONTENT__
  <footer class="doc-footer">
    <p>이 페이지는 <code>resume.md</code> 한 파일에서 생성됩니다.</p>
  </footer>
</article>
</body>
</html>
"""


def main():
    if not SRC.exists():
        sys.exit(f"원본을 찾을 수 없습니다: {SRC}")

    sections = load_document()
    content = (
        render_header(sections)
        + render_tenure(sections)
        + render_skills(sections)
        + render_experience(sections)
        + render_background(sections)
    )
    OUT.write_text(PAGE.replace("__CONTENT__", content), encoding="utf-8")

    published = OUT.read_text(encoding="utf-8")
    leaked = [w for w in ("연봉", "이직사유", "만원") if w in published]
    if leaked:
        sys.exit(f"중단: 공개판에 민감 항목이 남았습니다 → {leaked}")

    print(f"생성 완료: {OUT.relative_to(ROOT)} ({len(published):,} bytes)")
    print(f"제외된 항목: {', '.join(sorted(REDACT_FIELDS))}")


if __name__ == "__main__":
    main()
