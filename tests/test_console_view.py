from model.order import Order, OrderStatus
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


def test_시료_관리_하위_메뉴를_출력한다(capsys):
    view = ConsoleView()

    view.show_sample_menu()

    out = capsys.readouterr().out
    assert "신규 등록" in out
    assert "목록 조회" in out
    assert "이름 검색" in out


def test_시료_관리_하위_메뉴_선택_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["2"])
    view = ConsoleView()

    assert view.get_sample_menu_choice() == "2"


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


def test_시료_등록_성공_메시지를_출력한다(capsys):
    view = ConsoleView()
    sample = Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)

    view.show_sample_registered(sample)

    out = capsys.readouterr().out
    assert "S-001" in out


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


def test_시료_주문_입력을_순서대로_받아_dict로_반환한다(mocker):
    mocker.patch(
        "builtins.input",
        side_effect=["S-001", "삼성전자 파운드리", "200"],
    )
    view = ConsoleView()

    result = view.get_new_order_input()

    assert result == {
        "sample_id": "S-001",
        "customer_name": "삼성전자 파운드리",
        "quantity": 200,
    }


def test_주문_생성_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.RESERVED, "2026-07-15T09:32:15",
    )

    view.show_order_created(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "RESERVED" in out


def test_접수된_주문_목록을_출력한다(capsys):
    view = ConsoleView()
    orders = [
        Order(
            "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
            OrderStatus.RESERVED, "2026-07-15T09:32:15",
        ),
    ]

    view.show_pending_orders(orders)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "삼성전자 파운드리" in out


def test_접수된_주문이_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_pending_orders([])

    out = capsys.readouterr().out
    assert "접수된 주문이 없습니다" in out


def test_처리할_주문_ID_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["ORD-20260715-0001"])
    view = ConsoleView()

    assert view.get_order_id_to_process() == "ORD-20260715-0001"


def test_승인_거절_선택_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["1"])
    view = ConsoleView()

    assert view.get_approval_decision() == "1"


def test_승인_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.CONFIRMED, "2026-07-15T09:32:15",
    )

    view.show_order_approved(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "CONFIRMED" in out


def test_승인_처리_결과가_PRODUCING이면_그대로_표시한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0002", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.PRODUCING, "2026-07-15T09:32:15",
    )

    view.show_order_approved(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0002" in out
    assert "PRODUCING" in out


def test_거절_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.REJECTED, "2026-07-15T09:32:15",
    )

    view.show_order_rejected(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "REJECTED" in out


def test_모니터링_하위_메뉴를_출력한다(capsys):
    view = ConsoleView()

    view.show_monitoring_menu()

    out = capsys.readouterr().out
    assert "주문량 확인" in out
    assert "재고량 확인" in out


def test_모니터링_하위_메뉴_선택_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["1"])
    view = ConsoleView()

    assert view.get_monitoring_menu_choice() == "1"


def test_주문_상태별_개수를_출력한다(capsys):
    view = ConsoleView()
    counts = {
        OrderStatus.RESERVED: 2,
        OrderStatus.CONFIRMED: 1,
        OrderStatus.PRODUCING: 0,
        OrderStatus.RELEASE: 3,
    }

    view.show_order_counts(counts)

    out = capsys.readouterr().out
    assert "RESERVED" in out and "2" in out
    assert "RELEASE" in out and "3" in out


def test_재고_상태를_출력한다(capsys):
    view = ConsoleView()
    labels = {
        "S-001": {"label": "여유", "stock_qty": 480},
        "S-002": {"label": "부족", "stock_qty": 50},
        "S-003": {"label": "고갈", "stock_qty": 0},
    }

    view.show_stock_status(labels)

    out = capsys.readouterr().out
    assert "S-001 | 여유 (재고: 480)" in out
    assert "S-003 | 고갈 (재고: 0)" in out


def test_생산_라인_하위_메뉴를_출력한다(capsys):
    view = ConsoleView()

    view.show_production_menu()

    out = capsys.readouterr().out
    assert "생산 현황 조회" in out
    assert "생산완료 처리" in out


def test_생산_라인_하위_메뉴_선택_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["1"])
    view = ConsoleView()

    assert view.get_production_menu_choice() == "1"


def test_현재_생산중인_주문_정보를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.PRODUCING, "2026-07-15T09:00:00",
    )

    view.show_current_production(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "삼성전자 파운드리" in out


def test_현재_생산중인_주문_정보와_부족분_실생산량을_함께_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.PRODUCING, "2026-07-15T09:00:00",
    )

    view.show_current_production(order, shortage=190, actual_production_qty=207)

    out = capsys.readouterr().out
    assert "190" in out
    assert "207" in out


def test_현재_생산중인_주문이_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_current_production(None)

    out = capsys.readouterr().out
    assert "현재 생산 중인 주문이 없습니다" in out


def test_대기중인_생산_큐를_출력한다(capsys):
    view = ConsoleView()
    orders = [
        Order(
            "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
            OrderStatus.PRODUCING, "2026-07-15T09:00:00",
        ),
    ]

    view.show_production_queue(orders)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out


def test_대기중인_생산_큐가_없으면_안내_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_production_queue([])

    out = capsys.readouterr().out
    assert "대기 중인 생산 주문이 없습니다" in out


def test_생산완료_처리할_주문_ID_입력을_받는다(mocker):
    mocker.patch("builtins.input", side_effect=["ORD-20260715-0001"])
    view = ConsoleView()

    assert view.get_order_id_to_complete() == "ORD-20260715-0001"


def test_생산완료_처리_결과를_출력한다(capsys):
    view = ConsoleView()
    order = Order(
        "ORD-20260715-0001", "S-001", "삼성전자 파운드리", 200,
        OrderStatus.CONFIRMED, "2026-07-15T09:00:00",
    )

    view.show_production_completed(order)

    out = capsys.readouterr().out
    assert "ORD-20260715-0001" in out
    assert "CONFIRMED" in out


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


def test_에러_메시지를_출력한다(capsys):
    view = ConsoleView()

    view.show_error("문제가 발생했습니다: 잘못된 값입니다")

    out = capsys.readouterr().out
    assert "문제가 발생했습니다: 잘못된 값입니다" in out
