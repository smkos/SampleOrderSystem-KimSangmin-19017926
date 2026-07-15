import datetime as datetime_module

from controller.monitoring_controller import MonitoringController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_주문이_없으면_모든_상태의_집계는_0건이다():
    controller = MonitoringController(OrderRegistry(), SampleRegistry())

    counts = controller.count_orders_by_status()

    assert counts == {
        OrderStatus.RESERVED: 0,
        OrderStatus.CONFIRMED: 0,
        OrderStatus.PRODUCING: 0,
        OrderStatus.RELEASE: 0,
    }


def test_실제_주문registry의_상태별_주문수를_집계한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    order_registry = OrderRegistry()
    order_registry.create("S-001", "삼성전자 파운드리", 100)  # RESERVED
    reserved_to_reject = order_registry.create("S-001", "삼성전자 파운드리", 100)
    order_registry.reject(reserved_to_reject.order_id)  # REJECTED, 집계 제외

    controller = MonitoringController(order_registry, sample_registry)
    counts = controller.count_orders_by_status()

    assert counts[OrderStatus.RESERVED] == 1
    assert OrderStatus.REJECTED not in counts


def test_시료별_재고상태_라벨을_계산한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    sample_registry.register(Sample("S-002", "GaN 파워칩", 1.2, 0.88, 0))
    order_registry = OrderRegistry()
    order_registry.create("S-001", "삼성전자 파운드리", 100)  # RESERVED, S-001 미승인 총수량 100

    controller = MonitoringController(order_registry, sample_registry)
    labels = controller.stock_status_by_sample()

    assert labels["S-001"] == "부족"  # 재고 50 < 미승인 100
    assert labels["S-002"] == "고갈"  # 재고 0
