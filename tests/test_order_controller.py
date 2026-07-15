import datetime as datetime_module

import pytest

from controller.order_controller import OrderController
from controller.production_controller import ProductionController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry
from storage.order_repository import OrderRepository
from storage.sample_repository import SampleRepository


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def _controller(tmp_path, sample_registry):
    return OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )


def test_생성시_주문_저장소의_기존_주문을_레지스트리에_불러온다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    seed_controller = _controller(tmp_path, sample_registry)
    seed_controller.create_order("S-001", "삼성전자 파운드리", 200)

    restarted = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )

    assert len(restarted.list_orders()) == 1


def test_주문_생성에_성공하면_주문_저장소에도_반영된다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = _controller(tmp_path, sample_registry)

    controller.create_order("S-001", "삼성전자 파운드리", 200)

    reloaded = OrderRepository(tmp_path / "orders.json").load()
    assert len(reloaded) == 1


def test_승인시_재고가_예약되면_주문저장소와_시료저장소_모두_반영된다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    sample_repo_path = tmp_path / "samples.json"
    SampleRepository(sample_repo_path).save(sample_registry.list_all())
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(sample_repo_path),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    controller.approve_order(order.order_id)

    reloaded_orders = OrderRepository(tmp_path / "orders.json").load()
    reloaded_samples = SampleRepository(sample_repo_path).load()
    assert reloaded_orders[0].status.value == "CONFIRMED"
    assert reloaded_samples[0].stock_qty == 280  # 480 - 200 즉시 예약, 파일에도 반영


def test_주문_생성_검증에_실패하면_저장소를_변경하지_않는다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = _controller(tmp_path, sample_registry)

    with pytest.raises(ValueError):
        controller.create_order("S-001", "   ", 200)  # 공백 고객명 → 거부

    reloaded = OrderRepository(tmp_path / "orders.json").load()
    assert reloaded == []  # 실패 시 파일 변경 없음


def test_등록되지_않은_시료ID로_주문하면_거부한다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    controller = OrderController(
        OrderRegistry(),
        SampleRegistry(),
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )

    with pytest.raises(ValueError):
        controller.create_order("S-999", "삼성전자 파운드리", 200)


def test_등록된_시료ID면_RESERVED_상태의_주문이_생성된다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )

    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    assert order.sample_id == "S-001"
    assert order.status == OrderStatus.RESERVED


def test_재고가_충분하면_승인시_즉시_예약되어_재고가_감소한다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    approved = controller.approve_order(order.order_id)

    assert approved.status == OrderStatus.CONFIRMED
    assert sample_registry.search("S-001")[0].stock_qty == 280  # 480 - 200 즉시 예약


def test_거절하면_REJECTED로_전환된다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    rejected = controller.reject_order(order.order_id)

    assert rejected.status == OrderStatus.REJECTED


def test_출고해도_재고는_변하지_않는다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)
    controller.approve_order(order.order_id)  # CONFIRMED, 이미 200 예약됨 (280 남음)

    released = controller.release_order(order.order_id)

    assert released.status == OrderStatus.RELEASE
    assert sample_registry.search("S-001")[0].stock_qty == 280  # 출고 전후 변화 없음


def test_CONFIRMED가_아닌_주문을_출고처리하면_예외가_발생하고_재고가_바뀌지_않는다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)
    controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING

    with pytest.raises(ValueError):
        controller.release_order(order.order_id)
    assert sample_registry.search("S-001")[0].stock_qty == 50


def test_재고가_부족하면_승인시_PRODUCING이_되고_재고는_그대로다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    controller = OrderController(
        OrderRegistry(),
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    approved = controller.approve_order(order.order_id)

    assert approved.status == OrderStatus.PRODUCING
    assert sample_registry.search("S-001")[0].stock_qty == 50  # 예약하지 않음, 그대로


def test_두_CONFIRMED_주문을_순서대로_출고해도_둘_다_성공한다(tmp_path, mocker):
    """승인 시점 예약 덕분에, 두 주문 수량의 합(350)이 원래 재고(300)를 초과해도 경쟁
    상황 없이 둘 다 정상적으로 CONFIRMED를 거쳐 출고에 성공함을 증명하는 회귀 테스트.

    재설계 이전(승인 시 재고를 확인만 하고 차감하지 않는) 구현에서는 주문 B 승인 시점에
    재고가 여전히 300으로 보여 150 <= 300이 성립하므로 B가 곧바로 CONFIRMED가 되고, 이후
    complete_production(order_b)이 PRODUCING 상태가 아닌 주문을 대상으로 호출되어
    ValueError가 발생해 이 테스트가 실패한다. 재설계 이후 구현에서는 A가 예약한 뒤 재고가
    100으로 줄어 150 > 100이 되어 B가 PRODUCING으로 전환되고, 생산완료 처리를 거쳐
    CONFIRMED가 되어 두 주문 모두 정상적으로 출고된다."""
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 1.0, 300))
    order_registry = OrderRegistry()
    order_repository = OrderRepository(tmp_path / "orders.json")
    sample_repository = SampleRepository(tmp_path / "samples.json")
    controller = OrderController(
        order_registry,
        sample_registry,
        order_repository,
        sample_repository,
    )
    order_a = controller.create_order("S-001", "삼성전자 파운드리", 200)  # 300 >= 200, 승인 가능
    controller.approve_order(order_a.order_id)  # CONFIRMED, 재고 300 -> 100 즉시 예약
    order_b = controller.create_order("S-001", "SK하이닉스", 150)  # 100 < 150, 재고 부족
    approved_b = controller.approve_order(order_b.order_id)  # PRODUCING, 재고 100 그대로
    assert approved_b.status == OrderStatus.PRODUCING

    production_controller = ProductionController(
        order_registry,
        sample_registry,
        order_repository,
        sample_repository,
    )
    production_controller.complete_production(order_b.order_id)  # PRODUCING -> CONFIRMED
    # shortage = 150 - 100 = 50, actual_qty = ceil(50 / 1.0) = 50
    # 재고 100 -> 150(생산 반영) -> 0(주문 B 몫 예약)

    released_a = controller.release_order(order_a.order_id)
    released_b = controller.release_order(order_b.order_id)

    assert released_a.status == OrderStatus.RELEASE
    assert released_b.status == OrderStatus.RELEASE
    assert sample_registry.search("S-001")[0].stock_qty == 0


def test_접수된_주문만_걸러서_조회한다(tmp_path, mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 0, 0)
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
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 0, 0)
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
