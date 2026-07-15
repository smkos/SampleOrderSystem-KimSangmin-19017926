import math

from model.order import Order, OrderStatus
from model.production_queue import (
    calculate_actual_production_qty,
    calculate_shortage,
    calculate_total_production_time_min,
    sort_production_queue,
)


def test_주문수량이_재고보다_많으면_부족분은_차이값이다():
    assert calculate_shortage(quantity=200, stock_qty=50) == 150


def test_주문수량이_재고이하이면_부족분은_0이다():
    assert calculate_shortage(quantity=30, stock_qty=50) == 0


def test_실_생산량은_부족분을_수율로_나눈_뒤_올림한다():
    shortage = 150
    yield_rate = 0.92

    actual_qty = calculate_actual_production_qty(shortage, yield_rate)

    assert actual_qty == math.ceil(150 / 0.92)  # 164


def test_부족분이_0이면_실_생산량도_0이다():
    assert calculate_actual_production_qty(shortage=0, yield_rate=0.92) == 0


def test_총_생산_시간은_평균_생산시간과_실_생산량의_곱이다():
    total_time = calculate_total_production_time_min(
        avg_production_time_min=0.5, actual_production_qty=164
    )

    assert total_time == 82.0


def _order(order_id, status, created_at):
    return Order(order_id, "S-001", "삼성전자 파운드리", 100, status, created_at)


def test_생산큐는_PRODUCING_상태만_created_at_오름차순으로_정렬한다():
    later = _order("ORD-20260715-0003", OrderStatus.PRODUCING, "2026-07-15T11:00:00")
    earlier = _order("ORD-20260715-0001", OrderStatus.PRODUCING, "2026-07-15T09:00:00")
    not_producing = _order("ORD-20260715-0002", OrderStatus.CONFIRMED, "2026-07-15T08:00:00")

    queue = sort_production_queue([later, not_producing, earlier])

    assert [order.order_id for order in queue] == [earlier.order_id, later.order_id]


def test_생산큐_정렬은_원본_리스트를_변경하지_않는다():
    order_a = _order("ORD-20260715-0001", OrderStatus.PRODUCING, "2026-07-15T09:00:00")
    order_b = _order("ORD-20260715-0002", OrderStatus.PRODUCING, "2026-07-15T08:00:00")
    orders = [order_a, order_b]

    sort_production_queue(orders)

    assert orders == [order_a, order_b]
