[← PLAN.md 인덱스로 돌아가기](../PLAN.md)

# Cycle 16 — 출고 처리 메뉴 + `main.py` 진입점 (프로젝트의 마지막 사이클) (GREEN 완료)

**이전 사이클**: [Cycle 15 — 콘솔 View: 모니터링 메뉴 + 생산 라인 메뉴](cycle-15-console-view-monitoring-production-menus.md)
**다음 사이클**: 없음 — 이 사이클이 `PLAN.md` 로드맵의 마지막 사이클이다.

## 지금까지의 진행 상황 (컨텍스트)

Cycle 1~11에서 Model/Controller 계층(시료 등록/조회/검색, 주문 접수·승인/거절·출고 처리, 생산
큐 계산과 생산 완료 처리, 모니터링 집계)을 모두 구현했다. Cycle 12에서 `OrderController`/
`ProductionController`를 각각의 저장소(`OrderRepository`/`SampleRepository`)와 연결해
영속화를 확인했다. Cycle 13~15에서 `view/console_view.py`(`ConsoleView`)에 메인 메뉴 요약 정보
표시, 시료 관리, 시료 주문, 주문 승인/거절, 모니터링, 생산 라인 메뉴의 입출력을 모두 구현했다.
이 세 사이클을 거치며 다음 원칙들이 확립됐다.

1. `ConsoleView`는 어떤 Controller/Model도 import하지 않는 순수 입출력 클래스다 — 표시
   메서드는 이미 계산된 데이터를 받아 화면에 출력만 하고, 입력 메서드는 사용자 입력을 단순
   자료구조로 반환할 뿐, 그 값을 어느 Controller 메서드에 넘길지는 View가 알지 못한다.
2. 출력 검증은 `capsys`, 입력은 `mocker.patch("builtins.input", side_effect=[...])`.
3. 여러 하위 기능이 있는 메뉴에만 하위 메뉴(진입 화면)를 둔다.
4. "이미 걸러진/정렬된 데이터를 Controller가 만들어 View에 넘긴다"는 패턴이
   `OrderController.list_orders()`(Cycle 12), `ProductionController.list_production_queue()`/
   `current_production_order()`(Cycle 15)로 반복되어 왔다.

Cycle 13의 설계 판단 2·3번, Cycle 14의 설계 판단 1번은 다음 세 가지를 의도적으로 미뤄
두었다 — "메뉴 선택 → Controller 호출 → 결과 표시"라는 오케스트레이션 자체, `RESERVED`/
`CONFIRMED` 주문만 걸러내는 필터링의 최종 위치, `summary` dict를 실제 값으로 채우는 집계
로직. `plan/cycle-12-order-controller-persistence.md`(9~40행)의 로드맵은 이 모든 것을 마지막
사이클인 이번 Cycle 16에서 확정하도록 설계해 두었다. 이번 사이클은 지금까지와 반대 방향의
작업이다 — Cycle 13~15가 "View는 Controller를 모른다"를 지키는 데 집중했다면, 이번 사이클의
`main.py`는 처음으로 View의 반환값을 받아 어느 Controller 메서드를 호출할지 결정하고 그 결과를
다시 View로 넘기는 전체 흐름(오케스트레이션)을 조립한다.

## 목표

`PRD.md` §5(메인 메뉴)·§6.6(출고 처리)과 `SPEC.md` §2(`view/console_view.py`, 모든
Controller)에 따라 다음 두 가지를 완성한다.

1. **출고 처리 메뉴**: `CONFIRMED` 상태 주문 목록을 표시하고, 출고할 주문을 입력받아 `RELEASE`로
   전환한 결과를 표시한다.
2. **`main.py` 진입점**: 저장소 경로를 결정하고, 4개 Controller(`SampleController`,
   `OrderController`, `ProductionController`, `MonitoringController`)를 필요한 저장소/레지스트리
   공유 제약을 지키며 조립하고, 메인 메뉴 진입 시 요약 정보를 실제 값으로 채워 표시하고, 사용자의
   메뉴 선택에 따라 각 하위 메뉴로 진입해 View의 입력값을 해당 Controller 메서드 호출로 연결하고
   결과를 다시 View로 표시하는 메인 루프를 구동한다. "종료" 선택 시 루프를 빠져나온다.

