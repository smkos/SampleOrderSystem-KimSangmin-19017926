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
