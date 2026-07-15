from model.monitoring import (
    calculate_stock_status_label,
    count_orders_by_status,
    sum_pending_order_qty,
)
from model.order import Order, OrderStatus


def _order(order_id, sample_id, status, quantity=100):
    return Order(order_id, sample_id, "삼성전자 파운드리", quantity, status, "2026-07-15T09:32:15")


def test_상태별_주문수를_센다():
    orders = [
        _order("ORD-1", "S-001", OrderStatus.RESERVED),
        _order("ORD-2", "S-001", OrderStatus.RESERVED),
        _order("ORD-3", "S-001", OrderStatus.CONFIRMED),
        _order("ORD-4", "S-001", OrderStatus.PRODUCING),
        _order("ORD-5", "S-001", OrderStatus.RELEASE),
        _order("ORD-6", "S-001", OrderStatus.REJECTED),
    ]

    counts = count_orders_by_status(orders)

    assert counts == {
        OrderStatus.RESERVED: 2,
        OrderStatus.CONFIRMED: 1,
        OrderStatus.PRODUCING: 1,
        OrderStatus.RELEASE: 1,
    }


def test_REJECTED_주문은_상태별_집계에서_완전히_제외된다():
    orders = [_order("ORD-1", "S-001", OrderStatus.REJECTED)]

    counts = count_orders_by_status(orders)

    assert OrderStatus.REJECTED not in counts
    assert counts[OrderStatus.RESERVED] == 0


def test_특정_시료를_참조하는_RESERVED_주문_수량을_합산한다():
    orders = [
        _order("ORD-1", "S-001", OrderStatus.RESERVED, quantity=100),
        _order("ORD-2", "S-001", OrderStatus.RESERVED, quantity=50),
        _order("ORD-3", "S-001", OrderStatus.CONFIRMED, quantity=999),  # 미승인 아님 → 제외
        _order("ORD-4", "S-002", OrderStatus.RESERVED, quantity=999),  # 다른 시료 → 제외
    ]

    assert sum_pending_order_qty(orders, "S-001") == 150


def test_참조하는_RESERVED_주문이_없으면_미승인_수량은_0이다():
    orders = [_order("ORD-1", "S-002", OrderStatus.RESERVED, quantity=100)]

    assert sum_pending_order_qty(orders, "S-001") == 0


def test_재고가_0이면_고갈이다():
    assert calculate_stock_status_label(stock_qty=0, pending_order_qty=0) == "고갈"


def test_재고가_미승인_주문_총수량보다_적으면_부족이다():
    assert calculate_stock_status_label(stock_qty=50, pending_order_qty=100) == "부족"


def test_재고가_미승인_주문_총수량_이상이면_여유이다():
    assert calculate_stock_status_label(stock_qty=100, pending_order_qty=100) == "여유"