## 설계 판단 (모호한 지점 — 검토 필요)

### 1. 출고 처리 메뉴 View — 승인/거절과 유사하지만 전용 메서드를 새로 둔다

Cycle 14는 `get_order_id_to_process()`를 승인/거절 공용으로 이미 일반적인 이름으로 만들어
두었다. 출고 처리에도 재사용할지 검토했으나, 다음 이유로 **재사용하지 않고 전용 메서드를
새로 추가**하기로 판단한다.

- `show_pending_orders()`는 "접수된 주문이 없습니다"라는, `RESERVED` 상태에 특화된 안내
  문구를 갖고 있다. 출고 처리 대상은 `CONFIRMED` 상태이므로 문구가 다르며("출고 가능한
  주문이 없습니다"), 같은 메서드에 상태별 문구 분기를 추가하면 Cycle 13~15가 지켜온 "표시
  메서드는 이미 계산된 데이터를 그대로 보여주기만 한다"는 단순성이 깨진다.
- Cycle 15가 모니터링/생산 라인 각각에 전용 메서드 쌍(`show_order_counts`/`show_stock_status`,
  `show_current_production`/`show_production_queue`)을 추가한 것과 일관되게, 출고 처리도
  전용 메서드 쌍을 추가하는 편이 지금까지의 명명 관례(`show_<대상>`, `get_<입력 목적>`)와
  맞는다.

**판단**: `ConsoleView`에 다음 세 메서드를 추가한다.

- `show_releasable_orders(orders: list) -> None`: `CONFIRMED` 상태 주문 목록(이미 걸러진
  것을 그대로 받음)을 표시하고, 비어 있으면 "출고 가능한 주문이 없습니다" 안내를 출력한다.
- `get_order_id_to_release() -> str`: 출고할 주문 ID 입력을 받아 앞뒤 공백을 제거해 반환한다.
- `show_order_released(order) -> None`: 출고 처리 결과(전환된 `order.status`인 `RELEASE`)를
  표시한다.

### 2. "`CONFIRMED`만 걸러내는" 필터링 위치 — `OrderController`에 전용 조회 메서드 추가 (Cycle 14가 미뤄둔 결정 확정)

Cycle 14 설계 판단 1번은 "접수된 주문(`RESERVED`)만 걸러내는" 필터링 위치를 Cycle 16으로
미루면서, 후보로 (a) `OrderController` 전용 메서드, (b) `model/monitoring.py` 확장, (c)
`main.py` 인라인 처리를 제시했다.

이 프로젝트에는 이미 "Controller가 Registry를 조회해 파생 데이터(목록/집계)를 만들어 View에
넘긴다"는 패턴이 `OrderController.list_orders()`(Cycle 12), `ProductionController.
list_production_queue()`/`current_production_order()`(Cycle 15)로 반복되어 왔다.
`model/monitoring.py`는 "상태별 개수 집계"·"재고 상태 라벨 계산"처럼 통계적 집계를 위한 순수
함수 모음이지, 원본 리스트를 그대로 걸러 반환하는 필터링과는 성격이 다르다(집계 함수를
필터링 용도로 확장하면 책임이 섞인다). `main.py` 인라인 필터링은 코드가 간단해 보이지만, 이미
`OrderController`가 자신의 `Order` 목록을 관리하는 유일한 소유자이므로 "이 상태의 주문만
보여달라"는 조회 자체도 `OrderController`의 책임으로 두는 편이 일관성 있다 — `main.py`가
Registry 내부 데이터 구조나 `OrderStatus`를 직접 참조하며 필터링 로직을 갖는 것보다, 이미
확립된 조회 위임 패턴을 그대로 따르는 편이 결합도가 낮다.

**판단**: `controller/order_controller.py`에 다음 두 메서드를 추가한다.

- `OrderController.list_pending_orders() -> list[Order]`: `list_orders()`가 반환하는 목록 중
  `status == OrderStatus.RESERVED`인 주문만 필터링해 반환한다.
- `OrderController.list_releasable_orders() -> list[Order]`: `status == OrderStatus.CONFIRMED`인
  주문만 필터링해 반환한다.

이 두 메서드는 데이터를 변경하지 않는 순수 조회이므로 저장소 호출이 필요 없다(`list_orders()`와
동일).

### 3. 승인/거절 선택 문자열 → 실제 Controller 메서드 호출 분기 (Cycle 14가 미뤄둔 결정 확정)

`get_approval_decision()`은 화면에 "1. 승인  2. 거절"이라는 안내를 이미 출력하고 있으므로
(Cycle 14 GREEN 구현, `view/console_view.py` 89행), `main.py`는 그 관례를 그대로 따라
`"1"` → `approve_order()`, `"2"` → `reject_order()`로 분기한다. 그 외 입력은 유효하지
않은 선택으로 간주해 안내만 출력하고 하위 메뉴로 돌아간다(예외를 던지지 않는다 — 사용자가
잘못 입력했다고 프로그램이 죽으면 안 된다는 콘솔 애플리케이션의 일반적인 기대에 따른 최소
방어다. `SPEC.md`가 이 경우를 명시하지 않으므로 "무한 재입력 유도" 같은 정교한 처리는 하지
않고 하위 메뉴로 되돌아가는 것으로 최소화한다).

### 4. `summary` dict 조립 — `main.py`가 3개 Controller의 조회 결과를 조합한다 (Cycle 13이 미뤄둔 결정 확정)

Cycle 13이 `summary` 키(`sample_count`, `total_stock_qty`, `total_order_count`,
`pending_production_count`)를 이미 확정해 두었으므로, 이번 사이클은 그 값을 실제로 채우는
계산만 정의한다.

**판단**: `main.py`에 `build_summary(sample_controller, order_controller,
production_controller) -> dict`를 순수 함수로 둔다(Controller를 인자로 받아 각자의 조회
메서드만 호출하고 내부 상태를 직접 건드리지 않음).

- `sample_count` = `len(sample_controller.list_samples())`
- `total_stock_qty` = `sum(sample.stock_qty for sample in sample_controller.list_samples())`
- `total_order_count` = `len(order_controller.list_orders())`
- `pending_production_count` = `len(production_controller.list_production_queue())`
  ("생산라인 대기 건수"는 Cycle 15가 이미 확정한 `list_production_queue()`의 길이로
  정의한다 — 큐 전체(선두 포함)를 "대기 건수"로 삼는다는 것은 Cycle 15 설계 판단 3번과
  일관된다.)

`MonitoringController`는 이 집계에 필요하지 않다(모두 `SampleController`/`OrderController`/
`ProductionController`의 기존 조회 메서드만으로 충분하다). 다만 `MonitoringController`는
모니터링 메뉴 자체(Cycle 15에서 View만 완성됨)를 구동하기 위해 여전히 필요하므로, 조립 대상
4개 Controller에는 포함한다.

### 5. Controller 조립 — 저장소/레지스트리 인스턴스 공유 규칙 확정

Cycle 12는 "`OrderController`와 `ProductionController`는 같은 `OrderRepository`/
`SampleRepository` 인스턴스를 공유해야 한다"는 제약을 이미 확정해 두었다(그렇지 않으면 파일
버전 추적이 어긋나 스스로와 `ConflictError`를 일으킨다). `storage/sample_repository.py`의
충돌 감지 방식(마지막으로 불러온 시점의 파일 해시와 저장 시점의 실제 해시를 비교)을 다시
확인한 결과, 이 제약은 `OrderController`/`ProductionController` 쌍에만 한정되지 않는다 —
**`SampleController`도 `samples.json`에 쓰기(시료 등록 시)를 수행하므로, `SampleController`가
`OrderController`/`ProductionController`와 별도의 `SampleRepository` 인스턴스를 갖고 있으면,
한쪽이 쓰기를 한 뒤 다른 쪽이 (자신은 그 변경을 모른 채) 쓰기를 시도할 때 거짓 `ConflictError`가
발생할 수 있다.**

**판단**: `main.py`는 다음 순서로 조립한다.

1. `sample_repository = SampleRepository(SAMPLES_PATH)` — **단 하나만** 생성한다.
2. `order_repository = OrderRepository(ORDERS_PATH)` — **단 하나만** 생성한다.
3. `sample_registry = SampleRegistry()`, `order_registry = OrderRegistry()` — 각각 하나씩
   생성한다(Cycle 9 이후 `OrderController`/`ProductionController`가 이미 이 두 Registry를
   공유하는 구조).
4. `SampleController(sample_registry, sample_repository)`
5. `OrderController(order_registry, sample_registry, order_repository, sample_repository)`
6. `ProductionController(order_registry, sample_registry, order_repository, sample_repository)`
7. `MonitoringController(order_registry, sample_registry)`

즉 **`sample_repository`/`order_repository`/`sample_registry`/`order_registry` 네 인스턴스
모두 프로세스 전체에서 각각 단 하나씩만 만들어, 필요한 모든 Controller에 동일하게 주입한다.**
저장소 경로는 `main.py` 상단에 `SAMPLES_PATH = Path("samples.json")`,
`ORDERS_PATH = Path("orders.json")`로 상수화한다(작업 디렉터리 기준 상대 경로 — 콘솔
애플리케이션 실행 위치에 파일이 생성/갱신된다).

### 6. `main.py`의 테스트 전략 — `run_main_loop()`를 분리해 `input` side_effect로 끝까지 구동하는 통합 테스트

`SPEC.md` §6은 `main.py`에 대한 명시적 지침이 없다. 지금까지의 전략(Model/Controller는
실제 객체 조합, View는 `input`/`capsys` mock)을 그대로 확장하면 다음과 같은 결론에
도달한다 — `main.py`의 오케스트레이션 로직은 "내부 협력"(Controller↔View 연결)이므로 mock이
필요한 외부 경계가 아니다. 유일한 외부 경계는 여전히 표준 입출력과 파일시스템이며, 이미 확립된
방식(`mocker.patch("builtins.input", side_effect=[...])`, `capsys`, `tmp_path`)으로 충분히
격리할 수 있다.

**판단**:

- `main()` 함수 자체(저장소 경로 상수 사용, `if __name__ == "__main__"`)는 테스트하지
  않는다 — 대신 저장소 경로를 인자로 받는 `build_controllers(samples_path, orders_path)`와,
  조립된 Controller들과 `ConsoleView`를 받아 루프를 구동하는 `run_main_loop(view,
  sample_controller, order_controller, production_controller, monitoring_controller) ->
  None`으로 로직을 분리한다. 테스트는 `tmp_path`로 만든 저장소 경로를 `build_controllers()`에
  넘겨 실제 Controller 조합을 얻고, `run_main_loop()`을 직접 호출한다.
- 하나의 통합 테스트가 `input`의 `side_effect` 리스트로 "메인 메뉴 → 시료 등록 → 뒤로가기 →
  메인 메뉴 → 시료 주문 → 메인 메뉴 → 종료"처럼 여러 화면을 순서대로 통과시키고, `capsys`로
  각 단계의 출력 문구(등록 완료 메시지, 주문 접수 완료 메시지 등)를 확인하며, 동시에
  `tmp_path`의 `samples.json`/`orders.json`을 직접 열어 실제로 저장되었는지 확인한다 — Cycle
  12의 저장소 연동 검증과 Cycle 13~15의 View 입출력 검증을 하나의 흐름으로 잇는 최초의
  end-to-end 테스트다.
- 각 메뉴 흐름(시료 관리/시료 주문/승인·거절/모니터링/생산 라인/출고 처리)은 `run_main_loop()`
  내부에서 별도 함수(`_run_sample_menu(view, sample_controller)` 등)로 분리해, "종료"까지
  가지 않고 개별 하위 메뉴 동작만 검증하는 좁은 테스트도 추가한다(하나의 거대한 end-to-end
  테스트에만 의존하면 실패 시 원인 파악이 어려워지므로, Cycle 12~15가 지켜온 "한 사이클에
  하나의 동작만" 원칙을 테스트 단위에도 적용한다).
- `Order.created_at`/`order_id` 채번을 결정적으로 만들기 위해 기존과 동일하게
  `mocker.patch("model.order_registry.datetime")`을 사용한다.

### 7. 손상된 저장 파일(`duplicate_sample_ids()`) 안내 — 이번 사이클에도 포함하지 않는다

`SPEC.md` §5는 "건너뛴 `sample_id` 목록은 `duplicate_sample_ids()`로 조회할 수 있다(콘솔 View
연동 시 사용자 안내에 활용 예정)"이라고 언급한다. 이번이 마지막 사이클이지만, 다음 이유로
범위에 포함하지 않는다.

- Cycle 13이 이미 같은 사안을 검토해 "시료 관리 메뉴의 기본 흐름(등록/조회/검색)"으로 범위를
  좁히며 제외했고, 그 판단이 지금까지 재검토된 적이 없다.
- 이를 포함하려면 새로운 View 메서드(예: `show_duplicate_sample_ids()`)와 `main.py`가 메인
  메뉴 진입 시(또는 시료 관리 메뉴 진입 시) 이 목록을 조회해 표시하는 흐름을 새로 설계해야
  하는데, 이는 "출고 처리 메뉴 + `main.py` 조립"이라는 이번 사이클의 핵심 목표(지금까지 미뤄진
  오케스트레이션 결정들을 확정하는 것)와 결이 다른 별개의 기능 추가에 가깝다.
- 이 기능이 없어도 시스템의 정상 동작(시료 등록/주문/승인/생산/출고)에는 영향이 없다 — 손상된
  파일이 없는 한 `duplicate_sample_ids()`는 항상 빈 리스트를 반환한다.

**결론**: 이번 사이클에서도 계속 범위 밖으로 둔다. 필요해지면 프로젝트 완료 후 별도 개선
사이클로 다룬다.

### 8. 사이클 분할 여부 — 분할하지 않고 로드맵대로 하나의 사이클로 진행

출고 처리 메뉴(설계 판단 1·2번)는 Cycle 14의 승인/거절 메뉴와 동일한 패턴을 반복하는 작은
작업이라 그 자체로는 분할할 이유가 없다. `main.py` 조립(설계 판단 3~6번)은 새로운 시험 전략이
필요하긴 하지만, 실제로 새로 작성하는 로직은 "이미 존재하는 Controller 메서드를 어떤 순서로
호출할지 연결하는 배선(wiring)"이 대부분이고 새로운 계산/검증 규칙은 없다(Cycle 12처럼 서로
독립적으로 검증 가능한 이질적 작업 여러 개가 섞여 있지 않다). 따라서 Cycle 12와 달리 분할할
필요가 없다고 판단하여, `PLAN.md` 로드맵대로 이번 사이클로 프로젝트를 마무리한다.

## 이번 사이클에서 다룰 범위

- `controller/order_controller.py` (기존 `OrderController`에 메서드 추가):
  - `list_pending_orders() -> list[Order]`: `RESERVED` 상태 주문만 필터링.
  - `list_releasable_orders() -> list[Order]`: `CONFIRMED` 상태 주문만 필터링.
- `view/console_view.py` (기존 `ConsoleView`에 메서드 추가):
  - **출고 처리**:
    - `show_releasable_orders(orders: list) -> None`
    - `get_order_id_to_release() -> str`
    - `show_order_released(order) -> None`
- `main.py` (신규 파일):
  - `SAMPLES_PATH`, `ORDERS_PATH` 경로 상수.
  - `build_controllers(samples_path, orders_path) -> tuple`: 설계 판단 5번 순서로 4개
    Controller를 조립해 반환한다.
  - `build_summary(sample_controller, order_controller, production_controller) -> dict`:
    설계 판단 4번의 계산 규칙.
  - `run_main_loop(view, sample_controller, order_controller, production_controller,
    monitoring_controller) -> None`: 메인 메뉴 표시 → 선택 입력 → 하위 메뉴 분기 → "종료"
    선택 시 루프 탈출.
  - 하위 메뉴별 구동 함수(시료 관리/시료 주문/승인·거절/모니터링/생산 라인/출고 처리) —
    각각 View의 입력 메서드 호출 → 해당 Controller 메서드 호출 → View의 표시 메서드 호출을
    연결한다. 승인/거절 분기는 설계 판단 3번을 따른다.
  - `main() -> None`: `build_controllers(SAMPLES_PATH, ORDERS_PATH)`와 `ConsoleView()`를 만들어
    `run_main_loop()`을 호출한다. `if __name__ == "__main__": main()`.

## 이번 사이클에서 다루지 않는 것 (범위 초과 방지)

- `SampleController.duplicate_sample_ids()`의 콘솔 안내 — 설계 판단 7번에 따라 범위 밖.
- 저장 파일 동시 수정 충돌(`ConflictError`)이 발생했을 때 사용자에게 재시도를 안내하는 흐름 —
  Cycle 3·12에서도 동일하게 미뤄 온 사안이며, 이번 사이클도 예외가 그대로 전파되는 것만
  전제한다(콘솔에서 처리되지 않은 예외는 `main()`을 종료시킨다 — 이는 현재 `SPEC.md`에 정의된
  요구사항이 아니므로 새로 설계하지 않는다).
- 잘못된 메뉴 번호(정의되지 않은 범위 밖 숫자 등) 입력에 대한 정교한 재입력 유도 — 설계 판단
  3번 수준의 최소 방어(안내 후 하위 메뉴로 복귀)만 다루고, 그 이상의 입력 검증 UX는 다루지
  않는다.
- 생산 진행률(부분 생산량) 추적, `summary`의 "생산라인 대기 건수"를 큐 선두 제외 여부로
  재정의하는 것 — Cycle 15가 이미 결정한 정의(큐 전체 길이)를 그대로 재사용한다.
- 콘솔 애플리케이션의 반복 실행(재시작) 스크립트, 배포/패키징 — `SPEC.md`에 정의되지 않은
  범위.

## Mock 사용 범위 (SPEC.md §6 기준)

- `view/console_view.py`에 추가하는 출고 처리 메서드는 Cycle 13~15와 동일하게
  `mocker.patch("builtins.input", side_effect=[...])`와 `capsys`로 검증한다.
- `controller/order_controller.py`에 추가하는 `list_pending_orders()`/
  `list_releasable_orders()`는 "내부 협력" 계층이므로 실제 `OrderRegistry`/`SampleRegistry`/
  `OrderRepository`/`SampleRepository`를 조합해 테스트한다(mock 없음), 기존
  `tests/test_order_controller.py`의 패턴과 동일.
- `main.py`는 설계 판단 6번에 따라 표준 입출력만 외부 경계로 취급해 mock한다. 저장소는
  `tmp_path` 기반 실제 파일 I/O로 검증한다(파일시스템 mock 없음). `Order.created_at`/`order_id`
  채번만 `mocker.patch("model.order_registry.datetime")`으로 결정적으로 고정한다.

## 작성할 실패 테스트 (예시)

```python
# tests/test_order_controller.py — 기존 파일에 추가

import datetime as datetime_module

from controller.order_controller import OrderController
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry
from storage.order_repository import OrderRepository
from storage.sample_repository import SampleRepository


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_접수된_주문만_걸러서_조회한다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(
        OrderRegistry(), sample_registry,
        OrderRepository(tmp_path / "orders.json"), SampleRepository(tmp_path / "samples.json"),
    )
    reserved = controller.create_order("S-001", "삼성전자 파운드리", 100)
    confirmed = controller.create_order("S-001", "SK하이닉스", 50)
    controller.approve_order(confirmed.order_id)  # 재고 충분 → CONFIRMED

    pending = controller.list_pending_orders()

    assert [order.order_id for order in pending] == [reserved.order_id]


def test_출고_가능한_주문만_걸러서_조회한다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(
        OrderRegistry(), sample_registry,
        OrderRepository(tmp_path / "orders.json"), SampleRepository(tmp_path / "samples.json"),
    )
    reserved = controller.create_order("S-001", "삼성전자 파운드리", 100)
    confirmed = controller.create_order("S-001", "SK하이닉스", 50)
    controller.approve_order(confirmed.order_id)  # 재고 충분 → CONFIRMED

    releasable = controller.list_releasable_orders()

    assert [order.order_id for order in releasable] == [confirmed.order_id]
```

```python
# tests/test_console_view.py — 기존 파일에 추가

from model.order import Order, OrderStatus
from view.console_view import ConsoleView


def test_출고_가능한_주문_목록을_출력한다(capsys):
    view = ConsoleView()
    orders = [
        Order(
            "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
            OrderStatus.CONFIRMED, "2026-07-15T09:00:00",
        ),
    ]

    view.show_releasable_orders(orders)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out


def test_출고_가능한_주문이_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_releasable_orders([])

    out = capsys.readouterr().out
    assert "출고 가능한 주문이 없습니다" in out


def test_출고할_주문_ID_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["ORD-20260715-0001"])
    view = ConsoleView()

    assert view.get_order_id_to_release() == "ORD-20260715-0001"


