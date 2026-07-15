[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 10 — 출고 처리 (CONFIRMED → RELEASE) (GREEN 완료)

**이전 사이클**: [Cycle 9 — 생산 완료 처리 (PRODUCING → CONFIRMED)](cycle-09-production-completion.md)
**다음 사이클**: [Cycle 11 — 모니터링 집계 (상태별 주문 수, 재고 상태 라벨)](cycle-11-monitoring-aggregation.md)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능을, Cycle 5~7에서 주문 접수(`RESERVED`)와 승인/거절
(`RESERVED → CONFIRMED`/`PRODUCING`/`REJECTED`)을 구현했다. Cycle 8에서
`model/production_queue.py`에 부족분/실 생산량/총 생산 시간을 계산하는 순수 함수와 FIFO 정렬
함수를 만들었고, Cycle 9에서는 이 함수들을 실제 `Order`/`Sample` 데이터와 연결해
`ProductionController.complete_production()`으로 `PRODUCING → CONFIRMED` 전이와 재고 증가
(`SampleRegistry.increase_stock`)를 구현했다.

이제 상태 전이 규칙(`SPEC.md` §1.3)의 마지막 한 단계, `CONFIRMED → RELEASE`(출고 처리)만
남았다. Cycle 9는 "출고 시 재고를 감소시키는 메서드는 이번 사이클(Cycle 10)에서 별도로
다룬다"고 명시적으로 범위를 미뤄뒀다 — 이번 사이클이 그 사안을 해소한다.

## 목표

`PRD.md` §6.6(출고 처리)과 `SPEC.md` §1.3(상태 전이 규칙: `CONFIRMED --출고--> RELEASE`)에
따라, `CONFIRMED` 상태 주문에 대해 출고를 실행하면 ① 주문 상태가 `RELEASE`로 전환되고,
② 해당 시료(`Sample`)의 재고(`stock_qty`)가 주문 수량(`order.quantity`)만큼 감소하는 최소
동작을 구현한다. `CONFIRMED`가 아닌 주문에 대한 출고 시도는 `SPEC.md` §5·§1.3에 따라 예외를
발생시키고 상태·재고 모두 변경하지 않는다.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. 담당 모듈 — `order_controller.py`

Cycle 9와 달리 이번엔 `SPEC.md` §2가 이미 `order_controller.py`를 "주문 생성, 승인/거절,
**출고 처리**"라고 명시하고 있어 모호함이 없다. 기존 `OrderController`가 이미
`SampleRegistry`를 참조하고 있으므로(승인 시 재고 조회에 사용), 출고 시 재고 감소도 같은
컨트롤러에 자연스럽게 추가한다. 이 판단에는 이견의 여지가 크지 않다고 보지만, 혹시 다른
의견이 있으면 GREEN 진행 전에 조정 가능하다.

### 2. 출고 시 재고가 감소하는가

`SPEC.md` §4(계산 규칙)는 "생산 완료 시 재고가 실 생산량만큼 증가한다"는 규칙만 명시하고,
출고 시 재고가 감소하는지는 아직 규정하지 않는다. 다만 다음 근거로 **출고 시
`Sample.stock_qty`를 `order.quantity`만큼 감소시키는 것을 채택**한다.

- `PRD.md` §6.6은 "재고가 **충분해진** `CONFIRMED` 주문에 대해 출고를 처리한다"고 서술한다.
  이 문장은 "출고 = 재고에서 실제로 시료를 꺼내 고객에게 보내는 행위"임을 전제하고 있다 —
  그렇지 않다면 "충분해진 재고"라는 표현 자체가 의미를 갖기 어렵다(재고를 소비하지 않는다면
  재고 수준을 굳이 언급할 이유가 없다).
- Cycle 9에서 "생산 완료 시 재고 증가"를 도입해 재고가 생산에 따라 늘어나는 흐름을 이미
  구현했다. 대칭적으로 "출고 시 재고 감소"가 있어야 재고 수치가 실제 창고 재고를 의미 있게
  반영한다(그렇지 않으면 출고가 계속돼도 재고가 무한히 쌓이기만 하는 모순이 생긴다).
- **확인 필요 / `SPEC.md` 갱신 필요**: 이 판단이 맞다면 `SPEC.md` §4에 "출고 시 재고가
  주문 수량만큼 감소한다"는 규칙을 추가해야 한다. 이번 요청 범위는 계획(RED) 수립까지이므로
  `SPEC.md` 문서 자체의 수정은 계획 승인 이후 별도로 반영한다. 이 판단에 이견이 있으면(예:
  재고 감소를 아예 다루지 않고 "출고는 상태 전이일 뿐"으로 남기고 싶다면) GREEN 진행 전에
  조정 가능하다.

### 3. 재고가 부족한 상태에서 출고를 강행할 수 있는가 — 두 개념(주문 승인 시 "재고 충분"
   판정과, 출고 시점의 실제 재고)이 어긋날 수 있는 극단 상황

