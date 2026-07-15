from model import production_queue
from model.order import Order
from model.order_registry import OrderRegistry
from model.sample_registry import SampleRegistry
from storage.order_repository import OrderRepository
from storage.sample_repository import SampleRepository


class ProductionController:
    """OrderRegistry와 SampleRegistry를 연결해 생산 완료 처리를 수행한다."""

    def __init__(
        self,
        order_registry: OrderRegistry,
        sample_registry: SampleRegistry,
        order_repository: OrderRepository,
        sample_repository: SampleRepository,
    ):
        self._order_registry = order_registry
        self._sample_registry = sample_registry
        self._order_repository = order_repository
        self._sample_repository = sample_repository

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
        self._order_repository.save(self._order_registry.list_all())
        self._sample_repository.save(self._sample_registry.list_all())
        return order

    def list_production_queue(self) -> list:
        return production_queue.sort_production_queue(self._order_registry.list_all())

    def current_production_order(self):
        queue = self.list_production_queue()
        return queue[0] if queue else None
