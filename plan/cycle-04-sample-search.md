[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 4 — 시료 검색

**이전 사이클**: [Cycle 3 — 시료 컨트롤러 연동](cycle-03-sample-controller.md)
**다음 사이클**: 아직 계획되지 않음

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1에서 `Sample` 데이터 클래스와 인메모리 `SampleRegistry`(등록, 중복 ID/공백 이름 검증)를
구현했다. Cycle 2에서 `storage/sample_repository.py`의 `SampleRepository`로 시료 목록을
`samples.json`에 원자적으로 저장/로드하고 동시성 충돌을 감지하도록 구현했다. Cycle 3에서는
`controller/sample_controller.py`의 `SampleController`가 `SampleRegistry`와
`SampleRepository`를 연결해, 시작 시 저장소에서 시료를 불러와 레지스트리를 채우고
(손상된 파일의 중복 `sample_id`는 건너뛰고 `duplicate_sample_ids()`로 노출), 새 시료 등록이
성공하면 저장소에도 반영되도록 했다.

이제 시료 등록/조회/영속화는 모두 준비되었지만, `PRD.md` §6.1의 세 기능(등록/조회/검색) 중
"검색"만 아직 구현되지 않았다. Cycle 3의 "이번 사이클에서 다루지 않는 것"에도 "이름 등 속성으로
시료를 검색하는 기능 — 별도 사이클"로 명시되어 있으며, 이번이 그 사이클이다.

## 목표

`PRD.md` §6.1(시료 관리)의 "시료 검색: 이름 등 속성으로 특정 시료를 검색"을 구현한다.
`SPEC.md` §2는 `controller/sample_controller.py`가 "시료 등록/조회/검색"을 담당한다고 명시하고
있으므로, 이번 사이클에서 검색 기능의 최소 동작을 정의한다.

### 검색 방식에 대한 판단 (확인 필요했던 모호한 지점)

`PRD.md` §6.1은 "이름 등 속성으로 검색"이라고만 되어 있고, `SPEC.md`에는 검색 알고리즘(완전
일치/부분 일치/대소문자 구분 여부)이 정의되어 있지 않다. 이번 사이클에서는 다음과 같이
해석하여 진행한다 (사람 파트너 검토 시 이견이 있으면 조정):

- **속성 범위** (사람 파트너 검토 후 확정): `name`(시료명)과 `sample_id`(시료 ID) 모두 검색
  대상으로 한다. 검색어가 둘 중 하나에라도 부분 일치하면 결과에 포함한다.
- **일치 방식**: 부분 일치(포함 여부, substring match)로 해석한다. 콘솔에서 사용자가 시료명
  전체를 정확히 기억하지 못하는 경우가 많다는 일반적인 검색 UX 관례를 따른 것이며, PRD/SPEC에
  명시적 근거는 없다 — **확인 필요**.
- **대소문자 구분**: 구분하지 않는다(case-insensitive). 시료명이 대부분 한글이라 실효성은
  제한적이지만, 영문 코드명이 섞일 가능성을 고려한 관례적 선택이다 — **확인 필요**.
- **결과 없음**: 예외를 던지지 않고 빈 목록을 반환한다 (SPEC §5의 에러 규칙 목록에 "검색 결과
  없음"에 대한 언급이 없으므로, 오류가 아닌 정상적인 빈 결과로 취급한다).

## 검색 로직의 위치에 대한 판단

`SPEC.md` §2는 "Model은 입출력을 모르고... 순수 로직"만 담당하고, Controller가 Model과 View를
중개한다고 명시한다. 시료 검색은 이미 메모리에 있는 `Sample` 목록을 이름/ID로 필터링하는 순수
계산 로직이며, `SampleRegistry.list_all()`과 본질적으로 같은 층위(레지스트리가 보유한
컬렉션에 대한 조회 연산)에 속한다. 따라서:

- 검색 필터링 로직 자체는 `model/sample_registry.py`의 `SampleRegistry.search(keyword)`에
  둔다 (Cycle 1에서 이미 `register`/`list_all`이 여기 있으므로 일관성 유지). 검색 대상 속성이
  `name` 하나에서 `name`/`sample_id` 둘로 넓어지면서, "이름으로 찾는다"는 의미로 좁게 읽히는
  `find_by_name`이라는 이름은 더 이상 정확하지 않아 `search`로 이름을 바꾼다.
- `controller/sample_controller.py`의 `SampleController.search_samples(keyword)`는 이
  메서드를 그대로 위임 호출하는 얇은 통로 역할만 한다 (Cycle 3의 `list_samples()`와 동일한
  패턴).

## 이번 사이클에서 다룰 범위

- `model/sample_registry.py`: `SampleRegistry.search(keyword: str) -> list[Sample]`
  - `name` 또는 `sample_id`에 `keyword`가 대소문자 구분 없이 부분 문자열로 포함된 `Sample`을
    반환한다 (둘 중 하나만 일치해도 포함).
  - 일치하는 시료가 없으면 빈 목록을 반환한다 (예외 없음).
  - `keyword`가 공백만 있는 문자열이면 빈 목록을 반환한다 (전체 목록을 실수로 반환하지 않도록
    방지).
- `controller/sample_controller.py`: `SampleController.search_samples(keyword: str) -> list[Sample]`
  - `SampleRegistry.search()`를 그대로 호출해 반환한다 (저장소 접근 없음 — 검색은 항상
    현재 레지스트리 상태 기준).

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `name`/`sample_id` 이외의 속성으로 검색하는 기능 — 필요성이 확인되면 별도 사이클로 분리.
- `view/console_view.py` 및 실제 메뉴 입출력(검색어 입력 프롬프트, 결과 화면 표시) — 별도
  사이클(Cycle 12, 콘솔 View/Controller 통합)에서 다룬다.
- 검색 결과 정렬 순서, 페이지네이션 등 부가 기능 — SPEC.md에 근거가 없으므로 다루지 않는다.
- `Order` 관련 기능 — 범위 밖.

## Mock 사용 범위 (SPEC.md §6 기준)

- `model/sample_registry.py`는 "순수 로직" 계층이므로 실제 `Sample`/`SampleRegistry` 객체로
  직접 테스트하고 mock을 사용하지 않는다.
- `controller/sample_controller.py`는 "내부 협력" 계층이므로 실제 `SampleRegistry`,
  `SampleRepository`(`tmp_path` 기반 실제 파일 I/O)를 조합해 테스트하고 mock을 사용하지 않는다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_sample_registry.py 에 추가

def test_이름에_검색어가_포함된_시료만_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    registry.register(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = registry.search("웨이퍼")

    assert [s.sample_id for s in result] == ["S-001"]


def test_시료_ID에_검색어가_포함된_시료도_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    registry.register(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = registry.search("S-002")

    assert [s.sample_id for s in result] == ["S-002"]


def test_검색어가_대소문자를_구분하지_않는다():
    registry = SampleRegistry()
    registry.register(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = registry.search("gan")

    assert [s.sample_id for s in result] == ["S-002"]


def test_일치하는_시료가_없으면_빈_목록을_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    assert registry.search("존재하지않음") == []


def test_공백만_있는_검색어는_빈_목록을_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    assert registry.search("   ") == []
```

```python
# tests/test_sample_controller.py 에 추가

def test_컨트롤러의_시료_검색은_레지스트리에_위임한다(tmp_path):
    path = tmp_path / "samples.json"
    controller = SampleController(SampleRegistry(), SampleRepository(path))
    controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller.register_sample(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = controller.search_samples("웨이퍼")

    assert [s.sample_id for s in result] == ["S-001"]
```

## 진행 결과

- **RED/GREEN** (`bdacad2`, `44dad73`): 위 계획 중 `name` 부분 일치·대소문자 무시 검색을
  `SampleRegistry.find_by_name(keyword)` / `SampleController.search_samples(keyword)`로
  먼저 구현해 통과시켰다.
- **범위 확장 요청**: 검토 과정에서 검색 대상에 `sample_id`도 포함해 달라는 요청을 받아, 이
  문서의 "속성 범위"와 "이번 사이클에서 다룰 범위"를 갱신했다. `find_by_name`을 `search`로
  이름을 바꾸고, `name`/`sample_id` 중 하나라도 일치하면 포함하도록 범위를 넓힌다. 뒤이어 이
  변경을 위한 RED→GREEN을 추가로 진행한다.

---

**다음 사이클**: 아직 계획되지 않음
