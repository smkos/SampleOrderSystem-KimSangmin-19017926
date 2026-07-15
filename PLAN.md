# PLAN.md — 작업 계획 인덱스

`SPEC.md`를 기준으로 진행할 TDD 사이클(RED → GREEN → REVIEW)의 목록이다. 각 사이클의 상세
내용(목표, 범위, 예시 테스트, 진행 상태)은 `plan/` 디렉터리의 사이클별 파일에 있다.

각 사이클 파일은 이전/다음 사이클 링크와 "지금까지의 진행 상황" 요약을 포함해, 그 파일 하나만
보아도 전체 맥락(이전에 무엇이 끝났고 이번에 무엇을 하는지)을 잃지 않도록 작성한다. 새 사이클을
추가할 때도 이 형식을 유지한다.

각 단계는 사람 파트너의 검토를 받은 뒤에만 다음 단계로 넘어간다.

## 사이클 목록

| Cycle | 기능 | 상태 | 파일 |
|-------|------|------|------|
| 1 | 시료 등록 | GREEN 완료 | [plan/cycle-01-sample-registration.md](plan/cycle-01-sample-registration.md) |
| 2 | 시료 영속화 | GREEN 완료 | [plan/cycle-02-sample-persistence.md](plan/cycle-02-sample-persistence.md) |
