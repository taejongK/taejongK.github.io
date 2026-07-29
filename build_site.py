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

# 마스트헤드에 들어갈 편집 문구. 이력서 본문이 아니라 사이트 카피이므로
# 여기서 직접 관리한다.
TAGLINE = "LLM 서비스를 기획부터 배포까지"
FOCUS = ["Multi-Agent Orchestration", "RAG Pipeline", "LLMOps"]


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


def chips(text: str) -> str:
    """'기술: A, B, C' 의 값을 칩 목록으로."""
    items = [t.strip() for t in text.split(",") if t.strip()]
    return "".join(f'<li>{html.escape(i)}</li>' for i in items)


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


# ── 렌더링 ────────────────────────────────────────────────────────────
def render_masthead(sections):
    profile = {}
    sec = find(sections, "개인신상")
    for b in parse_bullets(sec["lines"]):
        k, v = split_kv(b.text)
        if k:
            profile[re.sub(r"\s+", "", k)] = v

    # 개인신상 다음의 본문 단락 = 자기소개
    idx = sections.index(sec)
    summary = []
    for line in sections[idx]["lines"]:
        line = line.strip()
        if line and not line.startswith("-") and line != "---":
            summary.append(line)

    name = profile.get("성명", "")
    contacts = []
    if profile.get("이메일"):
        contacts.append(('메일', f'mailto:{profile["이메일"]}', profile["이메일"]))
    if profile.get("Github"):
        gh = profile["Github"]
        contacts.append(('GitHub', gh, gh.replace("https://", "")))
    if profile.get("전화번호"):
        contacts.append(('전화', f'tel:{profile["전화번호"].replace("-", "")}', profile["전화번호"]))

    focus = "".join(f"<li>{html.escape(f)}</li>" for f in FOCUS)
    links = "".join(
        f'<li><span class="contact-label">{lbl}</span>'
        f'<a href="{href}">{html.escape(txt)}</a></li>'
        for lbl, href, txt in contacts
    )
    facts = []
    if profile.get("생년월일"):
        facts.append(profile["생년월일"])
    if profile.get("주소"):
        facts.append(trim_address(profile["주소"]))

    return f"""
<header class="masthead">
  <p class="eyebrow">Resume</p>
  <h1>{html.escape(name)}</h1>
  <p class="role">AI Engineer</p>
  <p class="tagline">{html.escape(TAGLINE)}</p>
  <ul class="focus">{focus}</ul>
  <ul class="contact">{links}</ul>
  <p class="personal">{html.escape(" · ".join(facts))}</p>
  <button type="button" class="print-btn" onclick="window.print()">PDF로 저장</button>
</header>

<section class="intro" aria-label="소개">
  {"".join(f"<p>{inline(p)}</p>" for p in summary)}
</section>
"""


def render_tenure(sections):
    rows = []
    for b in parse_bullets(find(sections, "경력 사항 요약")["lines"]):
        period, _, org = b.text.partition(":")
        span = re.match(r"^(.*?)\s*\((.*?)\)\s*$", period.strip())
        when, dur = (span.group(1), span.group(2)) if span else (period.strip(), "")
        parts = [p.strip() for p in org.split("/")]
        company = parts[0] if parts else org.strip()
        rest = " · ".join(parts[1:])
        rows.append(f"""
      <li>
        <div class="rail"><time>{html.escape(when)}</time><span class="dur">{html.escape(dur)}</span></div>
        <div class="rail-body"><span class="org">{html.escape(company)}</span>
        <span class="org-sub">{html.escape(rest)}</span></div>
      </li>""")
    return f"""
<section id="tenure" aria-labelledby="tenure-h">
  <h2 id="tenure-h">경력</h2>
  <ol class="tenure">{"".join(rows)}</ol>
</section>
"""


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
            k, v = split_kv(s[2:])
            current["items"].append((k, v))

    blocks = []
    for g in groups:
        items = []
        for k, v in g["items"]:
            if k:
                items.append(f'<li><span class="skill-k">{html.escape(k)}</span>'
                             f'<span class="skill-v">{inline(v)}</span></li>')
            else:
                items.append(f'<li><span class="skill-v skill-solo">{inline(v)}</span></li>')
        blocks.append(f"""
      <div class="skill-group">
        <h3>{html.escape(g["name"])}</h3>
        <ul>{"".join(items)}</ul>
      </div>""")
    return f"""
<section id="skills" aria-labelledby="skills-h">
  <h2 id="skills-h">핵심 기술</h2>
  <div class="skills">{"".join(blocks)}</div>
</section>
"""