이론적으로 `CONFIRMED` 주문은 승인 시점(또는 생산완료 시점)에 재고가 충분하다고 판정된
주문이지만, 같은 시료를 참조하는 **다른** `CONFIRMED` 주문이 먼저 출고되어 재고를 소비하면,
나중 주문을 출고하려는 시점에는 재고가 부족해질 수 있다(`SPEC.md`에 이 시나리오에 대한 규정은
없다). 두 선택지를 검토했다.

- **후보 A: 재고가 부족해도 출고를 강행하고 `stock_qty`가 음수가 될 수 있다.** 근거 없음 —
  오히려 `SPEC.md` §1.1이 `stock_qty: int, >= 0`이라는 불변식을 명시하고 있어 이를 위반한다.
- **후보 B: 재고가 부족하면 출고를 거부하고 예외를 발생시키며, 주문 상태·재고 모두 변경하지
  않는다.** `SPEC.md` §1.1의 `stock_qty >= 0` 불변식을 지키는 유일한 방법이며, `SPEC.md`
  §1.3의 "허용되지 않은 전이는 예외를 발생시키고 상태를 변경하지 않는다"는 원칙을 재고 검증에도
  동일하게 확장한 것으로 볼 수 있다.

**판단**: 후보 B를 채택한다. `SampleRegistry.decrease_stock(sample_id, qty)`는 감소 후
`stock_qty`가 0 미만이 되면 `ValueError`를 던지고 재고를 변경하지 않는다(Cycle 9의
`increase_stock`이 `qty < 0`을 막았던 것과 대칭되는 방어). `OrderController.release_order()`는
이 재고 부족 상황을 주문 상태 전이 **이전에** 미리 확인해, 부족하면 주문 상태(`CONFIRMED`)도
그대로 유지한 채 예외를 던진다(아래 4번 참고). **확인 필요**: 이 판단에 이견이 있으면(예:
재고 부족 시에도 출고를 허용해야 한다면) 조정 가능하다.

### 4. 처리 순서 — 재고 충분 여부를 먼저 확인한 뒤 상태를 전이한다 (Cycle 9와 반대 순서)

Cycle 9(생산완료)의 `increase_stock`은 실패할 수 없는 연산이었으므로(0 이상이면 항상 성공),
"상태 전이 먼저 → 재고 갱신 나중" 순서로도 부분 실패가 생기지 않았다. 하지만 이번 사이클의
`decrease_stock`은 재고 부족 시 실패할 수 있는 연산이다. 만약 "상태 전이(`CONFIRMED → RELEASE`)
먼저 → 재고 감소 나중" 순서를 그대로 따르면, 재고 부족으로 `decrease_stock`이 실패했을 때 이미
주문 상태는 `RELEASE`로 바뀌어 있는데 재고는 줄지 않는 불일치 상태가 남는다.

이를 막기 위해 `OrderController.release_order()`는 다음 순서를 따른다.

1. `order_registry.get(order_id)`로 대상 주문을 조회한다(존재하지 않으면 `ValueError`,
   아직 아무것도 변경하지 않음).
2. `sample_registry.list_all()`에서 같은 `sample_id`의 `Sample`을 찾는다.
3. `sample.stock_qty < order.quantity`이면(재고 부족) `ValueError`를 던진다 — 이 시점에는
   주문 상태도, 재고도 전혀 변경되지 않는다.
4. `order_registry.release(order_id)`를 호출한다 — 대상 주문이 `CONFIRMED`가 아니면 여기서
   `ValueError`가 발생하고 재고는 여전히 변경되지 않는다. `CONFIRMED`이면 `status`를 `RELEASE`로
   전환하고 반환한다.
5. `sample_registry.decrease_stock(sample.sample_id, order.quantity)`를 호출해 재고를
   감소시킨다(3번에서 이미 충분함을 확인했으므로 여기서는 실패하지 않는다).
6. 전환된 `order`를 반환한다.

