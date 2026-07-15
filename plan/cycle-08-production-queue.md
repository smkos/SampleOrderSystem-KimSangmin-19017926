[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 8 — 생산 큐 계산 로직 (부족분/실생산량/총생산시간, FIFO) (GREEN 완료)

**이전 사이클**: [Cycle 7 — 주문 승인/거절 (재고 확인 → CONFIRMED/PRODUCING/REJECTED)](cycle-07-order-approval.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능(등록/영속화/컨트롤러 연동/검색)을 완성했다. Cycle 5~6에서
`Order`/`OrderStatus`, `OrderRegistry.create()`(검증/채번 후 `RESERVED` 생성),
`OrderController.create_order()`, `storage/order_repository.py`(`orders.json` 영속화)를
구현했다. Cycle 7에서는 `OrderRegistry.approve()`/`reject()`와
`OrderController.approve_order()`/`reject_order()`를 추가해, `RESERVED` 주문을 재고 충분 여부에
따라 `CONFIRMED` 또는 `PRODUCING`으로, 혹은 `REJECTED`로 전이시켰다. 다만 Cycle 7은 "상태
전이"까지만 다루었고, `PRODUCING`으로 전환된 주문들을 실제로 얼마나, 어떤 순서로 생산해야
하는지 계산하는 로직은 아직 없다 — 이번 사이클이 그 계산 로직을 다룬다.

## 목표

`PRD.md` §6.5(생산 라인)와 `SPEC.md` §4(계산 규칙)에 따라, 다음 두 가지 순수 계산 로직을
`model/production_queue.py`에 구현한다.

1. 시료 하나에 대한 부족분/실 생산량/총 생산 시간 계산.
2. `PRODUCING` 상태 주문들을 `created_at` 오름차순(FIFO)으로 정렬하는 생산 큐 조회.

## 설계 판단 (모호한 지점 — 검토 필요)

1. **순수 함수 vs 클래스**: `SPEC.md` §2가 `production_queue.py`를 "생산 큐 계산 로직 (순수
   함수: 부족분/실생산량/총생산시간)"이라고 명시적으로 "순수 함수"라 부르고 있으므로, Cycle
   5~7에서 `SampleRegistry`/`OrderRegistry`처럼 상태를 들고 있는 클래스를 만드는 대신 **모듈
   수준의 순수 함수 여러 개**로 구현한다. 이 모듈은 어떤 내부 상태도 갖지 않는다(인메모리
   저장소 역할을 하지 않는다).

2. **함수 시그니처 — 원시값 vs `Sample`/`Order` 객체**: 부족분/실 생산량/총 생산 시간 계산은
   `Sample`의 `avg_production_time_min`/`yield_rate`와 `Order`/재고 비교값(`quantity`,
   `stock_qty`)만 있으면 되고, `Sample`/`Order` 객체의 다른 필드(`sample_id`, `name`,
   `customer_name` 등)는 전혀 사용하지 않는다. `SPEC.md` §4가 계산 규칙을 필드명 수준의 원시값
   공식(`max(0, quantity - stock_qty)` 등)으로 정의하고 있는 점도 고려해, 이 세 계산 함수는
   `Sample`/`Order` 객체가 아니라 **원시값(`int`/`float`)을 인자로 받는다** — 이렇게 하면
   `model/order.py`, `model/sample.py`에 대한 의존이 없는 순수 계산 함수가 되어 재사용성과
   테스트 용이성이 높아진다. 실제 `Order`/`Sample`에서 값을 꺼내 이 함수에 넘기는 조립 책임은
   Cycle 8 범위 밖의 `controller/production_controller.py`(다음 사이클 후보)가 맡는다.
   - **확인 필요**: 이 판단에 이견이 있어 "Sample과 Order를 통째로 받는 함수"를 선호한다면
     시그니처를 바꿀 수 있다.
   - FIFO 정렬 함수(`sort_production_queue`)는 예외적으로 `Order` 객체 리스트를 받는다 —
     정렬 기준(`created_at`)과 필터 기준(`status == PRODUCING`)이 모두 `Order`의 필드이므로,
     원시값으로 분해해 받으면 오히려 호출부가 복잡해지기 때문이다.

3. **함수 구성 — 개별 계산 함수 vs 한 번에 묶은 함수**: 부족분 → 실 생산량 → 총 생산 시간은
   순차적으로 계산에 필요한 값이 이어지므로(부족분이 실 생산량의 입력, 실 생산량이 총 생산
   시간의 입력), 세 개의 독립된 함수로 나눈다(각각 단위 테스트가 명확해짐):
   - `calculate_shortage(quantity: int, stock_qty: int) -> int`
   - `calculate_actual_production_qty(shortage: int, yield_rate: float) -> int`
   - `calculate_total_production_time_min(avg_production_time_min: float, actual_production_qty: int) -> float`
   - 이 세 함수를 하나의 `Order`/`Sample` 쌍에 대해 한 번에 묶어 호출하는 "요약" 함수(예:
     생산 큐 화면에 표시할 주문별 계산 결과 묶음)는 이번 사이클에서 만들지 않는다 — 그 조립은
     Sample/Order 조회가 필요한 Controller 책임이라고 보기 때문이다(2번 판단과 동일한 근거).
     **확인 필요**: 필요하다고 판단되면 다음 컨트롤러 사이클에서 추가하거나, 이번 사이클에
     포함시킬 수 있다.

4. **FIFO 정렬 함수의 필터링 범위**: `SPEC.md` §4는 "`PRODUCING` 상태 주문을 `created_at`
   오름차순으로 정렬"이라고만 명시한다. `sort_production_queue(orders: list[Order]) -> list[Order]`는
   입력받은 `Order` 목록 중 `status == OrderStatus.PRODUCING`인 것만 걸러 정렬된 새 리스트로
   반환한다(원본 리스트는 변경하지 않음). `PRODUCING`이 아닌 주문을 걸러내는 책임을 호출부가 아닌
   이 함수 자체에 두는 이유는 "생산 큐"라는 이름 자체가 이미 "생산 중인 것들의 목록"을 의미하기
   때문이다.

5. **시각 mock 불필요**: `SPEC.md` §6은 "생산 큐 FIFO 정렬 기준 시각 — `pytest-mock`으로 시각
   생성 함수를 mock"이라고 안내하지만, 이는 새로운 `created_at`을 생성하는 경우(예:
   `OrderRegistry.create()`)에 해당하는 지침이다. 이번 사이클의 정렬 함수는 **이미 존재하는**
   `Order.created_at` 문자열 값을 비교만 할 뿐 새로 생성하지 않으므로, 테스트에서
   `model.order.Order(...)` 생성자를 직접 호출해 원하는 `created_at` 문자열을 명시적으로
   지정하면 충분하다(`OrderRegistry.create()`를 거칠 필요가 없어 `datetime` mock도 필요 없다).

