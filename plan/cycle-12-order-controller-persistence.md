[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 12 — 주문/생산 컨트롤러 영속화 연동 (`OrderController`/`ProductionController` ↔ Repository) (GREEN 완료)

**이전 사이클**: [Cycle 11 — 모니터링 집계](cycle-11-monitoring-aggregation.md) (및
[Cycle 7·9·10 재설계 — 재고 예약 방식 전환](cycle-07-09-10-stock-reservation.md))
**다음 사이클**: [Cycle 13 — 콘솔 View 골격 + 메인 메뉴 요약 정보 + 시료 관리 메뉴](cycle-13-console-view-sample-menu.md)

## Cycle 12 분할 배경 — 왜 "콘솔 View/Controller 통합"을 한 사이클로 처리하지 않는가

`PLAN.md`에는 그동안 Cycle 12를 "콘솔 View/Controller 통합 (전체 메뉴 흐름)"이라는 개략 이름으로만
적어 두었다. 실제로 착수하려고 기존 코드를 점검해보니, 이 하나의 사이클로 묶기에는 다음과 같이
서로 독립적으로 검증 가능한 여러 작업이 섞여 있었다:

1. **주문/생산 컨트롤러의 영속화 연동이 아직 없다**: `SampleController`는 Cycle 3에서 이미
   `SampleRepository`와 연동되어 시작 시 로드/등록 시 저장을 하지만, `OrderController`와
   `ProductionController`는 Cycle 6에서 `OrderRepository`를 만든 이후로 한 번도 실제로
   연결되지 않았다. 이 상태로 View를 얹으면, 콘솔에서 주문을 생성/승인/생산완료해도
   애플리케이션을 재시작하면 전부 사라지는 반쪽짜리 기능이 된다. 이는 View 유무와 무관하게
   컨트롤러/모델 계층만으로 완결되게 검증할 수 있는 별도 단위다.
2. **콘솔 View 자체(메뉴 골격, 입출력 mock 전략)** — 아직 한 줄도 없는 새 영역.
3. **각 메뉴별 실제 흐름 연결** — 시료 관리, 시료 주문, 승인/거절, 모니터링, 생산 라인, 출고
   처리 각각을 어떤 입력에 어떤 출력을 내는지 좁혀서 검증해야 한다.
4. **`main.py` 진입점** — 저장소 경로 결정, 모든 Controller 조립, 메인 루프.

하나의 RED→GREEN 사이클로 이 네 가지를 한꺼번에 다루면 실패 테스트 하나하나가 "무엇이
실패해야 하는지"를 명확히 보여주기 어렵고, GREEN 구현도 지나치게 커진다
(`test-driven-development` 스킬의 "한 사이클에 하나의 동작만" 원칙과 어긋난다). 따라서 이번
로드맵을 다음과 같이 나눈다.

| Cycle | 범위 | 비고 |
|-------|------|------|
| **12 (이 문서)** | `OrderController`/`ProductionController` ↔ `OrderRepository`/`SampleRepository` 영속화 연동 | View 없음, 순수 컨트롤러/모델 계층 |
| 13 (예정) | 콘솔 View 골격 + 메인 메뉴 진입 시 요약 정보 표시 + 시료 관리 메뉴(등록/조회/검색) | `input`/`print` mock 전략 확정 |
| 14 (예정) | 시료 주문 메뉴 + 주문 승인/거절 메뉴 | Cycle 12에서 연동된 영속화를 그대로 재사용 |
| 15 (예정) | 모니터링 메뉴 + 생산 라인 메뉴(현재 생산 중 표시 + 대기 큐 조회 + 생산완료 처리) | `sort_production_queue`를 처음으로 실제 데이터에 연결 |
| 16 (예정) | 출고 처리 메뉴 + `main.py` 진입점(저장소 경로 결정, 전체 Controller 조립, 메인 루프) | 프로젝트의 마지막 사이클 |

Cycle 13~16의 세부 계획(목표/범위/예시 테스트)은 각 사이클 직전에 작성한다(기존 관례와 동일).
이번 문서는 Cycle 12만 상세히 다룬다.

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능을, Cycle 5~7에서 주문 접수(`RESERVED`)와 승인/거절을,
Cycle 8~9에서 생산 큐 계산과 생산 완료 처리를, Cycle 10에서 출고 처리를, Cycle 11에서 모니터링
집계를 구현했다. 이후 별도로 진행된 재고 예약 재설계([cycle-07-09-10-stock-reservation.md](cycle-07-09-10-stock-reservation.md))로
`OrderController.approve_order()`(승인 시 재고 충분하면 즉시 예약)와
`ProductionController.complete_production()`(생산 완료 시 재고 증가 후 즉시 재예약)의 재고 처리
시점이 확정됐다. 이 시점 이후로 `OrderStatus`/`Sample.stock_qty`가 정확히 언제 바뀌는지는
안정적으로 정의되어 있다.

그런데 `storage/order_repository.py`(Cycle 6에서 저장/로드/충돌 감지까지 구현 완료)는
`SampleRepository`와 달리 아직 `OrderController`/`ProductionController` 어디에도 연결되어
있지 않다. 즉:

- `OrderController`로 주문을 생성/승인/거절/출고해도 `orders.json`에 아무것도 기록되지 않는다.
- `ProductionController.complete_production()`으로 상태를 바꾸고 재고를 늘려도 `orders.json`,
  `samples.json` 어느 쪽에도 반영되지 않는다.
- 애초에 `OrderController`/`ProductionController`가 시작 시 `orders.json`을 읽어 `OrderRegistry`를
  채우는 로직도 없다.

이번 사이클은 이 갭을 Cycle 3(`SampleController` ↔ `SampleRepository` 연동)와 같은 패턴으로
메운다.

## 목표

`PRD.md` §6.2(시료 주문)·§6.3(주문 승인/거절)·§6.5(생산 라인 — 생산완료 처리)와 `SPEC.md` §2의
`storage/order_repository.py`가, 실제로 `OrderController`/`ProductionController`의 상태 변경
동작과 연결되어 파일에 반영되는 최소 동작을 정의한다. View는 전혀 다루지 않는다 — 이 사이클이
끝나면 "콘솔이 없어도, 컨트롤러 메서드 호출만으로 주문/재고 변경이 파일에 영속화된다"는 것을
테스트로 증명한다.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. `OrderRegistry`에 "이미 만들어진 `Order`를 그대로 복원"하는 메서드가 필요하다

`OrderRegistry.create()`는 `order_id` 채번(`datetime.now()` 기반)과 검증(공백 고객명, 0 이하
수량 거부)까지 함께 수행하므로, 저장소에서 불러온 *이미 완성된* `Order` 객체를 다시 넣는
용도로는 맞지 않는다(재채번되거나 불필요한 검증이 다시 실행된다). `SampleRegistry.register()`는
이 문제가 없었다(`Sample`은 생성 시점 로직이 없어 로드/신규 등록 모두 같은 검증만 거치면 된다).

**판단**: `model/order_registry.py`에 `OrderRegistry.restore(orders: list[Order]) -> None`을
새로 추가한다 — 채번/검증 없이 주어진 `Order` 목록을 그대로 내부 상태로 설정한다(컨트롤러
생성 시 저장소에서 불러온 목록을 한 번에 주입하는 용도로만 사용). **확인 필요**: 손상된
`orders.json`(예: 중복 `order_id`)에 대한 처리는 Cycle 6에서와 동일하게 이번에도 범위 밖으로
둔다(`SampleController.duplicate_sample_ids()`에 대응하는 요구사항이 `Order`에 대해 아직
`SPEC.md`에 명시되어 있지 않음). 필요해지면 이후 사이클에서 별도로 다룬다.

### 2. 저장소 의존성을 어떻게 주입할 것인가 — 기존 생성자에 필수 인자로 추가

`SampleController`가 `SampleRegistry`와 `SampleRepository`를 둘 다 필수로 주입받는 기존
패턴을 그대로 따른다. `OrderController`/`ProductionController` 생성자에 `order_repository:
OrderRepository`, `sample_repository: SampleRepository`를 필수 인자로 추가한다(선택적 `None`
기본값으로 만들어 저장 로직을 건너뛰게 하는 방식은 검토했으나 채택하지 않았다 — 저장소 없이
컨트롤러를 만드는 경로를 열어두면 "저장이 실제로 되는지"를 항상 신경 써야 하는 이중 분기가
생기고, `SampleController`의 기존 패턴과도 어긋난다).

이로 인해 기존 `tests/test_order_controller.py`(9개)와 `tests/test_production_controller.py`
(2개)의 생성자 호출부를 모두 `tmp_path` 기반 실제 저장소를 넘기도록 갱신해야 한다. Cycle
7·9·10 재설계 때도 기존 테스트 assertion을 광범위하게 갱신한 전례가 있으므로, 이번에도 동일한
방식(GREEN 단계에서 기존 테스트를 새 생성자 시그니처에 맞게 갱신)을 따른다.

`ProductionController`가 `SampleRepository`까지 필요한 이유: `complete_production()`이
`sample_registry.increase_stock()`/`decrease_stock()`으로 재고를 바꾸므로, 그 결과를
`samples.json`에도 반영해야 한다.

### 3. 어떤 저장소를 언제 저장할 것인가

메서드별로 실제로 바뀌는 데이터만 저장한다(불필요한 파일 쓰기를 피하기 위해):

| 메서드 | `order_repository.save()` | `sample_repository.save()` |
|--------|---------------------------|------------------------------|
| `OrderController.create_order()` | 항상 | 안 함 (재고 불변) |
| `OrderController.approve_order()` | 항상 | 재고가 실제로 예약(감소)된 경우만 (`stock_sufficient`가 참일 때) |
| `OrderController.reject_order()` | 항상 | 안 함 (재고 불변) |
| `OrderController.release_order()` | 항상 | 안 함 (재설계 이후 출고는 순수 상태 전이 — 재고 불변) |
| `ProductionController.complete_production()` | 항상 | 항상 (재고가 항상 바뀐다) |

각 저장은 해당 메서드가 예외 없이 끝까지 성공했을 때만 수행한다(기존 상태 전이 메서드들이
이미 대상 상태가 아니면 `ValueError`를 던지고 아무것도 바꾸지 않으므로, 예외가 나면 저장 호출
자체에 도달하지 않는다 — 실패 시 파일 변경 없음이 자동으로 보장된다).

### 4. 생성자에서 기존 주문을 불러오는 시점

`SampleController`와 동일하게, `OrderController.__init__()`에서
`order_repository.load()` 결과를 `order_registry.restore()`로 레지스트리에 채운다.
`ProductionController`는 자체적으로 데이터를 불러오지 않는다 — `OrderRegistry`/
`SampleRegistry` 인스턴스를 `OrderController`와 공유해서 주입받는 기존 구조(Cycle 9 이후 계속
그래왔듯)를 유지하므로, 로드는 `OrderController` 생성 시 한 번만 일어나면 충분하다.

같은 이유로 `OrderRepository`/`SampleRepository` 인스턴스도 `OrderController`와
`ProductionController`가 동일 인스턴스를 공유해야 한다 — 같은 파일을 가리키는 별도의 저장소
인스턴스를 두 컨트롤러에 각각 만들어 넘기면, 한 프로세스 안에서 저장소 인스턴스마다 독립적으로
추적하는 버전/충돌 감지 상태가 어긋나 같은 파일을 두고 스스로와 `ConflictError`를 일으킬 수
있다. 호출자(테스트, 그리고 이후 `main.py`)가 저장소 인스턴스를 한 번만 만들어 두 컨트롤러에
동일하게 주입해야 한다.

## 이번 사이클에서 다룰 범위

- `model/order_registry.py`:
  - `OrderRegistry.restore(orders: list[Order]) -> None`: 채번/검증 없이 주어진 목록을 그대로
    내부 상태로 설정한다.
- `controller/order_controller.py`:
  - 생성자가 `order_repository: OrderRepository`, `sample_repository: SampleRepository`를
    추가로 주입받는다(`SampleRegistry` 자리는 그대로 유지 — 기존 `sample_registry` 인자와
    별개로 저장소만 추가).
  - 생성 시점에 `order_repository.load()` 결과로 `order_registry.restore()`를 호출한다.
  - `create_order()`/`approve_order()`/`reject_order()`/`release_order()` 각각 성공 시,
    위 표에 따라 `order_repository.save(order_registry.list_all())`(항상) 및 필요한 경우
    `sample_repository.save(sample_registry.list_all())`를 호출한다.
- `controller/production_controller.py`:
  - 생성자가 `order_repository: OrderRepository`, `sample_repository: SampleRepository`를
    추가로 주입받는다.
  - `complete_production()` 성공 시 `order_repository.save(...)`와
    `sample_repository.save(...)`를 모두 호출한다.
- 기존 `tests/test_order_controller.py`, `tests/test_production_controller.py`의 생성자
  호출부를 새 시그니처(저장소 인자 추가)에 맞게 갱신한다(GREEN 단계에서 진행, 이번 RED
  단계에서는 새로 추가되는 영속화 검증 테스트만 작성한다).

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 콘솔 View, `main.py` 진입점 — Cycle 13~16.
- 손상된 `orders.json`(중복 `order_id`)에 대한 예외 없는 처리 — Cycle 6과 동일한 이유로 범위
  밖(위 설계 판단 1번 참고). `SPEC.md`에 `Order`에 대한 해당 요구사항이 아직 명시되지 않았다.
- `ConflictError`가 발생했을 때 컨트롤러가 이를 어떻게 사용자에게 안내할지(재시도 유도 등) —
  Cycle 3에서도 동일하게 미뤘던 것과 같은 이유로, 콘솔 View가 생기는 Cycle 13 이후에 다룬다.
  이번 사이클은 예외가 그대로 전파되는지만 확인한다.
- `MonitoringController`의 저장소 연동 — 모니터링은 데이터를 변경하지 않고 조회만 하므로
  저장소 연동이 필요 없다(범위 자체가 없음).

## Mock 사용 범위 (SPEC.md §6 기준)

- `controller/`는 "내부 협력" 계층이므로 `OrderRegistry`, `SampleRegistry`, `OrderRepository`,
  `SampleRepository`를 실제 객체로 조합해 테스트한다(mock 사용 안 함). 저장소도 `tmp_path` 기반
  실제 파일 I/O로 검증한다(Cycle 3·6과 동일한 이유 — 정상 경로에는 파일시스템 mock이 필요
  없다).
- `Order` 생성 시점(`created_at`, `order_id` 채번)을 결정적으로 만들기 위해 기존과 동일하게
  `mocker.patch("model.order_registry.datetime")`을 사용한다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_controller.py — 신규 테스트 추가 (기존 9개 테스트는 생성자 시그니처만 갱신)

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


def _controller(tmp_path, sample_registry):
    return OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )


