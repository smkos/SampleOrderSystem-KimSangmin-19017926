[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 7 — 주문 승인/거절 (재고 확인 → CONFIRMED/PRODUCING/REJECTED) (GREEN 완료)

**이전 사이클**: [Cycle 6 — 주문 영속화 (`OrderRepository`)](cycle-06-order-persistence.md)
**다음 사이클**: [Cycle 8 — 생산 큐 계산 로직 (부족분/실생산량/총생산시간, FIFO)](cycle-08-production-queue.md)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능(등록/영속화/컨트롤러 연동/검색)이 완성되었다. Cycle 5에서
`model/order.py`(`Order`, `OrderStatus`)와 `model/order_registry.py`(`OrderRegistry.create()` —
검증/채번 후 `RESERVED` 상태로 주문 생성), `controller/order_controller.py`
(`OrderController.create_order()` — 존재하지 않는 `sample_id` 거부 후 `OrderRegistry`에 위임)를
구현했다. `OrderController`는 `SampleController`가 아니라 `SampleRegistry`를 직접 참조하는
구조이며, 이는 "시료가 존재하는가"만 확인하면 되는 관심사이기 때문이었다 (Cycle 5 설계 판단 3번).
Cycle 6에서는 `storage/order_repository.py`(`OrderRepository`)로 `orders.json` 영속화(원자적
쓰기 + 충돌 감지)를 구현했으나, 아직 `OrderController`/`OrderRegistry`와 연결되어 있지 않다
(애플리케이션을 재시작하면 주문이 사라지는 상태 그대로).

`Order`는 지금까지 `status`가 생성 시 한 번 정해지고 이후 바뀐 적이 없는, 사실상 "생성 전용"
데이터 클래스로만 다뤄져 왔다. 이번 사이클이 처음으로 `Order`의 상태를 생성 이후에 변경하는
로직을 도입한다.

## 목표

`PRD.md` §6.3(주문 승인/거절)과 `SPEC.md` §1.3(상태 전이 규칙)에 따라, `RESERVED` 상태의 주문을
승인하면 재고 충분 여부(`SPEC.md` §4: `quantity <= stock_qty`)에 따라 `CONFIRMED` 또는
`PRODUCING`으로 전환하고, 거절하면 즉시 `REJECTED`로 전환하는 최소 동작을 구현한다.
`RESERVED`가 아닌 주문에 대한 승인/거절 시도는 예외를 발생시키고 상태를 바꾸지 않는다
(`SPEC.md` §5, §1.3).

## 설계 판단 (모호한 지점 — 검토 필요)

`SPEC.md`는 상태 전이 규칙(§1.3)과 계산 규칙(§4: 재고 충분 여부)만 정의하고, 승인/거절 로직을
`OrderRegistry`와 `OrderController` 중 어디에 둘지, `Order`의 상태를 어떻게 바꿀지는 구체적으로
명시하지 않는다. Cycle 5에서 `create_order`를 나눈 방식(존재 검증은 컨트롤러, 실제 생성/채번은
레지스트리)을 그대로 확장해 다음과 같이 판단했다 (이견이 있으면 조정):

1. **책임 분리 — `OrderRegistry` vs `OrderController`**: `OrderRegistry`는 `Order` 목록만 알고
   `Sample`/재고에 대한 지식이 없어야 한다(Cycle 5에서 확립된 경계: "존재하지 않는 `sample_id`로
   주문 생성 시도 거부"도 `OrderRegistry`가 아니라 `OrderController`가 `SampleRegistry`를 참조해
   처리했다). 따라서:
   - `OrderRegistry`에 `get(order_id) -> Order`(없으면 `ValueError`),
     `approve(order_id, stock_sufficient: bool) -> Order`,
     `reject(order_id) -> Order`를 추가한다. `approve`/`reject` 모두 대상 주문이 `RESERVED`가
     아니면 `ValueError`를 던지고 상태를 바꾸지 않는다. 재고 판단(`stock_sufficient`)은 이미
     계산된 `bool` 값을 인자로만 받을 뿐, 재고 자체는 조회하지 않는다.
   - `OrderController`에 `approve_order(order_id) -> Order`,
     `reject_order(order_id) -> Order`를 추가한다. `approve_order`는
     ① `order_registry.get(order_id)`로 대상 주문을 찾고, ② `sample_registry.list_all()`에서
     같은 `sample_id`의 `Sample`을 찾아 `order.quantity <= sample.stock_qty`를 계산한 뒤,
     ③ `order_registry.approve(order_id, stock_sufficient)`에 위임한다. `reject_order`는 바로
     `order_registry.reject(order_id)`에 위임한다.
   - **확인 필요**: `approve_order`가 대상 `Sample`을 못 찾는 경우(이론상 발생하지 않아야 함 —
     주문 생성 시 이미 `sample_id` 존재가 검증됨)를 별도로 방어할지는 이번 사이클 범위에서
     결정하지 않고, 발생 시 자연스러운 `StopIteration`/`None` 접근 오류로 남겨둔다. 필요하다고
     판단되면 GREEN 단계 이전에 명시적 방어 코드를 추가할 수 있다.

2. **존재하지 않는 `order_id`에 대한 승인/거절**: `SPEC.md` §5는 "`RESERVED`가 아닌 주문에 대한
   승인/거절 시도 → 거부"만 명시하고, 아예 존재하지 않는 `order_id`에 대한 처리는 명시하지
   않는다. `SampleController`가 존재하지 않는 `sample_id`를 `ValueError`로 거부해 온 기존
   패턴을 그대로 확장해, `OrderRegistry.get()`이 없으면 `ValueError`를 던지도록 한다 —
   **확인 필요**: SPEC에 명시되지 않은 확장이므로, 이 판단에 이견이 있으면 조정 가능하다.

3. **`Order` 상태 변경 방식 — 필드 직접 변경 vs 새 인스턴스 교체**: 현재 `Order`는 `dataclass`가
   아닌 일반 클래스이며 `frozen`이나 캡슐화 장치가 없는 평범한 가변(mutable) 객체다
   (`model/order.py` 참고). 이번 사이클에서 `OrderRegistry.approve()`/`reject()`는 리스트에서
   찾은 `Order` 객체의 `status` 필드를 **직접 변경**(`order.status = OrderStatus.CONFIRMED` 등)하는
   방식을 택한다. 새 `Order` 인스턴스를 만들어 리스트의 기존 원소를 교체하는 대신 이 방식을
   택한 이유:
   - `Order`가 이미 `__init__`에서 모든 필드를 공개 속성으로 노출하는 평범한 클래스라, 굳이
     불변성을 흉내 낼 이유가 없다.
   - `OrderController.create_order()`가 반환한 `Order`를 View/호출자가 들고 있다가, 이후
     `OrderRegistry.list_all()`로 조회한 "같은" 주문의 상태 변화를 참조 일관성 있게 반영하려면
     제자리 변경이 더 단순하다(새 인스턴스로 교체하면 먼저 반환됐던 참조는 상태가 갱신되지
     않는 문제가 생긴다).
   - **확인 필요**: `Sample`도 향후 `stock_qty`가 변경될 가능성이 있는데(생산 완료/출고 시),
     이때도 동일하게 "필드 직접 변경" 방식을 따를 것인지는 이번 사이클에서 결정하지 않고
     `Order`에 한해서만 이 판단을 적용한다. `Sample.stock_qty` 변경 방식은 해당 기능을 다루는
     사이클(생산 완료 처리 등)에서 별도로 재확인한다.

4. **컨트롤러/레지스트리 어디에도 `datetime` mock이 필요 없음**: 승인/거절은 새로운
   `order_id`/`created_at`을 생성하지 않으므로(이미 생성된 주문의 상태만 바꿈), Cycle 5와 달리
   `datetime` mock이 필요 없다. 다만 테스트에서 승인/거절 대상 주문을 만들려면
   `OrderRegistry.create()`를 거쳐야 하므로, 그 준비 단계에서는 Cycle 5와 동일하게
   `mocker.patch("model.order_registry.datetime")`을 사용한다(승인/거절 자체의 검증 로직에는
   mock이 필요 없다는 뜻).

## 이번 사이클에서 다룰 범위

- `model/order_registry.py`:
  - `OrderRegistry.get(order_id: str) -> Order`: 없으면 `ValueError`.
  - `OrderRegistry.approve(order_id: str, stock_sufficient: bool) -> Order`:
    - 대상 주문이 없으면 `ValueError`.
    - 대상 주문이 `RESERVED`가 아니면 `ValueError`(상태 변경 없음).
    - `stock_sufficient`가 `True`면 `status`를 `CONFIRMED`로, `False`면 `PRODUCING`으로 직접
      변경(mutate)하고 해당 `Order`를 반환.
  - `OrderRegistry.reject(order_id: str) -> Order`:
    - 대상 주문이 없으면 `ValueError`.
    - 대상 주문이 `RESERVED`가 아니면 `ValueError`(상태 변경 없음).
    - `status`를 `REJECTED`로 직접 변경하고 해당 `Order`를 반환.
- `controller/order_controller.py`:
  - `OrderController.approve_order(order_id: str) -> Order`: `order_registry.get()`으로 주문을
    찾고, `sample_registry.list_all()`에서 같은 `sample_id`의 `Sample.stock_qty`와
    `order.quantity`를 비교해 `stock_sufficient`를 계산한 뒤 `order_registry.approve()`에 위임.
  - `OrderController.reject_order(order_id: str) -> Order`: `order_registry.reject()`에 위임.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- "재고 부족 → 생산 라인에 자동 등록"의 실제 생산 큐 계산(부족분/실생산량/총생산시간, FIFO
  정렬) — `PRODUCING` 상태로 전환하는 것까지만 이번 사이클 범위이며, 생산 큐에 실제로 등록하는
  로직(`model/production_queue.py`)은 Cycle 8에서 다룬다.
- 생산 완료 처리(`PRODUCING → CONFIRMED`) — Cycle 9.
- 출고 처리(`CONFIRMED → RELEASE`) — Cycle 10.
- `OrderController`/`OrderRegistry`와 `OrderRepository`의 영속화 연동(승인/거절 후 자동 저장
  등) — 아직 로드맵에 명시된 사이클이 없다. Cycle 6에서와 동일한 이유로, 저장소 연동은 별도
  사이클에서 다룰 별개의 관심사로 보고 이번에도 포함하지 않는다.
- 콘솔 View/Controller 연동(승인/거절 메뉴 입출력) — Cycle 12.
- `RESERVED` 상태의 주문 목록 표시(PRD §6.3 "접수된 주문 목록") — View 연동이 필요한 조회
  기능이므로 Cycle 12에서 다룬다. 이번 사이클은 승인/거절이라는 상태 전이 자체에만 집중한다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/order_registry.py`의 `get`/`approve`/`reject`는 순수 로직(상태 전이, 존재 검증)이므로
  mock 없이 실제 `OrderRegistry`/`Order`로 직접 테스트한다. 다만 테스트용 주문을 만들기 위한
  `create()` 호출 준비 과정에서는 Cycle 5와 동일하게 `mocker.patch("model.order_registry.datetime")`을
  사용한다(주문 생성 자체는 이번 사이클의 대상이 아니므로 결정적 시각만 고정하면 충분하다).
- `controller/order_controller.py`는 "내부 협력" 계층이므로 실제 `OrderRegistry`,
  `SampleRegistry`를 조합해 테스트하고 mock을 사용하지 않는다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_registry.py (기존 파일에 추가)

import datetime as datetime_module

import pytest

from model.order import OrderStatus
from model.order_registry import OrderRegistry


def _mock_now(mocker, fixed_datetime):
    mock_datetime = mocker.patch("model.order_registry.datetime")
    mock_datetime.datetime.now.return_value = fixed_datetime


def test_재고가_충분하면_승인시_CONFIRMED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)

    approved = registry.approve(order.order_id, stock_sufficient=True)

    assert approved.status == OrderStatus.CONFIRMED


def test_재고가_부족하면_승인시_PRODUCING으로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)

    approved = registry.approve(order.order_id, stock_sufficient=False)

    assert approved.status == OrderStatus.PRODUCING


def test_거절하면_REJECTED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)

    rejected = registry.reject(order.order_id)

    assert rejected.status == OrderStatus.REJECTED


def test_RESERVED가_아닌_주문을_승인하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.reject(order.order_id)

    with pytest.raises(ValueError):
        registry.approve(order.order_id, stock_sufficient=True)
    assert registry.get(order.order_id).status == OrderStatus.REJECTED


def test_RESERVED가_아닌_주문을_거절하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=True)

    with pytest.raises(ValueError):
        registry.reject(order.order_id)
    assert registry.get(order.order_id).status == OrderStatus.CONFIRMED


def test_존재하지_않는_주문ID를_승인하면_예외가_발생한다():
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.approve("ORD-20260715-9999", stock_sufficient=True)
```

```python
# tests/test_order_controller.py (기존 파일에 추가)

import datetime as datetime_module

import pytest

from controller.order_controller import OrderController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def _mock_now(mocker, fixed_datetime):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = fixed_datetime


def test_재고가_충분하면_승인시_CONFIRMED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    approved = controller.approve_order(order.order_id)

    assert approved.status == OrderStatus.CONFIRMED


def test_재고가_부족하면_승인시_PRODUCING으로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    approved = controller.approve_order(order.order_id)

    assert approved.status == OrderStatus.PRODUCING


def test_거절하면_REJECTED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    rejected = controller.reject_order(order.order_id)

    assert rejected.status == OrderStatus.REJECTED
```

## 진행 결과

- **계획** (`0f18283` Cycle 7 계획: 주문 승인/거절 (재고 확인 → CONFIRMED/PRODUCING/REJECTED)):
  위 "설계 판단" 1~3번(`OrderRegistry`/`OrderController` 책임 분리, 존재하지 않는 `order_id` →
  `ValueError`, `Order` 상태의 제자리 변경 방식)을 사람 파트너 검토를 거쳐 이견 없이 그대로
  채택했다.
- **RED** (`53488b7` Cycle 7 RED: 주문 승인/거절 실패 테스트 작성): 위 예시 테스트대로
  `tests/test_order_registry.py`(6개 신규)와 `tests/test_order_controller.py`(3개 신규)를
  작성해 실패를 확인했다.
- **GREEN** (`0608d9a` Cycle 7 GREEN: 주문 승인/거절 최소 구현): `model/order_registry.py`에
  `OrderRegistry.get/approve/reject`를, `controller/order_controller.py`에
  `OrderController.approve_order/reject_order`를 계획대로 구현했다. `approve`/`reject`는
  대상 주문이 `RESERVED`가 아니면 `ValueError`를 던지고 상태를 바꾸지 않으며, `Order` 상태는
  리스트에서 찾은 객체의 `status` 필드를 직접 변경(mutate)하는 방식으로 구현했다.
- **verify-agent 독립 검증**: `Order` 상태 제자리 변경이 실제로 참조 일관되게 동작하는지
  (`get()`이 반환한 실제 객체의 필드를 직접 변경하는지), 그리고 예외가 상태 변경보다 먼저
  발생하는지(`RESERVED`가 아닌 주문을 승인/거절 시도할 때 상태가 바뀌지 않는지) 코드를 직접
  대조해 확인했고 문제 없음을 확인했다.
- **최종 결과**: `tests/test_order_registry.py`(6개 신규) + `tests/test_order_controller.py`
  (3개 신규) = 9개 테스트가 모두 통과하며, Cycle 1~6을 포함한 전체 테스트 41개가 회귀 없이
  통과한다.
- **범위 준수 확인**: 계획대로 생산 큐 계산, 생산완료/출고 처리, `OrderRepository` 연동,
  `view/` 관련 코드는 포함하지 않았다. `model/order.py`, `model/sample.py`,
  `model/sample_registry.py`, `storage/order_repository.py`, `storage/sample_repository.py`,
  `controller/sample_controller.py`는 수정되지 않았다.
