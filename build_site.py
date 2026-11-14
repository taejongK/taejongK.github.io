#!/usr/bin/env python3
"""
resume.md (비공개 전체판) → index.html (공개 사이트) 생성기.

resume.md 가 유일한 원본이다. 이 스크립트는 거기서 공개해도 되는 내용만
골라내 정적 사이트를 만든다. index.html 을 직접 고치지 말 것. 다음 빌드에
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

# 쓰기 직전 검사에 쓰는 금칙어. 사내 문자열 목록은 portfolio/_guard.py(비공개)에서 읽는다.
# 여기에 직접 적으면 가려 놓은 이름이 이 파일을 통해 그대로 공개된다.
# build_portfolio.py 와 같은 목록을 보도록 통일 (2026.09.23).
BANNED_WORDS = ["연봉", "이직사유", "만원"]
try:
    sys.path.insert(0, str(ROOT / "portfolio"))
    import _guard                                    # type: ignore
    BANNED_WORDS += list(_guard.WORDS)
except ImportError:
    pass

# 사이트 카피 (이력서 본문이 아니라 편집 문구이므로 여기서 관리한다)
GREETING = "AI Engineer 김태종"
HERO_TITLE = "에이전트가 <em>무엇을 기억할지</em><br>설계하고, 평가로 증명합니다."   # HTML 허용
HERO_LEAD = "장기기억 · 검색 랭킹 · 에이전트 아키텍처 · LLM 평가"
# 히어로 아래 성과 요약. (회사, 문장) 최근순, HTML 허용.
# 내용·수치는 resume.md 자기소개의 경력 요약 문단에서 옮긴 것이다. 그 문단을 고치면 여기도 고친다.
HERO_RESULTS = [
    ("버블탭", "캐릭터 챗봇(DAU 3,000, 일 30만 챗)의 LLM 레이어 담당. 장기기억 커스텀 검색 "
               "<strong>Precision@3 48%</strong>(장기 대화 <strong>68%</strong>), 유해 콘텐츠 차단 "
               "<strong>F1 18% → 87%</strong>, 월 15만 질의 검색 랭킹 개선안 설계·검증"),
    ("브릭", "<strong>사내 첫 LLM 적용 사례</strong>를 만들어 사업화 검토의 근거 제공"),
    ("알고리고", "압력 센서 졸음 탐지 모델로 <strong>현장 관리 인력을 절반</strong>으로 절감"),
]
# 위 요약으로 옮겨 간 문단의 첫머리. About 에서는 중복이라 뺀다.
ABOUT_MOVED = "알고리고에서는"

# ── 프로젝트 상세 페이지 ──────────────────────────────────────────────
# {resume.md 의 수행업무 제목: 슬러그}
# 슬러그는 원본 portfolio/<슬러그>.md 와 산출물 works/<슬러그>.html 양쪽에 쓰인다.
# 여기 추가하면 이력서에 "상세 보기" 링크가 붙고, build_portfolio.py 가 원본을 요구한다.
# build_portfolio.py 가 이 상수를 import 하므로 두 스크립트의 목록이 어긋날 수 없다.
#
# 산출물이 works/ 인 이유: projects/ 는 .gitignore 전체 차단 대상이라
# 그 아래 HTML 을 두면 GitHub Pages 에 배포되지 않는다.
DETAIL_PAGES = {
    "Chat Arena 개발 (사람 블라인드 투표 기반 모델·프롬프트 비교)": "chat-arena",
    "검색 랭킹 개선안 설계 및 평가 체계 구축": "search-ranking",
    "챗봇 장기기억 구조 설계 및 커스텀 기억 검색(RRF) 적용": "long-term-memory",
    "캐릭터 제작 에이전트 개발 (멀티 에이전트)": "character-agent",
    "프롬프트 관리 툴 개발 (사내 LLMOps)": "prompt-ops",
    "자체 서빙 모델 콘텐츠 필터 개발 (CoT 기반)": "content-filter",
}
DETAIL_DIR = "works"

# 상단 네비 우측 링크. (라벨, URL). 블로그·LinkedIn 이 생기면 여기 추가.
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
# 얼굴 중심(가로 0.507)에 맞춘 3:4 상반신 프레임. 머리가 세로의 약 43% 를 차지한다.
PHOTO_CROP = (0.226, 0.10, 0.788, 0.60)


def build_photo():
    """원본에서 웹용 사진을 생성한다. 실패하면 사진 없이 진행한다."""
    if PHOTO_SRC is None:
        return None
    if not PHOTO_SRC.exists():
        # 원본은 비공개라 클론에는 없다. 커밋된 웹용 파생본을 그대로 쓴다.
        return PHOTO_OUT.name if PHOTO_OUT.exists() else None
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
    return re.sub(r"\s*[–\u2014-]\s*", " ~ ", text.strip())


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
# 한 페이지 회사 소개서 구성: 히어로 → 01 About → 02 History → 03 Capabilities
# → 04 Works → 05 Contact. 섹션 id 는 영문이라 링크가 짧고 안정적이다.

# 총 경력 합산에서 빼는 직위. 목록에는 그대로 남긴다. 기록은 유지하고 합산만 제외
# (resume.md 작성 메모 24번).
EXCLUDED_FROM_TOTAL = ("인턴", "프리랜서")

# 프로젝트 본문에 소제목으로 렌더링되는 라벨. resume.md 에 적힌 순서·표기 그대로 나간다.
# '문제 / 방법 / 결과' 가 현재 표준. 나머지는 구 문서 호환용이다.
CONTENT_LABELS = ("문제", "방법", "결과", "해결", "성과", "역할",
                  "Problem", "Methods", "Result")
RESULT_LABELS = ("결과", "성과", "Result")

# 기술 스택 라벨. resume.md 는 '사용 기술' 을 쓰고, 구 표기도 받는다.
STACK_LABELS = ("사용 기술", "기술", "Skills")


def section_head(num: str, sid: str, eyebrow: str, title: str) -> str:
    """'01 / About' 머리말 + 큰 제목."""
    return (f'<header class="sec-head"><p class="eyebrow"><span class="num">{num}</span>'
            f' / {html.escape(eyebrow)}</p><h2 id="{sid}">{title}</h2></header>')


def load_profile(sections):
    sec = find(sections, "개인신상")
    profile = {}
    for b in parse_bullets(sec["lines"]):
        k, v = split_kv(b.text)
        if k:
            profile[re.sub(r"\s+", "", k)] = v
    paras = [l.strip() for l in sec["lines"]
             if l.strip() and not l.strip().startswith("-") and l.strip() != "---"]
    return profile, paras


def load_experience(sections):
    """경력기술서 → [{company, team, when, dur, facts{}, tasks[]}], 사이드 프로젝트 tasks."""
    start = next(i for i, s in enumerate(sections) if s["title"] == "경력기술서")
    companies, side = [], []
    for sec in sections[start + 1:]:
        if sec["level"] != 3:
            continue
        if sec["title"] == "사이드 프로젝트":
            side = parse_bullets(sec["lines"])
            continue
        head, when, dur = split_period(sec["title"])
        parts = [p.strip() for p in head.split(",")]
        facts, tasks = {}, []
        for b in parse_bullets(sec["lines"]):
            k, v = split_kv(b.text)
            if k and k in REDACT_FIELDS:
                continue
            if b.children:
                tasks.append(b)
            elif k:
                facts[k] = v
        companies.append({"company": parts[0], "team": " / ".join(parts[1:]),
                          "when": when, "dur": dur, "facts": facts, "tasks": tasks})
    return companies, side


def tenure_rows(sections):
    """경력 사항 요약 → [(기간, 기간길이, 조직, 합산제외)] 와 총 개월 수."""
    rows, total = [], 0
    for b in parse_bullets(find(sections, "경력 사항 요약")["lines"]):
        when, _, org = b.text.partition(":")
        m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", when.strip())
        span, raw = (m.group(1), m.group(2)) if m else (when.strip(), "")
        span = period(span)
        dur = resolve_duration(span, raw)
        excluded = any(k in org for k in EXCLUDED_FROM_TOTAL)
        if not excluded:
            total += parse_months(dur)
        rows.append((span, dur, org.strip(), excluded))
    return rows, total


def parse_task(task: Bullet) -> dict:
    t = {"when": "", "link": "", "stack": "", "stack_label": "사용 기술", "blocks": []}
    for child in task.children:
        k, v = split_kv(child.text)
        if k == "기간":
            t["when"] = period(v)
        elif k == "링크":
            t["link"] = v
        elif k in STACK_LABELS:
            t["stack"], t["stack_label"] = v, k
        elif k in CONTENT_LABELS:
            t["blocks"].append((k, v, [c.text for c in child.children]))
        elif t["blocks"]:
            t["blocks"][-1][2].append(child.text)   # 라벨 없는 줄은 직전 블록에 붙인다
        else:
            t["blocks"].append(("", child.text, []))
    return t


def task_body(t: dict) -> str:
    """문제 · 방법 · 결과 전문. 펼침 영역에 들어간다."""
    out = ""
    if t["link"]:
        label = re.sub(r"^https?://", "", t["link"].strip())
        out += (f'<p class="task-link"><a href="{html.escape(t["link"].strip())}"'
                f' target="_blank" rel="noopener">{html.escape(label)}</a></p>')
    for label, text, subs in t["blocks"]:
        if label:
            out += f'<h4 class="label">{html.escape(label)}</h4>'
        if text:
            out += f"<p>{inline(text)}</p>"
        if subs:
            out += "<ul>" + "".join(f"<li>{inline(s)}</li>" for s in subs) + "</ul>"
    return out


def task_summary(t: dict) -> str:
    """카드에 보일 한 줄: 결과 본문, 없으면 결과 첫 항목."""
    for label, text, subs in t["blocks"]:
        if label in RESULT_LABELS:
            return inline(text or (subs[0] if subs else ""))
    return ""


def render_hero(profile):
    name = profile.get("성명", "김태종")
    photo = build_photo()
    photo_html = (
        f'<img class="hero-photo" src="assets/{photo}" alt="{html.escape(name)}"'
        f' width="{PHOTO_BOX[0] // 2}" height="{PHOTO_BOX[1] // 2}">' if photo else "")
    results_html = "".join(
        f'<li><span class="k">{html.escape(k)}</span><span class="v">{v}</span></li>'
        for k, v in HERO_RESULTS)
    return f"""
