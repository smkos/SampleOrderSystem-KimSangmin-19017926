[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 6 — 주문 영속화 (`OrderRepository`)

**이전 사이클**: [Cycle 5 — 주문 모델 + 접수(RESERVED)](cycle-05-order-reservation.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~4에서 시료(Sample) 관련 기능이 완성되었고, 그중 Cycle 2에서 `storage/sample_repository.py`의
`SampleRepository`가 `samples.json`에 대한 원자적 쓰기(임시 파일 → `os.replace`)와 sha256 해시
기반 동시성 충돌 감지(`ConflictError`)를 구현해 검증까지 마쳤다. `_loaded` 플래그로 "load() 호출
여부"와 "로드된 파일의 해시값"을 구분해, "파일이 없는 상태로 load() → 이후 외부에서 파일 생성 →
save()" 엣지 케이스까지 정확히 처리하는 패턴이 확립되어 있다.

Cycle 5에서는 `model/order.py`(`Order`, `OrderStatus`)와 `model/order_registry.py`
(`OrderRegistry.create()` — 채번/검증 후 `RESERVED` 상태로 생성), `controller/order_controller.py`
(`OrderController.create_order()` — 존재하지 않는 `sample_id` 거부 후 위임)를 구현했다. 다만 이
`OrderRegistry`는 아직 인메모리로만 동작하며, 애플리케이션을 재시작하면 생성한 주문이 모두
사라진다.

이번 사이클은 `SPEC.md` §2/§3에 정의된 `storage/order_repository.py`로 `Order` 목록을
`orders.json`에 영속화한다. Cycle 2에서 확립한 원자적 쓰기 + 충돌 감지 패턴을 `Order`에 맞게
그대로 이식하되, `Sample`과 달리 `status` 필드가 `OrderStatus` enum이므로 JSON 직렬화 시
문자열로 변환/역변환하는 로직이 추가로 필요하다.

## 목표

`Order` 목록을 `orders.json` 파일로 저장하고 다시 불러올 수 있도록 하며(`SPEC.md` §3), 저장 중
실패해도 기존 파일이 손상되지 않고, 로드 이후 파일이 외부에서 변경되면 저장 시 충돌을
감지한다(`SPEC.md` §5).

## 설계 판단 (모호한 지점 — 검토 필요)

1. **`ConflictError`를 공유할지, 새로 정의할지**: `SPEC.md` §2는 `storage/sample_repository.py`와
   `storage/order_repository.py`를 나란히 독립된 모듈로 나열하고, `ConflictError`가 두 모듈이
   공유하는 공통 타입이라는 언급은 없다. 두 저장소가 완전히 다른 파일(`samples.json` /
   `orders.json`)을 다루고 서로 참조할 이유가 없으므로, `storage/order_repository.py`에
   `ConflictError`를 **새로 독립 정의**해 모듈 간 결합을 만들지 않는 쪽으로 판단했다. (참고:
   `Sample`↔`Order`가 서로 다른 파일을 다루는 것처럼, 두 저장소가 우연히 같은 이름의 예외를
   갖는 것은 "동일한 패턴을 각자 이식"한 결과이지 "공유 타입"이 될 필요는 없다고 본다.) —
   **확인 필요**: 만약 향후 `try/except ConflictError` 하나로 두 저장소를 함께 다루는 코드가
   필요해지면(예: Cycle 12 콘솔 통합에서 저장 실패를 한 곳에서 처리), 이때는 공통
   `storage/errors.py` 같은 공유 모듈로 리팩터링하는 것을 재검토할 수 있다. 지금은 중복을
   감수하고 독립시키는 쪽을 택한다.
2. **컨트롤러 연동 포함 여부**: Cycle 2(저장소만) → Cycle 3(컨트롤러 연동)으로 나뉜 전례를
   그대로 따라, 이번 사이클은 `OrderRepository` 자체(저장/로드/충돌 감지)만 다루고
   `OrderController`/`OrderRegistry`와의 연동(시작 시 로드, 생성 시 자동 저장)은 별도 사이클로
   분리한다.

## 이번 사이클에서 다룰 범위

- `storage/order_repository.py`:
  - `ConflictError(Exception)`: `order_repository` 전용으로 새로 정의.
  - `OrderRepository(path: Path)`
    - `save(orders: list[Order]) -> None`: `orders.json`에 원자적 쓰기(임시 파일 →
      `os.replace`). `Order.status`(`OrderStatus` enum)는 `status.value`(문자열)로 직렬화한다
      (`SPEC.md` §3 예시: `"status": "PRODUCING"`).
    - `load() -> list[Order]`: `orders.json`을 읽어 `Order` 목록으로 변환. 파일이 없으면 빈
      목록을 반환. 저장된 `status` 문자열은 `OrderStatus(value)`로 역변환한다.
    - 동시성 충돌 감지: Cycle 2의 `SampleRepository`와 동일하게 `_loaded` 플래그 +
      sha256 해시로, load() 이후 외부에서 파일이 변경되면 `save()` 시 `ConflictError`를
      발생시킨다. "파일이 없는 상태로 load() → 이후 외부에서 파일 생성 → save()" 엣지 케이스도
      Cycle 2와 동일하게 처리한다.
- 저장 포맷은 `SPEC.md` §3의 `orders.json` 스키마를 그대로 따른다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `model/order_registry.py`(`OrderRegistry`)와 `OrderRepository`를 연결하는 로직(예: 컨트롤러
  시작 시 자동 로드, 주문 생성/상태 변경 시 자동 저장) — 별도 사이클(Controller 연동)에서
  다룬다.
- 주문 승인/거절(`RESERVED → REJECTED`/`CONFIRMED`/`PRODUCING`), 재고 확인 분기 — Cycle 7.
- 생산 완료 처리, 생산 큐 계산(부족분/실생산량/총생산시간, FIFO 정렬) — Cycle 8~9.
- 출고 처리(`CONFIRMED → RELEASE`) — Cycle 10.
- 콘솔 View/Controller 연동 — Cycle 12.
- 손상된 `orders.json`(예: 중복 `order_id`)에 대한 처리 — `SampleController`의
  `duplicate_sample_ids()`에 대응하는 요구사항이 `Order`에 대해 SPEC.md에 명시되어 있지 않으므로
  이번 사이클에서는 다루지 않는다. 필요해지면 이후 사이클에서 SPEC 근거를 확인 후 추가한다.

## Mock 사용 범위 (SPEC.md §6 기준)

- 정상 저장/로드 경로는 `tmp_path` 픽스처로 실제 파일 I/O를 사용해 검증한다 (mock 사용 안 함).
- 원자적 쓰기 중 실패(예: `os.replace`가 예외를 던지는 상황)처럼 재현하기 어려운 실패 경로는
  `pytest-mock`의 `mocker`로 파일시스템 호출을 모의하여 검증한다 — SPEC.md §6이 정의한
  "외부 경계(파일시스템)"에 해당하므로 mock 사용이 적절하다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_repository.py (신규)

import pytest

from model.order import Order, OrderStatus
from storage.order_repository import ConflictError, OrderRepository


def _sample_order(order_id="ORD-20260715-0001", status=OrderStatus.RESERVED):
    return Order(order_id, "S-001", "삼성전자 파운드리", 200, status, "2026-07-15T09:32:15")


def test_저장한_주문_목록을_그대로_불러온다(tmp_path):
    repo = OrderRepository(tmp_path / "orders.json")
    repo.save([_sample_order()])

    loaded = repo.load()

    assert len(loaded) == 1
    assert loaded[0].order_id == "ORD-20260715-0001"
    assert loaded[0].status == OrderStatus.RESERVED


def test_저장된_status는_문자열로_기록된다(tmp_path):
    import json

    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.save([_sample_order(status=OrderStatus.PRODUCING)])

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data[0]["status"] == "PRODUCING"


def test_파일이_없으면_빈_목록을_반환한다(tmp_path):
    repo = OrderRepository(tmp_path / "orders.json")
    assert repo.load() == []


def test_쓰기_도중_실패해도_기존_파일이_손상되지_않는다(tmp_path, mocker):
    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.save([_sample_order()])

    mocker.patch("storage.order_repository.os.replace", side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        repo.save([_sample_order(order_id="ORD-20260715-0002")])

    # 실패 이전 저장 내용이 그대로 남아 있어야 한다
    assert repo.load()[0].order_id == "ORD-20260715-0001"


def test_로드_이후_외부에서_파일이_변경되면_저장시_충돌을_감지한다(tmp_path):
    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.save([_sample_order()])

    loaded_repo = OrderRepository(path)
    loaded_repo.load()

    # 다른 프로세스가 파일을 직접 수정한 상황을 재현
    other_repo = OrderRepository(path)
    other_repo.save([_sample_order(order_id="ORD-20260715-9999")])

    with pytest.raises(ConflictError):
        loaded_repo.save([_sample_order(order_id="ORD-20260715-0002")])


def test_로드시_파일이_없었는데_이후_외부에서_생성되면_저장시_충돌을_감지한다(tmp_path):
    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.load()  # 파일이 없는 상태로 로드

    other_repo = OrderRepository(path)
    other_repo.save([_sample_order()])

    with pytest.raises(ConflictError):
        repo.save([_sample_order(order_id="ORD-20260715-0002")])
```

이 목표/범위로 RED 단계를 진행해도 될지 검토 부탁드립니다.
