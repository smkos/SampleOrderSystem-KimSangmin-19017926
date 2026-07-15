import datetime

from model.order import Order, OrderStatus


class OrderRegistry:
    """주문을 인메모리로 보관하고, 생성 시 검증과 ID 채번을 수행한다."""

    def __init__(self):
        self._orders: list[Order] = []

    def create(self, sample_id: str, customer_name: str, quantity: int) -> Order:
        if not customer_name.strip():
            raise ValueError("고객명은 공백일 수 없습니다.")
        if quantity <= 0:
            raise ValueError("주문 수량은 0보다 커야 합니다.")

        now = datetime.datetime.now()
        date_prefix = now.strftime("%Y%m%d")
        order_id_prefix = f"ORD-{date_prefix}-"
        existing_count = sum(
            1 for order in self._orders if order.order_id.startswith(order_id_prefix)
        )
        order_id = f"{order_id_prefix}{existing_count + 1:04d}"
        created_at = now.isoformat()

        order = Order(order_id, sample_id, customer_name, quantity, OrderStatus.RESERVED, created_at)
        self._orders.append(order)
        return order

    def list_all(self) -> list[Order]:
        return list(self._orders)
