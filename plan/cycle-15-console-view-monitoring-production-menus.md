[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 15 — 콘솔 View: 모니터링 메뉴 + 생산 라인 메뉴 (GREEN 완료)

**이전 사이클**: [Cycle 14 — 콘솔 View: 시료 주문 메뉴 + 주문 승인/거절 메뉴](cycle-14-console-view-order-menus.md)
**다음 사이클**: [Cycle 16 — 출고 처리 메뉴 + `main.py` 진입점 (프로젝트의 마지막 사이클)](cycle-16-order-release-menu-main-entrypoint.md)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~11에서 Model/Controller 계층(시료 등록/조회/검색, 주문 접수·승인/거절·출고 처리, 생산
큐 계산 로직(`model/production_queue.py`)과 생산 완료 처리, 모니터링 집계(`MonitoringController`))을
모두 구현했다. Cycle 12에서 `OrderController`/`ProductionController`를 각각의 저장소와 연결해
영속화를 확인했다. Cycle 13에서 `view/console_view.py`(`ConsoleView`)를 신설해 콘솔 View의
골격과 입출력 mock 전략(`mocker.patch("builtins.input", side_effect=[...])` + `capsys`)을 확정하고,
메인 메뉴 요약 정보 표시와 시료 관리 하위 메뉴(등록/조회/검색)를 구현했다. Cycle 14에서는 같은
패턴을 계승해 시료 주문 메뉴와 주문 승인/거절 메뉴를 구현했다.

Cycle 13·14를 거치며 다음 두 원칙이 확정되어 이번 사이클도 그대로 계승한다.

1. **`ConsoleView`는 Controller를 호출하지 않는다** — 표시 메서드는 이미 계산된 데이터를 인자로
   받아 화면에 출력만 하고, 입력 메서드는 사용자 입력을 dict/문자열 등 단순 자료구조로 반환할
   뿐이다. "메뉴 선택 → Controller 호출 → 결과를 View로 표시"라는 오케스트레이션은
   `main.py`(Cycle 16)의 책임으로 남긴다.
2. **출력 검증은 `capsys`, 입력은 `mocker.patch("builtins.input", side_effect=[...])`**.
3. **여러 하위 기능이 있는 메뉴에만 진입 화면(하위 메뉴)을 둔다** — Cycle 13의 시료 관리(3개
   기능: 등록/조회/검색)는 하위 메뉴가 있었고, Cycle 14의 시료 주문(단일 동작)은 하위 메뉴 없이
   바로 입력을 받았다.

`plan/cycle-12-order-controller-persistence.md`의 로드맵(9~40행)에 따라 이번 사이클은 그중 세
번째 단계 — 모니터링 메뉴와 생산 라인 메뉴(현재 생산 중 표시 + 대기 큐 조회 + 생산완료 처리)의
화면 동작을 정의한다. 이번 사이클은 `model/production_queue.py`(Cycle 8에서 작성된 순수 함수,
`sort_production_queue`)를 처음으로 실제 데이터(`OrderRegistry`가 들고 있는 주문 목록)에
연결한다는 점에서 지금까지의 View 전용 사이클과 다르다 — `ConsoleView`뿐 아니라
`controller/production_controller.py`에도 새 조회 메서드를 추가한다.

## 목표

`PRD.md` §6.4(모니터링)·§6.5(생산 라인)와 `SPEC.md` §2(`view/console_view.py`,
`controller/production_controller.py`)·§4(생산 큐 정렬 규칙)에 따라, 다음 두 화면의 입출력과
그 배후의 조회 로직을 정의한다.

1. **모니터링**: 상태별 주문 수(`RESERVED`/`CONFIRMED`/`PRODUCING`/`RELEASE`, `REJECTED` 제외)와
   시료별 재고 상태 라벨(여유/부족/고갈)을 표시한다.
2. **생산 라인**: 현재 생산 중인 시료 정보와 대기 중인 생산 큐(FIFO)를 표시하고, 생산완료 처리를
   실행할 주문을 입력받아 그 결과(`PRODUCING → CONFIRMED`)를 표시한다.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. `sort_production_queue`를 실제 데이터에 연결하는 위치 — `ProductionController`에 신규 조회 메서드 추가

`model/production_queue.py`의 `sort_production_queue(orders)`는 Cycle 8에서 순수 함수로만
구현된 뒤, 지금까지 어떤 Controller에서도 호출되지 않았다. Cycle 13·14가 확립한 "View는
Controller를 호출하지 않고, 이미 계산된 데이터를 표시만 한다"는 원칙에 따르면, `orders`
목록을 가져와 `sort_production_queue()`에 넘기는 호출 자체는 View의 책임이 될 수 없다 —
`ConsoleView`는 어떤 Model/Registry에도 접근하지 않기 때문이다(Cycle 13에서 이미 "`ConsoleView`는
어떤 모듈도 import하지 않는 순수 입출력 클래스"로 구현됨).

Cycle 14의 설계 판단 1번("접수된 주문만 걸러내는 필터링 위치는 Cycle 16에서 결정")과 달리, 이번
사이클은 `sort_production_queue`를 실제로 연결하는 것 자체가 사이클의 핵심 목표이므로 위치
결정을 미루지 않는다.

**판단**: `controller/production_controller.py`에 다음 두 조회 메서드를 추가한다.

- `ProductionController.list_production_queue() -> list[Order]`: `order_registry.list_all()`을
  `production_queue.sort_production_queue()`에 넘겨 `PRODUCING` 상태 주문을 `created_at`
  오름차순(FIFO)으로 정렬한 목록을 반환한다.
- `ProductionController.current_production_order() -> Order | None`: 위 큐의 첫 번째 원소(FIFO
  선두 — 단일 생산 라인이 가장 먼저 처리할 주문)를 반환한다. 큐가 비어 있으면 `None`.

`OrderController.list_orders()`(Cycle 12)가 이미 "Controller가 Registry를 조회해 View에 넘길
데이터를 만든다"는 선례이므로, 동일한 패턴을 `ProductionController`에도 적용한다.

### 2. "현재 생산 중인 시료 정보"의 표기 수준 — FIFO 큐의 선두 주문 정보로 최소화, 부분 생산량은 추적하지 않는다

`PRD.md` §6.5는 "현재 생산 중인 시료 정보(예: 주문 정보, 현재까지의 생산량 등). 표기 수준은
자율적으로 결정"이라고만 명시한다. 현재 데이터 모델(`Order`, `Sample`)에는 "한 주문의 생산이
몇 개나 진행됐는지"를 추적하는 필드가 전혀 없다(생산은 `PRODUCING → CONFIRMED` 전이 시점에
한 번에 완료 처리되는 이산적 이벤트로만 모델링되어 있다, `SPEC.md` §4). 이 값을 표시하려면
새로운 상태(진행률 등)를 모델에 추가해야 하는데, 이는 `SPEC.md`에 정의되지 않은 새 요구사항을
만드는 것이라 이번 사이클 범위를 벗어난다.

**판단**: "현재 생산 중인 시료 정보"는 위 설계 판단 1번의 `current_production_order()`가
반환하는 `Order` 하나(선두 주문)의 기존 필드(`order_id`/`sample_id`/`customer_name`/
`quantity`/`created_at`)만으로 표시를 최소화한다. 생산량 진행률 같은 부가 정보는 다루지
않는다. **확인 필요**: 이 최소화 판단이 PRD의 "표기 수준 자율적 결정" 취지에 부합하는지 확인
부탁드린다.

### 3. "대기 주문 확인"은 큐 전체(선두 포함)를 그대로 보여준다 — 선두를 제외하지 않는다

PRD는 "대기 주문 확인: 생산 큐를 이용해 대기 중인 목록을 출력"이라고 정의한다. 단일 생산
라인은 큐를 순차 처리하므로, `PRODUCING` 상태인 모든 주문(선두 포함)이 넓은 의미에서 아직
`CONFIRMED`로 전환되지 못하고 "생산 대기/진행 중"인 상태다.

**판단**: `show_production_queue()`에는 `list_production_queue()`가 반환하는 전체 목록(선두
주문 포함)을 그대로 넘긴다 — 선두 주문을 제외한 목록을 별도로 계산하는 로직(예:
`queue[1:]`)은 추가하지 않는다. 화면에는 "현재 생산 중" 표시와 "대기 목록" 표시가 별개의
메서드로 나뉘어 있으므로, 선두 주문 정보가 두 화면에 중복 표시될 수 있으나 이는 정보 손실보다
낫다고 판단했다. **확인 필요**: 선두 주문을 대기 목록에서 제외해야 한다는 의견이 있으면
`ProductionController.list_production_queue()`가 아닌 별도 메서드(예:
`waiting_production_queue()`)로 분리할 수 있다.

### 4. 모니터링 메뉴·생산 라인 메뉴 모두 하위 메뉴(진입 화면)를 둔다

Cycle 12 로드맵(36행)이 이번 사이클 범위를 "모니터링 메뉴 + 생산 라인 메뉴(현재 생산 중 표시 +
대기 큐 조회 + 생산완료 처리)"로 명시했다. 모니터링은 2개 하위 기능(주문량 확인/재고량 확인),
생산 라인은 2개 하위 동작(생산 현황 조회/생산완료 처리)을 갖는다. Cycle 13이 확립한 기준("여러
하위 기능이 있는 메뉴에만 하위 메뉴 화면을 둔다" — 시료 관리 3개 기능은 하위 메뉴, Cycle 14의
시료 주문 단일 동작은 하위 메뉴 없음)에 따르면, 이번 두 메뉴 모두 하위 메뉴 화면을 두는 쪽이
일관된다.

