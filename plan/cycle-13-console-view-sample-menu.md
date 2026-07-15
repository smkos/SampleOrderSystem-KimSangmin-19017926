[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 13 — 콘솔 View 골격 + 메인 메뉴 요약 정보 + 시료 관리 메뉴

**이전 사이클**: [Cycle 12 — 주문/생산 컨트롤러 영속화 연동](cycle-12-order-controller-persistence.md)
**다음 사이클**: 아직 계획되지 않음 (예정: Cycle 14 — 시료 주문 메뉴 + 주문 승인/거절 메뉴)

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~11에서 Model/Controller 계층을 모두 구현했다 — 시료 등록/조회/검색
(`SampleController`), 주문 접수·승인/거절·출고 처리(`OrderController`), 생산 큐 계산과 생산
완료 처리(`ProductionController`), 모니터링 집계(`MonitoringController`)까지 순수 로직과
컨트롤러 단위 테스트로 검증됐다. Cycle 12(현재 GREEN 진행 중)에서는 `OrderController`/
`ProductionController`를 각각의 저장소(`OrderRepository`/`SampleRepository`)와 연결해,
콘솔이 없어도 컨트롤러 메서드 호출만으로 상태 변경이 파일에 영속화되는 것까지 확인했다.

이제 `SPEC.md` §2에 정의된 `view/console_view.py`만 아직 한 줄도 없는 마지막 미착수
영역이다. `plan/cycle-12-order-controller-persistence.md`의 로드맵(9~40행)은 이 영역을
Cycle 13~16으로 나누어 다루기로 이미 정해 두었다. 이번 사이클은 그중 첫 단계 — 콘솔 View의
골격과 입출력 mock 전략을 확정하고, 메인 메뉴 진입 시 요약 정보 표시 및 시료 관리 메뉴(등록/
조회/검색)의 화면 동작을 정의한다.

## 목표

`PRD.md` §5(메인 메뉴)·§6.1(시료 관리)과 `SPEC.md` §2(`view/console_view.py`)·§6(콘솔 I/O는
`input`/`print`를 mock해 테스트)에 따라, `ConsoleView`가 다음 두 화면의 입출력을 담당하는
최소 동작을 정의한다.

1. 메인 메뉴 진입 시 요약 정보(등록 시료 수, 총 재고, 전체 주문 수, 생산라인 대기 건수)와
   메뉴 목록을 출력하고, 사용자의 메뉴 선택을 입력받는다.
2. 시료 관리 하위 메뉴 — 신규 등록 입력, 목록 조회 출력, 이름 검색 입력/결과 출력.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. `input`/`print` mock 전략 — `mocker.patch("builtins.input", side_effect=[...])` + `capsys`

기존 PoC(`../MVC_PoC/view/console_view.py`)에는 콘솔 View 자체는 있지만 이를 검증하는
테스트 파일이 없어(생성만 되어 있고 `tests/`가 비어 있음) 재사용할 기존 테스트 패턴이 없다.
이번에 새로 다음 방식을 채택한다.

- **`input` mock**: `mocker.patch("builtins.input", side_effect=["S-001", "실리콘 웨이퍼-8인치", ...])`
  로 사용자가 순서대로 입력할 값을 스크립트한다. 여러 차례 `input()`을 호출하는 메서드(예:
  시료 등록 입력)를 한 번에 검증할 수 있다.
- **출력 검증**: `pytest` 내장 `capsys` 픽스처로 `capsys.readouterr().out`을 읽어 예상 문자열이
  포함되는지 확인한다. `mocker.patch("builtins.print")`로 호출 인자를 직접 assert하는 방식도
  검토했으나, 출력 문구가 여러 줄에 걸쳐 나뉘는 경우 각 `print()` 호출을 낱낱이 assert해야 해서
  테스트가 화면 문구의 사소한 줄바꿈 변경에도 깨지기 쉽다. `capsys`는 최종적으로 화면에 찍히는
  텍스트 전체를 대상으로 "이 문자열이 포함되는가"만 확인하므로 더 견고하다. **확인 필요**:
  `SPEC.md` §6은 "`pytest-mock`으로 `input`/`print` 등 콘솔 I/O를 mock"이라고 적어 두어 `print`도
  `mocker`로 mock하는 것을 전제한 것처럼 읽힐 수 있다. `capsys`는 mock이 아니라 pytest 내장
  캡처 픽스처이므로 이 문구와 정확히 일치하지는 않지만, "표준 입출력이라는 외부 경계를 실제
  구현에 영향 주지 않고 격리해서 검증한다"는 목적은 동일하게 달성한다. 이견이 있으면
  `mocker.patch("builtins.print")` 방식으로 조정 가능하다.

### 2. `ConsoleView`의 책임 범위 — 순수 입출력만, Controller 호출 없음

`SPEC.md` §2가 "Model은 입출력을 모르고, View는 Controller가 넘긴 값만 표시하며, Controller가
Model과 View를 중개한다"고 명시하므로, `ConsoleView`는 다음 두 종류의 메서드만 갖는다.

- **표시(output) 메서드**: 이미 계산된 데이터(요약 dict, `Sample` 리스트 등)를 인자로 받아
  화면에 출력만 한다. Controller를 호출하지 않는다.
- **입력(input) 메서드**: 사용자로부터 값을 받아 dict 등 단순 자료구조로 반환한다. 반환값을
  어느 Controller 메서드에 어떻게 넘길지는 View가 알지 못한다.

즉 "메뉴 선택 → 해당 Controller 메서드 호출 → 결과를 View로 표시"라는 흐름 자체(오케스트레이션)는
`ConsoleView`의 책임이 아니다. 이 흐름은 `PLAN.md` 로드맵상 `main.py`(Cycle 16, "전체 조립,
메인 루프")의 책임으로 남겨둔다. **판단**: 이번 사이클은 `ConsoleView`의 각 메서드를 개별
호출해 입력/출력만 검증하며, 실제 Controller와 연결된 end-to-end 메뉴 흐름은 다루지 않는다.
이렇게 하면 이번 사이클의 테스트가 `test-driven-development` 스킬의 "mock은 외부 경계에서만"
원칙을 지키면서도(Controller를 mock할 필요가 전혀 없다), View 계층만 독립적으로 완결되게
검증할 수 있다.

### 3. 메인 메뉴 요약 정보의 "생산라인 대기 건수" — 이번 사이클은 표시 형식만 정의, 실제 집계는 보류

`PRD.md` §5는 요약 정보 항목으로 "등록 시료 수, 총 재고, 전체 주문 수, 생산라인 대기 건수 등"을
예시로 든다. `ProductionController`에는 아직 대기 큐 조회 기능이 없다(Cycle 15 예정,
`sort_production_queue`를 실제 데이터에 연결하는 시점). 위 설계 판단 2번(View는 Controller를
호출하지 않는다)에 따라 이 문제는 자연스럽게 해소된다 — `ConsoleView.show_main_menu()`는
이미 계산되어 넘어온 `summary: dict`를 표시만 하므로, 그 dict를 "누가 어떻게 채우는가"는 이번
사이클의 관심사가 아니다. **판단**: `summary` dict의 키 이름과 표시 형식만 이번 사이클에서
확정한다 — `{"sample_count": int, "total_stock_qty": int, "total_order_count": int,
"pending_production_count": int}`. 실제로 이 네 값을 각 Controller에서 계산해 채우는 로직은
`main.py`가 조립되는 Cycle 16(또는 필요하다면 그 이전 사이클)에서 다룬다. 이번 사이클의 테스트는
임의의 고정된 dict를 넘겨 화면에 올바르게 표시되는지만 검증한다. **확인 필요**: 이 네 키 이름과
"생산라인 대기 건수"를 실제로 무엇으로 채울지(0 고정 vs `PRODUCING` 개수 등)는 Cycle 15/16에서
다시 판단이 필요하며, 이번 사이클에서 미리 결정하지 않는다.

### 4. `main.py` 진입점 — 이번 사이클에 포함하지 않는다

설계 판단 2번의 결론(View는 Controller를 호출하지 않고, 메서드 단위로 독립적으로 테스트
가능하다)에 따라 실행 가능한 진입점 없이도 이번 사이클의 목표를 충분히 검증할 수 있다.
`PLAN.md` 로드맵대로 `main.py`는 Cycle 16(마지막 사이클, 전체 조립)에 포함한다.

## 이번 사이클에서 다룰 범위

- `view/console_view.py` (신규): `ConsoleView` 클래스.
  - **메인 메뉴**:
    - `show_main_menu(summary: dict) -> None`: 요약 정보(`sample_count`, `total_stock_qty`,
      `total_order_count`, `pending_production_count`)와 메뉴 목록(시료 관리/시료 주문/주문
      승인·거절/모니터링/생산 라인/출고 처리/종료)을 출력한다.
    - `get_menu_choice() -> str`: 사용자의 메뉴 선택 입력을 받아 앞뒤 공백을 제거해 반환한다.
  - **시료 관리 하위 메뉴**:
    - `show_sample_menu() -> None`: 하위 메뉴(신규 등록/목록 조회/이름 검색/뒤로 가기)를
      출력한다.
    - `get_sample_menu_choice() -> str`: 하위 메뉴 선택 입력을 받아 반환한다.
    - `get_new_sample_input() -> dict`: 시료 ID, 이름, 평균 생산시간, 수율, 초기 재고 수량을
      순서대로 입력받아 `{"sample_id": str, "name": str, "avg_production_time_min": float,
      "yield_rate": float, "stock_qty": int}` 형태로 반환한다(형 변환만 수행, 값 검증은 하지
      않는다 — 검증은 `SampleRegistry`/`SampleController`의 책임).
    - `show_sample_registered(sample) -> None`: 등록 성공 메시지를 출력한다.
    - `show_sample_list(samples: list) -> None`: 시료 목록(ID/이름/재고 등)을 출력하고,
      목록이 비어 있으면 "등록된 시료가 없습니다" 안내를 출력한다.
    - `get_search_keyword() -> str`: 검색 키워드 입력을 받아 반환한다.
    - `show_search_results(samples: list) -> None`: 검색 결과를 출력하고, 결과가 없으면
      "검색 결과가 없습니다" 안내를 출력한다.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `main.py` 진입점, 메뉴 선택에 따른 실제 분기·루프(오케스트레이션) — Cycle 16.
- 시료 주문, 주문 승인/거절, 모니터링, 생산 라인, 출고 처리 메뉴의 입출력 — Cycle 14~16.
- `summary` dict를 실제 Controller 데이터로 채우는 로직(집계 조립) — Cycle 15/16 이후 판단.
- 사용자 입력값 검증(공백 이름 거부, 중복 ID 거부 등) — 이미 `SampleRegistry`/
  `SampleController`가 담당하며, View는 형 변환 이상의 검증을 하지 않는다.
- `SampleController.duplicate_sample_ids()`를 화면에 어떻게 안내할지 — `SPEC.md` §5에서
  "콘솔 View 연동 시 사용자 안내에 활용 예정"이라고 언급했으나, 이번 사이클 범위(등록/조회/
  검색의 기본 흐름)에는 포함하지 않는다. 필요하면 이후 사이클에서 별도로 다룬다.

## Mock 사용 범위 (SPEC.md §6 기준)

- `view/console_view.py`는 표준 입출력이라는 외부 경계이므로, `pytest-mock`의 `mocker`로
  `builtins.input`을 `side_effect` 리스트로 mock하고, `capsys` 픽스처로 출력을 캡처해 검증한다
  (위 설계 판단 1번).
- `Sample` 등 View에 넘길 데이터는 mock 없이 실제 객체(`Sample(...)` 생성자 직접 호출)를
  사용한다 — View 테스트가 검증해야 하는 것은 "주어진 데이터를 올바른 문구로 표시하는가"이지
  Model의 동작이 아니므로, 데이터 자체는 실제 값을 그대로 쓴다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_console_view.py (신규 파일)

from model.sample import Sample
from view.console_view import ConsoleView


def test_메인_메뉴_진입시_요약정보와_메뉴목록을_출력한다(capsys):
    view = ConsoleView()
    summary = {
        "sample_count": 3,
        "total_stock_qty": 480,
        "total_order_count": 5,
        "pending_production_count": 1,
    }

    view.show_main_menu(summary)

    out = capsys.readouterr().out
    assert "3" in out  # 등록 시료 수
    assert "480" in out  # 총 재고
    assert "5" in out  # 전체 주문 수
    assert "시료 관리" in out
    assert "출고 처리" in out


def test_메뉴_선택_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["1"])
    view = ConsoleView()

    assert view.get_menu_choice() == "1"


def test_시료_등록_입력을_순서대로_받아_dict로_반환한다(mocker):
    mocker.patch(
        "builtins.input",
        side_effect=["S-001", "실리콘 웨이퍼-8인치", "0.5", "0.92", "480"],
    )
    view = ConsoleView()

    result = view.get_new_sample_input()

    assert result == {
        "sample_id": "S-001",
        "name": "실리콘 웨이퍼-8인치",
        "avg_production_time_min": 0.5,
        "yield_rate": 0.92,
        "stock_qty": 480,
    }


def test_시료_목록을_출력한다(capsys):
    view = ConsoleView()
    samples = [Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)]

    view.show_sample_list(samples)

    out = capsys.readouterr().out
    assert "S-001" in out
    assert "실리콘 웨이퍼-8인치" in out
    assert "480" in out


