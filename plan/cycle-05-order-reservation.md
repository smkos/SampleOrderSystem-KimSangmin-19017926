[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 5 — 주문 모델 + 접수(RESERVED)

**이전 사이클**: [Cycle 4 — 시료 검색](cycle-04-sample-search.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4를 통해 시료(Sample) 관련 기능이 모두 완성되었다. `model/sample.py`의 `Sample`은
데이터만 보관하고, `model/sample_registry.py`의 `SampleRegistry`가 인메모리 등록/중복
검증/검색을 담당하며, `storage/sample_repository.py`의 `SampleRepository`가 `samples.json`에
대한 원자적 쓰기와 동시성 충돌 감지를 수행한다. `controller/sample_controller.py`의
`SampleController`가 이 둘을 연결해 시작 시 로드, 등록 시 저장을 처리하고, 손상된 파일의 중복
`sample_id`는 `duplicate_sample_ids()`로 노출한다.

이제 시료 쪽 기반이 갖춰졌으므로, `PRD.md` §6.2(시료 주문)와 §4(주문 상태 흐름)에 정의된 주문
접수 기능을 시작한다. 이 사이클은 `Order`/`OrderStatus` 모델과, 주문을 `RESERVED` 상태로
생성하는 최소 로직을 다룬다. 승인/거절/생산/출고 등 이후 상태 전이와 `orders.json` 영속화는
아직 다루지 않는다.

## 목표

`SPEC.md` §1.2(Order 데이터 모델)의 `Order`/`OrderStatus`를 정의하고, `PRD.md` §6.2("입력값 —
시료 ID, 고객명, 주문 수량. 생성 직후 주문 상태는 `RESERVED`")에 따라 주문을 생성해 `RESERVED`
상태로 만드는 최소 동작을 구현한다.

## 설계 판단 (모호한 지점 — 검토 필요)

`SPEC.md`는 `Order`의 필드와 검증 규칙, 모듈 구조(`model/order.py`, `controller/order_controller.py`)만
정의하고 있고, 주문 생성 로직을 어느 계층에 둘지, 주문 ID를 어떻게 생성할지는 구체적으로
명시하지 않는다. Cycle 1~4에서 확립된 `Sample`/`SampleRegistry`/`SampleController` 패턴을
그대로 확장해 다음과 같이 판단했다 (이견이 있으면 조정):

1. **`model/order.py`**: `Sample`과 동일하게 데이터만 보관한다 (SPEC §2: "Order — 데이터와
   상태만 보관"). `Order.__init__`은 `order_id`, `sample_id`, `customer_name`, `quantity`,
   `status`, `created_at`을 그대로 받아 저장할 뿐, 검증이나 상태 전이 로직을 갖지 않는다.
   `OrderStatus`는 `RESERVED`/`REJECTED`/`PRODUCING`/`CONFIRMED`/`RELEASE` 값을 갖는
   `enum.Enum`으로 정의한다.

2. **주문 생성/검증 로직의 위치**: `SampleRegistry`가 "등록된 시료를 인메모리로 보관하고, 등록
   시 검증을 수행"하는 것과 같은 층위로, `model/order_registry.py`에 새 `OrderRegistry`를 둔다.
   다만 `Sample`은 ID를 사용자가 직접 지정하는 반면 `Order`는 ID를 시스템이 생성해야 하므로
   (`ORD-YYYYMMDD-NNNN`), `SampleRegistry.register(sample)`처럼 완성된 객체를 받는 대신
   `OrderRegistry.create(sample_id, customer_name, quantity)`가 다음을 모두 수행한다:
   - `customer_name`이 공백만 있으면 거부 (`ValueError`).
   - `quantity <= 0`이면 거부 (`ValueError`).
   - 현재 시각을 기준으로 `order_id`(`ORD-YYYYMMDD-NNNN`, 같은 날짜 접두사를 가진 기존 주문
     수 + 1을 4자리로 패딩)와 `created_at`(ISO 8601)을 생성한다.
   - `status=OrderStatus.RESERVED`로 고정해 `Order`를 만들고 내부 목록에 추가한 뒤 반환한다.

   `존재하지 않는 sample_id로 주문 생성 시도 거부`(SPEC §5)는 `OrderRegistry`가 아니라
   `SampleRegistry`(시료 목록)에 대한 지식이 필요하므로 `OrderRegistry`의 책임 밖으로 둔다.

3. **`controller/order_controller.py`**: `SampleController`가 `SampleRegistry` +
   `SampleRepository`를 연결하는 것처럼, `OrderController`는 `OrderRegistry` + (아직
   영속화가 없으므로) `SampleRegistry`를 연결한다.
   `OrderController(order_registry: OrderRegistry, sample_registry: SampleRegistry)`로 구성하고,
   `create_order(sample_id, customer_name, quantity) -> Order`가:
   - 먼저 `sample_registry.list_all()`에 해당 `sample_id`가 없으면 `ValueError`로 거부한다
     (SPEC §5 "존재하지 않는 `sample_id`로 주문 생성 시도 → 거부").
   - 있으면 `order_registry.create(...)`를 그대로 호출해 위임한다.

   `SampleController`가 아니라 `SampleRegistry`를 직접 참조하는 이유: 이 시점의 검증은 "현재
   메모리에 등록된 시료 목록에 있는가"만 확인하면 되고, `SampleController`가 담당하는
   저장소 연동/중복 데이터 필터링은 이미 애플리케이션 시작 시 끝나 있는 관심사이기 때문이다.
   Controller 간 직접 의존(`SampleController` 참조)이 아니라 Model 계층(`SampleRegistry`)을
   공유하는 방식을 택해 결합도를 낮췄다 — **확인 필요**: 추후 View/Controller 통합(Cycle 12)
   시점에 이 구성이 어색하면 조정 가능하다.

4. **주문 ID/시각 생성과 mock 설계** (`SPEC.md` §6 마지막 행: "`Order.created_at` 생성...
   pytest-mock으로 시각 생성 함수를 mock해 결정적으로 테스트"): `model/order_registry.py`가
   모듈 최상단에서 `import datetime`하고, `OrderRegistry.create()` 내부에서
   `datetime.datetime.now()`를 직접 호출한다. 테스트에서는 생성자 주입(DI) 대신
   `mocker.patch("model.order_registry.datetime")`으로 `datetime.now()`가 고정된 값을
   반환하도록 격리해 `order_id`/`created_at`을 결정적으로 검증한다. SPEC이 명시적으로
   "pytest-mock으로 시각 생성 함수를 mock"하라고 했으므로, 생성자 파라미터로 시각 함수를
   주입받는 대안(DI) 대신 이 방식을 택했다 — **확인 필요**: DI 방식(예:
   `OrderRegistry(now_fn=datetime.datetime.now)`)이 더 명확한 테스트를 만든다는 반론이
   있다면 GREEN 단계 이전에 조정 가능하다.

## 이번 사이클에서 다룰 범위

- `model/order.py`:
  - `OrderStatus(enum.Enum)`: `RESERVED`, `REJECTED`, `PRODUCING`, `CONFIRMED`, `RELEASE`.
  - `Order`: `order_id`, `sample_id`, `customer_name`, `quantity`, `status`, `created_at`
    필드만 보관하는 데이터 클래스 (검증/전이 로직 없음).
- `model/order_registry.py`:
  - `OrderRegistry.create(sample_id: str, customer_name: str, quantity: int) -> Order`
    - `customer_name` 공백만 있으면 `ValueError`.
    - `quantity <= 0`이면 `ValueError`.
    - `order_id`를 `ORD-YYYYMMDD-NNNN` 형식으로 생성 (같은 날짜의 기존 주문 수 기준 4자리
      일련번호).
    - `created_at`을 ISO 8601 문자열로 생성.
    - `status=OrderStatus.RESERVED`로 `Order`를 만들어 내부 목록에 저장 후 반환.
  - `OrderRegistry.list_all() -> list[Order]`
- `controller/order_controller.py`:
  - `OrderController(order_registry: OrderRegistry, sample_registry: SampleRegistry)`
  - `create_order(sample_id: str, customer_name: str, quantity: int) -> Order`
    - `sample_registry`에 없는 `sample_id`면 `ValueError`로 거부.
    - 있으면 `order_registry.create(...)`에 위임.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `storage/order_repository.py`(주문 영속화, `orders.json` 저장/로드) — Cycle 6.
- 주문 승인/거절 로직 (`RESERVED → REJECTED`/`CONFIRMED`/`PRODUCING` 전이), 재고 확인 분기 —
  Cycle 7.
- 생산 완료 처리(`PRODUCING → CONFIRMED`), 생산 큐 계산(부족분/실생산량/총생산시간, FIFO
  정렬) — Cycle 8~9.
- 출고 처리(`CONFIRMED → RELEASE`) — Cycle 10.
- 허용되지 않은 상태 전이에 대한 예외 처리(SPEC §1.3) — 아직 전이 자체가 없으므로 이후 사이클.
- `view/console_view.py` 및 메뉴 입출력 — Cycle 12.
- `OrderController`가 `SampleController`/저장소와 연동하는 구조 — 영속화가 도입되는 Cycle 6
  이후 재검토.

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/order.py`, `model/order_registry.py`의 검증/ID 생성 로직은 "순수 로직" 계층이지만,
  `order_id`/`created_at` 생성에 쓰이는 "시스템 시각"만은 SPEC §6이 명시한 외부 경계이므로
  `pytest-mock`의 `mocker.patch("model.order_registry.datetime")`으로 격리해 결정적으로
  테스트한다. 그 외 검증 로직(공백 고객명, 수량 0 이하)은 mock 없이 실제 객체로 검증한다.
- `controller/order_controller.py`는 "내부 협력" 계층이므로 실제 `OrderRegistry`,
  `SampleRegistry`를 조합해 테스트하고 mock을 사용하지 않는다 (시각 mock은 내부적으로
  `OrderRegistry`가 필요로 하므로 컨트롤러 테스트에서도 `mocker.patch`를 그대로 사용한다).

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_registry.py (신규)

import datetime as datetime_module

import pytest

from model.order import OrderStatus
from model.order_registry import OrderRegistry


def _mock_now(mocker, fixed_datetime):
    mock_datetime = mocker.patch("model.order_registry.datetime")
    mock_datetime.datetime.now.return_value = fixed_datetime


def test_생성된_주문은_RESERVED_상태이다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    order = registry.create("S-001", "삼성전자 파운드리", 200)

    assert order.status == OrderStatus.RESERVED


def test_주문_ID는_ORD_날짜_4자리_일련번호_형식이다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    order = registry.create("S-001", "삼성전자 파운드리", 200)

    assert order.order_id == "ORD-20260715-0001"


def test_같은_날_두번째_주문은_일련번호가_증가한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    registry.create("S-001", "삼성전자 파운드리", 200)

    second = registry.create("S-002", "SK하이닉스", 50)

    assert second.order_id == "ORD-20260715-0002"


def test_고객명이_공백만_있으면_거부한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.create("S-001", "   ", 200)


def test_수량이_0이하이면_거부한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.create("S-001", "삼성전자 파운드리", 0)
```

```python
# tests/test_order_controller.py (신규)

import datetime as datetime_module

import pytest

from controller.order_controller import OrderController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def test_등록되지_않은_시료ID로_주문하면_거부한다(mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    controller = OrderController(OrderRegistry(), SampleRegistry())

    with pytest.raises(ValueError):
        controller.create_order("S-999", "삼성전자 파운드리", 200)


def test_등록된_시료ID면_RESERVED_상태의_주문이_생성된다(mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)

    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    assert order.sample_id == "S-001"
    assert order.status == OrderStatus.RESERVED
```

## 검토 요청

이 목표/범위로 RED 단계를 진행해도 될지 검토 부탁드립니다. 특히 위 "설계 판단" 3, 4번
(`OrderController`가 `SampleRegistry`를 직접 참조하는 구조, `datetime` 모듈 mock 방식)에
이견이 없는지 확인 부탁드립니다.

---

**다음 사이클**: 아직 계획되지 않음
