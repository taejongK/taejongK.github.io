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
resume.md          원본 (비공개 — 커밋되지 않음)
   │
   └─ build_site.py ──▶ index.html   공개 사이트
                        assets/style.css
```

내용을 고칠 때는 `resume.md` 를 수정하고 다시 빌드합니다. `index.html` 은 생성물이라
직접 고치면 다음 빌드에 덮어써집니다.

```bash
python3 build_site.py     # index.html 재생성
```

로컬에서 확인하려면:

```bash
python3 -m http.server 8899
# → http://127.0.0.1:8899
```

## 공개 범위

`resume.md` 는 제출용 전체판이라 연봉·이직사유 같은 항목이 들어 있고, `.gitignore` 로
커밋에서 제외됩니다. 빌드 시 `REDACT_FIELDS` 에 지정된 항목이 걸러지고, 주소는 동 단위까지만
남깁니다. 빌드 마지막에 민감 항목이 결과물에 남았는지 검사하고, 발견되면 빌드를 중단합니다.

`projects/` 이하의 프로젝트 소스도 실제 API 키와 업무 데이터를 포함하므로 공개되지 않습니다.