**판단**:
- 모니터링: `show_monitoring_menu()`/`get_monitoring_menu_choice()` 하위 메뉴 뒤에 "주문량
  확인"(`show_order_counts`), "재고량 확인"(`show_stock_status`) 두 표시 메서드를 둔다.
- 생산 라인: `show_production_menu()`/`get_production_menu_choice()` 하위 메뉴 뒤에 "생산 현황
  조회"(`show_current_production` + `show_production_queue`를 함께 호출), "생산완료
  처리"(`get_order_id_to_complete()` → `show_production_completed()`)를 둔다. "현재 생산 중
  표시"와 "대기 큐 조회"를 하나의 메뉴 항목("생산 현황 조회")으로 묶은 이유는, 두 정보 모두
  같은 큐 데이터에서 나오는 하나의 화면(생산 현황판)으로 보는 것이 자연스럽고, PRD도 이 둘을
  "생산 현황 표기"라는 절 하나로 함께 서술하기 때문이다. **확인 필요**: "현재 생산 중 표시"와
  "대기 큐 조회"를 별도 메뉴 항목으로 완전히 분리해야 한다는 의견이 있으면 조정 가능하다.

### 5. 주문 상태별 개수(`dict[OrderStatus, int]`)를 View가 어떻게 표시할지 — `status.value` 문자열로 표시

