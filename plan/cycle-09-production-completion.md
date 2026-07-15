[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 9 — 생산 완료 처리 (PRODUCING → CONFIRMED)

**이전 사이클**: [Cycle 8 — 생산 큐 계산 로직 (부족분/실생산량/총생산시간, FIFO)](cycle-08-production-queue.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능을 완성했다. Cycle 5~7에서 `Order`/`OrderStatus`,
`OrderRegistry.create()`, `OrderController.create_order()`, `storage/order_repository.py`,
그리고 `OrderRegistry.approve()`/`reject()` + `OrderController.approve_order()`/`reject_order()`를
구현해 `RESERVED` 주문을 재고 충분 여부에 따라 `CONFIRMED` 또는 `PRODUCING`으로, 혹은
`REJECTED`로 전이시켰다. Cycle 8에서는 `model/production_queue.py`에 부족분/실 생산량/총
생산 시간을 계산하는 순수 함수 3개(`calculate_shortage`, `calculate_actual_production_qty`,
`calculate_total_production_time_min`)와 FIFO 정렬 함수(`sort_production_queue`)를 구현했다.
다만 이 계산 함수들은 아직 실제 `Order`/`Sample` 데이터와 연결되지 않았고, `PRODUCING` 상태로
전환된 주문이 실제로 "생산 완료"되었을 때 무슨 일이 일어나는지(상태 전이, 재고 갱신)는 아직
구현되어 있지 않다 — 이번 사이클이 그 부분을 다룬다.

이번 사이클은 두 가지 이전 사이클에서 명시적으로 "확인 필요"로 미뤄둔 사안을 함께 해소한다.

1. Cycle 4→6 정합성 점검에서 지적된 낮은 우선순위 이슈: "생산 완료 처리(`PRODUCING`→
   `CONFIRMED`)를 어느 컨트롤러가 담당할지 `SPEC.md`에 명시되어 있지 않다."
2. Cycle 7 설계 판단 3번에서 미뤄둔 사안: "`Sample.stock_qty` 변경 방식은 생산 완료 처리를
   다루는 사이클에서 별도로 재확인한다."

## 목표

`PRD.md` §6.5(생산 라인)와 `SPEC.md` §1.3(상태 전이 규칙: `PRODUCING --생산완료--> CONFIRMED`)에
따라, `PRODUCING` 상태 주문의 생산을 완료 처리하면 ① 주문 상태가 `CONFIRMED`로 전환되고,
② 해당 시료(`Sample`)의 재고(`stock_qty`)가 `SPEC.md` §4의 "실 생산량"(`ceil(부족분/수율)`)만큼
증가하는 최소 동작을 구현한다. `PRODUCING`이 아닌 주문에 대한 생산완료 시도는 예외를
발생시키고 상태·재고 모두 변경하지 않는다(`SPEC.md` §1.3의 "허용되지 않은 전이" 원칙을
`PRODUCING→CONFIRMED` 전이에도 동일하게 적용).

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. 생산완료 처리를 어느 모듈/컨트롤러가 담당하는가

`SPEC.md` §2는 `order_controller.py`를 "주문 생성, 승인/거절, 출고 처리"로,
`production_controller.py`를 "생산 라인 현황, 대기 큐 조회"로 서술한다. 두 서술 모두 문자
그대로는 "생산 완료 처리(상태 전이 + 재고 갱신)"를 명시적으로 포함하지 않는다 — 이것이
Cycle 4→6 정합성 점검에서 지적된 갭이다.

두 후보를 검토했다.

- **후보 A: `order_controller.py`가 담당.** 근거: 생산완료도 결국 "주문 상태 전이"이고,
  `approve_order`/`reject_order`/(향후) 출고 처리와 같은 성격의 조작이라는 점에서 일관성이
  있다. `SPEC.md` §2 서술의 "승인/거절, 출고 처리"와 나란히 "생산완료 처리"를 추가하는 것도
  자연스럽다.
- **후보 B: `production_controller.py`(신규)가 담당.** 근거: `PRD.md` §6.5는 "생산 완료 시
  주문 상태를 `PRODUCING → CONFIRMED`로 변경"이라는 문장을 §6.3(주문 승인/거절)이나
  §6.6(출고 처리)이 아니라 **§6.5(생산 라인)** 절 안에 명시하고 있다. `PRD.md` §5의 메뉴 표에서도
  "생산 라인" 메뉴가 "현재 생산 중인 시료 및 대기 중인 생산 큐 확인"을 담당하도록 정의되어
  있어, 생산 진행 상황을 다루는 화면/로직이 이 메뉴(및 그 배후의 컨트롤러)에 속한다고 보는
  편이 PRD의 절 구성과 일치한다. 또한 재고 갱신 계산에 Cycle 8에서 만든
  `production_queue.py`의 순수 함수(`calculate_shortage`, `calculate_actual_production_qty`)를
  그대로 사용해야 하는데, 이 함수들은 "생산 라인" 도메인에 속하는 계산으로 설계되었다
  (Cycle 8 설계 판단 2번). `order_controller.py`는 지금까지 이 계산 함수들을 전혀 참조하지
  않았고, 승인/거절/출고는 재고를 "확인"만 할 뿐 "증가"시키지 않는다는 점에서 생산완료와
  성격이 다르다.

**판단**: 후보 B(`production_controller.py`)를 채택한다. PRD가 생산완료 전이를 "생산 라인"
절에 명시적으로 배치한 점이 가장 직접적인 근거이고, 재고를 계산해 갱신하는 로직이 이미
`production_queue.py`(생산 라인 도메인)에 있다는 점도 이를 뒷받침한다. 이번 사이클에서
`controller/production_controller.py`를 신규로 만들고, "생산 라인 현황/대기 큐 조회"뿐 아니라
"생산 완료 처리"도 이 모듈의 책임으로 삼는다.

**확인 필요 / SPEC.md 갱신 필요**: 이 판단이 맞다면, `SPEC.md` §2의 `production_controller.py`
서술을 "생산 라인 현황, 대기 큐 조회"에서 "생산 라인 현황, 대기 큐 조회, 생산 완료 처리"
등으로 갱신해 이 모호함을 해소해야 한다. 다만 이번 요청 범위는 계획(RED) 수립까지이므로,
`SPEC.md` 문서 자체의 수정은 이번 계획 승인 이후 별도로 반영한다. 이 판단(후보 A vs B)에
이견이 있으면 GREEN 진행 전에 조정 가능하다.

### 2. `Sample.stock_qty` 갱신 방식

Cycle 7 설계 판단 3번에서 `Order.status`를 "필드 직접 변경(mutate)" 방식으로 정하며,
`Sample.stock_qty` 갱신 방식은 이 사이클에서 재확인하기로 미뤄뒀다. `Order`와 동일한 이유로
(평범한 가변 클래스이고, 기존에 반환된 참조와의 일관성을 유지하려면 제자리 변경이 더
단순하다) **`Sample.stock_qty`도 필드 직접 변경(mutate) 방식을 그대로 따른다.**

이를 위해 `model/sample_registry.py`에 새 메서드 `SampleRegistry.increase_stock(sample_id: str,
qty: int) -> Sample`을 추가한다.

- 존재하지 않는 `sample_id`면 `ValueError`.
- `qty < 0`이면 `ValueError`(재고를 감소시키는 용도가 아님을 명확히 함 — 출고에 의한 재고
  감소는 Cycle 10에서 별도 메서드로 다룰 사안이며 이번 범위가 아니다).
- `qty == 0`은 허용한다. 이는 생산완료 시점에 이미 다른 주문의 생산완료로 재고가 채워져
  실 생산량이 0이 되는 경우(아래 3번 참고)를 자연스럽게 처리하기 위함이다.
- 대상 `Sample`을 찾아 `sample.stock_qty += qty`로 제자리 변경하고 해당 `Sample`을 반환한다.

### 3. "실 생산량" 계산 시점 — 승인 시점 값을 재사용하는가, 완료 시점에 재계산하는가

`SPEC.md` §4는 "실 생산량 = `ceil(부족분/수율)`"이라고만 정의하고, 이 계산을 언제(승인
시점? 완료 시점?) 수행해 어디에 저장해 두는지는 규정하지 않는다. `Order`/`Sample` 모델
어디에도 "이 주문을 위해 계산된 실 생산량"을 저장하는 필드가 없으므로(SPEC §1.1, §1.2에
그런 필드가 없음), 이번 사이클은 **생산완료 처리 시점에 `order.quantity`와 그 시점의
`sample.stock_qty`로 부족분/실 생산량을 다시 계산**하는 방식을 택한다. 근거:

- 생산 라인은 단일 라인이며 여러 주문이 `PRODUCING` 큐에 쌓일 수 있다(Cycle 8의 FIFO 큐).
  앞선 주문의 생산완료로 재고가 먼저 늘어난 뒤에 다음 주문이 완료 처리될 수 있으므로, 완료
  시점의 최신 `stock_qty` 기준으로 재계산하는 것이 "그 시점에 실제로 더 생산해야 하는 양"을
  더 정확히 반영한다(승인 시점에 계산해 어딘가에 저장해 두면, 그 값이 이후 재고 변화와 어긋날
  수 있다).
- **확인 필요**: 승인 시점 값을 고정해 저장하는 방식(예: `Order`에 필드 추가)을 선호한다면
  `SPEC.md` §1.2에 필드를 추가하는 별도 논의가 필요하며, 이번 사이클 범위를 벗어난다. 이견이
  있으면 조정 가능하다.

### 4. 처리 순서 — 상태 전이를 먼저, 재고 갱신을 나중에

생산완료 처리 도중 대상 주문이 `PRODUCING`이 아니면 예외를 던지고 재고를 전혀 건드리지
않아야 한다(부분 실패로 재고만 늘어나는 상황 방지). 이를 위해 `OrderRegistry.complete_
production(order_id)`가 (Cycle 7의 `approve`/`reject`와 동일하게) 상태 검증과 전이를 먼저
수행해 실패 시 즉시 예외를 던지도록 하고, `ProductionController.complete_production()`은 이
호출이 성공한 뒤에야 부족분/실 생산량을 계산해 `SampleRegistry.increase_stock()`을 호출한다.
(`order.quantity`와 `sample.stock_qty`는 상태 전이 자체와 무관한 값이므로, 상태를 먼저 바꾸고
나중에 계산해도 결과는 동일하다.)

## 이번 사이클에서 다룰 범위

- `model/order_registry.py`:
  - `OrderRegistry.complete_production(order_id: str) -> Order`:
    - 대상 주문이 없으면 `ValueError`.
    - 대상 주문이 `PRODUCING`이 아니면 `ValueError`(상태 변경 없음).
    - `status`를 `CONFIRMED`로 직접 변경(mutate)하고 해당 `Order`를 반환.
- `model/sample_registry.py`:
  - `SampleRegistry.increase_stock(sample_id: str, qty: int) -> Sample`:
    - 대상 시료가 없으면 `ValueError`.
    - `qty < 0`이면 `ValueError`(상태 변경 없음).
    - `sample.stock_qty += qty`로 직접 변경(mutate)하고 해당 `Sample`을 반환.
- `controller/production_controller.py` (신규):
  - `ProductionController(order_registry: OrderRegistry, sample_registry: SampleRegistry)`.
  - `ProductionController.complete_production(order_id: str) -> Order`:
    1. `order_registry.complete_production(order_id)`로 상태를 먼저 `CONFIRMED`로 전환(대상이
       `PRODUCING`이 아니면 여기서 예외 발생, 재고는 건드리지 않음).
    2. `sample_registry.list_all()`에서 `order.sample_id`와 일치하는 `Sample`을 찾는다.
    3. `production_queue.calculate_shortage(order.quantity, sample.stock_qty)`와
       `production_queue.calculate_actual_production_qty(shortage, sample.yield_rate)`로 실
       생산량을 계산한다.
    4. `sample_registry.increase_stock(sample.sample_id, actual_qty)`로 재고를 갱신한다.
    5. 전환된 `order`를 반환한다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 출고 처리(`CONFIRMED → RELEASE`) — Cycle 10.
- 콘솔 View/Controller 연동(생산 라인 메뉴 입출력, "현재 생산 중인 시료의 진행 상황" 표기,
  대기 큐 조회 메뉴) — Cycle 12. 이번 사이클은 `production_controller.py`에 "생산완료 처리"
  메서드 하나만 추가하며, PRD §6.5가 함께 언급하는 "생산 현황 표기"·"대기 주문 확인"(큐
  조회) 기능은 포함하지 않는다 — 이들은 Cycle 8에서 만든 `sort_production_queue`를 실제
  `OrderRegistry`/`SampleRegistry` 데이터와 연결하는 별도 조회 기능으로, View 연동과 함께
  다루는 편이 자연스러워 이후 사이클로 미룬다.
- `OrderController`/`OrderRegistry`/`SampleRegistry`와 `OrderRepository`/(향후)
  `SampleRepository`의 영속화 연동(생산완료 처리 후 자동 저장 등) — Cycle 6에서와 동일한
  이유로 별도 사이클로 유지한다.
- 모니터링 집계(재고 상태 라벨 등) — Cycle 11.
- 여러 `PRODUCING` 주문을 한꺼번에, 또는 FIFO 순서를 강제해 생산완료 처리하는 로직 — 이번
  사이클은 특정 `order_id` 하나를 완료 처리하는 최소 동작만 다루며, "생산 큐 순서를 지켜야만
  완료 처리를 허용"하는 규칙은 `SPEC.md`에 명시되어 있지 않으므로 도입하지 않는다.
- `Sample.stock_qty`를 감소시키는 메서드(출고 시 필요) — Cycle 10에서 별도로 다룬다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/order_registry.py`의 `complete_production`과 `model/sample_registry.py`의
  `increase_stock`은 순수 로직(상태 전이/필드 갱신, 존재 검증)이므로 mock 없이 실제 객체로
  직접 테스트한다. 다만 테스트용 `PRODUCING` 주문을 준비하려면 `OrderRegistry.create()` +
  `OrderRegistry.approve(stock_sufficient=False)`를 거쳐야 하므로, 그 준비 단계에서는 Cycle
  5·7과 동일하게 `mocker.patch("model.order_registry.datetime")`을 사용한다(생산완료 로직
  자체의 검증에는 mock이 필요 없다).
- `controller/production_controller.py`는 "내부 협력" 계층이므로 실제 `OrderRegistry`,
  `SampleRegistry`(및 필요 시 `OrderController`로 `PRODUCING` 상태를 준비)를 조합해 테스트하고
  mock을 사용하지 않는다(단, 위와 동일한 이유로 주문 생성 준비 단계에서는 `datetime` mock을
  사용한다).

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_registry.py (기존 파일에 추가)

def test_PRODUCING_주문을_생산완료_처리하면_CONFIRMED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=False)

    completed = registry.complete_production(order.order_id)

    assert completed.status == OrderStatus.CONFIRMED


def test_PRODUCING이_아닌_주문을_생산완료_처리하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=True)  # CONFIRMED로 전환됨

    with pytest.raises(ValueError):
        registry.complete_production(order.order_id)
    assert registry.get(order.order_id).status == OrderStatus.CONFIRMED


def test_존재하지_않는_주문ID를_생산완료_처리하면_예외가_발생한다():
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.complete_production("ORD-20260715-9999")
```

```python
# tests/test_sample_registry.py (기존 파일에 추가)

def test_재고를_증가시키면_수량이_늘어난다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))

    updated = registry.increase_stock("S-001", 164)

    assert updated.stock_qty == 214


def test_존재하지_않는_시료ID의_재고를_증가시키면_예외가_발생한다():
    registry = SampleRegistry()

    with pytest.raises(ValueError):
        registry.increase_stock("S-999", 10)


def test_음수만큼_재고를_증가시키면_예외가_발생하고_수량이_바뀌지_않는다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))

    with pytest.raises(ValueError):
        registry.increase_stock("S-001", -1)
    assert registry.search("S-001")[0].stock_qty == 50
```

```python
# tests/test_production_controller.py (신규 파일)

import datetime as datetime_module
import math

import pytest

from controller.order_controller import OrderController
from controller.production_controller import ProductionController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_생산완료_처리하면_주문상태가_CONFIRMED로_전환되고_재고가_실생산량만큼_증가한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    order_registry = OrderRegistry()
    order_controller = OrderController(order_registry, sample_registry)
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING

    production_controller = ProductionController(order_registry, sample_registry)
    completed = production_controller.complete_production(order.order_id)

    assert completed.status == OrderStatus.CONFIRMED
    expected_actual_qty = math.ceil((200 - 50) / 0.92)  # shortage=150 → 164
    updated_sample = sample_registry.search("S-001")[0]
    assert updated_sample.stock_qty == 50 + expected_actual_qty


def test_PRODUCING이_아닌_주문을_생산완료_처리하면_예외가_발생하고_재고가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    order_registry = OrderRegistry()
    order_controller = OrderController(order_registry, sample_registry)
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 480 >= 200 → CONFIRMED

    production_controller = ProductionController(order_registry, sample_registry)

    with pytest.raises(ValueError):
        production_controller.complete_production(order.order_id)
    assert sample_registry.search("S-001")[0].stock_qty == 480
```

이 목표/범위로 RED 단계를 진행해도 될지 검토 부탁드립니다.
