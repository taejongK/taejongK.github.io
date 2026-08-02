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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "resume.md"
OUT = ROOT / "index.html"

# ── 공개판에서 제외할 항목 ────────────────────────────────────────────
# 회사별 메타 중 아래 키는 사이트에 싣지 않는다.
REDACT_FIELDS = {"연봉", "이직사유"}

# 사이트 카피 (이력서 본문이 아니라 편집 문구이므로 여기서 관리한다)
GREETING = "안녕하세요. 김태종입니다."
TAGLINE = "\"좋아진 것 같다\"로는 배포하지 않습니다."

# 상단 네비 우측 링크. (라벨, URL) — 블로그·LinkedIn 이 생기면 여기 추가.
NAV_LINKS = [
    ("GitHub", "https://github.com/taejongK"),
]

# ── 프로필 사진 ───────────────────────────────────────────────────────
# 원본(인쇄용 고해상도)은 커밋하지 않고, 여기서 웹용 파생본만 만들어 공개한다.
# 사진을 빼려면 PHOTO_SRC 를 None 으로 두면 된다.
PHOTO_SRC = ROOT / "imgs" / "my_image.jpg"
PHOTO_OUT = ROOT / "assets" / "profile.jpg"
PHOTO_BOX = (440, 587)          # 파생본 픽셀 (화면 표시 220x293 의 2배)
# 원본에서 잘라낼 영역 비율 (좌, 상, 우, 하).
# 얼굴 중심(가로 0.507)에 맞춘 3:4 상반신 프레임 — 머리가 세로의 약 43% 를 차지한다.
PHOTO_CROP = (0.226, 0.10, 0.788, 0.60)


def build_photo():
    """원본에서 웹용 사진을 생성한다. 실패하면 사진 없이 진행한다."""
    if PHOTO_SRC is None or not PHOTO_SRC.exists():
        return None
    if PHOTO_OUT.exists() and PHOTO_OUT.stat().st_mtime >= PHOTO_SRC.stat().st_mtime:
        return PHOTO_OUT.name
    try:
        from PIL import Image
    except ImportError:
        print("  경고: Pillow 가 없어 사진을 갱신하지 못했습니다.")
        return PHOTO_OUT.name if PHOTO_OUT.exists() else None

    with Image.open(PHOTO_SRC) as im:
        w, h = im.size
        l, t, r, b = PHOTO_CROP
        im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
        im = im.resize(PHOTO_BOX, Image.LANCZOS)
        PHOTO_OUT.parent.mkdir(exist_ok=True)
        im.save(PHOTO_OUT, quality=86, optimize=True, progressive=True)
    print(f"  사진 생성: {PHOTO_OUT.name} "
          f"({PHOTO_SRC.stat().st_size / 1e6:.1f}MB → {PHOTO_OUT.stat().st_size / 1024:.0f}KB)")
    return PHOTO_OUT.name


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
    """'LangChain, FastAPI, React(Vite + TypeScript)' → 칩 span 나열.

    괄호 안의 쉼표는 항목 구분자가 아니므로 건너뛴다.
    """
    items = [t.strip() for t in re.split(r",\s*(?![^()]*\))", text) if t.strip()]
    return "".join(f'<span class="chip">{html.escape(t)}</span>' for t in items)


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


def fmt_months(n: int) -> str:
    """14 → '1년 2개월'."""
    y, m = divmod(max(n, 0), 12)
    return " ".join(p for p in (f"{y}년" if y else "", f"{m}개월" if m else "") if p) or "1개월 미만"


def parse_months(text: str) -> int:
    """'1년 2개월' → 14. 경력 총합 계산용."""
    y = re.search(r"(\d+)\s*년", text)
    m = re.search(r"(\d+)\s*개월", text)
    return (int(y.group(1)) * 12 if y else 0) + (int(m.group(1)) if m else 0)


