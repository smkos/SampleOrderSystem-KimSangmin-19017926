# S-Semi 반도체 시료 생산주문관리 시스템

가상의 반도체 회사 "S-Semi"가 시료(Sample) 주문의 접수·승인·생산·출고 흐름을 관리하기 위한
콘솔(CLI) 기반 시스템입니다.

## 빠른 시작 — 더미 데이터로 바로 체험하기

빈 상태에서 메뉴를 하나씩 눌러보기보다, 더미 시료 데이터를 먼저 채워 넣고 `main.py`를
실행해보는 쪽이 빠릅니다.

```bash
source .venv/bin/activate

# 더미 시료 10개를 samples.json에 생성
python -c "
from pathlib import Path
from devtools.dummy_data_generator import generate_dummy_samples
from storage.sample_repository import SampleRepository

repo = SampleRepository(Path('samples.json'))
repo.save(generate_dummy_samples(10, repo.load()))
"

# 프로그램 실행 (메인 메뉴에서 1 -> 2 로 등록된 시료 목록을 바로 확인 가능)
python main.py
```

`devtools/dummy_data_generator.py`는 시드 주입이 가능한 순수 함수라(`rng=random.Random(seed)`를
넘기면 항상 같은 결과) 재현 가능한 테스트 데이터를 만들 때도 유용합니다. 아직 콘솔 메뉴에는
연동되어 있지 않아 위처럼 파이썬 코드에서 직접 호출해야 합니다.

## 실행 방법

### 가상환경

저장소에 `.venv`가 이미 준비되어 있습니다(Python 3.14).

```bash
source .venv/bin/activate
```

의존 패키지는 `requirements-dev.txt`에 정의되어 있습니다(`pytest`, `pytest-mock`). 필요 시 설치:

```bash
pip install -r requirements-dev.txt
```

### 테스트 실행

```bash
pytest
```

### 프로그램 실행

```bash
python main.py
```

실행하면 현재 작업 디렉터리에 `samples.json`, `orders.json` 파일이 생성/사용됩니다(각각 시료,
주문 데이터를 저장). 이미 파일이 있다면 기존 데이터를 불러옵니다.

## 메뉴 사용법

프로그램 시작 시 등록 시료 수·총 재고·전체 주문 수·생산라인 대기 건수 요약이 표시되고, 아래
메인 메뉴로 진입합니다.

| 번호 | 메뉴 | 설명 |
|------|------|------|
| 1 | 시료 관리 | 신규 등록 / 목록 조회 / 이름 검색 |
| 2 | 시료 주문 | 고객 주문 접수 |
| 3 | 주문 승인/거절 | 접수된 주문 승인 또는 거절 |
| 4 | 모니터링 | 주문량 확인 / 재고량 확인 |
| 5 | 생산 라인 | 생산 현황 조회 / 생산완료 처리 |
| 6 | 출고 처리 | `CONFIRMED` 주문 출고 |
| 7 | 종료 | 프로그램 종료 |

일반적인 업무 흐름 예시:

1. `1. 시료 관리` → `1. 신규 등록`으로 시료 ID, 이름, 평균 생산시간, 수율, 초기 재고 수량을
   입력해 시료를 먼저 등록합니다.
2. `2. 시료 주문`으로 시료 ID·고객명·주문 수량을 입력해 주문을 접수합니다(`RESERVED`).
3. `3. 주문 승인/거절`에서 접수된 주문 목록을 확인하고, 주문 ID를 입력한 뒤 승인 또는 거절을
   선택합니다. 재고가 충분하면 즉시 `CONFIRMED`, 부족하면 생산 큐에 등록되어 `PRODUCING`이
   됩니다.
4. `5. 생산 라인`에서 생산 현황과 대기 큐를 확인하고, 생산이 끝난 주문 ID를 입력해 생산완료
   처리하면 `CONFIRMED`로 전환됩니다.
5. `6. 출고 처리`에서 `CONFIRMED` 상태 주문 중 출고할 주문 ID를 입력하면 `RELEASE`로 전환됩니다.
6. `4. 모니터링`에서 언제든 상태별 주문 수와 시료별 재고 현황을 확인할 수 있습니다.

존재하지 않는 시료 ID나 주문 ID 등 잘못된 값을 입력하면 오류 메시지가 표시됩니다.

## 주요 기능

- **시료 관리**: 신규 시료 등록, 전체 목록 조회, 이름으로 검색.
- **시료 주문**: 고객 요청에 따라 주문을 접수(`RESERVED` 생성).
- **주문 승인/거절**: 접수된 주문을 재고 상황에 따라 승인(`CONFIRMED`/`PRODUCING`)하거나 거절(`REJECTED`).
- **모니터링**: 상태별 주문 수, 시료별 재고 현황(여유/부족/고갈)을 확인.
- **생산 라인**: 현재 생산 중인 주문과 대기 큐(FIFO)를 조회하고, 생산완료 처리(`PRODUCING → CONFIRMED`).
- **출고 처리**: `CONFIRMED` 상태 주문을 출고 처리(`RELEASE`).

자세한 배경과 기능 명세는 `PRD.md`, 기술 설계는 `SPEC.md`를 참고하세요.

## 개발 관례

이 프로젝트는 TDD(RED → GREEN → REVIEW) 방식으로 사이클 단위로 개발되었습니다. 전체 개발
이력과 각 사이클의 목표/범위는 `PLAN.md`와 `plan/` 디렉터리를 참고하세요.
