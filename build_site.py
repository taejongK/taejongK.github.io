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
    ("버블탭", "캐릭터 챗봇(DAU 3,000)의 LLM 레이어를 맡고 있습니다. 기억 검색 "
               "<strong>Precision@3 48%</strong>, 유해 콘텐츠 차단 <strong>F1 18% → 87%</strong>"),
    ("브릭", "<strong>사내 첫 LLM 적용 사례</strong>를 만들어 사업화 검토의 근거가 됐습니다"),
    ("알고리고", "졸음 탐지 모델로 <strong>현장 관리 인력을 절반</strong>으로 줄였습니다"),
]
# 첫 화면 Works 카드에 보일 세 줄 (Why · What · How). 전문은 resume.md 와 상세 페이지에 있다.
# 수치는 resume.md 에 있는 것만 쓴다. resume.md 의 프로젝트 제목이 바뀌면 빌드가 멈춘다.
WORK_CARDS = {
    "이미지 검열 시스템 설계·구축 (판정 구조 설계 · clef-flash 직접 서빙 · 운영팀 검수 보조 도구)": (
        "채팅 이미지를 업로드 직후 1초 안에 판정해야 했고, 운영팀은 어드민 밖 판정 결과를 다시 확인하는 이중 작업 중이었음",
        "평가셋 <strong>탐지율 96% · 오탐률 0.7%</strong>, 이미지 1장 0.2초로 목표 충족. 운영팀 검수 도구로 사내 운영 중",
        "규정을 질문으로 옮기고, 확률을 내는 결정 모델을 직접 서빙해 분류 → 사유 2단계로 판정함"),
    "Chat Arena 개발 (사람 블라인드 투표 기반 모델·프롬프트 비교)": (
        "모델·프롬프트를 사람이 같은 맥락에서 비교한 데이터가 없었음",
        "기존 아레나와 점수 산식 일치 확인(무작위 50회 비교 차이 0), 공용 서버 반영 후 사내 6명 QA 진행",
        "실제 서빙 경로로 응답을 만들고, 블라인드 쌍대 투표를 Bradley-Terry로 집계함"),
    "검색 랭킹 개선안 설계 및 평가 체계 구축": (
        "월 15만 건 검색 질의가 있었지만 품질을 측정한 적이 없었음",
        "오프라인 <strong>Precision@10 +3.6 ~ +6.8p</strong>(6개 조합 중 5개 유의), 팀 적용안으로 확정",
        "평가 체계(층화 추출 · LLM 판정 · 부트스트랩 신뢰구간)를 먼저 세우고, 검색 필드 확장과 인기도 결합식을 설계함"),
    "프롬프트 해킹 시도 탐지 대시보드 개발 (룰 + LLM 2단계 판정)": (
        "해킹 지표가 9.7%만 판정한 표본 수치였고, 원문이 남지 않아 수법을 볼 수 없었음",
        "하루 <strong>29만 건 → 해킹 의심 10건</strong>, 하루 $3.83로 전수 판정",
        "룰은 후보만 고르고 LLM이 4개 축으로 채점, 운영팀이 근거를 보고 검수함"),
    "프롬프트 관리 툴 개발 (사내 LLMOps)": (
        "지금 쓰는 프롬프트가 어떤 이력과 테스트를 거쳐 배포됐는지 알 수 없었음",
        "팀 공용 단일 프롬프트 소스 확보, 수정·테스트 시간 <strong>1시간 → 30분</strong>",
        "프롬프트를 DB로 옮겨 git처럼 버전·diff·cherry-pick을 붙이고, MCP 서버로 Claude Code에서 바로 수정하게 함"),
    "자체 서빙 모델 콘텐츠 필터 개발 (CoT 기반)": (
        "자체 서빙 모델에 콘텐츠 필터가 없었고, 단순 금지 지시로는 F1 18.1%에 그쳤음",
        "미성년자 성적 콘텐츠 차단 <strong>F1 18.1% → 87.0%</strong>, 배포 후 관련 문의 0건",
        "답변 전에 분류를 먼저 출력하게 하고, 나이 → 성적 요소 → 최종 판정 순서로 추론하게 함"),
    "캐릭터 제작 에이전트 개발 (멀티 에이전트)": (
        "에이전트 하나로는 캐릭터·세계관·관계를 동시에 깊이 있게 설계하기 어려웠음",
        "프레임워크 없이 3단계 멀티 에이전트 PoC 완성(프로덕션 반영은 보류)",
        "Router가 필요한 도구만 골라 병렬 실행하고, Idea Agent가 결과를 합쳐 스트리밍함"),
    "LLM-as-judge 평가 체계 구축 (루브릭 프롬프트 설계 포함)": (
        "프롬프트나 모델을 바꿔도 좋아졌는지 감으로만 판단했음",
        "모델 채택·프롬프트 개선의 공통 측정 도구로 사용, 블라인드 QA로 자체 학습 모델 우위 확인(3.45 vs 3.02)",
        "객관적 제약은 규칙으로, 주관적 품질은 LLM 심사자가 채점하고 사람 평가로 보정함"),
    "프롬프트 탈취 대응 및 보안 프롬프트 재설계": (
        "유저가 만든 캐릭터 설정을 통해 시스템 프롬프트를 빼내려는 시도를 확인함",
        "탈취 시도 20종 재현 테스트 <strong>성공률 0%</strong>, 배포 후 재발 0건",
        "요청을 거절하지 않고, 내부 설정이 없는 것처럼 캐릭터가 흘려보내도록 재설계함"),
    "챗봇 장기기억 구조 설계 및 커스텀 기억 검색(RRF) 적용": (
        "긴 대화에서 캐릭터 일관성이 무너졌고, 기존 벡터 검색은 Recall 약 10%였음",
        "요약 품질 3.55 → 3.99, 기억 검색 <strong>Precision@3 48%</strong>(51~150턴 68%), 요약 API 비용 월 약 171만 원 제거",
        "검색을 걷어내고 요약·재압축 구조로 바꾼 뒤, 사실·최근성·관련성을 RRF로 합친 기억 검색을 더함"),
    "CS 챗봇 개발 (어드민 적용)": (
        "반복 문의로 CS 비용이 늘었고, 모호한 질문에는 맞는 문서를 찾지 못했음",
        "관련 문서 검색 성공률 <strong>20% → 80%</strong>, 어드민에 적용",
        "모호한 질문을 검색하기 좋은 문장으로 다시 쓰고, MMR 검색과 연속 대화를 붙임"),
    "RAG 기반 회사 솔루션 사용법 설명 챗봇 개발": (
        "솔루션 사용법 문의를 매번 사람이 응대했고, 사내에 LLM 적용 사례가 없었음",
        "내부 테스트 <strong>만족도 86%</strong>, 사내 첫 LLM 적용 사례로 사업화 검토의 근거가 됨",
        "기획부터 API·화면까지 직접 만들고, 검색 품질을 항목별로 측정해 실사용 가능 여부를 판단함"),
    "실시간 졸음 탐지 모델 개발 (이상탐지)": (
        "졸고 있는 학생을 찾으려면 매니저가 시간당 2명씩 순찰해야 했음",
        "Precision 0.92 모델로 알림 기반 순찰 전환, <strong>현장 인력 50% 절감</strong>",
        "현장 관찰로 라벨 기준을 세우고, 무게중심 변화 feature와 AutoEncoder → DeepSAD 준지도 학습을 적용함"),
    "자세분류 모델 성능 개선 (분류)": (
        "자세분류 정확도가 82%에 머물렀고, 특정 체형에서 특히 낮았음",
        "정확도 <strong>82% → 97%</strong>",
        "클러스터링으로 잘못된 데이터를 걸러 재학습하고, 체형 차이는 앙상블로 보완함"),
    "집중도 지표 개발 (통계)": (
        "학생이 얼마나 집중했는지 보여줄 지표가 없었음",
        "검증한 집중도 지표를 라이브러리로 배포, 월간 학습 보고서에 반영",
        "현장 관찰로 가설을 고쳐 움직임의 변화량 기준으로 지표를 설계함"),
    "카시트 호흡·심박 추정 연구 (신호 처리)": (
        "카시트로 호흡·심박을 읽어 졸음운전을 탐지할 수 있는지 확인하는 선행 연구",
        "실험실 오차 약 6%가 실제 주행에서 약 32%로 커져 실용화가 어렵다고 판단, 연구 단계에서 종료",
        "압력 센서 32개 카시트로 데이터를 직접 수집하고, FFT와 LSTM으로 신호를 추정함"),
    "데이터 바우처 사업 지원 및 데이터 분석·가공": (
        "지원 기업 대부분이 자사 현안을 데이터 과제로 정의하지 못했음",
        "컨설팅한 약 30개 업체 중 <strong>18곳 선정</strong>(선정률 60%)",
        "업체 현안을 데이터로 검증할 수 있는 과제로 구체화하고, 선정 후 분석·가공까지 맡음"),
    "연구 보고서 작성 에이전트 개발": (
        "주제 하나를 조사하려면 논문을 일일이 찾아 읽어야 했음",
        "10분 안에 1페이지 분량 연구 보고서를 자동 작성하는 에이전트 완성",
        "후속 질문을 만들고 Arxiv를 재귀적으로 검색해 결과를 보고서로 묶음"),
    "Semantic Segmentation 모델을 사용한 차량 파손 탐지 서비스 개발": (
        "파손 3종을 한 모델로 학습하면 클래스끼리 간섭해 정확도가 낮았음",
        "3종 파손 구분 서비스 완성(<strong>IoU 0.75</strong>)",
        "클래스별로 모델을 나누고, 파손 부위 crop 증강과 출력 채널 분리를 적용함"),
}

