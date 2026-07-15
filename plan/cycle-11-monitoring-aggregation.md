[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 11 — 모니터링 집계 (상태별 주문 수, 재고 상태 라벨) (GREEN 완료)

**이전 사이클**: [Cycle 10 — 출고 처리 (CONFIRMED → RELEASE)](cycle-10-order-release.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능을, Cycle 5~7에서 주문 접수(`RESERVED`)와 승인/거절
(`RESERVED → CONFIRMED`/`PRODUCING`/`REJECTED`)을 구현했다. Cycle 8에서
`model/production_queue.py`에 생산 관련 순수 계산 함수(부족분/실 생산량/총 생산 시간/FIFO
정렬)를 만들었고, Cycle 9에서 이를 실제 데이터와 연결한 `ProductionController.
complete_production()`(`PRODUCING → CONFIRMED` + 재고 증가)을 구현했다. Cycle 10에서는
`OrderController.release_order()`로 `CONFIRMED → RELEASE` 전이와 재고 감소를 구현해,
`SPEC.md` §1.3의 상태 전이 규칙(`RESERVED → REJECTED/CONFIRMED/PRODUCING`,
`PRODUCING → CONFIRMED`, `CONFIRMED → RELEASE`)을 모두 다뤘다.

이제 상태 전이 자체는 모두 구현되어 있으므로, 이번 사이클부터는 `PRD.md` §6.4(모니터링)와
`SPEC.md` §2의 `controller/monitoring_controller.py`("상태별 주문 수, 재고 현황 집계")를
다룬다. 지금까지 한 번도 만들어지지 않은 새 영역이다.

## 목표

`PRD.md` §6.4(모니터링)와 `SPEC.md` §4(계산 규칙 — 재고 상태 라벨)에 따라, 다음 두 가지
집계를 실제 `OrderRegistry`/`SampleRegistry` 데이터로 계산할 수 있는 최소 동작을 구현한다.

1. **주문량 확인**: `RESERVED`/`CONFIRMED`/`PRODUCING`/`RELEASE` 상태별 주문 수를 센다.
   `REJECTED` 주문은 집계에서 완전히 제외한다(`PRD.md` §6.4, §4의 표 "정상 흐름 외 상태이며
   모니터링 대상에서 제외").
2. **재고량 확인**: 시료별로 `SPEC.md` §4의 공식에 따라 재고 상태 라벨(`여유`/`부족`/`고갈`)을
   계산한다.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. 순수 계산 로직을 어디에 둘 것인가 — `model/monitoring.py`(신규) 채택

`SPEC.md` §2의 `model/` 목록(`sample.py`, `sample_registry.py`, `order.py`,
`order_registry.py`, `production_queue.py`)에는 모니터링 집계를 위한 순수 계산 모듈이 아직
없다. 두 후보를 검토했다.

- **후보 A: `controller/monitoring_controller.py` 안에 계산 로직을 직접 둔다.** 근거: 별도
  모듈을 만들지 않아도 되어 구조가 단순해진다. 다만 단점으로, `SPEC.md` §6(테스트/Mock
  전략)이 "`controller/`는 내부 협력 계층이므로 실제 Model/View를 조합해 테스트"한다고 규정할
  뿐 순수 계산 검증을 이 계층에 두라고 명시하지 않으며, `model/production_queue.py`가 이미
  "부족분/실 생산량/총 생산 시간"이라는 순수 계산을 컨트롤러(`production_controller.py`)와
  분리해 `model/`에 둔 선례와 어긋난다.
- **후보 B: `model/monitoring.py`(신규)에 순수 함수로 둔다.** 근거: Cycle 8의
  `production_queue.py` 선례(계산 로직은 `model/`에 순수 함수로, 실제 데이터 연결은
  `production_controller.py`에서)를 그대로 따른다. 상태별 개수 세기와 재고 라벨 계산은
  입력(`Order`/`Sample` 리스트, 정수)만으로 결정되는 순수 함수이므로 이 계층에 자연스럽게
  속한다.

**판단**: 후보 B(`model/monitoring.py` 신규)를 채택한다. **확인 필요 / `SPEC.md` 갱신 필요**:
이 판단이 맞다면 `SPEC.md` §2의 `model/` 목록에 `monitoring.py`(순수 계산: 상태별 주문 수,
재고 상태 라벨)를 추가해야 한다. 이번 요청 범위는 계획(RED) 수립까지이므로, `SPEC.md` 문서
자체의 수정은 계획 승인 이후 별도로 반영한다. 이견이 있으면 GREEN 진행 전에 조정 가능하다.

### 2. "미승인 주문 총수량"의 정의 — **확인 필요, 가장 모호한 지점**

`SPEC.md` §4는 재고 상태 라벨 공식을 "`stock_qty < 미승인 주문 총수량` → 부족"이라고만
서술하고, "미승인 주문"이 어떤 `OrderStatus` 집합을 가리키는지 정의하지 않는다. `PRD.md`
§6.4는 "주문 대비 재고 수준"이라는 더 느슨한 표현만 쓴다. 세 가지 후보를 검토했다.

- **후보 A: `RESERVED` 상태 주문만.** 근거: "미승인(未承認)"이라는 단어를 문자 그대로 읽으면
  "아직 승인/거절 여부가 결정되지 않은 주문" = `RESERVED`뿐이다. `CONFIRMED`/`PRODUCING`은
  이미 승인이 끝난 주문이므로 "미승인"이라는 표현과 맞지 않는다. 업무적으로도 이 라벨은
  "생산 담당자가 `RESERVED` 주문을 승인할지 판단할 때, 지금 쌓여 있는 미승인 요청 대비 재고가
  충분한지"를 보여주는 지표로 해석할 수 있어 `PRD.md` §6.3(주문 승인/거절) 워크플로와도
  자연스럽게 연결된다.
- **후보 B: `RESERVED` + `PRODUCING` (아직 재고에서 실제로 빠져나가지 않은 모든 유효 주문).**
  근거: `CONFIRMED`/`RELEASE`는 이미 승인이 끝났고, `PRODUCING`도 승인은 됐지만 아직 "생산
  중"이라 완전히 처리됐다고 보기 어렵다는 관점. 다만 "미승인"이라는 단어와는 다소 어긋난다
  (`PRODUCING`은 이미 승인된 주문이다).
- **후보 C: `RESERVED` + `PRODUCING` + `CONFIRMED` (아직 출고되지 않은 모든 유효 주문).**
  근거: "주문 대비 재고" 자체를 "아직 고객에게 나가지 않은 모든 수요"로 넓게 해석. 다만
  `CONFIRMED`는 승인 시점(또는 생산완료 시점)에 이미 "재고 충분"이 확인된 주문이므로, 이를
  다시 재고 부족 판정에 합산하면 방금 막 `CONFIRMED`로 전환된 주문 때문에 같은 시료가 곧바로
  "부족"으로 표시되는 역설이 쉽게 발생한다(예: 재고 200, 주문 200 승인 직후 `CONFIRMED` →
  후보 C대로면 미승인 총수량 200으로 계산되어 `stock_qty(200) < 200`은 거짓이라 "부족"은
  아니지만, 근소한 차이로도 쉽게 "부족"이 뜬다). 이 역설 때문에 후보 C는 채택하지 않는다.

**판단**: 후보 A(`RESERVED` 상태 주문만)를 채택한다. `SPEC.md`가 "미승인"이라는 단어를 명시적으로
선택했다는 점(단순히 "전체 주문"이나 "미출고 주문"이라고 쓰지 않았다는 점)이 가장 직접적인
근거다. **다만 이 해석에 이견이 있을 가능성이 가장 큰 지점이므로, GREEN 진행 전 사람 파트너의
명시적 확인을 요청한다.** 이견이 있으면(예: 후보 B를 원한다면) 계산 함수의 입력 필터링
조건 하나만 바꾸면 되므로 조정 비용은 크지 않다.

같은 시료를 참조하는 `RESERVED` 주문이 여러 건이면 그 수량을 모두 더한 값을 "미승인 주문
총수량"으로 사용한다(`SPEC.md`가 "총수량"이라는 표현을 쓰고 있어 합산임이 비교적 명확하다).

### 3. `count_orders_by_status`의 반환 형태

`REJECTED` 주문을 "완전히 무시"한다는 `PRD.md` §6.4 서술에 따라, 반환값(딕셔너리)에
`OrderStatus.REJECTED` 키 자체를 포함하지 않는다(0으로 표시하는 것도 하지 않는다 — 애초에
집계 대상이 아님을 명확히 하기 위함). `RESERVED`/`CONFIRMED`/`PRODUCING`/`RELEASE` 네 상태는
해당 주문이 하나도 없어도 0으로 키를 포함한다(메뉴 화면에서 "0건"으로 표시할 수 있도록).

## 이번 사이클에서 다룰 범위

- `model/monitoring.py` (신규, 순수 함수):
  - `count_orders_by_status(orders: list[Order]) -> dict[OrderStatus, int]`:
    `RESERVED`/`CONFIRMED`/`PRODUCING`/`RELEASE` 각각의 개수를 세어 딕셔너리로 반환.
    `REJECTED` 주문은 결과에서 완전히 제외(위 설계 판단 3번).
  - `sum_pending_order_qty(orders: list[Order], sample_id: str) -> int`: 주어진 `sample_id`를
    참조하는 `RESERVED` 상태 주문들의 `quantity` 합계를 반환(위 설계 판단 2번, 후보 A).
    해당 시료를 참조하는 `RESERVED` 주문이 없으면 0.
  - `calculate_stock_status_label(stock_qty: int, pending_order_qty: int) -> str`:
    `SPEC.md` §4 공식대로 `stock_qty == 0` → `"고갈"`, `stock_qty < pending_order_qty` →
    `"부족"`, 그 외 → `"여유"`를 반환.
- `controller/monitoring_controller.py` (신규):
  - `MonitoringController(order_registry: OrderRegistry, sample_registry: SampleRegistry)`.
  - `MonitoringController.count_orders_by_status() -> dict[OrderStatus, int]`:
    `order_registry.list_all()`을 `model.monitoring.count_orders_by_status()`에 그대로
    전달한 결과를 반환.
  - `MonitoringController.stock_status_by_sample() -> dict[str, str]`: `sample_registry.
    list_all()`의 각 `Sample`에 대해 `model.monitoring.sum_pending_order_qty()`와
    `calculate_stock_status_label()`을 이용해 `{sample_id: 라벨}` 형태의 딕셔너리를 구성해
    반환.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 콘솔 View/Controller 연동(모니터링 메뉴 입출력, 메인 메뉴 진입 시 요약 정보 표시 등) —
  Cycle 12.
- `OrderRepository`/(향후) `SampleRepository`로부터 실제 저장 파일을 읽어 집계하는 연동 —
  이번 사이클은 인메모리 `OrderRegistry`/`SampleRegistry` 데이터를 대상으로만 집계하며, 파일
  I/O는 다루지 않는다(Cycle 6·9·10과 동일한 이유).
- 생산 라인 현황/대기 큐 조회(`PRD.md` §6.5) — 이미 Cycle 8의 `sort_production_queue`가
  존재하며, 실제 데이터 연결 및 View 연동은 별도 사이클(Cycle 12 전후)에서 다룬다. 이번
  사이클은 `monitoring_controller.py`의 두 집계(주문 수, 재고 라벨)만 다룬다.
- 재고 상태 라벨을 시료별로 한 번에 조회하는 것 외에, 시료 목록 조회(`SampleController.
  list_samples()` 등)와 통합된 하나의 "모니터링 화면 데이터" 구조체를 만드는 것 — View 연동과
  함께 다루는 편이 자연스러워 Cycle 12로 미룬다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/monitoring.py`의 세 함수는 순수 로직(집계·비교 계산)이므로 mock 없이 실제 `Order`/
  `Sample` 객체(생성자 직접 호출)로 테스트한다(Cycle 8의 `test_production_queue.py`와 동일한
  패턴 — `OrderRegistry.create()`를 거치지 않으므로 `datetime` mock도 필요 없다).
- `controller/monitoring_controller.py`는 "내부 협력" 계층이므로 실제 `OrderRegistry`,
  `SampleRegistry`를 조합해 테스트하고 mock을 사용하지 않는다. 다만 테스트용 `RESERVED`/
  `CONFIRMED`/`PRODUCING` 주문을 준비하려면 `OrderRegistry.create()`(+ 필요 시 `approve()`)를
  거쳐야 하므로, 그 준비 단계에서는 Cycle 5·7·9·10과 동일하게 `mocker.patch("model.
  order_registry.datetime")`을 사용한다(집계 로직 자체의 검증에는 mock이 필요 없다).

## 작성할 실패 테스트 (예시)

```python
# tests/test_monitoring.py (신규 파일)

from model.monitoring import (
    calculate_stock_status_label,
    count_orders_by_status,
    sum_pending_order_qty,
)
from model.order import Order, OrderStatus


def _order(order_id, sample_id, status, quantity=100):
    return Order(order_id, sample_id, "삼성전자 파운드리", quantity, status, "2026-07-15T09:32:15")


def test_상태별_주문수를_센다():
    orders = [
        _order("ORD-1", "S-001", OrderStatus.RESERVED),
        _order("ORD-2", "S-001", OrderStatus.RESERVED),
        _order("ORD-3", "S-001", OrderStatus.CONFIRMED),
        _order("ORD-4", "S-001", OrderStatus.PRODUCING),
        _order("ORD-5", "S-001", OrderStatus.RELEASE),
        _order("ORD-6", "S-001", OrderStatus.REJECTED),
    ]

    counts = count_orders_by_status(orders)

    assert counts == {
        OrderStatus.RESERVED: 2,
        OrderStatus.CONFIRMED: 1,
        OrderStatus.PRODUCING: 1,
        OrderStatus.RELEASE: 1,
    }


def test_REJECTED_주문은_상태별_집계에서_완전히_제외된다():
    orders = [_order("ORD-1", "S-001", OrderStatus.REJECTED)]

    counts = count_orders_by_status(orders)

    assert OrderStatus.REJECTED not in counts
    assert counts[OrderStatus.RESERVED] == 0


def test_특정_시료를_참조하는_RESERVED_주문_수량을_합산한다():
    orders = [
        _order("ORD-1", "S-001", OrderStatus.RESERVED, quantity=100),
        _order("ORD-2", "S-001", OrderStatus.RESERVED, quantity=50),
        _order("ORD-3", "S-001", OrderStatus.CONFIRMED, quantity=999),  # 미승인 아님 → 제외
        _order("ORD-4", "S-002", OrderStatus.RESERVED, quantity=999),  # 다른 시료 → 제외
    ]

    assert sum_pending_order_qty(orders, "S-001") == 150


def test_참조하는_RESERVED_주문이_없으면_미승인_수량은_0이다():
    orders = [_order("ORD-1", "S-002", OrderStatus.RESERVED, quantity=100)]

    assert sum_pending_order_qty(orders, "S-001") == 0


def test_재고가_0이면_고갈이다():
    assert calculate_stock_status_label(stock_qty=0, pending_order_qty=0) == "고갈"


def test_재고가_미승인_주문_총수량보다_적으면_부족이다():
    assert calculate_stock_status_label(stock_qty=50, pending_order_qty=100) == "부족"


def test_재고가_미승인_주문_총수량_이상이면_여유이다():
    assert calculate_stock_status_label(stock_qty=100, pending_order_qty=100) == "여유"
```

```python
# tests/test_monitoring_controller.py (신규 파일)

import datetime as datetime_module

from controller.monitoring_controller import MonitoringController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_주문이_없으면_모든_상태의_집계는_0건이다():
    controller = MonitoringController(OrderRegistry(), SampleRegistry())

    counts = controller.count_orders_by_status()

    assert counts == {
        OrderStatus.RESERVED: 0,
        OrderStatus.CONFIRMED: 0,
        OrderStatus.PRODUCING: 0,
        OrderStatus.RELEASE: 0,
    }


def test_실제_주문registry의_상태별_주문수를_집계한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    order_registry = OrderRegistry()
    order_registry.create("S-001", "삼성전자 파운드리", 100)  # RESERVED
    reserved_to_reject = order_registry.create("S-001", "삼성전자 파운드리", 100)
    order_registry.reject(reserved_to_reject.order_id)  # REJECTED, 집계 제외

    controller = MonitoringController(order_registry, sample_registry)
    counts = controller.count_orders_by_status()

    assert counts[OrderStatus.RESERVED] == 1
    assert OrderStatus.REJECTED not in counts


def test_시료별_재고상태_라벨을_계산한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    sample_registry.register(Sample("S-002", "GaN 파워칩", 1.2, 0.88, 0))
    order_registry = OrderRegistry()
    order_registry.create("S-001", "삼성전자 파운드리", 100)  # RESERVED, S-001 미승인 총수량 100

    controller = MonitoringController(order_registry, sample_registry)
    labels = controller.stock_status_by_sample()

    assert labels["S-001"] == "부족"  # 재고 50 < 미승인 100
    assert labels["S-002"] == "고갈"  # 재고 0
```

## 진행 결과

- **RED** (`b8c700f` Cycle 11 RED: 모니터링 집계 실패 테스트 작성): 위 예시 테스트를
  `tests/test_monitoring.py`(7개 신규), `tests/test_monitoring_controller.py`(3개 신규)에
  작성해 실패를 확인했다.
- **GREEN** (`2802116` Cycle 11 GREEN: 모니터링 집계 최소 구현): 계획대로
  `model/monitoring.py`에 `count_orders_by_status()`, `sum_pending_order_qty()`,
  `calculate_stock_status_label()`을, `controller/monitoring_controller.py`에
  `MonitoringController.count_orders_by_status()`, `MonitoringController.
  stock_status_by_sample()`을 구현했다.
- **설계 판단 채택 여부**: 계획 문서의 세 가지 설계 판단(순수 계산 로직을
  `model/monitoring.py`에 두는 판단, "미승인 주문 총수량"을 `RESERVED` 상태 주문만으로
  해석하는 판단, `REJECTED`를 집계 딕셔너리에서 키 자체를 제외하는 반환 형태)은 사람 파트너
  검토를 거쳐 이견 없이 그대로 채택됐다.
- **verify-agent 독립 검증**: `REJECTED` 완전 제외, 재고 상태 라벨 공식 일치, RED→GREEN
  전환을 `git stash` 재현으로 확인했고 문제 없음을 확인했다.
- **최종 결과**: `tests/test_monitoring.py`(7개) + `tests/test_monitoring_controller.py`
  (3개) = 10개 테스트가 모두 통과하며, Cycle 1~10을 포함한 전체 테스트 81개가 회귀 없이
  통과한다.
- **범위 준수 확인**: 계획대로 `view/` 관련 코드, 저장소 연동, 생산 큐 실제 연결은 포함하지
  않았다.
- **참고 — Cycle 7·9·10 재고 예약 재설계와의 관계** (상세는
  [plan/cycle-07-09-10-stock-reservation.md](cycle-07-09-10-stock-reservation.md) 참고):
  Cycle 11 GREEN 완료 직후 별도로 진행된 재고 예약 재설계로 인해, 이제 `Sample.stock_qty`는
  이미 `CONFIRMED` 주문 몫이 예약(차감)된 값을 의미하게 됐다. 이는 `sum_pending_order_qty`가
  `RESERVED` 상태 주문만 합산하는 해석(설계 판단 2번)과 오히려 더 잘 맞아떨어진다 —
  `CONFIRMED`로 전환된 주문은 이미 재고에서 빠져 있으므로 "미승인(`RESERVED`) 주문 대비 남은
  재고"라는 지표가 더 정확해졌다. 이 재설계로 인해 `model/monitoring.py`,
  `controller/monitoring_controller.py` 코드 자체를 수정할 필요는 없었다(실제로 수정하지
  않았다).
