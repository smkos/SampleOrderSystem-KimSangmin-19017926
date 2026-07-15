# SPEC.md — 기술 설계 명세

`PRD.md`의 기능 명세를 실제 구현 가능한 수준으로 구체화한 문서. 각 기능의 TDD 사이클
(`PLAN.md`)을 시작하기 전, 데이터 모델·모듈 구조·저장 포맷·계산/에러 규칙을 여기서 먼저
확정한다.

## 1. 데이터 모델

### 1.1 Sample (시료)

| 필드 | 타입 | 설명 |
|------|------|------|
| `sample_id` | `str` | 시료 고유 ID (예: `S-001`). 등록 시 사용자가 지정, 중복 불가 |
| `name` | `str` | 시료명 (예: `실리콘 웨이퍼-8인치`). 공백만 있는 값 거부 |
| `avg_production_time_min` | `float` | 개당 평균 생산시간(분) |
| `yield_rate` | `float` | 수율. `0 < yield_rate <= 1` |
| `stock_qty` | `int` | 현재 재고 수량. `>= 0` |

### 1.2 Order (주문)

| 필드 | 타입 | 설명 |
|------|------|------|
| `order_id` | `str` | 주문번호. 형식 `ORD-YYYYMMDD-NNNN` (일자별 4자리 일련번호) |
| `sample_id` | `str` | 주문 대상 시료 ID. 등록된 시료만 참조 가능 |
| `customer_name` | `str` | 고객명. 공백만 있는 값 거부 |
| `quantity` | `int` | 주문 수량. `> 0` |
| `status` | `OrderStatus` | `RESERVED` \| `REJECTED` \| `PRODUCING` \| `CONFIRMED` \| `RELEASE` |
| `created_at` | `str` (ISO 8601) | 주문 접수 시각. 생산 큐 FIFO 정렬 기준 |

### 1.3 상태 전이 규칙

```
RESERVED --거절--> REJECTED
RESERVED --승인, 재고충분--> CONFIRMED
RESERVED --승인, 재고부족--> PRODUCING
PRODUCING --생산완료--> CONFIRMED
CONFIRMED --출고--> RELEASE
```

허용되지 않은 전이(예: `RELEASE` 상태 주문의 재승인, `REJECTED` 주문의 출고)는 예외를
발생시키고 상태를 변경하지 않는다.

## 2. 모듈 구조 (MVC_PoC 확장)

```
model/
  sample.py             # Sample — 데이터만 보관
  sample_registry.py    # SampleRegistry — 인메모리 등록/중복·공백 이름 검증/검색
  order.py               # Order, OrderStatus — 데이터와 상태만 보관
  order_registry.py       # OrderRegistry — 인메모리 생성/채번(ORD-YYYYMMDD-NNNN)/검증
  production_queue.py     # 생산 큐 계산 로직 (순수 함수: 부족분/실생산량/총생산시간)
view/
  console_view.py         # 메뉴별 입출력
controller/
  sample_controller.py    # 시료 등록/조회/검색, 저장소 연동 및 손상 데이터(중복 ID) 처리
  order_controller.py     # 주문 생성, 승인/거절, 출고 처리
  monitoring_controller.py # 상태별 주문 수, 재고 현황 집계
  production_controller.py # 생산 라인 현황, 대기 큐 조회, 생산 완료 처리(PRODUCING -> CONFIRMED)
storage/
  sample_repository.py    # samples.json 로드/저장 (원자적 쓰기 + 충돌 감지)
  order_repository.py     # orders.json 로드/저장 (원자적 쓰기 + 충돌 감지)
```

- Model은 입출력을 모르고, View는 Controller가 넘긴 값만 표시하며, Controller가 Model과
  View를 중개한다 (`MVC_PoC` 원칙 그대로 적용).
- `storage/*_repository.py`는 `DataPersistence_PoC`의 원자적 쓰기(임시 파일 → `os.replace`)와
  동시성 충돌 감지(`ConflictError`) 패턴을 그대로 이식한다. 다만 `ConflictError`는 저장소별로
  각각 독립적으로 정의하며(예: `sample_repository.ConflictError`와 `order_repository.ConflictError`는
  서로 다른 예외 타입), 두 저장소가 공유하는 타입이 아니다. 필요해지면 `storage/errors.py` 같은
  공유 모듈로의 리팩터링을 재검토할 수 있다.

