# 캐릭터 제작 에이전트

> Router → 병렬 Tool Agents → Idea Agent 3단계 파이프라인을 프레임워크 없이 직접 설계·구현한 멀티 에이전트 시스템입니다.

- 기간: 2026.05 ~ 2026.06 (2개월)
- 소속: (주)버블탭 AI코어팀
- 역할: 단독 기획·설계·개발
- 사용 기술: FastAPI, Python 3.12+, asyncio, Pydantic, sse-starlette, Jinja2, httpx, OpenRouter API

## 문제

AI 롤플레이 서비스에서 캐릭터 품질은 곧 프롬프트 품질입니다. 하지만 유저가 좋은 프롬프트를 직접 쓰기 어려웠고, 이것이 유입 후 첫 이탈 지점이었습니다.

- 유저가 고품질 캐릭터 프롬프트를 직접 작성하기 어려움
- 캐릭터·세계관·관계를 단일 에이전트로 동시에 설계하면 각 영역의 깊이가 얕아짐
- 프롬프트 변경이 품질에 미치는 영향을 측정할 수단이 없음

## 시스템 아키텍처

역할을 나눠 병렬로 돌리고, 마지막에 하나의 목소리로 합치는 구조입니다.

```
유저 입력
    │
    ▼
[1차]  Router  (v5.0.0)  · 비스트리밍
       · 모드 분류        아이디어 / JSX / 진단&압축
       · Concept 생성     genre, mood, core_appeal, constraints
       · tool_calls 선택 + per_tool_task 지시문 생성
    │
    ▼
[2차]  병렬 Tool Agents  · asyncio.gather
       ├── character_writer      이름 · 성격 · 말투 · 외모 · 배경
       ├── narrative_designer    세계관 · 배경사건 · 현재상황 · 로어북 시드
       └── relationship_designer 유저-캐릭터 관계 · 긴장감 · 도입부 힌트
       (진행상황을 SSE tool_start / tool_done 으로 프론트에 실시간 전송)
    │
    ▼
[3차]  Idea Agent  (v4.0.0)  · 스트리밍
       · ToolContext(tool_results) 주입
       · 최종 캐릭터 프롬프트 스트리밍 응답
```

Router가 입력을 보고 세 모드 중 하나를 고릅니다. **아이디어**는 캐릭터 프롬프트를 기획·작성하고, **JSX**는 캐릭터 상태창용 코드를 만들며, **진단&압축**은 기존 프롬프트를 진단하고 토큰을 줄이도록 압축합니다.

![Router가 선택해 병렬 실행한 Tool Agent 3종(서사 설계자 · 인물 작가 · 관계 설계자)과 SSE 진행 상태](parallel-tools.jpeg)

## 기술 의사결정

### LangChain / LangGraph 를 쓰지 않은 이유

이전 RAG 파이프라인에서 프레임워크 내부 검색 로직이 블랙박스여서, 로컬과 프로덕션 결과가 달라졌을 때 원인을 추적하지 못한 적이 있습니다. 이 규모의 오케스트레이션은 직접 구현해도 어렵지 않다고 판단했고, 덕분에 Router 프롬프트를 5세대까지 고치는 동안 동작을 전부 추적·수정할 수 있었습니다.

### 병렬 Tool 실행 (asyncio.gather)

세 Tool의 출력 스키마가 서로 독립적이라 `asyncio.gather`로 병렬 실행해, 순차 처리 대비 세 배의 대기를 없앴습니다. 병렬 실행으로 진행 상황이 보이지 않는 문제는 SSE queue로 `tool_start` / `tool_done` 이벤트를 프론트엔드에 전송해 해결했습니다.

### Router 의 선택적 Tool 활성화

처음에는 모든 요청에 세 Tool을 실행해, "이름만 바꿔줘" 같은 요청에도 LLM 호출이 세 번 나갔습니다. Router가 필요한 Tool만 고르도록 바꿔 불필요한 호출을 없앴습니다.

### Pydantic 으로 에이전트 간 계약 고정

`dict`로 넘기면 파싱 실패 지점을 찾기 어렵습니다. `Concept`, `ToolContext` Pydantic 모델로 Router 출력 → Tool 입력 → Idea Agent 입력의 스키마를 고정해, 실패 지점이 예외 메시지에 드러나게 했습니다.

### 프롬프트 버전 관리

- Router v1.0.0 → v5.0.0, Idea Agent v1.0.0 → v4.0.0 등 **37개 프롬프트 버전**을 파일로 관리
- 각 버전을 Jinja2 `.j2` 파일로 보존해 롤백·A/B 비교 가능
- 코드 수정 없이 설정의 버전 번호만 바꿔 프롬프트 교체

## 사용자 경험 설계

- 병렬 실행 진행 상태를 SSE로 노출해 여러 에이전트가 동시에 일하는 과정을 화면에 표시
- 텍스트 드래그 기반 **참조 문맥(Reference Context)**: 결과의 특정 부분만 선택해 수정·확장을 요청하는 UX로, 전체 재생성 없이 국소 수정 가능

![결과 일부를 드래그해 수정을 요청하는 참조 문맥 UX](reference-context.jpeg)

## 결과

![완성된 캐릭터 프롬프트 결과 화면](result-prompt.jpeg)

- Router → 병렬 Tool Agents → Idea Agent 3단계 파이프라인을 프레임워크 없이 설계·구현해 PoC를 완성했습니다
- 이후 개발팀 리소스 부족으로 프로덕션 반영은 보류됐습니다
