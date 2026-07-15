import datetime as datetime_module
import math

import pytest

from controller.order_controller import OrderController
from controller.production_controller import ProductionController
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample import Sample
from model.sample_registry import SampleRegistry


def _mock_now(mocker, fixed_datetime):
    mocker.patch("model.order_registry.datetime").datetime.now.return_value = fixed_datetime


def test_생산완료_처리하면_주문상태가_CONFIRMED로_전환되고_재고가_실생산량만큼_증가한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    order_registry = OrderRegistry()
    order_controller = OrderController(order_registry, sample_registry)
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING

    production_controller = ProductionController(order_registry, sample_registry)
    completed = production_controller.complete_production(order.order_id)

    assert completed.status == OrderStatus.CONFIRMED
    expected_actual_qty = math.ceil((200 - 50) / 0.92)  # shortage=150 → 164
    updated_sample = sample_registry.search("S-001")[0]
    assert updated_sample.stock_qty == 50 + expected_actual_qty


def test_PRODUCING이_아닌_주문을_생산완료_처리하면_예외가_발생하고_재고가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    order_registry = OrderRegistry()
    order_controller = OrderController(order_registry, sample_registry)
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 480 >= 200 → CONFIRMED

    production_controller = ProductionController(order_registry, sample_registry)

    with pytest.raises(ValueError):
        production_controller.complete_production(order.order_id)
    assert sample_registry.search("S-001")[0].stock_qty == 480
