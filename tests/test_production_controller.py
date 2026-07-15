import datetime as datetime_module
import math

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


def test_생산완료_처리하면_주문저장소와_시료저장소_모두_반영된다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    order_registry = OrderRegistry()
    orders_path = tmp_path / "orders.json"
    samples_path = tmp_path / "samples.json"
    order_controller = OrderController(
        order_registry, sample_registry,
        OrderRepository(orders_path), SampleRepository(samples_path),
    )
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING

    production_controller = ProductionController(
        order_registry, sample_registry,
        OrderRepository(orders_path), SampleRepository(samples_path),
    )
    production_controller.complete_production(order.order_id)

    reloaded_orders = OrderRepository(orders_path).load()
    reloaded_samples = SampleRepository(samples_path).load()
    assert reloaded_orders[0].status.value == "CONFIRMED"
    # shortage = 200 - 50 = 150, actual_qty = ceil(150 / 0.92) = 164, 순증가 = 164 - 150 = 14
    assert reloaded_samples[0].stock_qty == 14


def test_생산완료_처리하면_재고가_실생산량에서_주문수량을_뺀_만큼만_순증가한다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))
    order_registry = OrderRegistry()
    order_controller = OrderController(
        order_registry,
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 50 < 200 → PRODUCING (재고 변화 없음)

    production_controller = ProductionController(
        order_registry,
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    completed = production_controller.complete_production(order.order_id)

    assert completed.status == OrderStatus.CONFIRMED
    shortage = 200 - 50
    actual_qty = math.ceil(shortage / 0.92)  # 164
    expected_stock = 50 + actual_qty - 200  # 순증가 = actual_qty - shortage = 14
    updated_sample = sample_registry.search("S-001")[0]
    assert updated_sample.stock_qty == expected_stock


def test_PRODUCING이_아닌_주문을_생산완료_처리하면_예외가_발생하고_재고가_바뀌지_않는다(tmp_path, mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    sample_registry = SampleRegistry()
    sample_registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    order_registry = OrderRegistry()
    order_controller = OrderController(
        order_registry,
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )
    order = order_controller.create_order("S-001", "삼성전자 파운드리", 200)
    order_controller.approve_order(order.order_id)  # 재고 480 >= 200 → CONFIRMED, 즉시 예약되어 280

    production_controller = ProductionController(
        order_registry,
        sample_registry,
        OrderRepository(tmp_path / "orders.json"),
        SampleRepository(tmp_path / "samples.json"),
    )

    with pytest.raises(ValueError):
        production_controller.complete_production(order.order_id)
    assert sample_registry.search("S-001")[0].stock_qty == 280
