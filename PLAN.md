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
| 3 | 시료 컨트롤러 연동 | GREEN 완료 | [plan/cycle-03-sample-controller.md](plan/cycle-03-sample-controller.md) |
| 4 | 시료 검색 | GREEN 완료 | [plan/cycle-04-sample-search.md](plan/cycle-04-sample-search.md) |
| 5 | 주문 모델 + 접수(RESERVED) | GREEN 완료 | [plan/cycle-05-order-reservation.md](plan/cycle-05-order-reservation.md) |
| 6 | 주문 영속화 (`OrderRepository`) | GREEN 완료 | [plan/cycle-06-order-persistence.md](plan/cycle-06-order-persistence.md) |
| 7 | 주문 승인/거절 (재고 확인 → CONFIRMED/PRODUCING/REJECTED) | 미계획 | - |
| 8 | 생산 큐 계산 로직 (부족분/실생산량/총생산시간, FIFO) | 미계획 | - |
| 9 | 생산 완료 처리 (PRODUCING → CONFIRMED) | 미계획 | - |
| 10 | 출고 처리 (CONFIRMED → RELEASE) | 미계획 | - |
| 11 | 모니터링 집계 | 미계획 | - |
| 12 | 콘솔 View/Controller 통합 (전체 메뉴 흐름) | 미계획 | - |

> Cycle 4 이후는 개략적인 이름만 미리 적어 둔 것이며, 실제 진행하면서 범위가 나뉘거나 순서가
> 바뀔 수 있다. 각 사이클의 상세 계획(목표/범위/예시 테스트)은 직전 사이클이 끝난 뒤에야
> `plan/cycle-NN-*.md` 파일로 작성한다.