이 순서는 "재고 부족 여부를 사전에 확인해 두고, 그 결과가 확정된 뒤에야 되돌릴 수 없는 상태
전이를 수행한다"는 점에서 Cycle 7의 `approve_order`(재고 충분 여부를 먼저 계산한 뒤
`order_registry.approve()`에 위임)와 같은 패턴이며, Cycle 9와는 반대 순서지만 각 사이클의
연산이 실패할 수 있는지 여부에 따라 자연스럽게 갈리는 차이라고 판단한다. **확인 필요**: 이
순서 판단에 이견이 있으면 조정 가능하다.

## 이번 사이클에서 다룰 범위

- `model/order_registry.py`:
  - `OrderRegistry.release(order_id: str) -> Order`:
    - 대상 주문이 없으면 `ValueError`.
    - 대상 주문이 `CONFIRMED`가 아니면 `ValueError`(상태 변경 없음).
    - `status`를 `RELEASE`로 직접 변경(mutate)하고 해당 `Order`를 반환.
- `model/sample_registry.py`:
  - `SampleRegistry.decrease_stock(sample_id: str, qty: int) -> Sample`:
    - 대상 시료가 없으면 `ValueError`.
    - `qty < 0`이면 `ValueError`(상태 변경 없음).
    - 감소 후 `stock_qty`가 0 미만이 되면 `ValueError`(재고 부족, 상태 변경 없음).
    - `sample.stock_qty -= qty`로 직접 변경(mutate)하고 해당 `Sample`을 반환.
- `controller/order_controller.py`:
  - `OrderController.release_order(order_id: str) -> Order`: 위 "설계 판단 4번"의 순서(재고
    부족 여부 사전 확인 → `order_registry.release()` → `sample_registry.decrease_stock()`)를
    그대로 구현.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 콘솔 View/Controller 연동(출고 처리 메뉴 입출력) — Cycle 12.
- 모니터링 집계(재고 상태 라벨 등) — Cycle 11.
- `OrderController`/`OrderRegistry`/`SampleRegistry`와 `OrderRepository`/(향후)
  `SampleRepository`의 영속화 연동(출고 처리 후 자동 저장 등) — Cycle 6·9와 동일한 이유로
  별도 사이클로 유지한다.
- 같은 시료를 참조하는 여러 `CONFIRMED` 주문을 한꺼번에 출고 처리하거나 특정 순서(FIFO 등)를
  강제하는 로직 — `SPEC.md`에 이런 규칙이 명시되어 있지 않으므로 도입하지 않는다. 이번
  사이클은 특정 `order_id` 하나를 출고 처리하는 최소 동작만 다룬다.
- `SPEC.md` §4에 "출고 시 재고 감소" 규칙을 실제로 추가하는 문서 수정 — 계획 승인 이후 별도
  커밋으로 반영한다(이번 응답은 계획 문서 작성까지만).

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/order_registry.py`의 `release`와 `model/sample_registry.py`의 `decrease_stock`은
  순수 로직(상태 전이/필드 갱신, 존재·재고 검증)이므로 mock 없이 실제 객체로 직접 테스트한다.
  다만 테스트용 `CONFIRMED` 주문을 준비하려면 `OrderRegistry.create()` + `OrderRegistry.approve
  (stock_sufficient=True)`를 거쳐야 하므로, 그 준비 단계에서는 Cycle 5·7·9와 동일하게
  `mocker.patch("model.order_registry.datetime")`을 사용한다(출고 로직 자체의 검증에는 mock이
  필요 없다).
- `controller/order_controller.py`는 "내부 협력" 계층이므로 실제 `OrderRegistry`,
  `SampleRegistry`를 조합해 테스트하고 mock을 사용하지 않는다(단, 위와 동일한 이유로 주문 생성
  준비 단계에서는 `datetime` mock을 사용한다).

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_registry.py (기존 파일에 추가)

def test_CONFIRMED_주문을_출고처리하면_RELEASE로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=True)  # CONFIRMED

    released = registry.release(order.order_id)

    assert released.status == OrderStatus.RELEASE


def test_CONFIRMED가_아닌_주문을_출고처리하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=False)  # PRODUCING

    with pytest.raises(ValueError):
        registry.release(order.order_id)
    assert registry.get(order.order_id).status == OrderStatus.PRODUCING


def test_존재하지_않는_주문ID를_출고처리하면_예외가_발생한다():
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.release("ORD-20260715-9999")
```