def test_생성시_주문_저장소의_기존_주문을_레지스트리에_불러온다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    seed_repo = OrderRepository(tmp_path / "orders.json")
    seed_controller = _controller(tmp_path, sample_registry)
    seed_controller.create_order("S-001", "삼성전자 파운드리", 200)

    restarted = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )

    assert len(restarted.list_orders()) == 1  # list_orders()는 이번 사이클에서 추가하는 조회 통로


def test_주문_생성에_성공하면_주문_저장소에도_반영된다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = _controller(tmp_path, sample_registry)

    controller.create_order("S-001", "삼성전자 파운드리", 200)

    reloaded = OrderRepository(tmp_path / "orders.json").load()
    assert len(reloaded) == 1


def test_승인시_재고가_예약되면_주문저장소와_시료저장소_모두_반영된다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    sample_repo_path = tmp_path / "samples.json"
    SampleRepository(sample_repo_path).save(sample_registry.list_all())
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(sample_repo_path),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    controller.approve_order(order.order_id)

    reloaded_orders = OrderRepository(tmp_path / "orders.json").load()
    reloaded_samples = SampleRepository(sample_repo_path).load()
    assert reloaded_orders[0].status.value == "CONFIRMED"
    assert reloaded_samples[0].stock_qty == 280  # 480 - 200 즉시 예약, 파일에도 반영


