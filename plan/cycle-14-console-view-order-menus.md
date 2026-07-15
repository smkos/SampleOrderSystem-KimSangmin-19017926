[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 14 — 콘솔 View: 시료 주문 메뉴 + 주문 승인/거절 메뉴 (GREEN 완료)

**이전 사이클**: [Cycle 13 — 콘솔 View 골격 + 메인 메뉴 요약 정보 + 시료 관리 메뉴](cycle-13-console-view-sample-menu.md)
**다음 사이클**: [Cycle 15 — 콘솔 View: 모니터링 메뉴 + 생산 라인 메뉴](cycle-15-console-view-monitoring-production-menus.md)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~11에서 Model/Controller 계층(시료 등록/조회/검색, 주문 접수·승인/거절·출고 처리, 생산
큐 계산과 생산 완료 처리, 모니터링 집계)을 모두 구현했다. Cycle 12에서 `OrderController`/
`ProductionController`를 각각의 저장소(`OrderRepository`/`SampleRepository`)와 연결해, 콘솔이
없어도 컨트롤러 메서드 호출만으로 상태 변경이 파일에 영속화되는 것까지 확인했다.

Cycle 13에서 `view/console_view.py`(`ConsoleView`)를 신설해 콘솔 View의 골격과 입출력 mock
전략(`mocker.patch("builtins.input", side_effect=[...])` + `capsys`)을 확정하고, 메인 메뉴
진입 시 요약 정보 표시와 시료 관리 하위 메뉴(등록/조회/검색)의 입출력을 구현했다(진행 상태:
RED 완료 후 GREEN 진행 예정). 이때 다음 두 가지 설계 판단이 확정됐고, 이번 사이클도 그대로
계승한다.

1. **`ConsoleView`는 Controller를 호출하지 않는다** — 표시 메서드는 이미 계산된 데이터를
   인자로 받아 화면에 출력만 하고, 입력 메서드는 사용자 입력을 dict/문자열 등 단순 자료구조로
   반환할 뿐, 그 값을 어느 Controller 메서드에 넘길지는 알지 못한다. "메뉴 선택 → Controller
   호출 → 결과를 View로 표시"라는 오케스트레이션은 `main.py`(Cycle 16)의 책임으로 남긴다.
2. **출력 검증은 `capsys`, 입력은 `mocker.patch("builtins.input", side_effect=[...])`** — 화면
   문구 전체를 대상으로 "포함되는가"만 확인해 사소한 줄바꿈 변경에 테스트가 깨지지 않도록 한다.

이제 `PLAN.md`의 로드맵([plan/cycle-12-order-controller-persistence.md](cycle-12-order-controller-persistence.md)
9~40행)에 따라 이번 사이클은 그중 두 번째 단계 — 시료 주문 메뉴와 주문 승인/거절 메뉴의 화면
동작을 정의한다. `OrderController.create_order()`/`approve_order()`/`reject_order()`/
`list_orders()`는 Cycle 12에서 이미 저장소와 연동되어 있으므로, 이번 사이클은 그 위에 얹을
View만 다룬다.

## 목표

`PRD.md` §6.2(시료 주문)·§6.3(주문 승인/거절)과 `SPEC.md` §2(`view/console_view.py`)·§6(콘솔
I/O는 mock)에 따라, `ConsoleView`가 다음 두 화면의 입출력을 담당하는 최소 동작을 정의한다.

1. **시료 주문**: 시료 ID/고객명/주문 수량을 순서대로 입력받고, 생성된 주문(`RESERVED` 상태)의
   결과를 표시한다.
2. **주문 승인/거절**: 접수된 주문(`RESERVED`) 목록을 표시하고, 처리할 주문과 승인/거절 여부를
   입력받아, 그 결과(`CONFIRMED`/`PRODUCING`으로 전환됨 또는 `REJECTED`로 전환됨)를 표시한다.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. "접수된 주문 목록" 필터링은 View의 책임이 아니다 — Cycle 13의 `summary` dict 판단과 동일하게 보류

`PRD.md` §6.3은 "접수된 주문 목록: `RESERVED` 상태의 주문 목록을 표시"라고 명시한다.
`OrderController.list_orders()`(Cycle 12에서 추가)는 모든 상태의 주문을 반환하므로, 어딘가에서
`RESERVED`만 걸러내야 한다.

Cycle 13 설계 판단 2번("`ConsoleView`는 순수 입출력만 담당하고 Controller를 호출하지 않는다")과
설계 판단 3번("`summary` dict를 실제로 채우는 집계 조립은 `main.py`가 조립되는 Cycle 16으로
미룬다")을 그대로 적용하면, 이번에도 동일한 결론에 도달한다.

**판단**: `ConsoleView.show_pending_orders(orders: list) -> None`은 이미 걸러진 주문 목록을
그대로 표시만 한다 — 어떤 상태의 주문을 넘길지 결정하는 필터링 자체는 View의 책임이 아니다.
실제로 `RESERVED`만 걸러내는 코드가 어디에 위치할지(예: `OrderController`에
`list_pending_orders()` 같은 전용 조회 메서드를 추가할지, 아니면 `model/monitoring.py`의
`count_orders_by_status`처럼 순수 필터 함수를 `model/` 계층에 추가해 재사용할지, 혹은 `main.py`
조립 시점에 `[o for o in controller.list_orders() if o.status == OrderStatus.RESERVED]`처럼
인라인으로 처리할지)는 Controller/Model이 View와 실제로 연결되는 Cycle 16(`main.py` 전체
조립)에서 결정한다. 이번 사이클의 테스트는 `show_pending_orders()`에 `RESERVED` 주문만 담긴
리스트를 직접 넘겨 화면 표시만 검증한다 — Cycle 13의 `show_sample_list()`가 이미 걸러진/정렬된
데이터를 그대로 받아 표시만 하는 것과 동일한 패턴이다.

**확인 필요**: Cycle 16에서 필터링 위치를 결정할 때, `model/monitoring.py`에 이미 있는 상태별
집계 개념(`count_orders_by_status`)을 확장해 "상태별 필터링" 순수 함수를 추가하는 안과,
`OrderController`에 전용 조회 메서드를 추가하는 안 중 어느 쪽이 나은지는 그 시점에 다시
판단이 필요하다. 이번 사이클에서는 미리 결정하지 않는다.

### 2. 승인/거절 선택 입력값의 의미는 View가 해석하지 않는다

주문 승인/거절 메뉴에서 사용자는 처리할 주문을 고른 뒤 "승인"과 "거절" 중 하나를 선택해야
한다. Cycle 13의 `get_sample_menu_choice()`가 하위 메뉴 선택 문자열을 그대로 반환하고 그 값의
의미(어느 기능으로 분기할지)는 View가 판단하지 않았던 것과 동일하게, `get_approval_decision()`도
사용자가 입력한 원본 문자열(예: `"1"` 또는 `"2"`, 혹은 `"승인"`/`"거절"`)을 그대로 반환한다.
이 문자열을 승인/거절 중 무엇으로 해석해 어느 Controller 메서드(`approve_order`/
`reject_order`)를 호출할지는 `main.py`(Cycle 16)의 오케스트레이션 책임이다.

**판단**: 메뉴 표시 문구(`show_pending_orders()`가 함께 출력하는 안내 문구 등)에서 "1. 승인",
"2. 거절"처럼 선택지를 명시하고, `get_approval_decision()`은 그 선택 문자열을 그대로 반환한다
(형식은 Cycle 13의 `get_menu_choice()`/`get_sample_menu_choice()`와 동일하게 앞뒤 공백만
제거).

### 3. 승인 결과 표시 — "재고 상황에 따른 자동 분기" 결과를 그대로 보여주는 단일 메서드

`PRD.md` §6.3에 따르면 승인 처리 결과는 재고 상황에 따라 `CONFIRMED` 또는 `PRODUCING`으로
자동 분기한다. 이 분기 로직 자체는 이미 `OrderController.approve_order()`(Cycle 7/12)가
수행하므로, View는 그 결과로 돌아온 `Order` 객체의 `status`만 보고 표시하면 된다.

**판단**: 승인 성공을 표시하는 메서드는 `show_order_approved(order) -> None` 하나로 통일한다
(`order.status`가 `CONFIRMED`인지 `PRODUCING`인지에 따라 표시 문구만 달라질 뿐, 메서드를
분기 결과별로 나눌 필요는 없다 — Cycle 13의 `show_sample_registered(sample)`처럼 결과 객체
하나를 받아 표시하는 패턴과 일관된다). 거절 성공은 `show_order_rejected(order) -> None`으로
별도 메서드를 둔다(전이 결과가 항상 `REJECTED`로 고정이라 분기가 없으므로 승인과 자연스럽게
다른 메서드가 된다).

### 4. 시료 주문 메뉴는 하위 메뉴(진입 화면) 없이 입력→결과 표시 두 메서드로 충분하다

`PRD.md` §5의 메인 메뉴 목록에서 "시료 관리"만 등록/조회/검색 세 기능을 가진 하위 메뉴가
필요했다(Cycle 13에서 `show_sample_menu()`/`get_sample_menu_choice()` 추가). "시료 주문"은
PRD상 입력값(시료 ID/고객명/수량)을 받아 주문을 생성하는 단일 동작이므로, 별도 하위 메뉴 화면
없이 바로 입력을 받는다.

**판단**: `get_new_order_input() -> dict`, `show_order_created(order) -> None` 두 메서드만
정의한다. "주문 승인/거절"은 목록 표시 → 대상 선택 → 승인/거절 선택 → 결과 표시라는 여러
단계가 있으므로 하위 메뉴 화면 없이도 각 단계별 메서드(`show_pending_orders`,
`get_order_id_to_process`, `get_approval_decision`, `show_order_approved`,
`show_order_rejected`)로 충분히 표현된다 — Cycle 13에서 "시료 관리"에만 하위 메뉴 화면을 둔
것과 일관되게, 여러 하위 기능이 있는 메뉴에만 진입 화면을 둔다는 기준을 유지한다.

## 이번 사이클에서 다룰 범위

- `view/console_view.py` (기존 `ConsoleView`에 메서드 추가):
  - **시료 주문**:
    - `get_new_order_input() -> dict`: 시료 ID, 고객명, 주문 수량을 순서대로 입력받아
      `{"sample_id": str, "customer_name": str, "quantity": int}` 형태로 반환한다(형 변환만
      수행, 값 검증은 하지 않는다 — 검증은 `OrderRegistry`/`OrderController`의 책임).
    - `show_order_created(order) -> None`: 생성된 주문(`order_id`, `status`인
      `RESERVED` 포함)의 접수 완료 메시지를 출력한다.
  - **주문 승인/거절**:
    - `show_pending_orders(orders: list) -> None`: 이미 걸러진(`RESERVED`) 주문 목록을
      `order_id`/`sample_id`/`customer_name`/`quantity`와 함께 출력하고, 목록이 비어 있으면
      "접수된 주문이 없습니다" 안내를 출력한다.
    - `get_order_id_to_process() -> str`: 처리할 주문 ID 입력을 받아 앞뒤 공백을 제거해
      반환한다.
    - `get_approval_decision() -> str`: 승인/거절 선택 입력을 받아 앞뒤 공백을 제거해 그대로
      반환한다(해석은 하지 않는다).
    - `show_order_approved(order) -> None`: 승인 처리 결과(전환된 `order.status`가
      `CONFIRMED`/`PRODUCING` 중 무엇이든)를 표시한다.
    - `show_order_rejected(order) -> None`: 거절 처리 결과(`REJECTED`로 전환됨)를 표시한다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `main.py` 진입점, 메뉴 선택에 따른 실제 분기·루프(오케스트레이션) — Cycle 16.
- "접수된 주문(`RESERVED`)만 걸러내는" 필터링 로직의 실제 위치(Controller 전용 메서드 vs
  `model/monitoring.py` 확장 vs `main.py` 인라인) — 위 설계 판단 1번에 따라 Cycle 16(또는
  그 이전 재검토 사이클)에서 결정한다.
- 모니터링, 생산 라인, 출고 처리 메뉴의 입출력 — Cycle 15~16.
- 사용자 입력값 검증(존재하지 않는 시료 ID 거부, 수량 0 이하 거부, `RESERVED`가 아닌 주문에
  대한 승인/거절 거부 등) — 이미 `OrderRegistry`/`OrderController`가 담당하며, View는 형 변환
  이상의 검증을 하지 않는다.
- 승인/거절 선택 문자열(`"1"`/`"2"` 등)을 실제 `approve_order()`/`reject_order()` 호출로
  연결하는 분기 로직 — Cycle 16.

## Mock 사용 범위 (SPEC.md §6 기준)

- `view/console_view.py`는 표준 입출력이라는 외부 경계이므로, Cycle 13과 동일하게
  `mocker.patch("builtins.input", side_effect=[...])`와 `capsys`를 사용한다.
- `Order` 등 View에 넘길 데이터는 mock 없이 실제 객체(`Order(...)` 생성자 직접 호출)를
  사용한다 — Cycle 13에서 `Sample`을 실제 객체로 사용한 것과 동일한 이유다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_console_view.py — 기존 파일에 추가

from model.order import Order, OrderStatus
from view.console_view import ConsoleView


def test_시료_주문_입력을_순서대로_받아_dict로_반환한다(mocker):
    mocker.patch(
        "builtins.input",
        side_effect=["S-001", "삼성전자 파운드리", "200"],
    )
    view = ConsoleView()

    result = view.get_new_order_input()

    assert result == {
        "sample_id": "S-001",
        "customer_name": "삼성전자 파운드리",
        "quantity": 200,
    }


def test_주문_생성_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.RESERVED, "2026-07-15T09:32:15",
    )

    view.show_order_created(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "RESERVED" in out


def test_접수된_주문_목록을_출력한다(capsys):
    view = ConsoleView()
    orders = [
        Order(
            "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
            OrderStatus.RESERVED, "2026-07-15T09:32:15",
        ),
    ]

    view.show_pending_orders(orders)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "삼성전자 파운드리" in out


def test_접수된_주문이_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_pending_orders([])

    out = capsys.readouterr().out
    assert "접수된 주문이 없습니다" in out


def test_처리할_주문_ID_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["ORD-20260715-0001"])
    view = ConsoleView()

    assert view.get_order_id_to_process() == "ORD-20260715-0001"


def test_승인_거절_선택_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["1"])
    view = ConsoleView()

    assert view.get_approval_decision() == "1"