```python
# tests/test_sample_registry.py (기존 파일에 추가)

def test_재고를_감소시키면_수량이_줄어든다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 200))

    updated = registry.decrease_stock("S-001", 150)

    assert updated.stock_qty == 50


def test_존재하지_않는_시료ID의_재고를_감소시키면_예외가_발생한다():
    registry = SampleRegistry()

    with pytest.raises(ValueError):
        registry.decrease_stock("S-999", 10)


def test_음수만큼_재고를_감소시키면_예외가_발생하고_수량이_바뀌지_않는다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 200))

    with pytest.raises(ValueError):
        registry.decrease_stock("S-001", -1)
    assert registry.search("S-001")[0].stock_qty == 200


def test_재고보다_많은_수량을_감소시키면_예외가_발생하고_수량이_바뀌지_않는다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 200))

    with pytest.raises(ValueError):
        registry.decrease_stock("S-001", 201)
    assert registry.search("S-001")[0].stock_qty == 200
```

```python
# tests/test_order_controller.py (기존 파일에 추가)

def test_출고처리하면_주문상태가_RELEASE로_전환되고_재고가_주문수량만큼_감소한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)
    controller.approve_order(order.order_id)  # 재고 480 >= 200 → CONFIRMED

    released = controller.release_order(order.order_id)

    assert released.status == OrderStatus.RELEASE
    assert sample_registry.search("S-001")[0].stock_qty == 280


def test_CONFIRMED가_아닌_주문을_출고처리하면_예외가_발생하고_재고가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)
    controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING

    with pytest.raises(ValueError):
        controller.release_order(order.order_id)
    assert sample_registry.search("S-001")[0].stock_qty == 50


def test_재고가_부족하면_출고처리시_예외가_발생하고_상태와_재고가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 200))
    controller = OrderController(OrderRegistry(), sample_registry)
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)
    controller.approve_order(order.order_id)  # 재고 200 >= 200 → CONFIRMED
    # 같은 시료의 다른 주문이 먼저 재고를 소비해, 이 시점 재고가 부족해진 상황을 가정
    sample_registry.decrease_stock("S-001", 100)  # 남은 재고 100 < 주문 수량 200

    with pytest.raises(ValueError):
        controller.release_order(order.order_id)
    assert sample_registry.search("S-001")[0].stock_qty == 100
    assert controller._order_registry.get(order.order_id).status == OrderStatus.CONFIRMED
```

## 진행 결과

- **계획** (`daeffdd` Cycle 10 계획: 출고 처리 (CONFIRMED -> RELEASE)): 위 목표/범위와 네 가지
  설계 판단을 문서화했다.
- **RED** (`c041ad0` Cycle 10 RED: 출고 처리 실패 테스트 작성): 위 10개 테스트를
  `tests/test_order_registry.py`(3개 신규), `tests/test_sample_registry.py`(4개 신규),
  `tests/test_order_controller.py`(3개 신규)에 작성해 실패를 확인했다.
- **GREEN** (`8128714` Cycle 10 GREEN: 출고 처리 최소 구현): 계획대로
  `model/order_registry.py`에 `OrderRegistry.release()`를, `model/sample_registry.py`에
  `SampleRegistry.decrease_stock()`을, `controller/order_controller.py`에
  `OrderController.release_order()`를 구현했다.
- **SPEC.md 갱신** (`9433459` SPEC.md 갱신: 출고 시 재고 감소 규칙 명시): 계획 승인에 따라
  `SPEC.md` §4에 "출고 시 재고 반영"(주문 수량만큼 감소, 부족 시 거부) 규칙을 추가해, 설계
  판단 2번에서 남겨뒀던 확인 필요 항목을 해소했다.
- **설계 판단 채택 여부**: 계획 문서의 네 가지 설계 판단(담당 모듈 = `order_controller.py`,
  출고 시 재고 감소 채택, 재고 부족 시 거부, 재고 확인을 상태 전이보다 먼저 수행하는 처리
  순서)은 사람 파트너 검토를 거쳐 이견 없이 그대로 채택됐다.
- **verify-agent 독립 검증**: 처리 순서(재고 부족 시 상태·재고 모두 불변, "재고는 충분한데
  `CONFIRMED`가 아닌 경우" 재고가 먼저 줄지 않는지)를 코드 대조와 `git stash` 재현으로
  확인했고 문제 없음을 확인했다.
- **최종 결과**: `tests/test_order_registry.py`(3개 신규) + `tests/test_sample_registry.py`
  (4개 신규) + `tests/test_order_controller.py`(3개 신규) = 10개 테스트가 모두 통과하며, Cycle
  1~9를 포함한 전체 테스트 70개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 `view/` 관련 코드, 저장소 연동, 여러 주문 일괄 출고는 포함하지
  않았다. `model/order.py`, `model/sample.py`, `model/production_queue.py`,
  `controller/production_controller.py`, `controller/sample_controller.py`,
  `storage/order_repository.py`, `storage/sample_repository.py`는 수정되지 않았다.