def test_주문_생성_검증에_실패하면_저장소를_변경하지_않는다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = _controller(tmp_path, sample_registry)

    with pytest.raises(ValueError):
        controller.create_order("S-001", "   ", 200)  # 공백 고객명 → 거부

    reloaded = OrderRepository(tmp_path / "orders.json").load()
    assert reloaded == []  # 실패 시 파일 변경 없음
```

```python
# tests/test_production_controller.py — 신규 테스트 추가

def test_생산완료_처리하면_주문저장소와_시료저장소_모두_반영된다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    order_registry = OrderRegistry()
    orders_path = tmp_path / "orders.json"
    samples_path = tmp_path / "samples.json"
    order_controller = OrderController(
        order_registry, sample_registry,
        OrderRepository(orders_path), SampleRepository(samples_path),
    )
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING

    production_controller = ProductionController(
        order_registry, sample_registry,
        OrderRepository(orders_path), SampleRepository(samples_path),
    )
    production_controller.complete_production(order.order_id)

    reloaded_orders = OrderRepository(orders_path).load()
    reloaded_samples = SampleRepository(samples_path).load()
    assert reloaded_orders[0].status.value == "CONFIRMED"
    assert reloaded_samples[0].stock_qty == 14  # 순증가 = actual_qty(164) - shortage(150)... 계산은 GREEN 단계에서 실제 값으로 확정