`MonitoringController.count_orders_by_status()`는 `OrderStatus` enum을 키로 하는 dict를
반환한다(`model/monitoring.py`, Cycle 11). Cycle 14에서 `Order.status`를 표시할 때
`order.status.value`(예: `"RESERVED"`)를 문구에 사용한 것과 동일하게, `show_order_counts()`도
각 `OrderStatus` 키의 `.value`를 화면에 표시한다.

## 이번 사이클에서 다룰 범위

- `controller/production_controller.py` (기존 `ProductionController`에 메서드 추가):
  - `list_production_queue() -> list[Order]`: `production_queue.sort_production_queue()`를
    `order_registry.list_all()`에 적용한 결과를 반환한다.
  - `current_production_order() -> Order | None`: 위 큐의 첫 번째 원소, 없으면 `None`.
- `view/console_view.py` (기존 `ConsoleView`에 메서드 추가):
  - **모니터링**:
    - `show_monitoring_menu() -> None`: 하위 메뉴(주문량 확인/재고량 확인/뒤로 가기) 출력.
    - `get_monitoring_menu_choice() -> str`: 하위 메뉴 선택 입력.
    - `show_order_counts(counts: dict) -> None`: `OrderStatus` 키(`.value`로 표시)별 개수를
      출력한다.
    - `show_stock_status(labels: dict) -> None`: `sample_id`별 재고 상태 라벨(여유/부족/고갈)을
      출력한다.
  - **생산 라인**:
    - `show_production_menu() -> None`: 하위 메뉴(생산 현황 조회/생산완료 처리/뒤로 가기) 출력.
    - `get_production_menu_choice() -> str`: 하위 메뉴 선택 입력.
    - `show_current_production(order) -> None`: 현재 생산 중인 주문 정보(`order_id`/
      `sample_id`/`customer_name`/`quantity`)를 표시한다. `order`가 `None`이면 "현재 생산 중인
      주문이 없습니다" 안내를 출력한다.
    - `show_production_queue(orders: list) -> None`: FIFO 순으로 정렬된 대기 큐를 표시하고,
      목록이 비어 있으면 "대기 중인 생산 주문이 없습니다" 안내를 출력한다.
    - `get_order_id_to_complete() -> str`: 생산완료 처리할 주문 ID 입력을 받아 앞뒤 공백을
      제거해 반환한다.
    - `show_production_completed(order) -> None`: 생산완료 처리 결과(전환된
      `order.status`인 `CONFIRMED`)를 표시한다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `main.py` 진입점, 메뉴 선택에 따른 실제 분기·루프(오케스트레이션) — Cycle 16.