<section class="hero" id="top">
  <div class="hero-text">
    <p class="eyebrow">{html.escape(GREETING)}</p>
    <h1>{HERO_TITLE}</h1>
    <p class="hero-lead">{html.escape(HERO_LEAD)}</p>
    <p class="hero-cta"><a class="btn btn-primary" href="#works">지난 작업 보기</a>
      <a class="btn" href="#contact">연락하기</a></p>
  </div>
  {photo_html}
</section>
<ul class="results" aria-label="주요 성과">{results_html}</ul>
"""


def render_about(paras):
    statement, prose, principles = "", [], []
    for p in paras:
        lone = re.fullmatch(r"\*\*(.+)\*\*", p)
        lead = re.match(r"^\*\*(.+?[.。])\*\*\s*(.*)$", p)
        if lone and not statement:
            statement = lone.group(1)
        elif lead:
            principles.append((lead.group(1), lead.group(2)))
        else:
            prose.append(p)
    # 문단 첫머리가 바뀌면 조용히 중복 노출되므로 빌드를 멈춘다
    if not any(p.startswith(ABOUT_MOVED) for p in prose):
        sys.exit(f"중단: '{ABOUT_MOVED}' 로 시작하는 문단이 없습니다. ABOUT_MOVED 와 HERO_RESULTS 를 확인하세요.")
    prose = [p for p in prose if not p.startswith(ABOUT_MOVED)]
    cards = "".join(
        f'<li class="card"><h3>{inline(h)}</h3><p>{inline(b)}</p></li>' for h, b in principles)
    return (f'<section class="sec" aria-labelledby="about">'
            + section_head("01", "about", "About", "어떤 사람인가")
            + (f'<p class="statement">{inline(statement)}</p>' if statement else "")
            + '<div class="prose">' + "".join(f"<p>{inline(p)}</p>" for p in prose) + "</div>"
            + (f'<h3 class="sub">일하는 방식</h3><ul class="cards cards-3">{cards}</ul>' if cards else "")
            + "</section>")


def render_history(sections, companies, rows, total):
    info = {c["company"]: c for c in companies}
    seen, items = set(), ""
    for span, dur, org, excluded in rows:
        parts = [p.strip() for p in org.split("/")]
        comp = parts[0]
        c = info.get(comp)
        desc = ""
        if c and comp not in seen:
            seen.add(comp)
            facts = c["facts"]
            if facts.get("사업소개"):
                desc += f'<p class="tl-desc">{inline(facts["사업소개"])}</p>'
            if facts.get("담당업무"):
                desc += f'<p class="tl-role">{inline(facts["담당업무"])}</p>'
        tag = '<span class="tag">합산 제외</span>' if excluded else ""
        items += (f'<li class="tl-item{" excluded" if excluded else ""}">'
                  f'<p class="tl-when">{html.escape(span)}'
                  f'{" · " + html.escape(dur) if dur else ""}</p>'
                  f'<h3>{inline(comp)} {tag}</h3>'
                  f'<p class="tl-org">{html.escape(" · ".join(parts[1:]))}</p>{desc}</li>')

    extra = ""
    for title in ("학력 사항", "교육이수 사항", "과외 활동", "병역 사항"):
        sec = find(sections, title)
        if sec:
            lis = "".join(f"<li>{inline(b.text)}</li>" for b in parse_bullets(sec["lines"]))
            extra += f'<div class="bg-group"><h4>{html.escape(title)}</h4><ul>{lis}</ul></div>'

    total_html = (f'<p class="sec-note">총 경력 <strong>{html.escape(fmt_months(total))}</strong>'
                  f' (인턴·프리랜서 제외)</p>' if total else "")
    return (f'<section class="sec" aria-labelledby="history">'
            + section_head("02", "history", "History", "연혁") + total_html
            + f'<ol class="timeline">{items}</ol>'
            + f'<h3 class="sub">학력 · 교육 · 활동</h3><div class="bg-grid">{extra}</div>'
            + "</section>")


def render_capabilities(sections):
    sec = find(sections, "핵심 기술 요약")
    out = ""
    group, cards, tools = None, [], []

    def flush():
        nonlocal out
        if group is None:
            return
        out += f'<div class="cap-group"><h3 class="sub">{html.escape(group)}</h3>'
        if cards:
            cols = 3 if len(cards) == 3 else 2   # 핵심 역량 3개는 한 줄에
            out += f'<ul class="cards cards-{cols}">{"".join(cards)}</ul>'
        if tools:
            out += '<dl class="tools">' + "".join(
                f"<div><dt>{html.escape(k)}</dt><dd class=\"stack\">{chips(v)}</dd></div>"
                for k, v in tools) + "</dl>"
        out += "</div>"

    for line in sec["lines"]:
        s = line.strip()
        cat = re.match(r"^\*\*\[(.+)\]\*\*$", s)
        if cat:
            flush()
            group, cards, tools = cat.group(1), [], []
        elif s.startswith("- ") and group is not None:
            bold = re.match(r"^\*\*(.+?)\*\*:\s*(.*)$", s[2:])   # split_kv 는 12자 제한이라 따로 본다
            k, v = (bold.group(1), bold.group(2)) if bold else split_kv(s[2:])
            if k and not bold:
                tools.append((k, v))            # 'Frameworks: A, B' 같은 도구 나열
            else:
                title = f"<h4>{html.escape(k)}</h4>" if k else ""
                cards.append(f'<li class="card">{title}<p>{inline(v)}</p></li>')
    flush()
    return (f'<section class="sec" aria-labelledby="capabilities">'
            + section_head("03", "capabilities", "Capabilities", "역량") + out + "</section>")


def render_works(companies, side):
    def card(task, org):
        t = parse_task(task)
        title_txt = re.sub(r"<[^>]+>", "", inline(task.text))
        sid = slug(title_txt)
        detail = DETAIL_PAGES.get(title_txt)
        summary = task_summary(t)
        actions = ""
        if detail:
            actions += (f'<a class="btn btn-primary btn-sm" href="{DETAIL_DIR}/{detail}.html">'
                        f'상세 페이지 →</a>')
        return (f'<li class="work" id="{sid}">'
                f'<p class="work-meta">{html.escape(org)}'
                f'{" · " + html.escape(t["when"]) if t["when"] else ""}</p>'
                f'<h3>{inline(task.text)}</h3>'
                + (f'<p class="work-summary">{summary}</p>' if summary else "")
                + (f'<p class="stack">{chips(t["stack"])}</p>' if t["stack"] else "")
                + f'<details><summary>문제 · 방법 · 결과 펼치기</summary>'
                  f'<div class="work-body">{task_body(t)}</div></details>'
                + (f'<p class="work-actions">{actions}</p>' if actions else "")
                + "</li>")

    items = "".join(card(t, c["company"]) for c in companies for t in c["tasks"])
    items += "".join(card(t, "사이드 프로젝트") for t in side)
    return (f'<section class="sec" aria-labelledby="works">'
            + section_head("04", "works", "Works", "지난 작업")
            + f'<ol class="works">{items}</ol></section>')


def render_contact(profile):
    rows = []
    if profile.get("이메일"):
        rows.append(("이메일", f'<a href="mailto:{html.escape(profile["이메일"])}">'
                             f'{html.escape(profile["이메일"])}</a>'))
    if profile.get("전화번호"):
        rows.append(("연락처", f'<a href="tel:{profile["전화번호"].replace("-", "")}">'
                             f'{html.escape(profile["전화번호"])}</a>'))
    if profile.get("Github"):
        gh = profile["Github"]
        rows.append(("GitHub", f'<a href="{html.escape(gh)}" target="_blank" rel="noopener">'
                             f'{html.escape(gh.replace("https://", ""))}</a>'))
    if profile.get("생년월일"):
        rows.append(("생년월일", html.escape(profile["생년월일"])))
    lis = "".join(f'<li><span class="k">{k}</span><span class="v">{v}</span></li>' for k, v in rows)
    return (f'<section class="sec contact" aria-labelledby="contact">'
            + section_head("05", "contact", "Contact", "함께 일하고 싶다면")
            + f'<ul class="contact-list">{lis}</ul></section>')


def build_toc(content):
    """본문의 h2/h3 를 훑어 우측 목차를 만든다. 레퍼런스와 동일한 2단 위계."""
    items = []
    pat = r'<h([23]) id="([^"]+)">(.*?)<a class="hash-link"'
    for lv, sid, inner in re.findall(pat, content, re.S):
        text = re.sub(r'<span class="period">.*?</span>', "", inner, flags=re.S)
        text = re.sub(r"<[^>]+>", "", text).strip()
        if text:
            items.append(f'<li class="lv{lv}"><a href="#{sid}">{html.escape(html.unescape(text))}</a></li>')  # 본문은 이미 이스케이프돼 있어 한 번 풀고 다시 건다
    if not items:
        return ""
    return f'<nav class="toc" aria-label="\ubaa9\ucc28"><ul>{"".join(items)}</ul></nav>'


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>김태종 | AI Engineer</title>
<meta name="description" content="에이전트의 기억·검색 계층을 설계하고 평가로 증명하는 AI 엔지니어. 장기기억, 검색 랭킹, 에이전트 아키텍처.">
<meta property="og:title" content="김태종 | AI Engineer">
<meta property="og:description" content="에이전트의 기억·검색 계층을 설계하고 평가로 증명하는 AI 엔지니어. 장기기억, 검색 랭킹, 에이전트 아키텍처.">
<meta property="og:type" content="profile">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect x='12' y='12' width='76' height='76' rx='16' fill='%230077c8'/><text x='50' y='50' font-size='52' font-family='sans-serif' font-weight='700' fill='%23ffffff' text-anchor='middle' dominant-baseline='central'>TJ</text></svg>">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/site.js" defer></script>
</head>
<body>
<nav class="navbar">
  <div class="navbar-inner">
    <a class="navbar-brand" href="#top">@taejongK</a>
    <ul class="navbar-links">
      <li><a href="#about">About</a></li>
      <li><a href="#history">History</a></li>
      <li><a href="#capabilities">Capabilities</a></li>
      <li><a href="#works">Works</a></li>
      <li><a href="#contact">Contact</a></li>
    </ul>
  </div>
</nav>
<main class="site">
__CONTENT__
  <footer class="doc-footer">
    <p>최종 수정 __UPDATED__</p>
  </footer>
</main>
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

    # resume.md 도 커밋·배포되는 공개 원본이다. 산출물만 검사하면 원본으로 새어 나간다.
    leaked = [w for w in BANNED_WORDS if w in SRC.read_text(encoding="utf-8")]
    if leaked:
        sys.exit(f"중단: 공개 원본 resume.md 에 민감 항목이 있습니다 → {leaked}")

    sections = load_document()
    profile, paras = load_profile(sections)
    companies, side = load_experience(sections)
    rows, total = tenure_rows(sections)
    content = (
        render_hero(profile)
        + render_about(paras)
        + render_history(sections, companies, rows, total)
        + render_capabilities(sections)
        + render_works(companies, side)
        + render_contact(profile)
    )
    page = (PAGE.replace("__CONTENT__", content)
                .replace("__UPDATED__", date.today().strftime("%Y.%m.%d")))
    # 검사를 먼저 한다. 쓰고 나서 검사하면 차단에 실패해도 민감 정보가 디스크에 남는다.
    leaked = [w for w in BANNED_WORDS if w in page]
    if leaked:
        sys.exit(f"중단: 공개판에 민감 항목이 남았습니다 → {leaked} (index.html 미변경)")

    OUT.write_text(page, encoding="utf-8")

    print(f"생성 완료: {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} bytes)")
    print(f"제외된 항목: {', '.join(sorted(REDACT_FIELDS))}")


if __name__ == "__main__":
    main()
