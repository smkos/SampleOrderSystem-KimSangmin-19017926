# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**반도체 시료 생산주문관리 시스템** — 가상의 반도체 회사 "S-Semi"의 시료(Sample) 주문 접수·생산·출고
흐름을 콘솔 기반으로 관리하는 시스템. Agentic Engineering을 도입하여 기능 명세를 충족하는 고품질
코드를 개발하는 것이 목표. 상세 기능 명세와 설계는 이후 작성될 하위 문서(PRD.md 등)를 따른다.

이 프로젝트는 앞선 4개 PoC(Proof of Concept) 프로젝트의 결과물을 최대한 재사용/확장하여
구현한다:

| 순서 | PoC 경로 | 이 프로젝트에 재사용할 요소 |
|------|----------|------------------------------|
| 1 | `../MVC_PoC` | Model/View/Controller 패키지 구조, 역할 분리 원칙 |
| 2 | `../DataPersistence_PoC` | JSON 파일 영속화, 원자적 쓰기, 동시성 충돌 감지, 입력 검증, 출력 안전성 패턴 |
| 3 | `../DataMonitoring_PoC` | 실시간 모니터링 도구, diff/render 순수 함수 분리 |
| 4 | `../DummyDataGenerator_PoC` | 시드 주입 가능한 순수 함수 형태의 더미 데이터 생성기 |

## 개발 워크플로우 (모든 작업이 지켜야 할 공통 규칙)

- **TDD 필수**: 모든 기능 구현·버그 수정 전에 `test-driven-development` 스킬을 사용한다. 실패하는 테스트 없이 프로덕션 코드를 작성하지 않는다.
- **RED → GREEN → REVIEW 사이클**: 각 기능 단위마다 `plan.md`에 목표를 적고 검토를 받은 뒤(RED) 최소 구현으로 테스트를 통과시키고 검토를 받으며(GREEN), 구현이 `plan.md` 범위를 벗어나지 않았는지 확인하고 필요 시 리팩터링 전 검토를 받는다(REVIEW).
- **커밋 규칙**: 코드 작성과 문서 작성 사이에는 반드시 커밋을 분리한다 — 구현 코드 커밋 → 문서 작성 → 문서 커밋 → 추가 작업 문의, 순서를 지킨다. 커밋 메시지는 한글로 작성한다.
- **PoC 우선 재사용**: 새 기능을 설계하기 전에 위 PoC들에 이미 검증된 구현/패턴이 있는지 먼저 확인하고, 있다면 그대로 가져와 확장한다.
