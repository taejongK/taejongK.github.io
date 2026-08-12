# 김태종 — AI Engineer

**이력서: https://taejongK.github.io**

LLM 기반 AI 서비스를 기획부터 배포까지 만듭니다.
멀티 에이전트 오케스트레이션, RAG 파이프라인, LLMOps.

- 메일 · xowhddk123@gmail.com
- GitHub · [@taejongK](https://github.com/taejongK)

---

## 이 저장소

이력서 사이트의 소스입니다. 원본은 전부 비공개이고, 공개되는 HTML 은 거기서 생성됩니다.

```
resume.md              이력서 원본 (비공개 — 커밋되지 않음)
imgs/my_image.jpg      인쇄용 사진 원본 (비공개, 9MB)
   │
   └─ build_site.py ──▶ index.html           공개 사이트
                        assets/profile.jpg    웹용 사진 (41KB)

portfolio/*.md         프로젝트 상세 원본 (비공개 — 커밋되지 않음)
   │
   └─ build_portfolio.py ──▶ works/*.html    프로젝트 상세 페이지

slides/deck.md         슬라이드 덱 원본 (비공개 — 커밋되지 않음)
   │
   └─ build_slides.py ──▶ slides/portfolio.pdf   제출용 덱 (비공개)

resume_submit.md       제출본 (비공개)
   │
   └─ build_docx.py ──▶ resume_submit.docx       제출용 이력서 (비공개)
```

`index.html` 이 "무엇을 했는가"를 요약하면, `works/*.html` 은 아키텍처와 기술 의사결정까지
펼칩니다. 이력서의 해당 프로젝트에 **상세 보기 →** 링크가 자동으로 붙습니다.

내용을 고칠 때는 원본(`resume.md` / `portfolio/*.md`)을 수정하고 다시 빌드합니다.
`index.html` 과 `works/*.html` 은 생성물이라 직접 고치면 다음 빌드에 덮어써집니다.

```bash
python3 build_portfolio.py   # works/*.html 재생성
python3 build_site.py        # index.html + assets/profile.jpg 재생성

python3 -m http.server 8899
# → http://127.0.0.1:8899
```

상세 페이지를 추가하려면 `build_site.py` 의 `DETAIL_PAGES` 에
`{resume.md 의 수행업무 제목: 슬러그}` 를 넣고 `portfolio/<슬러그>.md` 를 만듭니다.
두 스크립트가 같은 상수를 공유하므로 목록이 어긋나면 빌드가 중단됩니다.

### 이미지

`portfolio/<슬러그>.md` 에 **한 줄 전체**로 `![캡션](파일명.png)` 을 쓰면 그림 자리가 생깁니다.
파일은 `assets/works/<슬러그>/` 에 넣습니다.

```
portfolio/prompt-ops.md 의  ![branch tree 화면](branch-tree.png)
    → assets/works/prompt-ops/branch-tree.png
```

파일이 **아직 없으면** 넣을 위치와 경로를 보여주는 자리 표시가 렌더되고, 파일을 넣고 다시
빌드하면 자동으로 이미지로 바뀝니다. 빌드가 끝날 때 비어 있는 자리를 목록으로 알려줍니다.

- 자리 표시는 **공개 사이트에도 그대로 보입니다.** 넣지 않을 자리는 해당 `![..](..)` 줄을 지우세요.
- 손으로 넣는 파일을 `works/` 아래에 두지 마세요 — 생성물이라 통째로 지워질 수 있습니다.
- **`assets/works/` 는 공개 폴더입니다.** 이미지 외에 참고용 문서(README 등)를 두지 마세요 —
  레포 루트 전체가 배포되므로 그대로 웹에 뜹니다. 참고 자료는 `portfolio/_originals/` 로.
- **빌드 가드는 텍스트만 검사합니다.** 스크린샷 안의 유저 대화·개인정보·API 키는
  걸러내지 못하므로 직접 확인해야 합니다.

### 슬라이드 덱 — `build_slides.py`

제출용 PDF 덱(29장, 16:9)을 만듭니다. Marp CLI 를 `npx` 로 부르므로 전역 설치가 필요 없습니다.

```bash
python3 build_slides.py           # slides/portfolio.pdf
python3 build_slides.py --png     # 장별 PNG 도 함께 (검토용)
python3 build_slides.py --check   # 검사만
```

- **`slides/` 는 통째로 `.gitignore` 대상** — 원본도 PDF 도 저장소에 올라가지 않습니다.
- 수치·기간의 기준은 `resume.md` 입니다. 덱은 압축할 뿐 새 수치를 만들지 않습니다.
- 가드는 개인정보에 더해 **사내 문자열** 까지 막고, 걸리면 PDF 를 만들지 않습니다.

### 제출용 이력서 — `build_docx.py`

```bash
python3 build_submit.py    # resume.md → resume_submit.md (작업 메모 제거)
python3 build_docx.py      # resume_submit.md → resume_submit.docx
```

- 서식은 `references/이력서_김태종_v1.1.0.docx` 를 **템플릿으로 재사용** 합니다 —
  본문만 비우고 채우므로 폰트·여백·스타일이 그대로 유지됩니다.
- 문제/방법/결과 위계는 들여쓰기 3단(0" / 0.25" / 0.5")으로 표현합니다.
- **입력은 `resume_submit.md` 입니다.** `resume.md` 를 직접 읽으면 작업 노트가 딸려 들어갑니다.
- 산출물은 연봉·연락처가 담긴 제출용 전체판이라 `.gitignore` 대상입니다.

### 차단 목록은 왜 저장소에 없는가 — `portfolio/_guard.py`

이미지에서 가린 이름을 스크립트의 차단 목록에 그대로 적으면, **가린 의미가 없어집니다**
— 저장소를 통해 평문으로 공개되기 때문입니다. 그래서 사내 문자열 목록만
`portfolio/_guard.py`(비공개)로 분리했고, 빌드 스크립트가 있으면 읽고 없으면 건너뜁니다.

```
portfolio/_guard.py   비공개 — 사내 문자열 목록
      ↑ import (없으면 폴백)
build_portfolio.py · build_slides.py   공개 — 개인정보·자격증명 가드만 내장
```

파일이 없어도 빌드는 됩니다. 다만 개인정보·API 키 가드만 동작하므로,
빌드 출력의 `사내 문자열 가드 적용/미적용` 표시를 확인하세요.
- 검토는 PNG 로 합니다. 슬라이드는 720px 고정이라 넘쳐도 자동으로 줄지 않으니,
  좌우로 이미지를 놓을 때는 `w:` 가 아니라 **`h:` 로 높이를 맞추세요.**

### 스크린샷 모자이크 — `mask_image.py`

가릴 영역을 좌표로 기록해두고 재현 가능하게 처리합니다.

```bash
python3 mask_image.py --grid branch-tree   # 좌표를 읽을 격자 사본 생성
python3 mask_image.py                      # MASKS 에 등록된 것 전부 처리
python3 mask_image.py branch-tree          # 하나만
```

원본은 `portfolio/_originals/<슬러그>/` 에 백업되고(비공개), 처리는 **항상 백업본에서 다시
시작**합니다. 재실행해도 모자이크가 겹쳐 쌓이지 않고, 좌표를 고쳐 몇 번이든 다시 돌릴 수 있습니다.
어느 영역을 왜 가렸는지는 `MASKS` 주석에 남깁니다. 처리 후에는 확대해서 판독 불가인지 확인하세요.

> 산출물이 `works/` 인 이유 — `projects/` 는 `.gitignore` 전체 차단 대상이라
> 그 아래 HTML 을 두면 GitHub Pages 에 배포되지 않습니다.

## 빌드가 자동으로 하는 일

- **민감 항목 제거** — `REDACT_FIELDS`(연봉)를 걸러내고, 주소는 동 단위까지만 남깁니다.
  마지막에 결과물을 다시 검사해서 남아 있으면 빌드를 중단합니다.
- **재직기간 계산** — `~ 현재` 로 끝나는 기간만 빌드 시점 날짜로 환산합니다.
  퇴사한 회사의 기간은 `resume.md` 에 적힌 값을 그대로 씁니다.
- **경력 총합** — 각 회사 재직 개월을 합산해 `경력 요약` 제목 옆에 표기합니다.
- **사진 생성** — 인쇄용 원본을 크롭·리사이즈해 웹용 파생본을 만듭니다.
  `PHOTO_CROP` 으로 구도를, `PHOTO_SRC = None` 으로 사진 제거를 제어합니다.
- **우측 목차** — 본문의 h2/h3 를 훑어 자동 생성합니다. 1280px 이상에서만 보입니다.

## 레이아웃

[kimcoder.io/resume](https://www.kimcoder.io/resume) 를 브라우저로 실측해 치수를 맞췄습니다.

| | 값 |
|---|---|
| 컨테이너 / 본문 / 목차 | 1400px / 1216px / 112px |
| 타이포 | h1 48 · h2 36 · h3 30 · p 20 · li 14px |
| 팔레트 | Tailwind gray 900·700·500·200 (무채색) |
| 프로젝트 | 2단 — 좌 제목·기간 / 우 성과·역할·기술 |
| 대응 | 라이트 전용 · 모바일 390px · A4 인쇄 |

## 재직기간 자동 갱신

재직 중인 회사의 기간과 경력 총합은 시간이 지나면 값이 늘어납니다.
`.github/workflows/refresh-dates.yml` 이 **매월 1일 09:00 KST** 에 `refresh_dates.py` 를
돌려 갱신하고, 값이 바뀐 경우에만 커밋합니다. 저장소 Actions 탭에서 수동 실행도 됩니다.

`resume.md` 는 개인정보 때문에 저장소에 없으므로 Actions 에서는 `build_site.py` 를
돌릴 수 없습니다. 대신 `refresh_dates.py` 가 `index.html` 안의 입사 연월을 읽어
아래 세 가지 숫자만 다시 계산합니다.

- `2025.06 ~ 현재 · N년 M개월` 의 재직기간 (퇴사한 회사는 건드리지 않습니다)
- `경력 요약` 옆의 경력 총합
- 문서 하단의 `최종 수정 YYYY.MM.DD`

**내용을 바꿀 때는 여전히 `resume.md` → `build_site.py` 입니다.**
이 워크플로는 숫자만 만집니다.

## 공개 범위

`resume.md` 는 제출용 전체판이라 연봉 같은 항목이 들어 있고, `.gitignore` 로 커밋에서
제외됩니다. 프로젝트 상세 원본인 `portfolio/` 도 같은 취급입니다.
`projects/` 이하 프로젝트 소스도 실제 API 키와 업무 데이터를 포함하므로 공개되지 않습니다.

공개되는 파일은 `index.html`, `works/`, `assets/`, 빌드 스크립트, `README.md` 뿐입니다.

두 빌드 스크립트 모두 **검사를 먼저 하고 통과할 때만 파일을 씁니다.** 쓰고 나서 검사하면
차단에 실패해도 민감 정보가 디스크에 남기 때문입니다. `build_portfolio.py` 는
개인정보(연봉·이직사유) 외에 API 키 패턴과 고객 데이터 파일명도 함께 막고,
한 파일이라도 걸리면 **아무 파일도 쓰지 않고** 중단합니다.