def test_승인_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.CONFIRMED, "2026-07-15T09:32:15",
    )

    view.show_order_approved(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "CONFIRMED" in out


def test_거절_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.REJECTED, "2026-07-15T09:32:15",
    )

    view.show_order_rejected(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "REJECTED" in out
```

> 위 테스트 목록은 예시이며, GREEN 단계에서 세부 문구(예: 승인 결과가 `PRODUCING`으로
> 전환된 경우의 표시)에 대해서도 동일한 방식(단일 동작 검증, mock 최소화)으로 테스트를
> 보강한다.

## 진행 결과

- **RED** (`b90bf86` Cycle 14 RED: 시료 주문/승인·거절 메뉴 View 실패 테스트 작성): 위 설계
  판단 1~4번(접수된 주문 목록 필터링 위치 보류, 승인/거절 선택 입력의 해석 보류, 결과 표시
  메서드 구성, 시료 주문 메뉴에 하위 메뉴를 두지 않는 기준)을 사람 파트너 검토를 거쳐 이견 없이
  채택했다. `tests/test_console_view.py`에 신규 테스트를 추가해 실패를 확인했다.
- **GREEN** (`7051972` Cycle 14 GREEN: 시료 주문/승인·거절 메뉴 View 최소 구현): 계획대로
  `view/console_view.py`에 `get_new_order_input`, `show_order_created`,
  `show_pending_orders`, `get_order_id_to_process`, `get_approval_decision`,
  `show_order_approved`, `show_order_rejected`를 구현했다. `order.status`(enum)를 표시할 때
  `order.status.value`(문자열)를 사용해 "RESERVED"/"CONFIRMED" 등 텍스트로 노출되도록
  했다(계획 문서에 명시되지 않은 세부 구현 선택이지만 표시 요건 충족을 위한 최소 구현이다).
- **최종 결과**: `tests/test_console_view.py`의 9개 신규 테스트(`PRODUCING` 케이스 포함)가 모두
  통과하며, 전체 테스트 105개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 `ConsoleView`는 여전히 어떤 Controller/Model도 import하지
  않는다(순수 입출력만 담당). `main.py`, 접수된 주문 필터링 로직의 실제 위치, 모니터링/생산
  라인/출고 처리 메뉴, 사용자 입력값 검증, 승인/거절 선택 문자열을 실제 Controller 호출로
  연결하는 분기 로직은 포함하지 않았다.
- **참고 — verify-agent 독립 검증 생략**: Cycle 12~13에 이어 이번 사이클도 verify-agent 독립
  검증을 생략했다(사람 파트너가 프로젝트 막바지 진행 속도를 위해 마지막 사이클까지 생략하고
  한 번에 몰아서 검증하기로 결정함). 이 검증은 나중에 몰아서 수행될 예정이다.
