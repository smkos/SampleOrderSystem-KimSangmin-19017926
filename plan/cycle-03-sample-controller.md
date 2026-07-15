[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 3 — 시료 컨트롤러 연동 (GREEN 완료)

**이전 사이클**: [Cycle 2 — 시료 영속화](cycle-02-sample-persistence.md)
**다음 사이클**: [Cycle 4 — 시료 검색](cycle-04-sample-search.md)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1에서 `Sample` 데이터 클래스와 인메모리 `SampleRegistry`(등록, 중복/공백 이름 검증)를
구현했다. Cycle 2에서 `storage/sample_repository.py`의 `SampleRepository`로 시료 목록을
`samples.json`에 원자적으로 저장/로드하고 동시성 충돌을 감지하는 로직을 구현했다. 하지만 두
모듈은 아직 서로 연결되어 있지 않다 — `SampleRegistry`에 등록해도 파일에 저장되지 않고,
애플리케이션을 다시 시작해도 `samples.json`에 저장된 내용이 `SampleRegistry`에 자동으로
채워지지 않는다. 이번 사이클은 `SPEC.md` §2에 정의된 `controller/sample_controller.py`의
`SampleController`로 이 둘을 연결한다.

## 목표

`PRD.md` §6.1(시료 관리)의 "시료 등록" 기능이 실제로 영속화되도록, `SampleController`가
시작 시 저장소에서 시료 목록을 불러와 레지스트리를 채우고, 새 시료 등록이 성공하면 그 결과를
다시 저장소에 저장하는 최소 동작을 정의한다 (`SPEC.md` §2 모듈 구조 근거).

## 이번 사이클에서 다룰 범위

- `controller/sample_controller.py`: `SampleController`
  - 생성 시 `SampleRegistry`와 `SampleRepository`를 주입받는다 (의존성 주입).
  - 생성 시점에 저장소의 `load()` 결과로 레지스트리를 채운다 (재시작 시 기존 시료 복원).
  - `register_sample(sample: Sample)`: `SampleRegistry.register()`를 호출해 등록에 성공하면,
    레지스트리의 전체 목록을 저장소에 `save()` 한다.
  - `SampleRegistry.register()`가 검증 실패로 `ValueError`를 던지면 저장소에는 아무것도
    저장하지 않는다 (등록 실패 시 파일 변경 없음).
  - `list_samples()`: 레지스트리의 현재 목록을 그대로 반환한다 (조회 메뉴가 쓸 최소 통로).
- (원래 계획에는 없었으나, verify-agent 검증 과정에서 편입) 저장소 파일에 동일한
  `sample_id`가 중복 저장되어 있는 손상 상태를 생성 시 예외 없이 처리하고,
  `duplicate_sample_ids()`로 건너뛴 중복 ID 목록을 외부에서 조회할 수 있게 한다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- 이름 등 속성으로 시료를 검색하는 기능(PRD §6.1 "시료 검색") — 별도 사이클.
- `view/console_view.py`, 실제 메뉴 입출력/사용자 입력 처리 — 별도 사이클.
- `Order` 관련 기능(주문 접수/승인/거절/생산/출고, `order_controller.py` 등) — 범위 밖.
- `SampleRepository.save()`가 `ConflictError`를 던지는 상황에서 컨트롤러가 이를 사용자에게
  어떻게 안내할지(재시도 유도 등)는 View 연동 사이클에서 다룬다. 이번 사이클은 예외가 그대로
  전파되는지만 확인한다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `controller/`는 "내부 협력" 계층이므로 `SampleRegistry`, `SampleRepository`를 실제 객체로
  조합해 테스트한다 (mock 사용 안 함).
- `SampleRepository`는 파일시스템이 외부 경계이지만, Cycle 2에서 이미 `tmp_path` 기반 실제
  파일 I/O로 정상 경로가 검증되었으므로, 이번 컨트롤러 테스트에서도 동일하게 `tmp_path`로
  생성한 실제 `SampleRepository` 인스턴스를 사용한다 (파일시스템 mock 불필요).

## 작성할 실패 테스트 (예시)

```python
def test_생성시_저장소의_기존_시료를_레지스트리에_불러온다(tmp_path):
    path = tmp_path / "samples.json"
    seed_repo = SampleRepository(path)
    seed_repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    controller = SampleController(SampleRegistry(), SampleRepository(path))

    assert [s.sample_id for s in controller.list_samples()] == ["S-001"]


def test_시료_등록에_성공하면_저장소에도_반영된다(tmp_path):
    path = tmp_path / "samples.json"
    controller = SampleController(SampleRegistry(), SampleRepository(path))

    controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    reloaded = SampleRepository(path).load()
    assert [s.sample_id for s in reloaded] == ["S-001"]


def test_등록_검증에_실패하면_저장소를_변경하지_않는다(tmp_path):
    path = tmp_path / "samples.json"
    controller = SampleController(SampleRegistry(), SampleRepository(path))
    controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    with pytest.raises(ValueError):
        controller.register_sample(Sample("S-001", "중복된 ID", 0.3, 0.9, 100))

    reloaded = SampleRepository(path).load()
    assert len(reloaded) == 1  # 실패 이전 상태 그대로 유지
```

## 진행 결과

- **RED** (`cbefa57` 시료 컨트롤러 연동 실패 테스트 작성): 위 3개 테스트를
  `tests/test_sample_controller.py`에 작성해 실패를 확인했다.
- **GREEN** (`39b038d` 시료 컨트롤러 연동 최소 구현): `controller/sample_controller.py`에
  `SampleController`를 구현했다. 생성자가 `SampleRegistry`와 `SampleRepository`를 주입받아
  `SampleRepository.load()` 결과로 레지스트리를 채우고, `register_sample()`이 성공하면 전체
  목록을 저장소에 `save()` 한다. 원래 계획된 3개 테스트가 모두 통과했다.
- **verify-agent의 독립 검증에서 엣지 케이스 발견**: 저장소 파일(`samples.json`)이 손상되어
  동일한 `sample_id`가 중복 저장되어 있으면, 생성자가 `SampleRegistry.register()`를 반복
  호출하다가 `ValueError`가 그대로 전파되어 `SampleController` 생성 자체가 실패하는 문제가
  있었다.
- **사람 파트너와 협의한 결론**: 에러 없이 정상 동작하되, 먼저 로드된 항목만 유지하고 건너뛴
  중복 ID를 컨트롤러 바깥에서 조회할 수 있게 한다. 사용자에게 안내하고 삭제를 유도하는 콘솔
  View는 아직 없으므로(별도 사이클), 이번 사이클에서는 중복 발생 사실을 노출하는 통로
  (`duplicate_sample_ids()`)만 추가한다.
- **추가 RED** (`bb65f77` 저장소 중복 시료 ID 처리 실패 테스트 추가): 손상된 `samples.json`
  (중복 ID 포함)을 직접 만들어 검증하는 실패 테스트 2개(정상 동작 확인, 중복 없을 때 빈 목록
  확인)를 추가해 실패를 확인했다.
- **추가 GREEN** (`dbeafcd` 저장소 중복 시료 ID를 예외 없이 처리): `__init__`에서
  `registry.register()` 호출 시 `ValueError`를 잡아 무시하고 해당 `sample_id`를 내부 리스트에
  기록하도록 최소 수정했다. `register_sample()`(사용자가 새 시료를 등록하는 정상 흐름)의 기존
  중복 검증 동작(예외 전파)은 그대로 유지된다.
- **최종 결과**: `tests/test_sample_controller.py`의 5개 테스트가 모두 통과하며, Cycle 1, 2를
  포함한 전체 테스트 13개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 시료 검색, 콘솔 View/Controller 연동, `Order` 관련 기능은 이번
  사이클에 포함하지 않았다. `model/sample_registry.py`, `storage/sample_repository.py`는
  수정되지 않았다.

---

**다음 사이클**: [Cycle 4 — 시료 검색](cycle-04-sample-search.md)
