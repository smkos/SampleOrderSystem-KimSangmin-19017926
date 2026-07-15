import datetime as datetime_module

import main
from model.sample import Sample
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
        Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)
    )
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    mocker.patch(
        "builtins.input",
        side_effect=[
            "2",                            # 메인 메뉴: 시료 주문
            "S-001", "삼성전자 파운드리", "100",  # 주문 입력 (재고 충분)
            "3",                            # 메인 메뉴: 주문 승인/거절
            "ORD-20260715-0001", "1",       # 주문 ID, 승인 선택
            "6",                            # 메인 메뉴: 출고 처리
            "ORD-20260715-0001",            # 출고할 주문 ID
            "7",                            # 메인 메뉴: 종료
        ],
    )

    main.run_main_loop(ConsoleView(), *controllers)

    out = capsys.readouterr().out
    assert "주문이 접수되었습니다: ORD-20260715-0001" in out
    assert "주문이 승인되었습니다: ORD-20260715-0001" in out
    assert "ORD-20260715-0001" in out and "RELEASE" in out

    reloaded_orders = order_controller.list_orders()
    assert reloaded_orders[0].status.value == "RELEASE"


def test_시료_관리_메뉴에서_신규_등록을_한다(tmp_path, mocker, capsys):
    sample_controller, order_controller, production_controller, monitoring_controller = (
        main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    )
    mocker.patch(
        "builtins.input",
        side_effect=[
            "1",            # 신규 등록
            "S-001", "실리콘 웨이퍼-8인치", "0.5", "0.92", "480",
            "4",            # 뒤로 가기
        ],
    )

    main._run_sample_menu(ConsoleView(), sample_controller)

    out = capsys.readouterr().out
    assert "시료가 등록되었습니다: S-001" in out
    assert sample_controller.list_samples()[0].sample_id == "S-001"


def test_시료_주문_메뉴에서_주문을_생성한다(tmp_path, mocker, capsys):
    sample_controller, order_controller, production_controller, monitoring_controller = (
        main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    )
    sample_controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    mocker.patch(
        "builtins.input",
        side_effect=["S-001", "삼성전자 파운드리", "100"],
    )

    main._run_order_menu(ConsoleView(), order_controller)

    out = capsys.readouterr().out
    assert "주문이 접수되었습니다: ORD-20260715-0001" in out
    assert order_controller.list_orders()[0].sample_id == "S-001"


def test_주문_승인_거절_메뉴에서_승인을_처리한다(tmp_path, mocker, capsys):
    sample_controller, order_controller, production_controller, monitoring_controller = (
        main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    )
    sample_controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 100)
    mocker.patch(
        "builtins.input",
        side_effect=[order.order_id, "1"],
    )

    main._run_approval_menu(ConsoleView(), order_controller)

    out = capsys.readouterr().out
    assert "주문이 승인되었습니다" in out
    assert order_controller.list_orders()[0].status.value == "CONFIRMED"


def test_모니터링_메뉴에서_주문_상태별_개수를_조회한다(tmp_path, mocker, capsys):
    sample_controller, order_controller, production_controller, monitoring_controller = (
        main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    )
    sample_controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    order_controller.create_order("S-001", "삼성전자 파운드리", 100)
    mocker.patch(
        "builtins.input",
        side_effect=["1", "3"],  # 주문량 확인 → 뒤로 가기
    )

    main._run_monitoring_menu(ConsoleView(), monitoring_controller)

    out = capsys.readouterr().out
    assert "RESERVED" in out


def test_생산_라인_메뉴에서_생산완료_처리를_한다(tmp_path, mocker, capsys):
    sample_controller, order_controller, production_controller, monitoring_controller = (
        main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    )
    sample_controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 부족 → PRODUCING
    mocker.patch(
        "builtins.input",
        side_effect=["2", order.order_id, "3"],  # 생산완료 처리 → 주문 ID → 뒤로 가기
    )

    main._run_production_menu(ConsoleView(), production_controller)

    out = capsys.readouterr().out
    assert "생산이 완료되었습니다" in out
    assert order_controller.list_orders()[0].status.value == "CONFIRMED"


def test_존재하지_않는_시료ID로_주문하면_에러_메시지를_출력하고_계속_진행한다(tmp_path, mocker, capsys):
    controllers = main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    mocker.patch(
        "builtins.input",
        side_effect=[
            "2",                                  # 메인 메뉴: 시료 주문
            "S-999", "존재안하는고객", "10",        # 존재하지 않는 시료 ID -> ValueError 발생 기대
            "7",                                  # 메인 메뉴: 종료
        ],
    )

    main.run_main_loop(ConsoleView(), *controllers)  # 예외 없이 정상 종료되어야 함

    out = capsys.readouterr().out
    assert "S-999" in out or "존재하지 않는" in out or "오류" in out  # 에러 메시지가 출력됐는지(정확한 문구는 GREEN 단계에서 확정)


def test_시료_등록에서_수량에_숫자가_아닌_값을_입력해도_프로그램이_죽지_않는다(tmp_path, mocker, capsys):
    controllers = main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    mocker.patch(
        "builtins.input",
        side_effect=[
            "1", "1",                              # 메인 메뉴: 시료 관리 -> 신규 등록
            "S-001", "실리콘 웨이퍼", "abc", "0.9", "100",  # "abc"는 float 변환 실패
            "4",                                   # 시료 관리: 뒤로 가기
            "7",                                   # 메인 메뉴: 종료
        ],
    )

    main.run_main_loop(ConsoleView(), *controllers)  # 예외 없이 정상 종료되어야 함 (여기가 핵심 검증)


def test_출고_처리_메뉴에서_출고를_처리한다(tmp_path, mocker, capsys):
    sample_controller, order_controller, production_controller, monitoring_controller = (
        main.build_controllers(tmp_path / "samples.json", tmp_path / "orders.json")
    )
    sample_controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 0, 0))
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 100)
    order_controller.approve_order(order.order_id)  # 재고 충분 → CONFIRMED
    mocker.patch(
        "builtins.input",
        side_effect=[order.order_id],
    )

    main._run_release_menu(ConsoleView(), order_controller)

    out = capsys.readouterr().out
    assert "RELEASE" in out
    assert order_controller.list_orders()[0].status.value == "RELEASE"
