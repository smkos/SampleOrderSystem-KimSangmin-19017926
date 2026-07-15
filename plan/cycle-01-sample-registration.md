[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 1 — 시료 등록 (GREEN 완료)

**이전 사이클**: 없음 (첫 사이클)
**다음 사이클**: [Cycle 2 — 시료 영속화](cycle-02-sample-persistence.md)

## 완료 요약

`model/sample.py`(`Sample`)와 `model/sample_registry.py`(`SampleRegistry`)를 추가해 인메모리
등록·중복 ID 거부·공백 이름 거부를 구현했다. `tests/test_sample_registry.py`의 3개 테스트가
모두 통과한다. JSON 영속화, 조회/검색 메뉴, View/Controller 연동은 다음 사이클들로 넘긴다.

## 지금까지의 진행 상황 (컨텍스트)

이 사이클 이전에 구현된 것은 없다. `SPEC.md`를 기준으로 진행하는 최초 사이클이며, 이후 모든
기능(주문 생성, 승인/거절, 생산, 출고, 모니터링)이 여기서 정의하는 `Sample` 모델과 등록
로직에 의존한다.

## 목표

`SPEC.md` §1.1의 `Sample` 모델과, 새로운 시료를 등록하는 기능의 최소 동작을 정의한다.
이 사이클은 이후 모든 기능이 의존하는 가장 기본 단위이므로 가장 먼저 다룬다.

## 이번 사이클에서 다룰 범위

- `model/sample.py`: `Sample` 데이터 클래스 — `sample_id`, `name`, `avg_production_time_min`,
  `yield_rate`, `stock_qty` 필드만 보관 (SPEC §1.1).
- 시료 등록 시 검증 규칙 (SPEC §5 관련):
  - `sample_id` 중복 등록 거부.
  - `name`이 공백만 있는 값이면 거부.
- 등록 성공 시 시료 목록에 반영되는지 확인 (영속화/파일 저장은 이후 사이클에서 다룸 — 이번
  사이클은 인메모리 등록 로직까지만).

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- JSON 파일 영속화(`storage/sample_repository.py`) — 별도 사이클.
- 시료 조회/검색 메뉴 — 별도 사이클.
- 콘솔 View/Controller 연동 — 별도 사이클.

## 작성할 실패 테스트 (예시)

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

## 검토 요청 (완료됨)

RED/GREEN 모두 검토·승인되어 커밋되었다.

---

**다음 사이클**: [Cycle 2 — 시료 영속화](cycle-02-sample-persistence.md)