```

> 참고: `test_생성시_주문_저장소의_기존_주문을_레지스트리에_불러온다` 예시는
> `OrderController.list_orders()`라는 조회 메서드가 아직 없다는 것을 전제로 한다 —
> `SampleController.list_samples()`에 대응하는 통로가 `OrderController`에도 필요하다고 보고
> 이번 사이클 범위에 포함했다(Cycle 14의 "시료 주문 메뉴"가 접수된 주문 목록을 조회할 때 이
> 메서드를 재사용할 것이다). **확인 필요**: 이 메서드 추가가 사이클 범위를 벗어난다고 판단되면
> (예: "조회는 View 연동 사이클에서"), 제외하고 Cycle 14로 미룰 수 있다 — 다만 영속화 테스트
> 자체(재시작 후 주문이 남아있는지)를 검증하려면 `order_registry`를 직접 참조하는 대신 어떤
> 조회 통로가 있어야 하므로, 최소한의 `list_orders()` 정도는 이번 사이클에 포함하는 편이
> 자연스럽다고 판단했다.

## 진행 결과

- **계획** (`a858478` Cycle 12 계획: 주문/생산 컨트롤러 영속화 연동): 위 설계 판단 1~4번
  (`OrderRegistry.restore()` 신설, 저장소 필수 주입, 메서드별 저장 대상 표,
  `OrderController.list_orders()` 추가, 두 컨트롤러의 저장소 인스턴스 공유)을 사람 파트너
  검토를 거쳐 이견 없이 그대로 채택했다.
- **RED** (`8893a2b` Cycle 12 RED: 주문/생산 컨트롤러 영속화 연동 실패 테스트 작성): 위 예시
  테스트대로 `tests/test_order_controller.py`(4개 신규), `tests/test_production_controller.py`
  (1개 신규)를 작성해 실패를 확인했다.
- **GREEN** (`b76c86a` Cycle 12 GREEN: 주문/생산 컨트롤러 영속화 연동 최소 구현): 계획대로
  `model/order_registry.py`에 `OrderRegistry.restore()`를, `controller/order_controller.py`에
  저장소 필수 주입 + 생성 시 로드 + 성공 시 저장 + `list_orders()`를,
  `controller/production_controller.py`에 저장소 필수 주입 + 성공 시 저장을 구현했다.
- **GREEN 진행 중 발견/수정한 문제 두 가지**:
  1. RED 단계에서 커밋된 `test_production_controller.py`의 기대값이 계획 문서(14)와 다르게
     (64) 잘못 적혀 있던 것을 발견해 14로 수정했다(재고 50, shortage=150, actual_qty=164,
     최종 재고 = 50 + 164 - 200 = 14).
  2. 기존 회귀 테스트
     `test_두_CONFIRMED_주문을_순서대로_출고해도_둘_다_성공한다`에서, `OrderController`와
     `ProductionController`가 같은 파일을 가리키는 서로 다른 저장소 인스턴스를 각각 생성해
     쓰다 보니 인스턴스별 충돌 감지 상태가 어긋나 스스로와 `ConflictError`가 발생하는 문제를
     발견했다. 두 컨트롤러가 저장소 인스턴스를 공유하도록 테스트를 수정해 해결했다(이 설계
     판단은 위 설계 판단 4번 문단에 이미 반영되어 있다).
- **최종 결과**: `tests/test_order_controller.py`(4개 신규) + `tests/test_production_controller.py`
  (1개 신규) = 5개 테스트가 모두 통과하며, 전체 테스트 85개가 회귀 없이 통과한다(기존 9개+2개
  테스트의 생성자 호출부도 새 시그니처에 맞게 갱신됨).
- **범위 준수 확인**: 계획대로 콘솔 View, `main.py`, 손상된 `orders.json` 처리, `ConflictError`
  사용자 안내는 포함하지 않았다. `model/order.py`, `model/sample.py`, `model/production_queue.py`,
  `model/monitoring.py`, `controller/sample_controller.py`, `controller/monitoring_controller.py`,
  `model/sample_registry.py`, `storage/order_repository.py`, `storage/sample_repository.py`는
  수정되지 않았다.
- **참고 — verify-agent 독립 검증 생략**: 이번 사이클은 verify-agent 독립 검증을 생략했다(사람
  파트너가 프로젝트 막바지 진행 속도를 위해 Cycle 12부터 마지막 사이클까지 verify-agent/
  doc-consistency-verifier를 생략하고 마지막에 한 번에 몰아서 검증하기로 결정함). 이 검증은
  나중에 몰아서 수행될 예정이다.
