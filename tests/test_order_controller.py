import datetime as datetime_module

import pytest

from controller.order_controller import OrderController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def test_등록되지_않은_시료ID로_주문하면_거부한다(mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    controller = OrderController(OrderRegistry(), SampleRegistry())

    with pytest.raises(ValueError):
        controller.create_order("S-999", "삼성전자 파운드리", 200)


def test_등록된_시료ID면_RESERVED_상태의_주문이_생성된다(mocker):
    mocker.patch(
        "model.order_registry.datetime"
    ).datetime.now.return_value = datetime_module.datetime(2026, 7, 15, 9, 32, 15)
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    controller = OrderController(OrderRegistry(), sample_registry)

    order = controller.create_order("S-001", "삼성전자 파운드리", 200)

    assert order.sample_id == "S-001"
    assert order.status == OrderStatus.RESERVED
