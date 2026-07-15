from model.order import Order
from model.order_registry import OrderRegistry
from model.sample_registry import SampleRegistry


class OrderController:
    """OrderRegistry와 SampleRegistry를 연결해 주문 접수를 처리한다."""

    def __init__(self, order_registry: OrderRegistry, sample_registry: SampleRegistry):
        self._order_registry = order_registry
        self._sample_registry = sample_registry

    def create_order(self, sample_id: str, customer_name: str, quantity: int) -> Order:
        if not any(sample.sample_id == sample_id for sample in self._sample_registry.list_all()):
            raise ValueError(f"존재하지 않는 시료 ID입니다: {sample_id}")
        return self._order_registry.create(sample_id, customer_name, quantity)
