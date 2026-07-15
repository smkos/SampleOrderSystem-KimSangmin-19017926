from model.order import Order, OrderStatus

_COUNTED_STATUSES = [
    OrderStatus.RESERVED,
    OrderStatus.CONFIRMED,
    OrderStatus.PRODUCING,
    OrderStatus.RELEASE,
]


def count_orders_by_status(orders: list[Order]) -> dict[OrderStatus, int]:
    counts = {status: 0 for status in _COUNTED_STATUSES}
    for order in orders:
        if order.status in counts:
            counts[order.status] += 1
    return counts


def sum_pending_order_qty(orders: list[Order], sample_id: str) -> int:
    return sum(
        order.quantity for order in orders
        if order.sample_id == sample_id and order.status == OrderStatus.RESERVED
    )


def calculate_stock_status_label(stock_qty: int, pending_order_qty: int) -> str:
    if stock_qty == 0:
        return "고갈"
    if stock_qty < pending_order_qty:
        return "부족"
    return "여유"
