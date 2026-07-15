[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 2 — 시료 영속화 (GREEN 완료)

**이전 사이클**: [Cycle 1 — 시료 등록](cycle-01-sample-registration.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1에서 `Sample` 데이터 클래스와 인메모리 `SampleRegistry`(등록, 중복/공백 이름 검증)를
구현했다. 하지만 애플리케이션을 재시작하면 등록한 시료가 사라진다 — 이번 사이클은 `SPEC.md`
§2/§3에 정의된 `storage/sample_repository.py`로 시료 목록을 `samples.json`에 영속화한다.
`DataPersistence_PoC`의 원자적 쓰기(임시 파일 → `os.replace`)와 동시성 충돌 감지
(`ConflictError`) 패턴을 그대로 이식한다.

## 목표

`Sample` 목록을 JSON 파일로 저장하고 다시 불러올 수 있도록 하며, 저장 중 실패해도 기존
파일이 손상되지 않고, 로드 이후 파일이 외부에서 변경되면 저장 시 충돌을 감지한다.

## 이번 사이클에서 다룰 범위

- `storage/sample_repository.py`: `SampleRepository`
  - `save(samples: list[Sample])`: `samples.json`에 원자적 쓰기(임시 파일 → `os.replace`).
  - `load() -> list[Sample]`: `samples.json`을 읽어 `Sample` 목록으로 변환. 파일이 없으면
    빈 목록을 반환.
  - 동시성 충돌 감지: `load()` 시점의 파일 상태(해시/mtime)를 기억해 두고, `save()` 직전
    파일이 외부에서 변경된 것이 감지되면 `ConflictError`를 발생시킨다 (SPEC §5).
- 저장 포맷은 `SPEC.md` §3의 JSON 스키마를 그대로 따른다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `model/sample_registry.py`와 `SampleRepository`를 연결하는 로직(예: 등록 시 자동 저장) —
  Controller 연동 사이클에서 다룬다.
- 콘솔 View/Controller 연동 — 별도 사이클.
- `orders.json` 영속화(`OrderRepository`) — 별도 사이클.

## Mock 사용 범위 (SPEC.md §6 기준)

- 정상 저장/로드 경로는 `tmp_path` 픽스처로 실제 파일 I/O를 사용해 검증한다 (mock 사용 안 함).
- 원자적 쓰기 중 실패(예: `os.replace`가 예외를 던지는 상황)처럼 재현하기 어려운 실패 경로는
  `pytest-mock`의 `mocker`로 파일시스템 호출을 모의하여 검증한다 — 이는 SPEC.md §6이 정의한
  "외부 경계(파일시스템)"에 해당하므로 mock 사용이 적절하다.

## 작성할 실패 테스트 (예시)

```python
def test_저장한_시료_목록을_그대로_불러온다(tmp_path):
    repo = SampleRepository(tmp_path / "samples.json")
    repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    loaded = repo.load()

    assert len(loaded) == 1
    assert loaded[0].sample_id == "S-001"


def test_파일이_없으면_빈_목록을_반환한다(tmp_path):
    repo = SampleRepository(tmp_path / "samples.json")
    assert repo.load() == []


def test_쓰기_도중_실패해도_기존_파일이_손상되지_않는다(tmp_path, mocker):
    path = tmp_path / "samples.json"
    repo = SampleRepository(path)
    repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    mocker.patch("storage.sample_repository.os.replace", side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        repo.save([Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220)])

    # 실패 이전 저장 내용이 그대로 남아 있어야 한다
    assert repo.load()[0].sample_id == "S-001"


def test_로드_이후_외부에서_파일이_변경되면_저장시_충돌을_감지한다(tmp_path):
    path = tmp_path / "samples.json"
    repo = SampleRepository(path)
    repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    loaded_repo = SampleRepository(path)
    loaded_repo.load()

    # 다른 프로세스가 파일을 직접 수정한 상황을 재현
    other_repo = SampleRepository(path)
    other_repo.save([Sample("S-999", "외부에서 추가된 시료", 0.1, 0.5, 10)])

    with pytest.raises(ConflictError):
        loaded_repo.save([Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220)])
```

## 진행 결과

- **RED** (`8d2c9bc` 시료 영속화 실패 테스트 작성): 위 4개 테스트를 `tests/test_sample_repository.py`에
  작성해 실패를 확인했다.
- **구현 착수 중 verify-agent가 사전 검토로 버그 시나리오를 지적**: 구현 초안에서 `load()`가
  파일이 없을 때도 `_last_loaded_hash = None`으로 기록해, "load()를 아예 호출한 적 없는 초기
  상태"와 구분되지 않는 문제가 있었다. 이 때문에 "파일이 없는 상태로 load() → 이후 다른
  인스턴스가 파일을 새로 생성 → 원래 인스턴스가 save()" 시나리오에서 충돌 감지가 되지 않고
  조용히 덮어쓰는 버그가 있었다.
- **추가 RED** (`202cef4` 동시성 충돌 감지 엣지 케이스 실패 테스트 추가): 위 버그를 재현하는
  실패 테스트 `test_로드시_파일이_없었는데_이후_외부에서_생성되면_저장시_충돌을_감지한다`를
  먼저 추가해 실패를 확인했다.
- **GREEN** (`1d1f2a0` 시료 영속화 최소 구현): `storage/sample_repository.py`에
  `SampleRepository`, `ConflictError`를 구현해 5개 테스트를 모두 통과시켰다.
  `DataPersistence_PoC`의 원자적 쓰기(임시 파일 → `os.replace`)와 sha256 해시 기반 충돌 감지
  패턴을 이식하면서, "load() 호출 여부"를 별도로 추적하는 `_loaded` 플래그를 두어 "로드된
  파일의 해시값"과 구분함으로써 위 엣지 케이스 버그도 함께 해결했다. 버그가 있던 중간
  구현은 별도로 커밋되지 않았고, 이 커밋이 유일한 구현 커밋이다.
- **최종 결과**: `tests/test_sample_repository.py`의 5개 테스트가 모두 통과하며, Cycle 1을
  포함한 전체 테스트 8개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 `SampleRegistry` 연동, 콘솔 View/Controller 연동,
  `orders.json`/`OrderRepository`는 이번 사이클에 포함하지 않았다.

---

**다음 사이클**: 아직 계획되지 않음