def test_등록된_시료가_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_sample_list([])

    out = capsys.readouterr().out
    assert "등록된 시료가 없습니다" in out


def test_검색_키워드_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["웨이퍼"])
    view = ConsoleView()

    assert view.get_search_keyword() == "웨이퍼"


def test_검색_결과를_출력한다(capsys):
    view = ConsoleView()
    samples = [Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)]

    view.show_search_results(samples)

    out = capsys.readouterr().out
    assert "S-001" in out


def test_검색_결과가_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_search_results([])

    out = capsys.readouterr().out
    assert "검색 결과가 없습니다" in out
```

> 위 테스트 목록은 예시이며, GREEN 단계에서 시료 관리 하위 메뉴 출력(`show_sample_menu`)과
> 하위 메뉴 선택(`get_sample_menu_choice`), 등록 성공 메시지(`show_sample_registered`) 등
> "다룰 범위"에 나열된 나머지 메서드에 대해서도 동일한 방식(단일 동작 검증, mock 최소화)으로
> 테스트를 추가한다.

## 검토 요청

위 목표/범위(특히 설계 판단 1~4번 — `capsys` 기반 출력 검증 전략, `ConsoleView`의 "순수
입출력만" 책임 범위, `summary` dict 표시 형식만 확정하고 실제 집계는 보류하는 판단, `main.py`
제외)로 RED 단계를 진행해도 될지 검토 부탁드립니다.