## 이번 사이클에서 다룰 범위

`model/production_queue.py`에 다음 순수 함수를 구현한다.

- `calculate_shortage(quantity: int, stock_qty: int) -> int`
  - `max(0, quantity - stock_qty)`.
- `calculate_actual_production_qty(shortage: int, yield_rate: float) -> int`
  - `math.ceil(shortage / yield_rate)`.
  - `shortage == 0`이면 결과는 `0`.
- `calculate_total_production_time_min(avg_production_time_min: float, actual_production_qty: int) -> float`
  - `avg_production_time_min * actual_production_qty`.
- `sort_production_queue(orders: list[Order]) -> list[Order]`
  - `orders` 중 `status == OrderStatus.PRODUCING`인 것만 걸러 `created_at` 오름차순(문자열
    사전식 비교로 충분 — `created_at`은 ISO 8601 형식이므로 사전식 정렬이 시간 순서와 일치한다)
    으로 정렬한 새 리스트를 반환한다. 원본 리스트는 변경하지 않는다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `controller/production_controller.py`(생산 라인 현황, 대기 큐 조회) — `SampleRegistry`/
  `OrderRegistry`를 조회해 이 사이클의 계산 함수에 실제 값을 넘기고 결과를 조립하는 책임은
  별도 사이클로 미룬다(Cycle 2 → 3 전례와 동일하게 "순수 계산 로직 먼저, Controller 연동은
  별도"). `PLAN.md` 로드맵의 다음 사이클 후보로 남긴다.
- 생산 완료 처리(`PRODUCING → CONFIRMED`, `Sample.stock_qty` 갱신) — Cycle 9.
- 출고 처리(`CONFIRMED → RELEASE`) — Cycle 10.
- 콘솔 View/Controller 연동(생산 라인 메뉴 입출력) — Cycle 12.
- "현재 생산 중인 시료의 진행 상황(현재까지의 생산량 등)" 표기 — PRD §6.5가 "표기 수준은
  자율적으로 결정"이라 명시했고, 이는 계산 로직이 아니라 화면 구성/상태 추적의 문제이므로 이
  사이클(계산 로직)의 범위 밖이며, 향후 컨트롤러/View 연동 사이클에서 다룰 사안으로 남긴다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/production_queue.py`는 `model/`(Sample, Order, production_queue 계산) 계층으로,
  순수 로직이므로 mock을 사용하지 않는다.
- FIFO 정렬 테스트에 필요한 `Order` 인스턴스는 `OrderRegistry.create()`를 거치지 않고
  `model.order.Order(...)` 생성자를 직접 호출해 `created_at`을 원하는 문자열로 고정하므로,
  `datetime` mock도 필요 없다(설계 판단 5번).

## 작성할 실패 테스트 (예시)

```python
# tests/test_production_queue.py (신규 파일)

import math

from model.order import Order, OrderStatus
from model.production_queue import (
    calculate_actual_production_qty,
    calculate_shortage,
    calculate_total_production_time_min,
    sort_production_queue,
)


def test_주문수량이_재고보다_많으면_부족분은_차이값이다():
    assert calculate_shortage(quantity=200, stock_qty=50) == 150


def test_주문수량이_재고이하이면_부족분은_0이다():
    assert calculate_shortage(quantity=30, stock_qty=50) == 0


def test_실_생산량은_부족분을_수율로_나눈_뒤_올림한다():
    shortage = 150
    yield_rate = 0.92

    actual_qty = calculate_actual_production_qty(shortage, yield_rate)

    assert actual_qty == math.ceil(150 / 0.92)  # 164


def test_부족분이_0이면_실_생산량도_0이다():
    assert calculate_actual_production_qty(shortage=0, yield_rate=0.92) == 0


def test_총_생산_시간은_평균_생산시간과_실_생산량의_곱이다():
    total_time = calculate_total_production_time_min(
        avg_production_time_min=0.5, actual_production_qty=164
    )

    assert total_time == 82.0


def _order(order_id, status, created_at):
    return Order(order_id, "S-001", "삼성전자 파운드리", 100, status, created_at)


def test_생산큐는_PRODUCING_상태만_created_at_오름차순으로_정렬한다():
    later = _order("ORD-20260715-0003", OrderStatus.PRODUCING, "2026-07-15T11:00:00")
    earlier = _order("ORD-20260715-0001", OrderStatus.PRODUCING, "2026-07-15T09:00:00")
    not_producing = _order("ORD-20260715-0002", OrderStatus.CONFIRMED, "2026-07-15T08:00:00")

    queue = sort_production_queue([later, not_producing, earlier])

    assert [order.order_id for order in queue] == [earlier.order_id, later.order_id]


def test_생산큐_정렬은_원본_리스트를_변경하지_않는다():
    order_a = _order("ORD-20260715-0001", OrderStatus.PRODUCING, "2026-07-15T09:00:00")
    order_b = _order("ORD-20260715-0002", OrderStatus.PRODUCING, "2026-07-15T08:00:00")
    orders = [order_a, order_b]

    sort_production_queue(orders)

    assert orders == [order_a, order_b]
```

## 진행 결과

- **RED** (`861b6bc` 생산 큐 계산 로직 실패 테스트 작성): 위 7개 테스트를
  `tests/test_production_queue.py`에 작성해 실패를 확인했다.
- **GREEN** (`7067dd6` 생산 큐 계산 로직 최소 구현): `model/production_queue.py`에 계획대로
  `calculate_shortage`, `calculate_actual_production_qty`,
  `calculate_total_production_time_min`, `sort_production_queue` 4개 순수 함수를 구현했다.
- **verify-agent 독립 검증에서 결함 발견**: `SampleRegistry.register()`가 `SPEC.md` §1.1의
  `0 < yield_rate <= 1` 제약을 검증하지 않아, `yield_rate=0`인 시료가 등록되면
  `calculate_actual_production_qty()`에서 `ZeroDivisionError`가 날 수 있는 문제였다. 이는
  Cycle 8이 새로 만든 결함이 아니라 Cycle 1부터 있던 기존 갭이 이번에 처음 실질적 영향(0으로
  나누기)으로 드러난 것이다. 사람 파트너와 논의한 결과, 이 갭은 Cycle 1 범위에 별도의 미니
  RED→GREEN(`fbf1773`/`bd1d67c`)으로 보완하기로 했다(상세 내용은
  [Cycle 1 문서](cycle-01-sample-registration.md) 참고).
- **최종 결과**: `tests/test_production_queue.py`의 7개 테스트가 모두 통과하며, 전체 테스트
  48개(yield_rate 검증 보완 이전 기준. 보완 이후에는 51개)가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 `controller/production_controller.py`, 생산완료/출고 처리,
  `view/` 관련 코드는 포함하지 않았다. `model/order.py`, `model/sample.py`,
  `model/order_registry.py`, `model/sample_registry.py`(생산 큐 계산 자체와는 무관),
  `controller/order_controller.py`, `controller/sample_controller.py`는 이 사이클에서
  수정되지 않았다.