- 출고 처리 메뉴의 입출력 — Cycle 16.
- 생산 진행률(부분 생산량) 추적 — `SPEC.md`에 정의되지 않은 새 데이터 모델 요구사항이므로
  범위 밖(위 설계 판단 2번 참고).
- 사용자 입력값 검증(존재하지 않는 주문 ID, `PRODUCING`이 아닌 주문에 대한 생산완료 처리 거부
  등) — 이미 `OrderRegistry.complete_production()`/`ProductionController.complete_production()`이
  담당하며, View는 형 변환 이상의 검증을 하지 않는다.
- `MonitoringController`/`ProductionController` 자체의 저장소 연동 — 모니터링은 조회만 하므로
  해당 없음(Cycle 12에서 이미 확인). `ProductionController`의 신규 조회 메서드
  (`list_production_queue`/`current_production_order`) 역시 데이터를 변경하지 않는 순수 조회이므로
  저장소 호출이 필요 없다.
- 생산완료 처리 선택 문자열을 실제 `ProductionController.complete_production()` 호출로 연결하는
  분기 로직 — Cycle 16.

## Mock 사용 범위 (SPEC.md §6 기준)

- `view/console_view.py`는 표준 입출력이라는 외부 경계이므로, Cycle 13·14와 동일하게
  `mocker.patch("builtins.input", side_effect=[...])`와 `capsys`를 사용한다.
- `controller/production_controller.py`는 "내부 협력" 계층이므로 `OrderRegistry`,
  `SampleRegistry`, `OrderRepository`, `SampleRepository`를 실제 객체로 조합해 테스트한다(mock
  사용 안 함). `Order.created_at` 생성 시점만 기존과 동일하게
  `mocker.patch("model.order_registry.datetime")`으로 결정적으로 고정한다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_production_controller.py — 신규 테스트 추가

import datetime as datetime_module

from controller.order_controller import OrderController
from controller.production_controller import ProductionController
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry
from storage.order_repository import OrderRepository
from storage.sample_repository import SampleRepository


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_생산_큐를_FIFO_순으로_조회한다(tmp_path, mocker):
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 10))
    order_registry = OrderRegistry()
    order_repo = OrderRepository(tmp_path / "orders.json")
    sample_repo = SampleRepository(tmp_path / "samples.json")
    order_controller = OrderController(order_registry, sample_registry, order_repo, sample_repo)

    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    first = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(first.order_id)  # 재고 10 < 200 → PRODUCING

    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 5, 0))
    second = order_controller.create_order("S-001", "SK하이닉스", 300)
    order_controller.approve_order(second.order_id)  # PRODUCING

    production_controller = ProductionController(order_registry, sample_registry, order_repo, sample_repo)

    queue = production_controller.list_production_queue()

    assert [order.order_id for order in queue] == [first.order_id, second.order_id]


