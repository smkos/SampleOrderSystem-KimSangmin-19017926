[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 18 — 더미 주문(Order) 데이터 생성기 (`DummyDataGenerator_PoC` 이식, 로드맵 확장)

**이전 사이클**: [Cycle 17 — 더미 시료(Sample) 데이터 생성기](cycle-17-dummy-sample-generator.md)
**다음 사이클**: 아직 없음 (저장 wrapper, 콘솔 메뉴 연동 등은 이후 사이클에서 새로 계획한다 —
이번 사이클의 "다루지 않는 것" 참고)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~16을 거치며 `PRD.md`의 모든 기능(시료 등록, 주문 접수·승인/거절, 생산, 출고, 모니터링)이
구현 완료되었다. Cycle 17에서는 사람 파트너의 요청으로 로드맵을 확장해
`devtools/dummy_data_generator.py`를 신설하고, `Sample` 도메인 객체를 시드 주입 가능한 순수
함수(`generate_dummy_sample`, `generate_dummy_samples`)로 재현 가능하게 생성하는 기능을
구현했다(GREEN 완료). Cycle 17은 설계 판단 6번에서 더미 `Order` 생성을 명시적으로 다음 사이클로
미뤄뒀다 — "더미 `Order` 생성은 참조할 실제(또는 더미) `Sample` 목록이 먼저 있어야 하므로,
`existing_samples`에서 `sample_id`를 무작위로 골라 연결해야 한다"는 전제가 이제 충족되었다(Cycle
17의 `generate_dummy_samples`가 그 `Sample` 목록을 만들어 줄 수 있다).

이번 Cycle 18은 그 후속으로, `Order`용 더미 데이터 생성 순수 함수를 같은
`devtools/dummy_data_generator.py`에 추가한다.

## 목표

`SPEC.md` §1.2(Order 필드)를 기준으로, 기존 `Sample` 목록을 참조해 재현 가능한(시드 주입 가능한)
더미 주문 입력값을 생성하는 순수 함수를 작성한다. `Order` 자체는 `SPEC.md` §1.2에 정의된 필드를
갖지만, 이 사이클이 다루는 것은 `OrderController.create_order()`/`OrderRegistry.create()`에
바로 넘길 수 있는 입력값 생성이다(설계 판단 1번 참고).

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. 반환 타입 — 완성된 `Order` 객체가 아니라 `dict` 입력값을 반환한다

`SPEC.md` §1.2에 따르면 `order_id`는 `ORD-YYYYMMDD-NNNN` 형식으로 **자동 채번**되고,
`created_at`도 **자동 생성**되며, `status`도 등록 시점에 항상 `RESERVED`로 자동 설정된다. 이
채번·생성·검증 로직은 이미 `OrderRegistry.create(sample_id, customer_name, quantity)`(및 이를
감싸는 `OrderController.create_order`)가 전적으로 책임진다(Cycle 5).

Cycle 17에서는 `Sample`이 `SampleRegistry.register()`가 채번하지 않는 도메인이라 생성기가 직접
`sample_id`를 채번하고 완성된 `Sample` 객체를 반환하는 것이 타당했다. 그러나 `Order`는 반대로
"Registry가 이미 채번을 전담하는" 도메인이므로, 생성기가 임의의 `order_id`/`created_at`을 미리
만들어 `Order` 객체를 완성하면:

- 실제로 `OrderController.create_order()`에 등록할 때는 그 값들이 다시 버려지고 Registry가 새로
  채번한 값으로 대체되어, 애초에 만든 값이 무의미해진다.
- "누가 `order_id`를 채번하는가"에 대해 이 프로젝트 전체에서 지켜온 "Registry가 채번을 책임진다"
  원칙(Cycle 5, 6, 12)과 충돌한다 — 생성기가 자체적으로 `order_id` 형식(`ORD-YYYYMMDD-NNNN`,
  일자별 4자리 일련번호)을 흉내 내 계산하려면 `OrderRegistry`의 내부 채번 로직(같은 날짜의 기존
  주문 수 세기)을 중복 구현해야 하며, 이는 두 코드베이스가 어긋날 위험을 만든다.

