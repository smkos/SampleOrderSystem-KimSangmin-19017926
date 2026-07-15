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