def test_현재_생산중인_주문은_큐의_선두이다(tmp_path, mocker):
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 10))
    order_registry = OrderRegistry()
    order_repo = OrderRepository(tmp_path / "orders.json")
    sample_repo = SampleRepository(tmp_path / "samples.json")
    order_controller = OrderController(order_registry, sample_registry, order_repo, sample_repo)

    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)

    production_controller = ProductionController(order_registry, sample_registry, order_repo, sample_repo)

    current = production_controller.current_production_order()

    assert current.order_id == order.order_id


def test_생산_큐가_비어있으면_현재_생산중인_주문은_없다(tmp_path):
    sample_registry = SampleRegistry()
    order_registry = OrderRegistry()
    order_repo = OrderRepository(tmp_path / "orders.json")
    sample_repo = SampleRepository(tmp_path / "samples.json")
    production_controller = ProductionController(order_registry, sample_registry, order_repo, sample_repo)

    assert production_controller.current_production_order() is None
```

```python
# tests/test_console_view.py — 기존 파일에 추가

from model.order import Order, OrderStatus
from view.console_view import ConsoleView


def test_주문_상태별_개수를_출력한다(capsys):
    view = ConsoleView()
    counts = {
        OrderStatus.RESERVED: 2,
        OrderStatus.CONFIRMED: 1,
        OrderStatus.PRODUCING: 0,
        OrderStatus.RELEASE: 3,
    }

    view.show_order_counts(counts)

    out = capsys.readouterr().out
    assert "RESERVED" in out and "2" in out
    assert "RELEASE" in out and "3" in out


def test_재고_상태를_출력한다(capsys):
    view = ConsoleView()
    labels = {"S-001": "여유", "S-002": "부족", "S-003": "고갈"}

    view.show_stock_status(labels)

    out = capsys.readouterr().out
    assert "S-001" in out and "여유" in out
    assert "S-003" in out and "고갈" in out


def test_현재_생산중인_주문_정보를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.PRODUCING, "2026-07-15T09:00:00",
    )

    view.show_current_production(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "삼성전자 파운드리" in out


def test_현재_생산중인_주문이_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_current_production(None)

    out = capsys.readouterr().out
    assert "현재 생산 중인 주문이 없습니다" in out


def test_대기중인_생산_큐를_출력한다(capsys):
    view = ConsoleView()
    orders = [
        Order(
            "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
            OrderStatus.PRODUCING, "2026-07-15T09:00:00",
        ),
    ]

    view.show_production_queue(orders)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out


def test_대기중인_생산_큐가_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_production_queue([])

    out = capsys.readouterr().out
    assert "대기 중인 생산 주문이 없습니다" in out


def test_생산완료_처리할_주문_ID_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["ORD-20260715-0001"])
    view = ConsoleView()

    assert view.get_order_id_to_complete() == "ORD-20260715-0001"