**판단**: `generate_dummy_order_input(existing_samples, rng) -> dict` 형태로, `{"sample_id":
str, "customer_name": str, "quantity": int}` 3개 키만 담은 dict를 반환한다. 호출자(다음
사이클의 wrapper 또는 콘솔 메뉴)는 이 dict를
`order_controller.create_order(**generate_dummy_order_input(...))`처럼 바로 전개해 넘길 수
있다. `order_id`/`created_at`/`status`는 이 함수의 관심사가 아니다 — Cycle 17에서 `Sample`에
대해 내렸던 "완성된 도메인 객체를 직접 반환한다"는 판단과 의도적으로 다른 형태이며, 그 이유는
두 도메인의 채번 책임 소재가 다르기 때문이다(`Sample`은 Registry가 채번하지 않고, `Order`는
Registry가 채번한다).

### 2. `existing_samples`가 비어 있을 때의 동작 — `ValueError`

더미 주문은 반드시 등록된 `Sample`을 참조해야 하므로(`SPEC.md` §1.2 — `sample_id`는 "등록된
Sample 참조"), 참조할 `Sample`이 하나도 없으면 유효한 더미 주문 입력값을 만들 수 없다.
`OrderController.create_order()`도 존재하지 않는 `sample_id`를 넘기면 결국 실패하므로, 애초에
호출하지 못하게 생성 시점에 `ValueError`를 던지는 편이 실패를 더 빨리, 더 명확한 원인으로
드러낸다. Cycle 17이 `count < 0`일 때 `ValueError`를 던진 것과 같은 "유효하지 않은 입력을
조기에 거부한다"는 방침과도 일치한다.

**판단**: `existing_samples`가 빈 리스트면 `ValueError`를 던진다.

### 3. `customer_name`/`quantity` 범위

- `customer_name`: 미리 정의한 반도체 고객사명 접두어 목록(예: `삼성전자 파운드리`, `SK하이닉스`,
  `TSMC코리아`, `DB하이텍`)에서 하나를 무작위로 고른다 — Cycle 17이 `Sample.name`을 도메인에
  맞는 조합으로 생성한 것과 동일한 접근이며, `SPEC.md` §1.2 예시(`"삼성전자 파운드리"`)와도
  자연스럽게 어울린다. 완전한 무작위 문자열보다 도메인에 맞는 값이 테스트/데모 용도로 더
  유용하다.
- `quantity`: `rng.randint(1, 500)` — `SPEC.md` §1.2의 `quantity > 0` 제약을 항상 만족하며,
  기존 예시 데이터(`SPEC.md` 예시의 `200`)와 비슷한 자릿수 범위로 좁힌다.
- `sample_id`: `rng.choice(existing_samples).sample_id` — `existing_samples`에서 무작위로 하나
  선택한다.

### 4. 모듈 위치 — Cycle 17과 동일한 `devtools/dummy_data_generator.py`에 함수 추가

새 파일로 분리할 만큼 이 함수가 크거나 독립적이지 않고(단일 함수, `Sample` 생성 로직과 마찬가지로
파일 I/O 없는 순수 함수), Cycle 17이 이미 정의한 "부가 개발 도구는 `devtools/`에 둔다"는 위치
판단을 그대로 따르는 것이 자연스럽다. 기존 `_NAME_PREFIXES`/`_NAME_SUFFIXES`와 이름 형태가
겹치므로 새 상수는 `_CUSTOMER_NAME_CANDIDATES` 등으로 구분해 같은 파일에 추가한다.

**판단**: 별도 파일로 분리하지 않고 `devtools/dummy_data_generator.py`에 함수를 추가한다.

### 5. 저장 wrapper/콘솔 메뉴 연동 — 이번 사이클에도 포함하지 않는다

Cycle 17과 동일한 이유(계층 분리 — "무작위 값 생성"과 "그 값을 Controller에 등록하는
오케스트레이션"을 분리해 각각 검증)로, `add_dummy_orders(count, order_controller,
existing_samples, rng=None)` 같은 wrapper 함수와 콘솔 View 메뉴 연동은 이후 별도 사이클로
미룬다.

**판단**: 이번 사이클은 순수 함수(`generate_dummy_order_input`)만 다룬다.

## 이번 사이클에서 다룰 범위

- `devtools/dummy_data_generator.py`에 함수 추가:
  - `generate_dummy_order_input(existing_samples: list, rng: random.Random | None = None) ->
    dict`:
    - `existing_samples`가 빈 리스트면 `ValueError`.
    - `rng`가 없으면 `random.Random()`(비결정적)을 기본값으로 사용.
    - 반환값은 `{"sample_id": str, "customer_name": str, "quantity": int}` 정확히 3개 키를
      가진 dict.
    - `sample_id`는 `existing_samples` 중 하나(`rng.choice`)의 `sample_id`.
    - `customer_name`은 미리 정의한 후보 목록 중 하나(`rng.choice`).
    - `quantity`는 `rng.randint(1, 500)`.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 완성된 `Order` 객체 생성이나 `order_id`/`created_at`/`status` 채번 로직 재구현 (설계 판단
  1번 — 이는 여전히 `OrderRegistry.create()`/`OrderController.create_order()`의 책임이다).
- 여러 개의 더미 주문 입력값을 한 번에 생성하는 `generate_dummy_order_inputs(count, ...)` 같은
  복수형 함수 — Cycle 17의 `generate_dummy_samples`처럼 count 기반 반복이 필요한지는 이번
  사이클 결과를 본 뒤 판단한다(단일 입력값 생성 함수만 우선 검증).
- `OrderController`/저장소에 실제로 등록·저장하는 wrapper 함수 (설계 판단 5번).
- 콘솔 View 메뉴 연동 (설계 판단 5번).
- `SPEC.md` 문서 갱신 (계획 승인 후 별도 진행 권장).

## Mock 사용 범위 (SPEC.md §6 기준)

- `devtools/dummy_data_generator.py`는 파일 I/O나 표준 입출력이 없는 순수 함수이므로, Cycle
  17과 동일하게 mock 없이 실제 `random.Random(고정 시드)`와 `Sample` 객체로 직접 테스트한다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_dummy_data_generator.py (기존 파일에 추가)

import random

import pytest

from devtools.dummy_data_generator import generate_dummy_order_input
from model.sample import Sample


def test_동일한_시드로_생성하면_완전히_같은_주문_입력값이_생성된다():
    samples = [Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100)]

    first = generate_dummy_order_input(samples, rng=random.Random(42))
    second = generate_dummy_order_input(samples, rng=random.Random(42))

    assert first == second


def test_existing_samples가_비어있으면_ValueError():
    with pytest.raises(ValueError):
        generate_dummy_order_input([], rng=random.Random(1))


def test_생성된_sample_id는_existing_samples_중_하나다():
    samples = [
        Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100),
        Sample("S-002", "GaN 에피택셜-6인치", 2.0, 0.8, 50),
    ]
    existing_ids = {s.sample_id for s in samples}

    result = generate_dummy_order_input(samples, rng=random.Random(7))

    assert result["sample_id"] in existing_ids


def test_생성된_quantity는_0보다_크다():
    samples = [Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100)]

    result = generate_dummy_order_input(samples, rng=random.Random(7))

    assert result["quantity"] > 0


def test_반환값은_sample_id_customer_name_quantity_키만_가진다():
    samples = [Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100)]

    result = generate_dummy_order_input(samples, rng=random.Random(7))

    assert set(result.keys()) == {"sample_id", "customer_name", "quantity"}
```

## 검토 요청

위 목표/범위(특히 설계 판단 1번 — Cycle 17의 `Sample`과 달리 완성된 `Order` 객체가 아니라
`dict` 입력값만 반환하는 판단, 설계 판단 2번 — `existing_samples`가 비어 있으면 `ValueError`를
던지는 판단, 설계 판단 5번 — 저장 wrapper/콘솔 메뉴 연동을 다음 사이클로 미루는 판단)으로 RED
단계를 진행해도 될지 검토 부탁드립니다.