def test_출고_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.RELEASE, "2026-07-15T09:00:00",
    )

    view.show_order_released(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "RELEASE" in out
```

```python
# tests/test_main.py (신규 파일)

import datetime as datetime_module

import main
from view.console_view import ConsoleView


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_시료_등록_후_메인_메뉴_요약정보에_반영된다(tmp_path, mocker, capsys):
    controllers = main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    sample_controller, order_controller, production_controller, monitoring_controller = controllers
    mocker.patch(
        "builtins.input",
        side_effect=[
            "1",            # 메인 메뉴: 시료 관리
            "1",            # 시료 관리: 신규 등록
            "S-001", "실리콘 웨이퍼-8인치", "0.5", "0.92", "480",  # 시료 입력
            "4",            # 시료 관리: 뒤로 가기
            "7",            # 메인 메뉴: 종료
        ],
    )

    main.run_main_loop(ConsoleView(), *controllers)

    out = capsys.readouterr().out
    assert "시료가 등록되었습니다: S-001" in out
    assert "등록 시료 수: 1" in out  # 두 번째 메인 메뉴 출력에 반영됨
    reloaded = sample_controller.list_samples()
    assert reloaded[0].sample_id == "S-001"


def test_주문_생성부터_출고까지_전체_흐름이_저장소에_반영된다(tmp_path, mocker, capsys):
    controllers = main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    sample_controller, order_controller, production_controller, monitoring_controller = controllers
    sample_controller.register_sample(
        __import__("model.sample", fromlist=["Sample"]).Sample(
            "S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480
        )
    )
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    mocker.patch(
        "builtins.input",
        side_effect=[
            "2",                          # 메인 메뉴: 시료 주문
            "S-001", "삼성전자 파운드리", "100",  # 주문 입력 (재고 충분)
            "3",                          # 메인 메뉴: 주문 승인/거절
            "ORD-20260715-0001", "1",     # 주문 ID, 승인 선택
            "4",                          # 주문 승인/거절: 뒤로 가기 (하위 메뉴가 있다면)
            "6",                          # 메인 메뉴: 출고 처리
            "ORD-20260715-0001",          # 출고할 주문 ID
            "7",                          # 메인 메뉴: 종료
        ],
    )

    main.run_main_loop(ConsoleView(), *controllers)

    reloaded_orders = order_controller.list_orders()
    assert reloaded_orders[0].status.value == "RELEASE"
```

> 참고: 위 `test_main.py` 예시의 `input` side_effect 순서(특히 승인/거절 메뉴의 하위 메뉴
> 유무, 각 단계 사이의 "뒤로 가기" 필요 여부)는 실제 `run_main_loop()` 구현 세부 흐름에 따라
> GREEN 단계에서 조정될 수 있다 — RED 단계에서 `main.py`의 각 하위 메뉴 함수 시그니처를 먼저
> 정의한 뒤, 그 흐름에 맞춰 `input` 순서를 확정한다. 또한 각 하위 메뉴(시료 관리/시료 주문/
> 승인·거절/모니터링/생산 라인/출고 처리)를 종료까지 가지 않고 개별적으로 검증하는 좁은
> 테스트도 함께 추가한다(설계 판단 6번 참고).

## 진행 결과

- **RED** (`c745eca` Cycle 16 계획, `f1ae73a` Cycle 16 RED): 위 설계 판단 1~8번(출고 처리
  전용 View 메서드 신설, `CONFIRMED` 필터링을 `OrderController`에 두는 판단, 승인/거절 선택
  분기, `summary` 집계를 `main.py`의 순수 함수로 두는 판단, 저장소/레지스트리 4개 인스턴스를
  프로세스 전체에서 단 하나씩만 공유하는 조립 규칙, `run_main_loop()` 분리 테스트 전략,
  손상된 시료 파일 안내를 계속 범위 밖에 두는 판단, 사이클을 분할하지 않고 로드맵대로 하나로
  진행하는 판단)을 사람 파트너 검토를 거쳐 이견 없이 채택했다.
  `tests/test_order_controller.py`, `tests/test_console_view.py`에 신규 테스트를 추가하고,
  신규 파일 `tests/test_main.py`를 작성해 실패를 확인했다.
- **GREEN** (`d725314` Cycle 16 GREEN): 계획대로 `controller/order_controller.py`에
  `list_pending_orders()`/`list_releasable_orders()`를, `view/console_view.py`에 출고 처리
  메뉴 3개 메서드(`show_releasable_orders`, `get_order_id_to_release`, `show_order_released`)를,
  `main.py`(신규)에 `build_controllers()`(설계 판단 5번의 저장소/레지스트리 공유 규칙 그대로),
  `build_summary()`, `run_main_loop()`, 6개 하위 메뉴 함수(시료 관리/시료 주문/승인·거절/
  모니터링/생산 라인/출고 처리), `main()`을 구현했다. RED 단계에서 이미 커밋된
  `tests/test_main.py`의 `input` side_effect 순서(승인/거절 뒤에 "뒤로 가기" 없이 바로 다음
  메뉴로 이어짐)와 GREEN 구현이 정확히 일치해, `test_main.py` 자체는 수정이 필요 없었다.
- **최종 결과**: 신규 테스트 14개(`test_order_controller.py` 2개 + `test_console_view.py` 4개
  + `test_main.py` 8개)가 모두 통과하며, 전체 테스트 134개가 회귀 없이 통과한다.
- **범위 준수 확인**: 계획대로 `SampleController.duplicate_sample_ids()`의 콘솔 안내, 저장
  파일 동시 수정 충돌(`ConflictError`)이 발생했을 때 사용자에게 재시도를 안내하는 흐름은
  포함하지 않았다.
- **사람 파트너의 수동 실행 검증**: 이 프로젝트에서 처음으로 실제 실행 가능한 진입점
  (`main.py`)이 생겼으므로, 사람 파트너가 임시 디렉터리에서 `python main.py`를 직접 실행해
  수동으로 검증했다. 시료 등록(1 → 1 → 시료 정보 입력)과 시료 주문(2 → 시료ID/고객명/수량)까지
  진행한 뒤 종료했고, 메인 메뉴 요약(등록 시료 수/총 재고/전체 주문 수)이 실제로 갱신되어
  표시되는 것과 `samples.json`/`orders.json` 파일에 실제로 저장되는 것을 직접 확인했다(실제
  프로젝트 루트 파일은 건드리지 않음). 정상 동작을 확인했다.
- **참고 — verify-agent 독립 검증 생략**: Cycle 12~15에 이어 이번 사이클도 verify-agent 독립
  검증은 생략했다(마지막에 한 번에 몰아서 검증하기로 함). 다만 사람 파트너의 수동 실행 검증은
  이번 사이클에서 별도로 이뤄졌다.