def test_생산완료_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.CONFIRMED, "2026-07-15T09:00:00",
    )

    view.show_production_completed(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "CONFIRMED" in out
```

> 위 테스트 목록은 예시이며, GREEN 단계에서 모니터링/생산 라인 하위 메뉴 표시
> (`show_monitoring_menu`/`get_monitoring_menu_choice`/`show_production_menu`/
> `get_production_menu_choice`) 등 "다룰 범위"에 나열된 나머지 메서드에 대해서도 동일한 방식
> (단일 동작 검증, mock 최소화)으로 테스트를 추가한다.

## 진행 결과

- **RED** (`9d4af5a` Cycle 15 RED: 모니터링/생산 라인 메뉴 View 및 FIFO 큐 연결 실패 테스트):
  위 설계 판단 1~5번(`sort_production_queue`를 `ProductionController`의 신규 조회 메서드로
  연결하는 위치, "현재 생산 중" 표시를 큐 선두 주문의 기존 필드만으로 최소화하고 진행률은
  다루지 않는 판단, 대기 큐에서 선두 주문을 제외하지 않는 판단, 모니터링/생산 라인 모두 하위
  메뉴를 두는 판단, 상태별 개수를 `.value` 문자열로 표시하는 판단)을 사람 파트너 검토를 거쳐
  이견 없이 채택했다. `tests/test_production_controller.py`와 `tests/test_console_view.py`에
  신규 테스트를 추가해 실패를 확인했다.
- **GREEN** (`e8c297e` Cycle 15 GREEN: 모니터링/생산 라인 메뉴 View 및 FIFO 큐 연결 최소 구현):
  계획대로 `controller/production_controller.py`에 `list_production_queue()`,
  `current_production_order()`를 구현해 Cycle 8의 `sort_production_queue()`를 처음으로 실제
  데이터에 연결했다. `view/console_view.py`에는 모니터링 하위 메뉴(`show_monitoring_menu`,
  `get_monitoring_menu_choice`, `show_order_counts`, `show_stock_status`)와 생산 라인 하위
  메뉴(`show_production_menu`, `get_production_menu_choice`, `show_current_production`,
  `show_production_queue`, `get_order_id_to_complete`, `show_production_completed`)를
  구현했다. `ConsoleView`는 여전히 어떤 Controller/Model도 import하지 않는다.
- **최종 결과**: 신규 테스트 18개(`test_production_controller.py` 3개 + `test_console_view.py`
  15개)가 모두 통과하며, 전체 테스트 120개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 `main.py` 진입점, 메뉴 선택에 따른 실제 분기·루프, 출고 처리
  메뉴의 입출력, 생산 진행률(부분 생산량) 추적, 사용자 입력값 검증, 생산완료 처리 선택 문자열을
  실제 Controller 호출로 연결하는 분기 로직은 포함하지 않았다.
- **참고 — verify-agent 독립 검증 생략**: Cycle 12~14에 이어 이번 사이클도 verify-agent 독립
  검증을 생략했다(사람 파트너가 프로젝트 막바지 진행 속도를 위해 마지막 사이클까지 생략하고
  한 번에 몰아서 검증하기로 결정함). 이 검증은 나중에 몰아서 수행될 예정이다.

**추가 보완** (Cycle 18 이후, 계획 문서 없는 애드혹 수정 — RED `0b0cc67` → GREEN `8ea066b`):
사람 파트너가 `python main.py`를 직접 실행해보다가, "모니터링 → 재고량 확인"이 라벨(여유/부족/
고갈)만 보여주고 실제 재고 수량은 보여주지 않는다는 점을 발견했다. `PRD.md` §6.4는 원래부터
"시료별 현재 재고 수량과 ... 상태 표기"를 요구하고 있었으므로, 이는 범위 이탈이 아니라 그동안
누락되어 있던 PRD 요구사항을 뒤늦게 충족시킨 것이다. `MonitoringController.stock_status_by_sample()`의
반환 타입을 `dict[str, str]`(`{sample_id: 라벨}`)에서 `dict[str, dict]`(`{sample_id: {"label":
str, "stock_qty": int}}`)로 바꾸고, `ConsoleView.show_stock_status()`가
`"S-001 | 여유 (재고: 480)"` 형식으로 출력하도록 수정했다. `model/monitoring.py`의
`calculate_stock_status_label()` 자체는 변경하지 않았다. 이 반환 타입 변경은 Cycle 11이 원래
정의한 형태(`dict[str, str]`)와 다르므로, `plan/cycle-11-monitoring-aggregation.md`에도
상호 참조 각주를 남겼다. 관련 테스트(`test_시료별_재고상태_라벨을_계산한다`,
`test_재고_상태를_출력한다`) assertion을 갱신했고, 전체 테스트 142개가 회귀 없이 통과했다.
