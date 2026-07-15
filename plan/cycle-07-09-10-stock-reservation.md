[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 7·9·10 재설계 — 재고 예약(승인/생산완료 시점 즉시 차감) 방식으로 전환

**관련 사이클(수정 대상)**: [Cycle 7 — 주문 승인/거절](cycle-07-order-approval.md),
[Cycle 9 — 생산 완료 처리](cycle-09-production-completion.md),
[Cycle 10 — 출고 처리](cycle-10-order-release.md)
**이 재설계가 놓이는 위치**: Cycle 10 GREEN 완료 이후, Cycle 11(모니터링 집계, 현재 RED
검토 대기) GREEN 진행 이전. **새 사이클이 아니라 이미 GREEN 완료된 Cycle 7·9·10의 재고 처리
동작 자체를 고치는 작업**이므로 `PLAN.md` 사이클 목록에는 새 행을 추가하지 않는다(대신
`PLAN.md`에 이 문서로의 짧은 각주만 남긴다).

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능을, Cycle 5~7에서 주문 접수(`RESERVED`)와 승인/거절
(`RESERVED → CONFIRMED`/`PRODUCING`/`REJECTED`)을 구현했다. Cycle 8에서
`model/production_queue.py`에 부족분/실 생산량/총 생산 시간 계산 함수를 만들었고, Cycle
9에서 이를 실제 데이터와 연결한 `ProductionController.complete_production()`
(`PRODUCING → CONFIRMED` + 재고 증가)을, Cycle 10에서 `OrderController.release_order()`로
`CONFIRMED → RELEASE` 전이와 재고 감소를 구현해 `SPEC.md` §1.3의 상태 전이 규칙을 모두
다뤘다. 이 세 사이클 모두 GREEN 완료 상태이며 전체 테스트 스위트도 통과하는 상태다.

그런데 이 세 사이클을 GREEN으로 끝낸 뒤, 사람 파트너와 재고 흐름을 다시 검토하는 과정에서
설계 결함이 발견됐다: **"승인(approve)" 시점에는 재고를 확인만 할 뿐 실제로 차감하지
않는다.** 그 결과 같은 시료를 참조하는 두 주문이 재고가 아직 충분한 시점에 각각 독립적으로
승인되면 — 승인 시점에는 재고를 차감하지 않으므로 둘 다 "재고 충분"으로 판정되어 — 두
주문 모두 `CONFIRMED`가 될 수 있다. 하지만 실제로는 두 주문 수량의 합이 재고를 초과할 수
있어, 첫 번째 주문은 출고에 성공하지만 두 번째 주문은 출고 시점에 재고 부족으로 실패하게
된다(Cycle 10 `test_재고가_부족하면_출고처리시_예외가_발생하고_상태와_재고가_바뀌지_않는다`가
바로 이 경쟁 상황을 전제로 작성된 테스트다 — 즉 기존 설계는 이 경쟁 상황이 "정상적으로
발생 가능한" 시나리오라고 보고 그에 대한 방어만 마련해 뒀을 뿐, 애초에 경쟁 상황 자체를
막지는 못했다).

사람 파트너와 논의 끝에 다음 방향으로 재설계하기로 합의했다: **주문이 `CONFIRMED` 상태가
되는 순간(승인 시 재고가 바로 충분했거나, 생산완료로 재고를 확보한 직후) 그 주문 몫의
재고를 즉시 예약(차감)한다. 출고 시에는 이미 예약이 끝나 있으므로 재고를 다시 확인하거나
차감하지 않고 상태만 전환한다.** 이 재설계가 이번 문서의 목표다.

## 목표

`PRD.md` §6.3(승인/거절), §6.5(생산 라인), §6.6(출고 처리)과 `SPEC.md` §1.1
(`Sample.stock_qty: int, >= 0`), §1.3(상태 전이 규칙)에 따라, 재고 차감 시점을 "출고 시점"에서
"`CONFIRMED` 전이 시점(승인 즉시 확정 또는 생산완료 직후)"으로 옮긴다. 이를 통해 두 개의
`CONFIRMED` 주문이 동시에 존재하더라도 그 시점에 이미 각자의 몫이 예약되어 있으므로, 이후
어떤 순서로 출고하더라도 재고 부족이 발생하지 않음을 보장한다.

## 설계 판단

### 1. `approve_order()` — 재고 충분 시 즉시 예약, 부족 시 그대로 둔다

- 재고 충분(`order.quantity <= sample.stock_qty`) → 기존과 동일하게
  `order_registry.approve(order_id, stock_sufficient=True)`로 `CONFIRMED` 전이. **전이가
  성공한 뒤** `sample_registry.decrease_stock(sample.sample_id, order.quantity)`를 호출해
  그 주문 몫을 즉시 예약(차감)한다.
- 재고 부족 → `order_registry.approve(order_id, stock_sufficient=False)`로 `PRODUCING`
  전이. 이 경우 재고는 건드리지 않는다(아직 실제로 생산되지 않은 수량을 미리 차감할 수는
  없다 — `stock_qty >= 0` 불변식을 지키기 위해서도 필요하다).
- 처리 순서는 Cycle 7의 기존 순서(상태 전이 먼저 → 재고 갱신 나중)를 유지한다. 승인 시
  재고 충분 여부는 상태 전이 이전에 이미 확정된 값(`stock_sufficient`)이므로, `approve()`
  자체가 실패할 수 없고(대상이 `RESERVED`가 아닌 경우만 예외) 그 경우엔 애초에
  `decrease_stock`을 호출하지 않으므로 Cycle 9와 같은 이유로 순서가 안전하다.

### 2. `complete_production()` — 재고 증가 후, 같은 주문 몫을 다시 예약한다

- 기존처럼 부족분(`shortage = quantity - stock_qty_before`)과 실 생산량
  (`actual_qty = ceil(shortage / yield_rate)`)을 계산해 `increase_stock(actual_qty)`를
  호출한다.
- **추가**: 그 직후 같은 주문 몫을 예약하기 위해 `decrease_stock(order.quantity)`를 이어서
  호출한다. 순증가량은 `actual_qty - order.quantity`이며, 이 값이 항상 0 이상임을 증명할 수
  있다.

  ```
  shortage = quantity - stock_qty_before      (quantity > stock_qty_before 이므로 shortage > 0)
  actual_qty = ceil(shortage / yield_rate)     (yield_rate <= 1 이므로 actual_qty >= shortage)

  stock_qty_after_increase = stock_qty_before + actual_qty
  stock_qty_after_reserve  = stock_qty_before + actual_qty - quantity
                           = stock_qty_before + actual_qty - (shortage + stock_qty_before)
                           = actual_qty - shortage
                           >= 0   (actual_qty >= shortage 이므로)
  ```

  따라서 `decrease_stock(order.quantity)`가 재고 부족으로 실패하는 경우는 없다(항상
  `actual_qty >= shortage`이므로 예약 후에도 `stock_qty >= 0` 불변식이 지켜진다). 이 증명이
  이번 재설계가 안전한 핵심 근거다.
- 호출 순서: `order_registry.complete_production()`(상태 전이) →
  `sample_registry.increase_stock(actual_qty)`(생산량 반영) →
  `sample_registry.decrease_stock(order.quantity)`(예약). 세 호출 모두 실패할 수 없는
  것으로 증명됐으므로(상태 전이는 대상이 `PRODUCING`이 아닐 때만 실패하고, 그 경우 뒤의 두
  호출은 아예 실행되지 않는다) Cycle 9의 기존 처리 순서를 그대로 유지해도 안전하다.

### 3. `release_order()` — 재고 확인/차감 로직을 완전히 제거한다

- 이미 `CONFIRMED` 전이 시점에 예약이 끝나 있으므로, 출고 시점에는 재고를 다시 확인하거나
  차감할 필요가 없다. `OrderController.release_order()`는 `order_registry.release(order_id)`
  호출 하나로 단순화한다 — 대상이 `CONFIRMED`가 아니면 여전히 `ValueError`를 던지지만, 재고는
  애초에 손대지 않으므로 "재고 부족으로 출고를 거부"하는 경로 자체가 사라진다.
- `model/sample_registry.py`의 `decrease_stock`/`increase_stock` 메서드 자체는 그대로
  유지한다(승인/생산완료 쪽에서 계속 사용). 삭제 대상은 `OrderController.release_order()`
  내부의 재고 확인·차감 호출뿐이다.

### 4. `model/order_registry.py`, `model/sample_registry.py`의 메서드 시그니처는 변경 없음

Cycle 7·9·10에서 이미 구현된 `OrderRegistry.approve/reject/complete_production/release`와
`SampleRegistry.increase_stock/decrease_stock`는 이번 재설계에서 시그니처나 내부 검증 로직을
바꿀 필요가 없다(둘 다 이미 "존재하지 않으면 예외", "음수면 예외", "감소 후 0 미만이면
예외"를 갖추고 있고, 이는 재설계 이후에도 그대로 유효한 불변식이다). 바뀌는 것은 오직
**어느 컨트롤러가 이 메서드들을 어느 시점에 호출하는가**뿐이다 — 즉 이번 재설계는
`controller/order_controller.py`와 `controller/production_controller.py` 두 파일의 호출
순서/시점만 변경하는 작업이다.

## 이번에 다룰 범위

- `controller/order_controller.py`:
  - `approve_order()`: 재고 충분 판정 후 `order_registry.approve(stock_sufficient=True)`가
    성공하면 이어서 `sample_registry.decrease_stock(sample.sample_id, order.quantity)`를
    호출하도록 수정. 재고 부족 경로(`stock_sufficient=False`)는 재고를 건드리지 않는 기존
    동작 유지.
  - `release_order()`: 재고 확인(`sample.stock_qty < order.quantity` 체크)과
    `sample_registry.decrease_stock()` 호출을 제거하고, `order_registry.release(order_id)`
    호출만 남기도록 단순화.
- `controller/production_controller.py`:
  - `complete_production()`: 기존 `increase_stock(actual_qty)` 호출 뒤에
    `sample_registry.decrease_stock(sample.sample_id, order.quantity)` 호출을 추가.
- `model/order_registry.py`, `model/sample_registry.py`: 수정 불필요(설계 판단 4번 참고).
  다만 GREEN 단계에서 실제로 수정이 필요 없는지 다시 한번 확인한다.

## 이번에 다루지 않는 것 (범위 초과 방지)

- 영속화 연동(`OrderRepository`/`SampleRepository`와의 자동 저장) — Cycle 6·9·10에서와
  동일한 이유로 여전히 별도 사이클의 관심사다.
- 콘솔 View/Controller 연동 — Cycle 12.
- 모니터링 집계(Cycle 11) — 이번 재설계와 무관하게 별도로 진행한다. 다만 Cycle 11이 아직
  GREEN 진행 전(RED 검토 대기)이므로, 이 재설계를 먼저 GREEN까지 끝낸 뒤 Cycle 11 GREEN을
  진행하는 순서를 권장한다(Cycle 11의 재고 상태 라벨 계산은 `stock_qty`를 참조하므로, 재고
  차감 시점이 바뀌는 이번 재설계를 먼저 반영해 두는 편이 안전하다).
- 동시에 같은 시료를 참조하는 여러 주문을 한꺼번에 승인하는 배치 처리, 또는 승인 순서를
  강제하는 로직 — `SPEC.md`에 명시되어 있지 않으므로 도입하지 않는다. 이번 재설계는 "각
  주문을 승인/생산완료 처리하는 시점에 그 주문 몫만큼 즉시 예약한다"는 규칙 하나만 다룬다.
- `SampleRegistry.increase_stock`/`decrease_stock`의 검증 로직 자체 변경 — 설계 판단 4번에서
  다룬 대로 이번 재설계 범위가 아니다.

## SPEC.md 갱신 필요 사항 (계획 승인 후 별도 반영)

`SPEC.md` §4의 다음 두 규칙을 재설계에 맞게 갱신해야 한다(실제 문서 수정은 이번 계획 승인
이후 별도 커밋으로 진행한다):

- **"생산 완료 시 재고 반영"**: 현재는 "실 생산량만큼 `stock_qty`가 증가한다"만 명시한다.
  재설계 후에는 "실 생산량만큼 증가한 뒤, 그 주문의 수량만큼 즉시 예약(감소)되어 순증가량은
  `실 생산량 - 주문 수량`이다"로 갱신해야 한다.
- **"출고 시 재고 반영"**: 현재는 "주문 수량만큼 감소한다. 재고가 부족하면 출고를 거부하고
  상태·재고 모두 변경하지 않는다"로 되어 있다. 재설계 후에는 "출고 시에는 재고를 확인하거나
  변경하지 않는다(이미 `CONFIRMED` 전이 시점에 예약이 끝나 있다)"로 갱신해야 한다.
- 아울러 **"승인 시 재고 반영"**이라는 새 규칙을 §4에 추가해야 한다: "승인 시 재고가 충분해
  즉시 `CONFIRMED`로 전환되면, 그 순간 주문 수량만큼 재고가 즉시 예약(감소)된다. 재고 부족으로
  `PRODUCING`으로 전환되는 경우 재고는 변경되지 않는다."

## 영향받는 기존 테스트 처리 방향 (실제 수정은 GREEN 단계에서 진행)

- **제거 대상**: `tests/test_order_controller.py`의
  `test_재고가_부족하면_출고처리시_예외가_발생하고_상태와_재고가_바뀌지_않는다`
  (Cycle 10) — 이 재설계 하에서는 `CONFIRMED` 주문이 항상 이미 예약을 마친 상태이므로,
  "출고 시점에 재고가 부족해 실패하는" 시나리오 자체가 발생할 수 없다. 이 테스트는 재설계
  전 설계(출고 시점 재고 확인)를 전제로 작성된 것이므로 통째로 제거한다.
- **갱신 대상**: Cycle 7의
  `test_재고가_충분하면_승인시_CONFIRMED로_전환된다`(양쪽 파일 — `test_order_registry.py`는
  `OrderRegistry.approve()` 자체만 검증하므로 영향 없음, `test_order_controller.py`는
  `OrderController.approve_order()`를 검증하므로 영향 있음)에 재고가 실제로 얼마나
  차감됐는지(`sample_registry.search(...)[0].stock_qty`) 검증하는 assertion을 추가해야
  한다. Cycle 9의
  `test_생산완료_처리하면_주문상태가_CONFIRMED로_전환되고_재고가_실생산량만큼_증가한다`도
  "실생산량만큼 증가"가 아니라 "실생산량에서 주문수량을 뺀 만큼 순증가"로 assertion을
  갱신해야 한다. Cycle 10의
  `test_출고처리하면_주문상태가_RELEASE로_전환되고_재고가_주문수량만큼_감소한다`은 "출고 시
  재고가 변하지 않는다"로 assertion을 뒤집어야 한다.
- 위 갱신 방향은 계획 문서로 방향만 제시하며, 실제 테스트 파일 수정은 GREEN 단계
  (재설계 구현과 함께)에서 진행한다.

## Mock 사용 범위 (SPEC.md §6 기준)

Cycle 5·7·9·10과 동일하게, `OrderRegistry.create()`로 테스트용 주문을 준비하는 단계에서는
`mocker.patch("model.order_registry.datetime")`을 사용한다. 이번 재설계 자체(재고 차감 시점
이동)는 순수 로직/내부 협력 계층의 호출 순서 변경일 뿐 새로운 외부 경계(파일 I/O, 콘솔
I/O, 시각 생성)를 추가하지 않으므로, 그 외 추가 mock은 필요 없다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_controller.py — 기존 테스트 assertion 갱신 + 신규 테스트 추가

def test_재고가_충분하면_승인시_즉시_예약되어_재고가_감소한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    approved = controller.approve_order(order.order_id)

    assert approved.status == OrderStatus.CONFIRMED
    assert sample_registry.search("S-001")[0].stock_qty == 280  # 480 - 200 즉시 예약


def test_재고가_부족하면_승인시_PRODUCING이_되고_재고는_그대로다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    approved = controller.approve_order(order.order_id)

    assert approved.status == OrderStatus.PRODUCING
    assert sample_registry.search("S-001")[0].stock_qty == 50  # 예약하지 않음, 그대로


def test_출고해도_재고는_변하지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)
    controller.approve_order(order.order_id)  # CONFIRMED, 이미 200 예약됨 (280 남음)

    released = controller.release_order(order.order_id)

    assert released.status == OrderStatus.RELEASE
    assert sample_registry.search("S-001")[0].stock_qty == 280  # 출고 전후 변화 없음


def test_두_CONFIRMED_주문을_순서대로_출고해도_둘_다_성공한다(mocker):
    """승인 시점 예약 덕분에, 두 주문의 합이 원래 재고를 초과해도(각자 예약된 몫만큼만
    출고하므로) 경쟁 상황 없이 둘 다 출고에 성공함을 증명하는 회귀 테스트."""
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 300))
    controller = OrderController(OrderRegistry(), sample_registry)
    order_a = controller.create_order("S-001", "삼성전자 파운드리", 200)  # 300 >= 200, 승인 가능
    controller.approve_order(order_a.order_id)  # CONFIRMED, 재고 300 -> 100 즉시 예약
    order_b = controller.create_order("S-001", "SK하이닉스", 100)  # 100 >= 100, 승인 가능
    controller.approve_order(order_b.order_id)  # CONFIRMED, 재고 100 -> 0 즉시 예약

    released_a = controller.release_order(order_a.order_id)
    released_b = controller.release_order(order_b.order_id)

    assert released_a.status == OrderStatus.RELEASE
    assert released_b.status == OrderStatus.RELEASE
    assert sample_registry.search("S-001")[0].stock_qty == 0
```

```python
# tests/test_production_controller.py — 기존 테스트 assertion 갱신

def test_생산완료_처리하면_재고가_실생산량에서_주문수량을_뺀_만큼만_순증가한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    order_registry = OrderRegistry()
    order_controller = OrderController(order_registry, sample_registry)
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING (재고 변화 없음)

    production_controller = ProductionController(order_registry, sample_registry)
    completed = production_controller.complete_production(order.order_id)

    assert completed.status == OrderStatus.CONFIRMED
    shortage = 200 - 50
    actual_qty = math.ceil(shortage / 0.92)  # 164
    expected_stock = 50 + actual_qty - 200  # 순증가 = actual_qty - shortage = 14
    updated_sample = sample_registry.search("S-001")[0]
    assert updated_sample.stock_qty == expected_stock
```

이 재설계/범위로 RED 단계를 진행해도 될지 검토 부탁드립니다.
