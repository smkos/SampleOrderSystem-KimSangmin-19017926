from model import production_queue
from model.order import Order
from model.order_registry import OrderRegistry
from model.sample_registry import SampleRegistry


class ProductionController:
    """OrderRegistry와 SampleRegistry를 연결해 생산 완료 처리를 수행한다."""

    def __init__(self, order_registry: OrderRegistry, sample_registry: SampleRegistry):
        self._order_registry = order_registry
        self._sample_registry = sample_registry

    def complete_production(self, order_id: str) -> Order:
        order = self._order_registry.complete_production(order_id)
        sample = next(
            sample for sample in self._sample_registry.list_all()
            if sample.sample_id == order.sample_id
        )
        shortage = production_queue.calculate_shortage(order.quantity, sample.stock_qty)
        actual_qty = production_queue.calculate_actual_production_qty(shortage, sample.yield_rate)
        self._sample_registry.increase_stock(sample.sample_id, actual_qty)
        self._sample_registry.decrease_stock(sample.sample_id, order.quantity)
        return order
