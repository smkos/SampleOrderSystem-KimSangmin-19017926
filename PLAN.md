# PLAN.md — 작업 계획

`SPEC.md`를 기준으로 진행할 TDD 사이클(RED → GREEN → REVIEW)의 목표를 사이클 단위로 기록한다.
각 단계는 사람 파트너의 검토를 받은 뒤에만 다음 단계로 넘어간다.

## Cycle 1 — 시료 등록 (RED)

### 목표

`SPEC.md` §1.1의 `Sample` 모델과, 새로운 시료를 등록하는 기능의 최소 동작을 정의한다.
이 사이클은 이후 모든 기능(주문 생성, 승인/거절, 생산, 모니터링)이 의존하는 가장 기본
단위이므로 가장 먼저 다룬다.

### 이번 사이클에서 다룰 범위

- `model/sample.py`: `Sample` 데이터 클래스 — `sample_id`, `name`, `avg_production_time_min`,
  `yield_rate`, `stock_qty` 필드만 보관 (SPEC §1.1).
- 시료 등록 시 검증 규칙 (SPEC §5 관련):
  - `sample_id` 중복 등록 거부.
  - `name`이 공백만 있는 값이면 거부.
- 등록 성공 시 시료 목록에 반영되는지 확인 (영속화/파일 저장은 이후 사이클에서 다룸 — 이번
  사이클은 인메모리 등록 로직까지만).

### 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- JSON 파일 영속화(`storage/sample_repository.py`) — 별도 사이클.
- 시료 조회/검색 메뉴 — 별도 사이클.
- 콘솔 View/Controller 연동 — 별도 사이클.

### 작성할 실패 테스트 (예시)

```python
def test_등록된_시료가_목록에_추가된다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    assert len(registry.list_all()) == 1

def test_중복된_sample_id는_등록을_거부한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    with pytest.raises(ValueError):
        registry.register(Sample("S-001", "다른 시료", 0.3, 0.9, 100))

def test_공백만_있는_이름은_등록을_거부한다():
    registry = SampleRegistry()
    with pytest.raises(ValueError):
        registry.register(Sample("S-002", "   ", 0.3, 0.9, 100))
```

### 검토 요청

위 목표와 테스트 범위로 RED 단계를 진행해도 될지 검토 부탁드립니다. 승인해 주시면 실패하는
테스트를 작성하고 실패하는 것을 확인한 뒤 다시 공유하겠습니다.