def render_task(task: Bullet, ordinal: str) -> str:
    """회사 내 개별 수행업무 / 사이드 프로젝트 1건."""
    period = outcome_text = stack = link = ""
    outcomes, roles = [], []

    for child in task.children:
        k, v = split_kv(child.text)
        if k == "기간":
            period = v
        elif k == "링크":
            link = v
        elif k == "성과":
            if v:
                outcome_text = v
            outcomes += [c.text for c in child.children]
        elif k == "역할":
            roles += [c.text for c in child.children]
            if v:
                roles.insert(0, v)
        elif k == "기술":
            stack = v
        else:
            roles.append(child.text)

    head = f'<h4>{inline(task.text)}</h4>'
    meta = []
    if period:
        meta.append(f'<span class="task-period">{html.escape(period)}</span>')
    if link:
        meta.append(f'<span class="task-link">{inline(link)}</span>')
    meta_html = f'<p class="task-meta">{"".join(meta)}</p>' if meta else ""

    body = ""
    if outcome_text:
        body += f'<p class="outcome">{inline(outcome_text)}</p>'
    if outcomes:
        body += '<ul class="outcome-list">' + "".join(
            f"<li>{inline(o)}</li>" for o in outcomes) + "</ul>"
    if roles:
        body += '<ul class="roles">' + "".join(
            f"<li>{inline(r)}</li>" for r in roles) + "</ul>"
    if stack:
        body += f'<ul class="stack">{chips(stack)}</ul>'

    return f"""
        <article class="task">
          <span class="task-ord" aria-hidden="true">{ordinal}</span>
          {head}{meta_html}{body}
        </article>"""


def render_experience(sections):
    start = next(i for i, s in enumerate(sections) if s["title"] == "경력기술서")
    entries, side = [], None
    for sec in sections[start + 1:]:
        if sec["level"] != 3:
            continue
        if sec["title"] == "사이드 프로젝트":
            side = sec
            continue
        entries.append(sec)

    blocks = []
    for sec in entries:
        head, _, period = sec["title"].partition("　")
        period = period.strip("　 ").strip()
        parts = [p.strip() for p in head.split(",")]
        company, rest = parts[0], " · ".join(parts[1:])

        bullets = parse_bullets(sec["lines"])
        facts, tasks = [], []
        for b in bullets:
            k, v = split_kv(b.text)
            if k and k in REDACT_FIELDS:
                continue
            if b.children:
                tasks.append(b)
            elif k:
                facts.append((k, v))

        fact_html = "".join(
            f"<div><dt>{html.escape(k)}</dt><dd>{inline(v)}</dd></div>" for k, v in facts)
        task_html = "".join(render_task(t, f"{i + 1:02d}") for i, t in enumerate(tasks))
        span = re.match(r"^(.*?)\s*\((.*?)\)\s*$", period)
        when, dur = (span.group(1), span.group(2)) if span else (period, "")

        blocks.append(f"""
      <article class="entry">
        <div class="rail">
          <time>{html.escape(when)}</time>
          <span class="dur">{html.escape(dur)}</span>
        </div>
        <div class="entry-body">
          <h3>{html.escape(company)}</h3>
          <p class="entry-sub">{html.escape(rest)}</p>
          <dl class="facts">{fact_html}</dl>
          <div class="tasks">{task_html}</div>
        </div>
      </article>""")

    out = f"""
<section id="experience" aria-labelledby="exp-h">
  <h2 id="exp-h">경력기술서</h2>
  <div class="entries">{"".join(blocks)}</div>
</section>
"""
    if side:
        projects = parse_bullets(side["lines"])
        out += f"""
<section id="projects" aria-labelledby="proj-h">
  <h2 id="proj-h">사이드 프로젝트</h2>
  <div class="projects">{"".join(
            render_task(p, f"{i + 1:02d}") for i, p in enumerate(projects))}</div>
</section>
"""
    return out


def render_background(sections):
    blocks = []
    for title in ("학력 사항", "교육이수 사항", "과외 활동", "병역 사항"):
        sec = find(sections, title)
        if not sec:
            continue
        items = [f"<li>{inline(b.text)}</li>" for b in parse_bullets(sec["lines"])]
        blocks.append(f"""
      <div class="bg-group">
        <h3>{html.escape(title)}</h3>
        <ul>{"".join(items)}</ul>
      </div>""")
    return f"""
<section id="background" aria-labelledby="bg-h">
  <h2 id="bg-h">학력 · 그 외</h2>
  <div class="background">{"".join(blocks)}</div>
</section>
"""


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
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#9634;</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<main class="sheet">
__CONTENT__
<footer class="colophon">
  <p>이 페이지는 <code>resume.md</code> 한 파일에서 생성됩니다.</p>
</footer>
</main>
</body>
</html>
"""


def main():
    if not SRC.exists():
        sys.exit(f"원본을 찾을 수 없습니다: {SRC}")

    sections = load_document()
    content = (
        render_masthead(sections)
        + render_tenure(sections)
        + render_skills(sections)
        + render_experience(sections)
        + render_background(sections)
    )
    OUT.write_text(PAGE.replace("__CONTENT__", content), encoding="utf-8")

    # 공개판에 민감 항목이 새어나가지 않았는지 확인
    published = OUT.read_text(encoding="utf-8")
    leaked = [w for w in ("연봉", "이직사유", "만원") if w in published]
    if leaked:
        sys.exit(f"중단: 공개판에 민감 항목이 남았습니다 → {leaked}")

    print(f"생성 완료: {OUT.relative_to(ROOT)} ({len(published):,} bytes)")
    print(f"제외된 항목: {', '.join(sorted(REDACT_FIELDS))}")


if __name__ == "__main__":
    main()