def resolve_duration(when: str, dur: str) -> str:
    """재직 중인 회사의 기간은 빌드 시점 기준으로 다시 계산한다.

    resume.md 에 '1년 2개월' 처럼 적혀 있어도 시간이 지나면 틀린 값이 되므로,
    '~ 현재' / '~ 재직중' 으로 끝나는 기간만 오늘 날짜로 환산한다.
    재직 개월 수는 입사월과 당월을 모두 포함하는 국내 이력서 관례를 따른다.
    """
    m = re.match(r"^(\d{4})\.(\d{1,2})\s*~\s*(?:현재|재직\s*중)$", when.strip())
    if not m:
        return duration(dur)
    today = date.today()
    months = (today.year - int(m.group(1))) * 12 + (today.month - int(m.group(2))) + 1
    return fmt_months(months)


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
    when = period(when)
    return head.strip(), when, resolve_duration(when, dur)


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

    name = profile.get("성명", "김태종")
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

    photo = build_photo()
    photo_html = (
        f'<img class="masthead-photo" src="assets/{photo}" alt="{html.escape(name)}"'
        f' width="{PHOTO_BOX[0] // 2}" height="{PHOTO_BOX[1] // 2}">' if photo else "")

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

<div class="page">
<article class="doc" id="top">
  <div class="masthead-row">
    <div class="masthead-text">
      <h1>{html.escape(GREETING)}</h1>
      <p class="tagline">{html.escape(TAGLINE)}</p>
      <ul class="profile">{rows}</ul>
      <button type="button" class="print-btn" onclick="window.print()">PDF로 저장</button>
    </div>
    {photo_html}
  </div>

  {heading(2, "자기소개")}
  {"".join(f"<p>{inline(p)}</p>" for p in summary)}