# 첫 화면 역량 카드 문구. resume.md 의 긴 설명은 제출용 이력서에만 쓴다.
CAP_SHORT = {   # (항목, 한 줄 설명)
    "Memory & Retrieval": [
        ("장기기억", "벡터 검색 한계 규명 → 요약 구조로 전환"),
        ("기억 검색", "다중 신호 RRF · Precision@3 48%"),
        ("검색 랭킹", "Precision@10 최대 +6.8p"),
    ],
    "Evaluation": [
        ("Chat Arena", "블라인드 쌍대 비교 · Bradley-Terry"),
        ("검색 평가", "LLM 판정 · 부트스트랩 신뢰구간"),
        ("LLM-as-judge", "규칙 + LLM 채점, 사람 평가로 보정"),
    ],
    "Safety & Content Moderation": [
        ("콘텐츠 필터", "F1 18% → 87%"),
        ("이미지 검열", "탐지율 96% · 오탐률 0.7%"),
        ("해킹 탐지", "하루 29만 건 → 의심 10건"),
    ],
}

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
    "이미지 검열 시스템 설계·구축 (판정 구조 설계 · clef-flash 직접 서빙 · 운영팀 검수 보조 도구)": "image-moderation",
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
def breaks(html_text: str) -> str:
    """합니다체 문장이 끝나는 곳에서 줄을 바꾼다. 여러 문장이 한 줄로 이어 붙으면 읽기 어렵다."""
    return re.sub(r"(니다\.(?:</strong>)?)\s+(?=\S)", r"\1<br>", html_text)


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
        f'<li><span class="k">{html.escape(k)}</span><span class="v">{breaks(v)}</span></li>'
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
    stmt = re.sub(r"([,?]) ", r"\1<br>", inline(statement))   # 쉼표·물음표에서 줄을 나눈다
    cards = "".join(
        f'<li class="card"><h3>{inline(h)}</h3><p>{inline(b)}</p></li>' for h, b in principles)
    return (f'<section class="sec" aria-labelledby="about">'
            + section_head("01", "about", "About", "어떤 사람인가")
            + (f'<p class="statement">{stmt}</p>' if statement else "")
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
                body = (f'<ul>{"".join(f"<li><strong>{h}</strong><span>{d}</span></li>" for h, d in CAP_SHORT[k])}</ul>'
                        if k in CAP_SHORT else f'<p>{inline(v)}</p>')
                cards.append(f'<li class="card">{title}{body}</li>')
    flush()
    return (f'<section class="sec" aria-labelledby="capabilities">'
            + section_head("03", "capabilities", "Capabilities", "역량") + out + "</section>")


def render_works(companies, side):
    def card(task, org):
        t = parse_task(task)
        title_txt = re.sub(r"<[^>]+>", "", inline(task.text))
        sid = slug(title_txt)
        detail = DETAIL_PAGES.get(title_txt)
        if title_txt not in WORK_CARDS:
            sys.exit(f"중단: WORK_CARDS 에 '{title_txt}' 가 없습니다. 첫 화면 세 줄 요약을 추가하세요.")
        why, what, how = WORK_CARDS[title_txt]
        short = re.sub(r"\s*\([^()]*\)$", "", title_txt)        # 제목 끝 괄호 설명은 첫 화면에서 뺀다
        dates = re.findall(r"\d{4}\.\d{2}", t["when"])
        when = (f"{dates[0]} ~ {dates[-1]}" if len(dates) > 1 and dates[0] != dates[-1]
                else dates[0] if dates else t["when"])
        rows = "".join(f"<div><dt>{k}</dt><dd>{breaks(v)}</dd></div>"
                       for k, v in (("Why", why), ("What", what), ("How", how)))
        if detail:
            more = (f'<p class="work-actions"><a class="btn btn-primary btn-sm" '
                    f'href="{DETAIL_DIR}/{detail}.html">상세 페이지 →</a></p>')
        else:   # 상세 페이지가 없는 작업만 이력서 전문을 접어서 둔다
            more = (f'<details><summary>전체 내용 펼치기</summary>'
                    f'<div class="work-body">{task_body(t)}</div></details>')
        return (f'<li class="work" id="{sid}">'
                f'<p class="work-meta">{html.escape(org)}{" · " + html.escape(when) if when else ""}</p>'
                f'<h3>{html.escape(short)}</h3>'
                f'<dl class="wwh">{rows}</dl>{more}</li>')

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
