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

    def restore(self, orders: list[Order]) -> None:
        self._orders = list(orders)

    def get(self, order_id: str) -> Order:
        for order in self._orders:
            if order.order_id == order_id:
                return order
        raise ValueError(f"존재하지 않는 주문 ID입니다: {order_id}")

    def approve(self, order_id: str, stock_sufficient: bool) -> Order:
        order = self.get(order_id)
        if order.status != OrderStatus.RESERVED:
            raise ValueError(f"RESERVED 상태의 주문만 승인할 수 있습니다: {order_id}")
        order.status = OrderStatus.CONFIRMED if stock_sufficient else OrderStatus.PRODUCING
        return order

    def reject(self, order_id: str) -> Order:
        order = self.get(order_id)
        if order.status != OrderStatus.RESERVED:
            raise ValueError(f"RESERVED 상태의 주문만 거절할 수 있습니다: {order_id}")
        order.status = OrderStatus.REJECTED
        return order

    def complete_production(self, order_id: str) -> Order:
        order = self.get(order_id)
        if order.status != OrderStatus.PRODUCING:
            raise ValueError(f"PRODUCING 상태의 주문만 생산완료 처리할 수 있습니다: {order_id}")
        order.status = OrderStatus.CONFIRMED
        return order

    def release(self, order_id: str) -> Order:
        order = self.get(order_id)
        if order.status != OrderStatus.CONFIRMED:
            raise ValueError(f"CONFIRMED 상태의 주문만 출고 처리할 수 있습니다: {order_id}")
        order.status = OrderStatus.RELEASE
        return order