"""


def render_tenure(sections):
    rows, total = [], 0
    for b in parse_bullets(find(sections, "경력 사항 요약")["lines"]):
        when, _, org = b.text.partition(":")
        m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", when.strip())
        span, raw = (m.group(1), m.group(2)) if m else (when.strip(), "")
        span = period(span)
        dur = resolve_duration(span, raw)
        total += parse_months(dur)
        rows.append(f'<li>{inline(org.strip())} '
                    f'<span class="period">{html.escape(span)}'
                    f'{" · " + html.escape(dur) if dur else ""}</span></li>')
    badge = (f' <span class="period">총 {html.escape(fmt_months(total))}</span>'
             if total else "")
    return (heading(2, "경력 요약" + badge, anchor="경력 요약")
            + f'<ul class="tenure">{"".join(rows)}</ul>')


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
        out += (f'<div class="skill-group">'
                + heading(4, html.escape(g["name"]))
                + f'<ul>{items}</ul></div>')
    return out


# 프로젝트 본문에 소제목으로 렌더링되는 라벨. resume.md 에 적힌 순서·표기 그대로 나간다.
# '문제 / 방법 / 결과' 가 현재 표준. 나머지는 구 문서 호환용이다.
CONTENT_LABELS = ("문제", "방법", "결과", "해결", "성과", "역할",
                  "Problem", "Methods", "Result")

# 기술 스택 라벨. resume.md 는 '사용 기술' 을 쓰고, 구 표기도 받는다.
STACK_LABELS = ("사용 기술", "기술", "Skills")


def render_task(task: Bullet, level: int = 5) -> str:
    """수행업무 / 사이드 프로젝트 1건. 레퍼런스의 라벨 소제목 구조를 따른다."""
    when = link = stack = ""
    stack_label = "사용 기술"
    blocks: list[tuple[str, str, list[str]]] = []   # (라벨, 본문, 하위 항목)

    for child in task.children:
        k, v = split_kv(child.text)
        if k == "기간":
            when = period(v)
        elif k == "링크":
            link = v
        elif k in STACK_LABELS:
            stack, stack_label = v, k
        elif k in CONTENT_LABELS:
            blocks.append((k, v, [c.text for c in child.children]))
        elif blocks:
            # 라벨 없는 줄은 직전 블록에 붙인다.
            blocks[-1][2].append(child.text)
        else:
            blocks.append(("", child.text, []))

    title_txt = re.sub(r"<[^>]+>", "", inline(task.text))
    aside = heading(level, inline(task.text), anchor=title_txt).replace(
        f'<h{level} id=', f'<h{level} class="task-title" id=')
    if when:
        aside += f'<p class="task-period">{html.escape(when)}</p>'

    main = ""
    if link:
        label = re.sub(r"^https?://", "", link.strip())
        main += (f'<p class="task-link"><a href="{html.escape(link.strip())}"'
                 f' target="_blank" rel="noopener">{html.escape(label)}</a></p>')
    for label, text, subs in blocks:
        if label:
            main += f'<h6 class="label">{html.escape(label)}</h6>'
        if text:
            main += f"<p>{inline(text)}</p>"
        if subs:
            main += "<ul>" + "".join(f"<li>{inline(s)}</li>" for s in subs) + "</ul>"
    if stack:
        main += (f'<h6 class="label">{html.escape(stack_label)}</h6>'
                 f'<p class="stack">{chips(stack)}</p>')

    return (f'<div class="task"><div class="task-aside">{aside}</div>'
            f'<div class="task-main">{main}</div></div>')


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
        out += "".join(render_task(p) for p in parse_bullets(side["lines"]))
    return out


def render_background(sections):
    out = heading(2, "학력 및 기타")
    for title in ("학력 사항", "교육이수 사항", "과외 활동", "병역 사항"):
        sec = find(sections, title)
        if not sec:
            continue
        items = "".join(f"<li>{inline(b.text)}</li>" for b in parse_bullets(sec["lines"]))
        out += (f'<div class="bg-group">'
                + heading(4, html.escape(title))
                + f'<ul>{items}</ul></div>')
    return out


def build_toc(content):
    """본문의 h2/h3 를 훑어 우측 목차를 만든다. 레퍼런스와 동일한 2단 위계."""
    items = []
    pat = r'<h([23]) id="([^"]+)">(.*?)<a class="hash-link"'
    for lv, sid, inner in re.findall(pat, content, re.S):
        text = re.sub(r'<span class="period">.*?</span>', "", inner, flags=re.S)
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            items.append(f'<li class="lv{lv}"><a href="#{sid}">{html.escape(text)}</a></li>')
    if not items:
        return ""
    return f'<nav class="toc" aria-label="\ubaa9\ucc28"><ul>{"".join(items)}</ul></nav>'


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>김태종 — AI Engineer</title>
<meta name="description" content="잴 수 없다고 여겨지는 것에 기준을 세우는 AI 엔지니어. LLM 평가 체계, 에이전트 아키텍처, LLMOps.">
<meta property="og:title" content="김태종 — AI Engineer">
<meta property="og:description" content="잴 수 없다고 여겨지는 것에 기준을 세우는 AI 엔지니어. LLM 평가 체계, 에이전트 아키텍처, LLMOps.">
<meta property="og:type" content="profile">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#bbe2fb">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect x='12' y='12' width='76' height='76' rx='16' fill='%23bbe2fb'/><text x='50' y='50' font-size='52' font-family='sans-serif' font-weight='700' fill='%231b6fa8' text-anchor='middle' dominant-baseline='central'>TJ</text></svg>">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
__CONTENT__
  <footer class="doc-footer">
    <p>최종 수정 __UPDATED__</p>
  </footer>
</article>
__TOC__
</div>
<script>
/* 로드 시점의 #앵커 이동 보정.
   웹폰트와 사진이 늦게 들어오면서 문서 높이가 바뀌면 브라우저가 처음 시도한
   프래그먼트 스크롤이 무산된다. 로드가 끝난 뒤 한 번 더 정확히 맞춰준다. */
(function () {
  function jump() {
    var id = decodeURIComponent((location.hash || "").slice(1));
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    var root = document.documentElement;
    var prev = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";   // 보정 이동은 애니메이션 없이
    el.scrollIntoView();
    root.style.scrollBehavior = prev;
  }
  window.addEventListener("load", function () { jump(); setTimeout(jump, 150); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(jump);
})();
</script>
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
    page = (PAGE.replace("__CONTENT__", content)
                .replace("__TOC__", build_toc(content))
                .replace("__UPDATED__", date.today().strftime("%Y.%m.%d")))
    # 검사를 먼저 한다. 쓰고 나서 검사하면 차단에 실패해도 민감 정보가 디스크에 남는다.
    leaked = [w for w in ("연봉", "이직사유", "만원") if w in page]
    if leaked:
        sys.exit(f"중단: 공개판에 민감 항목이 남았습니다 → {leaked} (index.html 미변경)")

    OUT.write_text(page, encoding="utf-8")
    published = OUT.read_text(encoding="utf-8")

    print(f"생성 완료: {OUT.relative_to(ROOT)} ({len(published):,} bytes)")
    print(f"제외된 항목: {', '.join(sorted(REDACT_FIELDS))}")


if __name__ == "__main__":
    main()
