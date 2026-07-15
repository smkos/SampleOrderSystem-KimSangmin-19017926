# spec.md — 기술 설계 명세

`PRD.md`의 기능 명세를 실제 구현 가능한 수준으로 구체화한 문서. 각 기능의 TDD 사이클
(`plan.md`)을 시작하기 전, 데이터 모델·모듈 구조·저장 포맷·계산/에러 규칙을 여기서 먼저
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
  order.py               # Order, OrderStatus — 데이터와 상태만 보관
  production_queue.py     # 생산 큐 계산 로직 (순수 함수: 부족분/실생산량/총생산시간)
view/
  console_view.py         # 메뉴별 입출력
controller/
  sample_controller.py    # 시료 등록/조회/검색
  order_controller.py     # 주문 생성, 승인/거절, 출고 처리
  monitoring_controller.py # 상태별 주문 수, 재고 현황 집계
  production_controller.py # 생산 라인 현황, 대기 큐 조회
storage/
  sample_repository.py    # samples.json 로드/저장 (원자적 쓰기 + 충돌 감지)
  order_repository.py     # orders.json 로드/저장 (원자적 쓰기 + 충돌 감지)
```

- Model은 입출력을 모르고, View는 Controller가 넘긴 값만 표시하며, Controller가 Model과
  View를 중개한다 (`MVC_PoC` 원칙 그대로 적용).
- `storage/*_repository.py`는 `DataPersistence_PoC`의 원자적 쓰기(임시 파일 → `os.replace`)와
  동시성 충돌 감지(`ConflictError`) 패턴을 그대로 이식한다.

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
