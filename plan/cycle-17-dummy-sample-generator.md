[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 17 — 더미 시료(Sample) 데이터 생성기 (`DummyDataGenerator_PoC` 이식, 로드맵 확장) (GREEN 완료)

**이전 사이클**: [Cycle 16 — 출고 처리 메뉴 + `main.py` 진입점](cycle-16-order-release-menu-main-entrypoint.md)
**다음 사이클**: 아직 없음 (더미 주문 생성기, 저장 wrapper, 콘솔 메뉴 연동 등은 이후 사이클에서
새로 계획한다 — 이번 사이클의 "다루지 않는 것" 참고)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~16을 거치며 `model/`(`Sample`/`SampleRegistry`, `Order`/`OrderRegistry`,
`production_queue`, `monitoring`), `controller/`(`SampleController`/`OrderController`/
`ProductionController`/`MonitoringController`), `view/console_view.py`, `storage/*_repository.py`,
`main.py`(전체 조립)까지 `PRD.md`의 모든 기능(시료 등록, 주문 접수·승인/거절, 생산, 출고,
모니터링)이 구현 완료되었다(Cycle 16은 이 계획 시점에 아직 RED 검토 대기 중이나, 본 사이클과
무관하게 독립적으로 진행된다).

이번 사이클은 `PRD.md`/`SPEC.md`에 정의된 신규 기능이 아니라, 사람 파트너의 요청으로
로드맵을 확장해 추가하는 **개발/테스트 편의 도구**다. `CLAUDE.md`는 이 프로젝트가 재사용할 4개
PoC 중 하나로 `DummyDataGenerator_PoC`("시드 주입 가능한 순수 함수 형태의 더미 데이터 생성기")를
명시하고 있으며, 지금까지 이 PoC는 아직 이식되지 않았다. 이 PoC를 조사한 결과, 핵심 인터페이스는
`random.seed()` 전역 호출이 아니라 `random.Random` 인스턴스를 인자로 주입받는 순수 함수이며,
"순수 데이터 생성 함수"(파일 I/O 없음, `generate_dummy_contact(s)`)와 "저장까지 하는 wrapper
함수"(`add_dummy_contacts`, 내부에서 `contacts_crud.load/save_contacts` 호출)가 명확히
분리되어 있었다.

## 목표

`DummyDataGenerator_PoC`의 "시드 주입 가능한 순수 함수" 패턴을 이 프로젝트의 `Sample` 모델에
이식한다 — 테스트/데모용으로 임의의 `Sample` 목록을 재현 가능하게 생성하는 순수 함수를
작성한다. `SPEC.md`에 아직 정의되지 않은 새 도구이므로, 이번 사이클의 판단 내용을 근거로 승인 후
`SPEC.md`에 별도 절을 추가하는 것을 권장한다(이번 계획 단계에서는 문서 수정을 하지 않는다).

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. 순수 함수 vs 저장 wrapper — 이번 사이클은 순수 함수만 다룬다

`DummyDataGenerator_PoC`는 순수 함수(`generate_dummy_contact(s)`)와 저장 wrapper
(`add_dummy_contacts`, 내부에서 `contacts_crud.load/save_contacts` 호출)를 분리해 두었다. 이
프로젝트는 이미 `SampleRegistry.register()`가 중복 ID·공백 이름·수율 범위 검증을 수행하고,
`SampleController.register_sample()`이 그 등록 결과를 저장소(`SampleRepository`)에 반영하는
계층 구조를 갖고 있다(Cycle 1, 3). 따라서 "저장까지 하는 wrapper"에 해당하는 것은 PoC의
`contacts_crud.load/save_contacts` 직접 호출이 아니라 **기존 `SampleController.register_sample()`을
반복 호출하는 것**이 이 프로젝트의 계층 구조와 맞는다.

다만 이 wrapper(예: `add_dummy_samples(count, sample_controller, rng=None)`)를 이번 사이클에
함께 넣을지, 순수 함수만 먼저 다룰지 판단이 필요했다. **판단**: 이번 사이클은 순수 함수만
다룬다 — 지금까지의 사이클 진행 관례(Cycle 1이 "인메모리 등록"만 다루고 영속화를 Cycle 2로
미룬 것과 동일하게)를 따라, "무작위 필드값을 생성하는 순수 로직"과 "그 결과를
`SampleController`에 등록하는 오케스트레이션"을 분리해 각각 검증한다. wrapper 함수와 콘솔 메뉴
연동은 다음 사이클로 미룬다.

### 2. 모듈 위치 — `SPEC.md` §2에 새 항목 없음, 최상위 `devtools/` 신설

`SPEC.md` §2(모듈 구조)는 `model/`/`view/`/`controller/`/`storage/` 네 디렉터리만 정의하며,
더미 데이터 생성기가 들어갈 자리가 없다. 다음 두 후보를 검토했다.

- (a) `model/` 안에 순수 함수로 추가 — `model/`은 "이 시스템의 실제 도메인 로직"(`Sample`,
  `SampleRegistry`, 생산 큐 계산, 모니터링 집계)만 담아 왔다. 더미 데이터 생성은 도메인 로직이
  아니라 테스트/데모 편의 도구이므로, 여기 섞으면 "Model은 시스템이 실제로 필요로 하는 로직만
  담는다"는 지금까지의 경계가 흐려진다.
- (b) 최상위 `devtools/` 신설 — `DummyDataGenerator_PoC` 자체도 `MVC_PoC`/`DataPersistence_PoC`
  구조에 속하지 않는 별개의 최상위 스크립트(`dummy_data_generator.py`)였다. 이 프로젝트에서도
  더미 데이터 생성기를 시스템의 정식 기능(MVC 계층)이 아닌 부가 개발 도구로 취급하는 것이
  PoC의 원래 성격과 일치한다.

**판단**: (b) `devtools/dummy_data_generator.py`를 신설한다. `SPEC.md` §2는 이번 계획 승인 후
별도로 "부가 도구" 절을 추가해 이 위치를 문서화할 것을 권장한다(이번 계획 단계에서는 수정하지
않음).

### 3. Sample 채번 — `SampleRegistry`/`SampleController`에 없는 로직을 생성기가 직접 담당

`OrderRegistry.create()`와 달리 `SampleRegistry.register()`는 `sample_id`를 자동 채번하지
않는다(`SPEC.md` §1.1 — "등록 시 사용자가 지정"). 더미 생성기가 실제로 쓸모 있으려면 스스로
`sample_id`를 채번해야 한다. `DummyDataGenerator_PoC`의 `generate_dummy_contacts()`가
`contacts_crud.next_id(existing_contacts)`를 호출해 다음 ID를 계산하던 것과 동일한 필요성이다.

**판단**: `devtools/dummy_data_generator.py`에 `_next_sample_id(existing_samples: list[Sample])
-> str` 내부 헬퍼를 둔다. `S-` 접두사 + 숫자 형식(`SPEC.md` §1.1 예시 `S-001`)의 기존
`sample_id`들에서 가장 큰 숫자를 찾아 그다음 번호부터(`S-{n:03d}`, 3자리 미만이면 0-padding,
넘치면 자리수가 늘어남) 이어서 채번한다. `S-`로 시작하지 않거나 숫자가 아닌 형식의 기존
`sample_id`(예: 손상되었거나 사용자가 임의 형식으로 등록한 경우)는 채번 계산에서 무시하되,
생성된 후보 ID가 우연히 기존 목록과 겹치면 건너뛰고 다음 번호를 사용해 중복을 피한다(방어적
처리 — `SPEC.md` §5의 "중복 ID 등록 거부"와 충돌하지 않도록).

### 4. 반환 타입 — `dict`가 아닌 `Sample` 객체를 직접 반환

`DummyDataGenerator_PoC`는 연락처를 `dict`로 반환했다(그 PoC의 연락처 도메인 자체가 원시
`dict` 기반이었기 때문). 이 프로젝트는 이미 `Sample`이라는 정식 도메인 객체가 있고,
`SampleController.register_sample(sample)`/`SampleRegistry.register(sample)` 모두 `Sample`
인스턴스를 인자로 받는다. **판단**: `dict`가 아니라 `Sample` 인스턴스를 직접 생성해 반환한다 —
호출자(다음 사이클의 wrapper)가 바로 `register_sample()`에 넘길 수 있어야 불필요한 변환 단계가
없다. 이는 PoC 패턴에서 의도적으로 벗어나는 지점이라 명시해 둔다.

### 5. 필드값 범위 — `SPEC.md` §1.1 제약을 지키는 현실적인 범위 설정

`avg_production_time_min`(> 0), `yield_rate`(`0 < yield_rate <= 1`), `stock_qty`(>= 0) 외에는
`SPEC.md`에 상한이 없다. 다음 범위를 제안한다(모두 시드 주입된 `rng`로 생성, 결정론적):

- `name`: 미리 정의한 시료명 접두어 목록(예: `실리콘 웨이퍼`, `GaN 에피택셜`, `SiC 파워소자`,
  `GaAs RF소자`)과 규격 접미어(예: `4인치`, `6인치`, `8인치`, `12인치`)를 조합해
  `"{접두어}-{접미어}"` 형태로 생성한다 — 완전한 무작위 문자열보다 도메인(반도체 시료)에 맞는
  이름을 만들기 위함.
- `avg_production_time_min`: `round(rng.uniform(0.1, 5.0), 2)` — 0보다 크다는 제약을 항상
  만족.
- `yield_rate`: `round(rng.uniform(0.7, 1.0), 2)` — `0 < yield_rate <= 1` 제약을 항상 만족하며,
  현실적인 반도체 공정 수율 범위(70~100%)로 좁힌다.
- `stock_qty`: `rng.randint(0, 1000)` — `>= 0` 제약을 항상 만족.

### 6. Order 더미 생성·wrapper·콘솔 메뉴 연동 — 이번 사이클에는 포함하지 않는다

더미 `Order` 생성은 참조할 실제(또는 이미 생성된 더미) `Sample`이 먼저 존재해야 하므로 이번
`Sample` 더미 생성기가 먼저 검증되어야 설계할 수 있다. 또한 `Order` 더미 생성기는
`OrderController.create_order(sample_id, customer_name, quantity)`가 이미 채번(`order_id`)과
`created_at` 생성, 존재하는 `sample_id` 검증을 모두 수행하므로, 순수 함수가 만들어야 할 값은
"기존 `Sample` 목록 중 하나를 무작위로 고른 `sample_id`, 무작위 `customer_name`, 무작위
`quantity`"뿐이다 — `Sample`보다 설계가 단순하지만, 이번 사이클 범위를 좁게 유지하기 위해
별도 사이클로 미룬다.

**판단**: 이번 사이클은 `Sample` 더미 생성 순수 함수까지만 다룬다. 다음 항목은 이후 별도
사이클로 넘긴다.

- 더미 `Order` 생성 순수 함수(`existing_samples`에서 `sample_id`를 무작위로 골라 연결).
- `add_dummy_samples(count, sample_controller, rng=None)` / `add_dummy_orders(...)` 같은 저장
  wrapper 함수(설계 판단 1번).
- 콘솔 View/`main.py`에 "더미 데이터 생성" 메뉴 추가.
- `SPEC.md` §2에 `devtools/` 위치를 공식 문서화하는 것(계획 승인 후 별도 진행 권장).

## 이번 사이클에서 다룰 범위

- `devtools/dummy_data_generator.py` (신규 파일):
  - `generate_dummy_sample(sample_id: str, rng: random.Random) -> Sample`: 주어진
    `sample_id`로 단일 더미 `Sample`을 생성한다(설계 판단 5번의 필드 범위).
  - `generate_dummy_samples(count: int, existing_samples: list[Sample], rng:
    random.Random | None = None) -> list[Sample]`:
    - `count < 0`이면 `ValueError`.
    - `rng`가 없으면 `random.Random()`(비결정적)을 기본값으로 사용.
    - `existing_samples`를 참고해 `_next_sample_id()`로 이어지는 `sample_id`를 채번하며
      `count`개의 `Sample`을 생성해 반환한다(등록/저장은 하지 않음 — 순수 함수).

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 더미 `Order` 생성 (설계 판단 6번).
- `SampleController`/저장소에 실제로 등록·저장하는 wrapper 함수 (설계 판단 1·6번).
- 콘솔 View 메뉴 연동 (설계 판단 6번).
- `SPEC.md` §2 문서 갱신 (설계 판단 2·6번 — 계획 승인 후 별도 진행).
- 손상된 `sample_id`(예: `S-` 접두어가 아닌 형식)를 실제로 갖는 `existing_samples`에 대한
  포괄적 형식 파싱 규칙 확정 — 설계 판단 3번의 "무시 + 중복 시 건너뛰기" 최소 방어만 다루고,
  그 이상의 정교한 형식 검증은 다루지 않는다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `devtools/dummy_data_generator.py`는 파일 I/O나 표준 입출력이 없는 순수 함수이므로, `model/`
  계층과 동일하게 mock 없이 실제 `random.Random(고정 시드)`와 `Sample` 객체로 직접 테스트한다.
  `random.Random` 인스턴스에 고정 시드를 주입하는 것 자체가 "결정적 재현"을 보장하는 방식이며,
  `mocker.patch`로 난수 생성을 가로챌 필요가 없다(PoC와 동일한 접근).

## 작성할 실패 테스트 (예시)

```python
# tests/test_dummy_data_generator.py (신규 파일)

import random

import pytest

from devtools.dummy_data_generator import generate_dummy_sample, generate_dummy_samples
from model.sample import Sample


def test_동일한_시드로_생성하면_완전히_같은_시료_목록이_생성된다():
    first = generate_dummy_samples(5, [], rng=random.Random(42))
    second = generate_dummy_samples(5, [], rng=random.Random(42))

    assert [(s.sample_id, s.name, s.avg_production_time_min, s.yield_rate, s.stock_qty)
            for s in first] == \
           [(s.sample_id, s.name, s.avg_production_time_min, s.yield_rate, s.stock_qty)
            for s in second]


def test_count가_음수이면_ValueError():
    with pytest.raises(ValueError):
        generate_dummy_samples(-1, [], rng=random.Random(1))


def test_기존_시료_다음_번호부터_이어서_채번된다():
    existing = [Sample("S-001", "기존 시료", 0.5, 0.9, 100)]

    generated = generate_dummy_samples(2, existing, rng=random.Random(1))

    assert [s.sample_id for s in generated] == ["S-002", "S-003"]


def test_생성된_시료의_수율은_0보다_크고_1_이하다():
    generated = generate_dummy_samples(20, [], rng=random.Random(7))

    assert all(0 < s.yield_rate <= 1 for s in generated)


def test_생성된_시료의_재고와_생산시간은_유효_범위를_만족한다():
    generated = generate_dummy_samples(20, [], rng=random.Random(7))

    assert all(s.stock_qty >= 0 for s in generated)
    assert all(s.avg_production_time_min > 0 for s in generated)
```

## 진행 결과

- **RED** (`0e61080`): 위 설계 판단 1~6번(순수 함수만 이번 사이클에 다루고 저장 wrapper는 다음
  사이클로 미루는 판단, 새 최상위 `devtools/` 디렉터리 신설, `SampleRegistry`가 채번하지 않는
  `sample_id`를 생성기가 직접 채번하는 판단, PoC의 `dict` 대신 `Sample` 객체를 직접 반환하는
  판단, 필드값 범위 설정, 더미 `Order` 생성/wrapper/콘솔 메뉴 연동을 별도 사이클로 미루는 판단)을
  사람 파트너 검토를 거쳐 이견 없이 채택했다. 계획 문서의 예시 테스트 5개를 그대로
  `tests/test_dummy_data_generator.py`(신규 파일)에 작성해 실패를 확인했다.
- **GREEN** (`8ac9b2b`): 계획대로 `devtools/dummy_data_generator.py`(신규 파일)에
  `generate_dummy_sample`, `generate_dummy_samples`, `_next_sample_id`를 구현했다. 설계 판단
  1~6번 모두 GREEN 구현에서 이견 없이 그대로 채택됐다.
- **최종 결과**: 신규 테스트 5개가 모두 통과하며, 전체 테스트 139개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 더미 `Order` 생성, `SampleController`/저장소에 실제로 등록·저장하는
  wrapper 함수, 콘솔 View 메뉴 연동, `SPEC.md` 갱신은 이번 사이클에 포함하지 않고 다음 사이클
  이후로 이관했다.
