import datetime as datetime_module

import pytest

from model.order import OrderStatus
from model.order_registry import OrderRegistry


def _mock_now(mocker, fixed_datetime):
    mock_datetime = mocker.patch("model.order_registry.datetime")
    mock_datetime.datetime.now.return_value = fixed_datetime


def test_생성된_주문은_RESERVED_상태이다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    order = registry.create("S-001", "삼성전자 파운드리", 200)

    assert order.status == OrderStatus.RESERVED


def test_주문_ID는_ORD_날짜_4자리_일련번호_형식이다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    order = registry.create("S-001", "삼성전자 파운드리", 200)

    assert order.order_id == "ORD-20260715-0001"


def test_같은_날_두번째_주문은_일련번호가_증가한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    registry.create("S-001", "삼성전자 파운드리", 200)

    second = registry.create("S-002", "SK하이닉스", 50)

    assert second.order_id == "ORD-20260715-0002"


def test_고객명이_공백만_있으면_거부한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.create("S-001", "   ", 200)


def test_수량이_0이하이면_거부한다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.create("S-001", "삼성전자 파운드리", 0)


def test_재고가_충분하면_승인시_CONFIRMED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)

    approved = registry.approve(order.order_id, stock_sufficient=True)

    assert approved.status == OrderStatus.CONFIRMED


def test_재고가_부족하면_승인시_PRODUCING으로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)

    approved = registry.approve(order.order_id, stock_sufficient=False)

    assert approved.status == OrderStatus.PRODUCING


def test_거절하면_REJECTED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)

    rejected = registry.reject(order.order_id)

    assert rejected.status == OrderStatus.REJECTED


def test_RESERVED가_아닌_주문을_승인하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.reject(order.order_id)

    with pytest.raises(ValueError):
        registry.approve(order.order_id, stock_sufficient=True)
    assert registry.get(order.order_id).status == OrderStatus.REJECTED


def test_RESERVED가_아닌_주문을_거절하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=True)

    with pytest.raises(ValueError):
        registry.reject(order.order_id)
    assert registry.get(order.order_id).status == OrderStatus.CONFIRMED


def test_존재하지_않는_주문ID를_승인하면_예외가_발생한다():
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.approve("ORD-20260715-9999", stock_sufficient=True)


def test_PRODUCING_주문을_생산완료_처리하면_CONFIRMED로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=False)

    completed = registry.complete_production(order.order_id)

    assert completed.status == OrderStatus.CONFIRMED


def test_PRODUCING이_아닌_주문을_생산완료_처리하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=True)  # CONFIRMED로 전환됨

    with pytest.raises(ValueError):
        registry.complete_production(order.order_id)
    assert registry.get(order.order_id).status == OrderStatus.CONFIRMED


def test_존재하지_않는_주문ID를_생산완료_처리하면_예외가_발생한다():
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.complete_production("ORD-20260715-9999")


def test_CONFIRMED_주문을_출고처리하면_RELEASE로_전환된다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=True)  # CONFIRMED

    released = registry.release(order.order_id)

    assert released.status == OrderStatus.RELEASE


def test_CONFIRMED가_아닌_주문을_출고처리하면_예외가_발생하고_상태가_바뀌지_않는다(mocker):
    _mock_now(mocker, datetime_module.datetime(2026, 7, 15, 9, 32, 15))
    registry = OrderRegistry()
    order = registry.create("S-001", "삼성전자 파운드리", 200)
    registry.approve(order.order_id, stock_sufficient=False)  # PRODUCING

    with pytest.raises(ValueError):
        registry.release(order.order_id)
    assert registry.get(order.order_id).status == OrderStatus.PRODUCING


def test_존재하지_않는_주문ID를_출고처리하면_예외가_발생한다():
    registry = OrderRegistry()

    with pytest.raises(ValueError):
        registry.release("ORD-20260715-9999")