## 3. 저장 포맷

`samples.json`, `orders.json` 두 개의 JSON 파일로 분리 저장한다 (배열 형태, 각 원소는 §1의
필드를 그대로 담은 객체).

```json
// samples.json
[
  {"sample_id": "S-001", "name": "실리콘 웨이퍼-8인치", "avg_production_time_min": 0.5, "yield_rate": 0.92, "stock_qty": 480}
]
```

```json
// orders.json
[
  {"order_id": "ORD-20260416-0043", "sample_id": "S-003", "customer_name": "삼성전자 파운드리", "quantity": 200, "status": "PRODUCING", "created_at": "2026-04-16T09:32:15"}
]
```

## 4. 계산 규칙

- **부족분** = `max(0, quantity - stock_qty)`
- **재고 충분 여부** = `quantity <= stock_qty`
- **실 생산량** = `ceil(부족분 / yield_rate)`
- **총 생산 시간(분)** = `avg_production_time_min * 실 생산량`
- **재고 상태 라벨** (모니터링): `stock_qty == 0` → 고갈, `stock_qty < 미승인 주문 총수량` → 부족, 그 외 → 여유
- **생산 큐 정렬**: `PRODUCING` 상태 주문을 `created_at` 오름차순(FIFO)으로 정렬

## 5. 에러/검증 규칙

- 존재하지 않는 `sample_id`로 주문 생성 시도 → 거부.
- 이미 등록된 `sample_id` 재등록 시도 → 거부.
- 수량이 0 이하인 주문 생성 시도 → 거부.
- `RESERVED`가 아닌 주문에 대한 승인/거절 시도 → 거부.
- `CONFIRMED`가 아닌 주문에 대한 출고 시도 → 거부.
- 저장 파일 동시 수정 충돌 시 `ConflictError` 발생, 데이터 유실 없이 재시도 유도 (`DataPersistence_PoC` 패턴).
- 저장 파일(`samples.json`)이 손상되어 동일한 `sample_id`가 중복 저장되어 있으면, `SampleController`는
  예외를 던지지 않고 먼저 로드된 항목만 유지하며 나머지 중복 항목은 건너뛴다. 건너뛴 `sample_id`
  목록은 `duplicate_sample_ids()`로 조회할 수 있다 (콘솔 View 연동 시 사용자 안내에 활용 예정).

## 6. 테스트/Mock 전략

`test-driven-development` 스킬의 원칙("mock은 외부 경계에서만") 을 이 프로젝트의 계층 구조에
적용하면 다음과 같이 나뉜다.

| 계층 | 외부 경계 여부 | Mock 사용 |
|------|----------------|-----------|
| `model/` (Sample, Order, production_queue 계산) | 아니오 — 순수 로직 | 실제 객체로 직접 테스트, mock 사용 안 함 |
| `controller/` (Model↔View 중개) | 아니오 — 내부 협력 | 실제 Model/View를 조합해 테스트. View 대신 테스트용 stub view만 필요 시 사용 |
| `storage/*_repository.py` (파일 I/O) | **예** — 파일시스템 | `pytest-mock`의 `mocker`로 파일시스템 호출(예: 쓰기 실패, 동시성 충돌 상황)을 격리 테스트. 정상 경로는 임시 디렉터리(`tmp_path`)를 이용한 실제 파일 I/O로 검증 |
| `view/console_view.py` (콘솔 입출력) | **예** — 표준 입출력 | `pytest-mock`으로 `input`/`print` 등 콘솔 I/O를 mock |
| `Order.created_at` 생성, 생산 큐 FIFO 정렬 기준 시각 | **예** — 시스템 시각 | `pytest-mock`으로 시각 생성 함수를 mock해 결정적으로 테스트 |

내부 모듈 간 호출(Model↔Controller 등)을 mock하기 시작하면 결합도가 과도하다는 신호이므로,
그 경우 mock을 늘리기보다 설계(의존성 주입 등)를 먼저 점검한다.
