# 김태종 — AI Engineer

**이력서: https://taejongK.github.io**

LLM 기반 AI 서비스를 기획부터 배포까지 만듭니다.
멀티 에이전트 오케스트레이션, RAG 파이프라인, LLMOps.

- 메일 · xowhddk123@gmail.com
- GitHub · [@taejongK](https://github.com/taejongK)

---

## 이 저장소

이력서 사이트의 소스입니다. `resume.md` 한 파일이 원본이고, 나머지는 전부 거기서 생성됩니다.

```
resume.md              원본 (비공개 — 커밋되지 않음)
imgs/my_image.jpg      인쇄용 사진 원본 (비공개, 9MB)
   │
   └─ build_site.py ──▶ index.html          공개 사이트
                        assets/profile.jpg   웹용 사진 (41KB)
```

내용을 고칠 때는 `resume.md` 를 수정하고 다시 빌드합니다. `index.html` 은 생성물이라
직접 고치면 다음 빌드에 덮어써집니다.

```bash
python3 build_site.py     # index.html + assets/profile.jpg 재생성

python3 -m http.server 8899
# → http://127.0.0.1:8899
```

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
제외됩니다. `projects/` 이하 프로젝트 소스도 실제 API 키와 업무 데이터를 포함하므로
공개되지 않습니다.

공개되는 파일은 `index.html`, `assets/`, `build_site.py`, `README.md` 뿐입니다.
